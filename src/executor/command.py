"""Command Executor - выполнение консольных команд."""

import asyncio
import shlex
import subprocess
from dataclasses import dataclass
from typing import Optional

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CommandResult:
    """Результат выполнения команды."""
    stdout: str
    stderr: str
    exit_code: int
    timeout: bool = False


class CommandExecutor:
    """Класс для выполнения консольных команд."""

    def __init__(self, timeout: Optional[int] = None):
        """Инициализация исполнителя.
        
        Args:
            timeout: Таймаут выполнения команды (в секундах)
        """
        self.timeout = timeout or settings.command_timeout

    async def execute(self, command: str) -> CommandResult:
        """Асинхронное выполнение команды.
        
        Args:
            command: Строка команды
            
        Returns:
            CommandResult с результатом выполнения
        """
        logger.info("command_executing", command=command)
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
                return CommandResult(
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    exit_code=process.returncode or 0
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.warning("command_timeout", command=command)
                return CommandResult(stdout="", stderr="Command timed out", exit_code=-1, timeout=True)
                
        except Exception as e:
            logger.error("command_error", command=command, error=str(e))
            return CommandResult(stdout="", stderr=str(e), exit_code=-1)
