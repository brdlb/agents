"""LLM Provider Factory - создание провайдеров."""

from typing import Optional

from src.llm.providers.base import LLMProvider
from src.llm.providers.gemini_cli import GeminiCLIProvider
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
        
        logger.info(
            "llm_provider_creating",
            provider_name=name,
            model=model or settings.default_model,
        )
        
        if name.lower() == "openai":
            provider = OpenAIProvider(
                api_key=api_key or settings.openai_api_key,
                model=model or settings.default_model,
                **kwargs
            )
            logger.info(
                "llm_provider_created",
                provider_name="openai",
                model=provider.model,
            )
            return provider
        
        if name.lower() == "openrouter":
            provider = OpenRouterProvider(
                api_key=api_key or settings.openrouter_api_key,
                model=model or settings.default_model,
                **kwargs
            )
            logger.info(
                "llm_provider_created",
                provider_name="openrouter",
                model=provider.model,
            )
            return provider
        
        if name.lower() == "gemini-cli" or name.lower() == "gemini_cli":
            provider = GeminiCLIProvider(
                model=model or settings.default_model,
                **kwargs
            )
            logger.info(
                "llm_provider_created",
                provider_name="gemini-cli",
                model=provider.model,
            )
            return provider
        
        # В будущем здесь будут другие провайдеры
        logger.error("llm_provider_unknown", provider_name=name)
        raise ValueError(f"Unknown LLM provider: {name}")

    @staticmethod
    def get_default() -> LLMProvider:
        """Получение провайдера по умолчанию из настроек."""
        return LLMFactory.create()
