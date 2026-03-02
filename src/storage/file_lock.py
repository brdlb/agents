"""File Locking - файловые блокировки для параллельного доступа."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from filelock import AsyncFileLock as FileLockBase

from src.utils.logging import get_logger

logger = get_logger(__name__)


class FileLock:
    """Менеджер файловых блокировок с async поддержкой."""

    def __init__(self, lock_dir: Path, timeout: float = 30.0):
        """Инициализация менеджера блокировок.
        
        Args:
            lock_dir: Директория для хранения файлов блокировок
            timeout: Таймаут ожидания блокировки в секундах
        """
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._locks: dict[str, FileLockBase] = {}

    def _get_lock_path(self, file_path: Path) -> Path:
        """Получение пути к файлу блокировки."""
        # Создаем уникальное имя файла блокировки
        lock_name = f"{file_path.stem}.lock"
        return self.lock_dir / lock_name

    def _get_or_create_lock(self, file_path: Path) -> FileLockBase:
        """Получение или создание блокировки для файла."""
        lock_path = self._get_lock_path(file_path)
        key = str(lock_path)
        
        if key not in self._locks:
            self._locks[key] = FileLockBase(lock_path, timeout=self.timeout)
        
        return self._locks[key]

    @asynccontextmanager
    async def lock(self, file_path: Path) -> AsyncIterator[None]:
        """Контекстный менеджер для блокировки файла.
        
        Args:
            file_path: Путь к файлу для блокировки
            
        Yields:
            None
            
        Raises:
            TimeoutError: Если не удалось получить блокировку
        """
        lock = self._get_or_create_lock(file_path)
        
        logger.debug("acquiring_lock", path=str(file_path))
        
        try:
            await lock.acquire()
            logger.debug("lock_acquired", path=str(file_path))
            yield
        except Exception as e:
            logger.error("lock_error", path=str(file_path), error=str(e))
            raise
        finally:
            await lock.release()
            logger.debug("lock_released", path=str(file_path))

    async def try_lock(self, file_path: Path) -> bool:
        """Попытка получить блокировку без ожидания.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если блокировка получена
        """
        lock = self._get_or_create_lock(file_path)
        
        try:
            return await lock.acquire(timeout=0)
        except TimeoutError:
            return False

    def release_all(self) -> None:
        """Освобождение всех блокировок."""
        self._locks.clear()

