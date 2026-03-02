"""Утилиты для загрузки системных промтов из markdown файлов."""

import os
from pathlib import Path
from typing import Optional

# Базовая директория проекта
BASE_DIR = Path(__file__).parent.parent.parent

# Директория с промтами
PROMPTS_DIR = BASE_DIR / "prompts"


class PromptLoader:
    """Загрузчик системных промтов из файлов."""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """Инициализация загрузчика.
        
        Args:
            prompts_dir: Путь к директории с промтами. По умолчанию prompts/ в корне проекта.
        """
        self.prompts_dir = prompts_dir or PROMPTS_DIR
    
    def load_prompt(self, filename: str, default: Optional[str] = None) -> str:
        """Загрузка промта из файла.
        
        Args:
            filename: Имя файла промта (например, 'default.md', 'subagent.md')
            default: Значение по умолчанию, если файл не найден
            
        Returns:
            Содержимое промта
        """
        filepath = self.prompts_dir / filename
        
        if not filepath.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"Prompt file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    
    def load_prompt_with_context(
        self,
        filename: str,
        context: dict[str, str],
        default: Optional[str] = None
    ) -> str:
        """Загрузка промта с подстановкой контекста.
        
        Args:
            filename: Имя файла промта
            context: Словарь для подстановки в промт (например, {user_id: "123"})
            default: Значение по умолчанию, если файл не найден
            
        Returns:
            Промт с подставленными значениями
        """
        template = self.load_prompt(filename, default)
        
        # Подставляем значения из контекста
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            template = template.replace(placeholder, str(value))
        
        return template


# Глобальный экземпляр загрузчика
_default_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Получение глобального экземпляра загрузчика промтов."""
    global _default_loader
    if _default_loader is None:
        _default_loader = PromptLoader()
    return _default_loader


def load_prompt(filename: str, default: Optional[str] = None) -> str:
    """Удобная функция для загрузки промта."""
    return get_prompt_loader().load_prompt(filename, default)


def load_prompt_with_context(filename: str, context: dict[str, str], default: Optional[str] = None) -> str:
    """Удобная функция для загрузки промта с контекстом."""
    return get_prompt_loader().load_prompt_with_context(filename, context, default)
