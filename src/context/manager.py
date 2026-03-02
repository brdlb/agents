"""Context Manager - управление контекстом из markdown файлов."""

import asyncio
from pathlib import Path
from typing import Optional

import aiofiles

from src.context.tokenizer import Tokenizer
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """Менеджер контекста из файлов."""

    def __init__(self, context_dir: Optional[Path] = None):
        """Инициализация менеджера.
        
        Args:
            context_dir: Директория с markdown файлами
        """
        self.context_dir = context_dir or settings.context_dir
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.tokenizer = Tokenizer()
        self.max_tokens = settings.max_context_tokens
        self._cache: dict[str, tuple[str, int]] = {}  # path -> (content, tokens)

    async def load_file(self, file_path: Path) -> tuple[str, int]:
        """Загрузка контента файла и подсчет токенов."""
        if not file_path.exists():
            logger.warning("file_not_found", path=str(file_path))
            return "", 0

        # Проверка кеша (в MVP просто по пути, в будущем по mtime)
        path_key = str(file_path)
        if path_key in self._cache:
            return self._cache[path_key]

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()
            tokens = self.tokenizer.count_tokens(content)
            
            self._cache[path_key] = (content, tokens)
            return content, tokens

    async def get_all_context(self, additional_dir: Optional[Path] = None) -> str:
        """Сборка всего контекста из директорий."""
        dirs = [self.context_dir]
        if additional_dir:
            dirs.append(additional_dir)
            # Также проверяем поддиректорию archives
            archive_dir = additional_dir / "archives"
            if archive_dir.exists():
                dirs.append(archive_dir)
        
        files = []
        for d in dirs:
            if d.exists():
                # Ищем md файлы в текущей директории (не рекурсивно, чтобы избежать дублей)
                files.extend(list(d.glob("*.md")))
        
        files.sort()  # Для детерминированного порядка
        
        total_content = []
        current_tokens = 0
        
        for file_path in files:
            content, tokens = await self.load_file(file_path)
            if not content:
                continue
                
            if current_tokens + tokens > self.max_tokens:
                logger.warning(
                    "context_limit_reached", 
                    file=file_path.name, 
                    current=current_tokens, 
                    adding=tokens
                )
                # Пытаемся добавить хотя бы часть, если это возможно
                remaining = self.max_tokens - current_tokens
                if remaining > 100:  # Минимум 100 токенов смысла
                    truncated = self.tokenizer.truncate_text(content, remaining)
                    total_content.append(f"--- File: {file_path.name} (truncated) ---\n{truncated}")
                break
            
            total_content.append(f"--- File: {file_path.name} ---\n{content}")
            current_tokens += tokens
            
        return "\n\n".join(total_content)

    def clear_cache(self):
        """Очистка кеша."""
        self._cache.clear()

    async def get_system_prompt_with_context(self, base_prompt: str, user_dir: Optional[Path] = None) -> str:
        """Сборка системного промпта с учетом контекста."""
        self.clear_cache()
        context = await self.get_all_context(additional_dir=user_dir)
        if not context:
            return base_prompt
            
        full_prompt = (
            f"{base_prompt}\n\n"
            "У тебя есть доступ к следующему контексту из локальных файлов:\n"
            "==========================================================\n"
            f"{context}\n"
            "==========================================================\n"
            "Используй эту информацию для ответов на вопросы пользователя."
        )
        return full_prompt
