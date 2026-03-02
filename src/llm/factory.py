"""LLM Provider Factory - создание провайдеров."""

from typing import Optional

from src.llm.providers.base import LLMProvider
from src.llm.providers.openai import OpenAIProvider
from src.llm.providers.openrouter import OpenRouterProvider
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """Фабрика для создания LLM провайдеров."""

    @staticmethod
    def create(
        provider_name: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """Создание экземпляра провайдера.
        
        Args:
            provider_name: Имя провайдера (openai, openrouter, etc.)
            api_key: API ключ
            model: Модель
            
        Returns:
            Экземпляр LLMProvider
        """
        name = provider_name or settings.llm_provider
        
        if name.lower() == "openai":
            return OpenAIProvider(
                api_key=api_key or settings.openai_api_key,
                model=model or settings.default_model,
                **kwargs
            )
        
        if name.lower() == "openrouter":
            return OpenRouterProvider(
                api_key=api_key or settings.openrouter_api_key,
                model=model or settings.default_model,
                **kwargs
            )
        
        # В будущем здесь будут другие провайдеры
        raise ValueError(f"Unknown LLM provider: {name}")

    @staticmethod
    def get_default() -> LLMProvider:
        """Получение провайдера по умолчанию из настроек."""
        return LLMFactory.create()
