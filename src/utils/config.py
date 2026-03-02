"""Конфигурация приложения с использованием pydantic-settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env файла."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = Field(default="", description="Токен Telegram бота")
    telegram_admin_ids: str = Field(default="", description="ID администраторов через запятую")

    # LLM Provider
    llm_provider: str = Field(default="openai", description="Провайдер LLM")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API ключ")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API ключ")
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API ключ")
    local_llm_url: Optional[str] = Field(default=None, description="URL локального LLM")
    local_llm_model: Optional[str] = Field(default=None, description="Модель локального LLM")
    default_model: str = Field(default="gpt-4o-mini", description="Модель по умолчанию")

    # Storage
    data_dir: Path = Field(default=Path("./data"), description="Директория для данных")
    session_ttl: int = Field(default=86400, description="Время жизни сессии (секунды)")
    max_sessions_per_user: int = Field(default=10, description="Макс. сессий на пользователя")

    # Context
    context_dir: Path = Field(default=Path("./context"), description="Директория контекста")
    max_context_tokens: int = Field(default=8000, description="Макс. токенов в контексте")

    # Command Executor
    allowed_commands: str = Field(default="ls,cd,cat,grep,tail,head,pwd,echo,find", description="Разрешенные команды")
    max_concurrent_commands: int = Field(default=3, description="Макс. параллельных команд")
    command_timeout: int = Field(default=30, description="Таймаут команды (секунды)")

    # Logging
    log_level: str = Field(default="INFO", description="Уровень логирования")
    log_format: str = Field(default="json", description="Формат логов")

    def get_admin_ids(self) -> list[int]:
        """Получение списка ID администраторов."""
        if not self.telegram_admin_ids:
            return []
        return [int(uid.strip()) for uid in self.telegram_admin_ids.split(",") if uid.strip()]

    def get_allowed_commands_list(self) -> list[str]:
        """Получение списка разрешенных команд."""
        return [cmd.strip() for cmd in self.allowed_commands.split(",") if cmd.strip()]


# Глобальный экземпляр настроек
settings = Settings()

