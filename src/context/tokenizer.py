"""Tokenizer - подсчет токенов в тексте."""

from typing import Optional

import tiktoken

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Tokenizer:
    """Класс для работы с токенизацией."""

    def __init__(self, model_name: Optional[str] = None):
        """Инициализация токенизатора.
        
        Args:
            model_name: Название модели (например, gpt-4o-mini)
        """
        self.model_name = model_name or settings.default_model
        try:
            # Для OpenRouter моделей используем cl100k_base
            if self.model_name.startswith("openrouter/"):
                self.encoding = tiktoken.get_encoding("cl100k_base")
            else:
                self.encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            logger.warning("model_encoding_not_found", model=self.model_name, fallback="cl100k_base")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Подсчет токенов в тексте."""
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Обрезка текста до максимального количества токенов."""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        """Подсчет токенов в списке сообщений (приблизительно)."""
        num_tokens = 0
        for message in messages:
            # Каждое сообщение имеет метаданные (role, name)
            num_tokens += 4  
            for key, value in message.items():
                num_tokens += self.count_tokens(value)
                if key == "name":
                    num_tokens += -1  # Если есть имя, роль опускается
        num_tokens += 2  # Каждому ответу предшествует <|start|>assistant
        return num_tokens
