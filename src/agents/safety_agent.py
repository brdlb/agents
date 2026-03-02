"""Safety Agent - проверка безопасности команд."""

import re
from typing import Optional

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SafetyAgent:
    """Агент безопасности для проверки команд."""

    FORBIDDEN_PATTERNS = [
        r'rm\s+-rf\s+/(?!tmp)',  # Удаление всего кроме /tmp
        r'format\s+',
        r'del\s+/[sq]',
        r'>\s*/dev/sd',
        r'mkfs\.',
        r'dd\s+if=.*of=/dev/',
        r'shutdown',
        r'reboot',
    ]

    def __init__(self, allowed_commands: Optional[list[str]] = None):
        """Инициализация.
        
        Args:
            allowed_commands: Список разрешенных команд
        """
        self.allowed_commands = allowed_commands or settings.get_allowed_commands_list()

    def is_safe(self, command: str) -> tuple[bool, str]:
        """Проверка команды на безопасность.
        
        Returns:
            (is_safe, reason)
        """
        if not command:
            return False, "Empty command"

        # 1. Если разрешены все команды (*)
        if "*" in self.allowed_commands:
            # Все равно проверяем на явно запрещенные паттерны
            for pattern in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return False, f"Command matches forbidden pattern: {pattern}"
            return True, "All commands allowed (*)"

        # 2. Проверка по списку разрешенных
        base_cmd = command.split()[0] if command.split() else ""
        if base_cmd not in self.allowed_commands:
            return False, f"Command '{base_cmd}' is not in the allowed list"

        # 3. Проверка на запрещенные паттерны
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command matches forbidden pattern: {pattern}"

        return True, "Safe"
