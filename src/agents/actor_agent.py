"""Actor Agent - реализация агента с использованием Actor Framework."""

import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

import aiofiles

from src.agents.base import BaseAgent
from src.agents.safety_agent import SafetyAgent
from src.agents.sub_agent import SubAgent
from src.context.manager import ContextManager
from src.executor.command import CommandExecutor
from src.executor.web_search import WebSearchExecutor
from src.llm.providers.base import LLMProvider
from src.utils.logging import get_logger
from src.actors.base import Actor
from src.actors.system import ActorSystem
from src.actors.message import ActorMessage, MessageType, ExecuteCommand, WebSearchQuery
from src.actors.actors.command_actor import CommandActor
from src.actors.actors.web_search_actor import WebSearchActor


class ActorAgent(Actor, BaseAgent):
    """Агент, реализованный с использованием Actor Framework."""
    
    def __init__(
        self,
        provider: LLMProvider,
        on_progress: Optional[Callable[[str], Any]] = None,
        context_manager: Optional[ContextManager] = None,
        command_executor: Optional[CommandExecutor] = None,
        safety_agent: Optional[SafetyAgent] = None,
        web_search_executor: Optional[WebSearchExecutor] = None,
        actor_id: str = None
    ):
        """Инициализация агента-актора."""
        # Инициализация Actor
        Actor.__init__(self, actor_id)
        
        # Инициализация BaseAgent
        BaseAgent.__init__(self, provider, on_progress)
        
        # Компоненты
        self.context_manager = context_manager or ContextManager()
        self.command_executor = command_executor or CommandExecutor()
        self.safety_agent = safety_agent or SafetyAgent()
        self.web_search_executor = web_search_executor or WebSearchExecutor()
        
        self.logger = get_logger(self.__class__.__name__)

    def spawn_subagent(self, system_prompt: str = None) -> SubAgent:
        """Создание SubAgent для делегирования задач.
        
        Args:
            system_prompt: Системный промпт для SubAgent
            
        Returns:
            Созданный SubAgent
        """
        sub_agent = SubAgent(
            provider=self.provider,
            system_prompt=system_prompt or "You are a helpful assistant specialized in completing delegated tasks."
        )
        return sub_agent

    async def run(
        self, 
        user_input: str, 
        history: list[dict[str, str]], 
        user_id: Optional[int] = None,
        user_dir: Optional[Path] = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """Обработка запроса пользователя с поддержкой инструментов через акторы."""
        self.logger.info("actor_agent_run", user_id=user_id, user_input=user_input[:50])
        
        # Загрузка истории из JSONL если есть
        user_history_context = ""
        if user_dir:
            history_path = user_dir / "history.jsonl"
            if history_path.exists():
                try:
                    async with aiofiles.open(history_path, "r", encoding="utf-8") as f:
                        lines = await f.readlines()
                        # Берем последние 20 записей для контекста
                        last_lines = lines[-20:]
                        user_history_context = "\n".join([line.strip() for line in last_lines])
                except Exception as e:
                    self.logger.error("history_load_error", error=str(e))

        # 1. Подготовка системного промпта
        soul_path = f"data/users/{user_id}/soul.md" if user_id else "context/memory/soul.md"
        user_md_path = f"data/users/{user_id}/user.md" if user_id else "context/memory/user.md"
        
        base_system_prompt = (
            f"You are an autonomous AI agent for User {user_id}. "
            f"You have access to your internal 'soul' and 'user' memory files:\n"
            f"1. 'soul.md': {soul_path} - Your identity and behavior.\n"
            f"2. 'user.md': {user_md_path} - Knowledge about the user.\n"
            "3. Archived topics: You can find summaries of previous discussions in 'archives/*.md' files within your context.\n\n"
            "You can update memory files using 'run_command' (e.g., echo \"...\" > path/to/file).\n"
            "Always explain what you are going to do before running a command."
        )
        
        if user_history_context:
            base_system_prompt += f"\n\nRecent raw message history for context:\n{user_history_context}"
            
        full_system_prompt = await self.context_manager.get_system_prompt_with_context(base_system_prompt, user_dir=user_dir)
        
        # 2. Формирование сообщений для LLM (не включая новый user_input еще)
        messages = [{"role": "system", "content": full_system_prompt}]
        for msg in history:
            if msg["role"] != "system":
                # Убеждаемся что передаем только нужные поля
                cleaned_msg = {"role": msg["role"], "content": msg.get("content")}
                if msg.get("tool_calls"):
                    cleaned_msg["tool_calls"] = msg["tool_calls"]
                if msg.get("tool_call_id"):
                    cleaned_msg["tool_call_id"] = msg["tool_call_id"]
                messages.append(cleaned_msg)
        
        messages.append({"role": "user", "content": user_input})
        
        new_messages = [] # Только те сообщения, которые мы создали в этом запуске
        
        # Определение инструментов
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute a shell command and get its output",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the internet for information using DuckDuckGo",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_task",
                    "description": "Delegate a complex task to a sub-agent for parallel or specialized processing",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "The task to delegate to the sub-agent"
                            }
                        },
                        "required": ["task"]
                    }
                }
            }
        ]
        
        # Основной цикл обработки (макс. 5 итераций для инструментов)
        for i in range(5):
            await self.notify("🤖 Думаю...")
            
            # Конвертируем сообщения в LLMMessage
            llm_messages = self.provider.format_messages(messages)
            
            # Запрос к LLM
            response = await self.provider.generate(llm_messages, tools=tools)
            
            # Если нет вызовов инструментов, возвращаем текст
            if not response.tool_calls:
                new_messages.append({"role": "assistant", "content": response.content})
                return response.content, new_messages
            
            # Обработка вызовов инструментов
            assistant_msg = {"role": "assistant", "content": response.content, "tool_calls": response.tool_calls}
            messages.append(assistant_msg)
            new_messages.append(assistant_msg)
            
            async def handle_tool_call(tool_call):
                tool_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])

                if tool_name == "run_command":
                    command = args.get("command", "")
                    await self.notify("🛠️ Вызываю субагента для выполнения задачи...")
                    
                    # Создаем актора для выполнения команды
                    command_actor = CommandActor(
                        safety_agent=self.safety_agent,
                        executor=self.command_executor
                    )
                    await self.spawn_child(command_actor)
                    
                    # Отправляем сообщение актору и ждем ответ
                    result = await command_actor.ask(ActorMessage(
                        id=f"cmd_{uuid4().hex[:8]}",
                        sender=self.actor_id,
                        recipient=command_actor.actor_id,
                        payload=ExecuteCommand(command=command),
                        message_type=MessageType.EXECUTE_COMMAND,
                        reply_to=self.actor_id
                    ))
                    
                    if result.payload.success:
                        result_content = f"Exit code: {result.payload.data['exit_code']}\nSTDOUT: {result.payload.data['stdout']}\nSTDERR: {result.payload.data['stderr']}"
                        if result.payload.data.get('timeout'):
                            result_content += "\nNote: Command timed out."
                    else:
                        result_content = f"Error: {result.payload.error}"

                elif tool_name == "web_search":
                    query = args.get("query", "")
                    await self.notify(f"🌐 Ищу в интернете: {query}...")
                    
                    # Создаем актора для веб-поиска
                    search_actor = WebSearchActor(executor=self.web_search_executor)
                    await self.spawn_child(search_actor)
                    
                    # Отправляем сообщение актору и ждем ответ
                    result = await search_actor.ask(ActorMessage(
                        id=f"search_{uuid4().hex[:8]}",
                        sender=self.actor_id,
                        recipient=search_actor.actor_id,
                        payload=WebSearchQuery(query=query),
                        message_type=MessageType.WEB_SEARCH,
                        reply_to=self.actor_id
                    ))
                    
                    if result.payload.success:
                        result_content = json.dumps(result.payload.data['results'], ensure_ascii=False, indent=2)
                    else:
                        result_content = f"Error: {result.payload.error}"
                
                elif tool_name == "delegate_task":
                    task = args.get("task", "")
                    await self.notify("🤝 Делегирую задачу суб-агенту...")
                    
                    # Создаём SubAgent
                    sub_agent = self.spawn_subagent()
                    await self.spawn_child(sub_agent)
                    
                    # Отправляем задачу суб-агенту и ждём ответ
                    result = await sub_agent.ask(ActorMessage(
                        id=f"delegate_{uuid4().hex[:8]}",
                        sender=self.actor_id,
                        recipient=sub_agent.actor_id,
                        payload={"task": task},
                        message_type=MessageType.DELEGATE_TASK,
                        reply_to=self.actor_id
                    ))
                    
                    # Извлекаем результат
                    if result.payload.get("success"):
                        result_content = result.payload.get("result", "No response")
                    else:
                        result_content = f"Error: {result.payload.get('error', 'Unknown error')}"
                
                else:
                    result_content = f"Error: Unknown tool '{tool_name}'"
                
                return {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": result_content
                }

            # Выполняем все вызовы инструментов параллельно
            tool_results = await asyncio.gather(*[handle_tool_call(tc) for tc in response.tool_calls])
            
            for tool_msg in tool_results:
                messages.append(tool_msg)
                new_messages.append(tool_msg)
        
        return "Извините, я зациклился при выполнении команд.", new_messages

    async def receive(self, message):
        """Обработка входящих сообщений от других акторов."""
        # В данной реализации агент-актор может получать результаты от своих дочерних акторов
        if message.message_type == "child_result":
            self.logger.info("received_child_result", actor_id=message.sender)
        elif message.message_type == "child_error":
            self.logger.error("received_child_error", actor_id=message.sender, error=message.payload.get('error'))
        else:
            self.logger.warning("unknown_message_type", message_type=message.message_type)