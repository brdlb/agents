"""LLM Provider Base - абстрактный базовый класс для LLM провайдеров."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMMessage:
    """Сообщение для LLM."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    """Ответ от LLM."""
    content: str
    model: str
    usage: dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class LLMProvider(ABC):
    """Абстрактный базовый класс LLM провайдера."""

    def __init__(self, api_key: str | None = None, model: str | None = None, **kwargs: Any):
        """Инициализация провайдера.
        
        Args:
            api_key: API ключ провайдера
            model: Модель для использования
            **kwargs: Дополнительные параметры
        """
        self.api_key = api_key
        self.model = model
        self.extra_kwargs = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        **kwargs: Any
    ) -> LLMResponse:
        """Генерация текста на основе сообщений.
        
        Args:
            messages: Список сообщений
            **kwargs: Дополнительные параметры (temperature, max_tokens и т.д.)
            
        Returns:
            LLMResponse с сгенерированным текстом
        """
        pass

    @abstractmethod
    async def get_token_count(self, text: str) -> int:
        """Подсчет количества токенов в тексте.
        
        Args:
            text: Текст для подсчета токенов
            
        Returns:
            Количество токенов
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Проверка соединения с провайдером.
        
        Returns:
            True если соединение успешно
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Имя провайдера."""
        pass

    def format_messages(self, messages: list[dict[str, Any]]) -> list[LLMMessage]:
        """Форматирование сообщений в LLMMessage.
        
        Args:
            messages: Список словарей с role и content
            
        Returns:
            Список LLMMessage
        """
        return [
            LLMMessage(
                role=m["role"], 
                content=m.get("content") or "",
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id")
            ) 
            for m in messages
        ]

