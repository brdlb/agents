"""OpenAI LLM Provider - реализация с async поддержкой."""

from typing import Any

import openai
import tiktoken
from openai import AsyncOpenAI

from src.llm.providers.base import LLMMessage, LLMProvider, LLMResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI провайдер для работы с GPT моделями."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        **kwargs: Any
    ):
        """Инициализация OpenAI провайдера.
        
        Args:
            api_key: OpenAI API ключ
            model: Модель для использования (gpt-4o-mini, gpt-4, gpt-3.5-turbo)
            base_url: Кастомный URL для проксирования (опционально)
            **kwargs: Дополнительные параметры
        """
        super().__init__(api_key=api_key, model=model, **kwargs)
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self._encoding: tiktoken.Encoding | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    def _get_encoding(self) -> tiktoken.Encoding:
        """Получение编码器 для подсчета токенов."""
        if self._encoding is None:
            # Используем cl100k_base для GPT-4 и GPT-3.5
            self._encoding = tiktoken.get_encoding("cl100k_base")
        return self._encoding

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int | None = 2048,
        **kwargs: Any
    ) -> LLMResponse:
        """Генерация текста через OpenAI API.
        
        Args:
            messages: Список сообщений
            temperature: Температура генерации (0-2)
            max_tokens: Максимальное количество токенов
            **kwargs: Дополнительные параметры
            
        Returns:
            LLMResponse с сгенерированным текстом
        """
        # Форматирование сообщений для OpenAI API
        openai_messages = []
        for m in messages:
            msg = {"role": m.role, "content": m.content}
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            openai_messages.append(msg)
        
        logger.debug(
            "openai_generate",
            model=self.model,
            message_count=len(messages)
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            message = response.choices[0].message
            content = message.content or ""
            usage = response.usage
            
            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens
                },
                finish_reason=response.choices[0].finish_reason,
                tool_calls=tool_calls
            )
        except openai.APIError as e:
            logger.error("openai_api_error", error=str(e))
            raise

    async def get_token_count(self, text: str) -> int:
        """Подсчет токенов с помощью tiktoken.
        
        Args:
            text: Текст для подсчета
            
        Returns:
            Количество токенов
        """
        encoding = self._get_encoding()
        return len(encoding.encode(text))

    async def validate_connection(self) -> bool:
        """Проверка соединения с OpenAI API.
        
        Returns:
            True если соединение успешно
        """
        try:
            # Пробуем получить список моделей
            await self.client.models.list()
            logger.info("openai_connection_valid")
            return True
        except Exception as e:
            logger.error("openai_connection_error", error=str(e))
            return False

    async def close(self) -> None:
        """Закрытие соединения."""
        await self.client.close()

