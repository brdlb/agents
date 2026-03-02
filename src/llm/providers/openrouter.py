"""OpenRouter LLM Provider - реализация через OpenAI-совместимый API."""

from typing import Any, Optional

from src.llm.providers.openai import OpenAIProvider
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OpenRouterProvider(OpenAIProvider):
    """Провайдер для OpenRouter, наследующий логику OpenAI."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openrouter/free",
        base_url: str = "https://openrouter.ai/api/v1",
        **kwargs: Any
    ):
        """Инициализация OpenRouter провайдера.
        
        Args:
            api_key: OpenRouter API ключ
            model: Модель (например, google/gemini-2.0-flash-001)
            base_url: URL OpenRouter API
            **kwargs: Дополнительные параметры (site_url, site_name и т.д.)
        """
        # OpenRouter ожидает специфические заголовки для рейтинга, но они опциональны
        # Мы можем пробросить их через extra_headers в AsyncOpenAI если нужно
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            **kwargs
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    async def validate_connection(self) -> bool:
        """Проверка соединения с OpenRouter."""
        try:
            # У OpenRouter проверка моделей работает так же
            await self.client.models.list()
            logger.info("openrouter_connection_valid")
            return True
        except Exception as e:
            logger.error("openrouter_connection_error", error=str(e))
            return False
