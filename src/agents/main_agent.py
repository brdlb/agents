"""Main Agent - основной агент системы с поддержкой выполнения команд."""

import json
from pathlib import Path
from typing import Any, Callable, Optional

import aiofiles

from src.agents.base import BaseAgent
from src.agents.safety_agent import SafetyAgent
from src.agents.context_agent import ContextAgent
from src.context.manager import ContextManager
from src.executor.command import CommandExecutor
from src.executor.web_search import WebSearchExecutor
from src.llm.providers.base import LLMProvider, LLMMessage
from src.utils.logging import get_logger
from src.utils.prompts import load_prompt_with_context

logger = get_logger(__name__)


class MainAgent(BaseAgent):
    """Главный агент, координирующий работу и выполняющий команды."""

    def __init__(
        self,
        provider: LLMProvider,
        on_progress: Optional[Callable[[str], Any]] = None,
        context_manager: Optional[ContextManager] = None,
        command_executor: Optional[CommandExecutor] = None,
        safety_agent: Optional[SafetyAgent] = None,
        web_search_executor: Optional[WebSearchExecutor] = None
    ):
        """Инициализация главного агента."""
        super().__init__(provider, on_progress)
        self.context_manager = context_manager or ContextManager()
        self.command_executor = command_executor or CommandExecutor()
        self.safety_agent = safety_agent or SafetyAgent()
        self.web_search_executor = web_search_executor or WebSearchExecutor()
        self.context_agent = ContextAgent(provider)

    async def run(
        self, 
        user_input: str, 
        history: list[dict[str, str]], 
        user_id: Optional[int] = None,
        user_dir: Optional[Path] = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """Обработка запроса пользователя с поддержкой инструментов."""
        logger.info("main_agent_run", user_id=user_id, user_input=user_input[:50])
        
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
                    logger.error("history_load_error", error=str(e))

        # 1. Подготовка системного промпта из файла
        soul_path = f"data/users/{user_id}/soul.md" if user_id else "context/memory/soul.md"
        user_md_path = f"data/users/{user_id}/user.md" if user_id else "context/memory/user.md"
        
        # Формируем контекст для подстановки в промт
        context = {
            "user_id": str(user_id) if user_id else "unknown",
            "soul_path": soul_path,
            "user_md_path": user_md_path,
            "history_context": f"\n\nRecent raw message history for context:\n{user_history_context}" if user_history_context else ""
        }
        
        base_system_prompt = load_prompt_with_context(
            "agent.md",
            context,
            # Fallback - если файл не найден
            f"You are an autonomous AI agent for User {user_id}. "
            f"You have access to your internal 'soul' and 'user' memory files:\n"
            f"1. 'soul.md': {soul_path} - Your identity and behavior.\n"
            f"2. 'user.md': {user_md_path} - Knowledge about the user.\n"
            "3. Archived topics: You can find summaries of previous discussions in 'archives/*.md' files within your context.\n\n"
            "You can update memory files using 'run_command' (e.g., echo \"...\" > path/to/file).\n"
            "Always explain what you are going to do before running a command."
        )
            
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
                await self._analyze_context_shift(messages, new_messages, user_id, user_dir)
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
                    
                    # Проверка безопасности
                    is_safe, reason = self.safety_agent.is_safe(command)
                    if not is_safe:
                        result_content = f"Error: Command rejected by safety agent. Reason: {reason}"
                    else:
                        # Выполнение команды
                        res = await self.command_executor.execute(command)
                        result_content = f"Exit code: {res.exit_code}\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
                        if res.timeout:
                            result_content += "\nNote: Command timed out."
                
                elif tool_name == "web_search":
                    query = args.get("query", "")
                    await self.notify(f"🌐 Ищу в интернете: {query}...")
                    results = await self.web_search_executor.search(query)
                    result_content = json.dumps(results, ensure_ascii=False, indent=2)
                
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

    async def _analyze_context_shift(
        self, 
        messages: list[dict[str, Any]], 
        new_messages: list[dict[str, Any]], 
        user_id: Optional[int], 
        user_dir: Optional[Path]
    ) -> Optional[dict[str, Any]]:
        """Вспомогательный метод для анализа смены контекста."""
        if not user_id or not user_dir:
            return None
            
        # Передаем всю историю (включая системный промпт и текущий диалог)
        full_history_for_analysis = messages + new_messages
        archive_info = await self.context_agent.analyze_and_archive(
            full_history_for_analysis, 
            user_id, 
            user_dir
        )
        
        if archive_info:
            await self.notify(f"📦 Контекст темы '{archive_info['title']}' архивирован.")
            # Добавляем сервисное сообщение в историю о архивации
            archive_msg = {
                "role": "system", 
                "content": f"Previous discussion archived: {archive_info['summary']}. Ref: archives/{archive_info['filename']}"
            }
            new_messages.append(archive_msg)
        
        return archive_info
