"""SubAgent - агент для обработки задач, делегированных родительским агентом."""

import uuid
from typing import Optional

from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType
from src.llm.providers.base import LLMProvider, LLMMessage
from src.utils.logging import get_logger


class SubAgent(Actor):
    """Агент для обработки задач от родительского агента с использованием LLM."""
    
    def __init__(
        self,
        provider: LLMProvider,
        actor_id: str = None,
        system_prompt: str = None
    ):
        """Инициализация SubAgent.
        
        Args:
            provider: LLM провайдер для генерации ответов
            actor_id: Уникальный идентификатор актора
            system_prompt: Системный промпт для LLM
        """
        super().__init__(actor_id)
        self.provider = provider
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.logger = get_logger(self.__class__.__name__)
    
    async def receive(self, message: ActorMessage):
        """Обработка входящего сообщения.
        
        Args:
            message: Входящее сообщение от родительского агента
        """
        # Проверяем тип сообщения
        if message.message_type == MessageType.DELEGATE_TASK or message.message_type.value == "delegate_task":
            await self._handle_delegated_task(message)
        else:
            self.logger.warning(
                "unsupported_message_type",
                message_type=message.message_type,
                actor_id=self.actor_id
            )
    
    async def _handle_delegated_task(self, message: ActorMessage):
        """Обработка делегированной задачи от родительского агента.
        
        Args:
            message: Сообщение с задачей от родителя
        """
        try:
            # Извлекаем задачу из payload
            task = message.payload
            if isinstance(task, dict):
                task_text = task.get("task", task.get("content", str(task)))
            else:
                task_text = str(task)
            
            self.logger.info(
                "processing_delegated_task",
                actor_id=self.actor_id,
                task_preview=task_text[:50]
            )
            
            # Подготовка сообщений для LLM
            messages = [
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=task_text)
            ]
            
            # Генерация ответа через LLM
            response = await self.provider.generate(messages)
            
            # Отправка результата родителю через reply_to
            if message.reply_to and self.system:
                result_message = ActorMessage(
                    id=f"result_{uuid.uuid4().hex[:8]}",
                    sender=self.actor_id,
                    recipient=message.reply_to,
                    payload={
                        "task": task_text,
                        "result": response.content,
                        "model": response.model,
                        "success": True
                    },
                    message_type=MessageType.RESPONSE,
                    correlation_id=message.id
                )
                await self.system.send(result_message)
                
                self.logger.info(
                    "task_result_sent",
                    actor_id=self.actor_id,
                    recipient=message.reply_to
                )
            else:
                self.logger.warning(
                    "no_reply_to_address",
                    actor_id=self.actor_id,
                    has_reply_to=bool(message.reply_to),
                    has_system=bool(self.system)
                )
                
        except Exception as e:
            self.logger.error(
                "task_processing_error",
                actor_id=self.actor_id,
                error=str(e)
            )
            
            # Отправляем сообщение об ошибке родителю
            if message.reply_to and self.system:
                error_message = ActorMessage(
                    id=f"error_{uuid.uuid4().hex[:8]}",
                    sender=self.actor_id,
                    recipient=message.reply_to,
                    payload={
                        "task": str(message.payload),
                        "error": str(e),
                        "success": False
                    },
                    message_type=MessageType.ERROR,
                    correlation_id=message.id
                )
                await self.system.send(error_message)
    
    async def ask(self, message: ActorMessage, timeout: float = 60.0) -> ActorMessage:
        """Отправка запроса с ожиданием ответа (увеличенный таймаут для LLM).
        
        Args:
            message: Сообщение для отправки
            timeout: Таймаут ожидания ответа (по умолчанию 60 секунд)
            
        Returns:
            Ответ от актора
        """
        return await super().ask(message, timeout=timeout)
