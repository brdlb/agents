"""Base Agent - базовый класс для всех агентов."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from src.llm.providers.base import LLMProvider, LLMMessage, LLMResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Абстрактный класс агента."""

    def __init__(
        self,
        provider: LLMProvider,
        on_progress: Optional[Callable[[str], Any]] = None
    ):
        """Инициализация агента.
        
        Args:
            provider: Провайдер LLM
            on_progress: Callback для уведомлений о прогрессе
        """
        self.provider = provider
        self.on_progress = on_progress

    @abstractmethod
    async def run(self, user_input: str, history: list[dict[str, str]]) -> str:
        """Запуск агента для обработки запроса.
        
        Args:
            user_input: Запрос пользователя
            history: История сообщений
            
        Returns:
            Ответ агента
        """
        pass

    async def notify(self, message: str):
        """Отправка уведомления о прогрессе."""
        if self.on_progress:
            if asyncio.iscoroutinefunction(self.on_progress):
                await self.on_progress(message)
            else:
                self.on_progress(message)


# Импорт asyncio здесь, чтобы избежать circular import в __init__ если потребуется
import asyncio
