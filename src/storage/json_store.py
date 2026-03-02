"""JSON Storage - базовое хранилище с async file I/O."""

import asyncio
import json
from pathlib import Path
from typing import Any, Callable, TypeVar

import aiofiles

from src.storage.file_lock import FileLock
from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class JSONStore:
    """Async JSON хранилище с файловыми блокировками."""

    def __init__(self, base_dir: Path, lock_dir: Path | None = None):
        """Инициализация хранилища.
        
        Args:
            base_dir: Базовая директория для хранения файлов
            lock_dir: Директория для файлов блокировок
        """
        self.base_dir = Path(base_dir)
        self.lock_dir = Path(lock_dir) if lock_dir else self.base_dir / ".locks"
        self.file_lock = FileLock(self.lock_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, *parts: str) -> Path:
        """Получение пути к файлу."""
        return self.base_dir.joinpath(*parts)

    async def read(self, *parts: str, default: T | None = None) -> T | None:
        """Чтение данных из JSON файла.
        
        Args:
            parts: Части пути к файлу
            default: Значение по умолчанию, если файл не существует
            
        Returns:
            Десериализованные данные или default
        """
        file_path = self._get_file_path(*parts)
        
        if not file_path.exists():
            return default
        
        async with self.file_lock.lock(file_path):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content) if content else default
            except json.JSONDecodeError as e:
                logger.error("json_decode_error", path=str(file_path), error=str(e))
                return default
            except Exception as e:
                logger.error("read_error", path=str(file_path), error=str(e))
                raise

    async def write(self, data: Any, *parts: str) -> None:
        """Запись данных в JSON файл.
        
        Args:
            data: Данные для записи (будут сериализованы в JSON)
            parts: Части пути к файлу
        """
        file_path = self._get_file_path(*parts)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Атомарная запись через временный файл
        temp_path = file_path.with_suffix(".tmp")
        
        async with self.file_lock.lock(file_path):
            try:
                async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                
                # Атомарная замена
                temp_path.replace(file_path)
                logger.debug("write_success", path=str(file_path))
            except Exception as e:
                logger.error("write_error", path=str(file_path), error=str(e))
                # Удаляем временный файл при ошибке
                if temp_path.exists():
                    temp_path.unlink()
                raise

    async def delete(self, *parts: str) -> bool:
        """Удаление файла.
        
        Returns:
            True если файл был удален, False если не существовал
        """
        file_path = self._get_file_path(*parts)
        
        if not file_path.exists():
            return False
        
        async with self.file_lock.lock(file_path):
            try:
                file_path.unlink()
                logger.debug("delete_success", path=str(file_path))
                return True
            except Exception as e:
                logger.error("delete_error", path=str(file_path), error=str(e))
                raise

    async def exists(self, *parts: str) -> bool:
        """Проверка существования файла."""
        file_path = self._get_file_path(*parts)
        return file_path.exists()

    async def list_files(self, *parts: str, pattern: str = "*.json") -> list[Path]:
        """Список файлов в директории.
        
        Args:
            parts: Части пути к директории
            pattern: Glob паттерн для фильтрации файлов
            
        Returns:
            Список путей к файлам
        """
        dir_path = self._get_file_path(*parts)
        if not dir_path.exists():
            return []
        return list(dir_path.glob(pattern))

    async def update(
        self,
        updater: Callable[[dict], dict],
        *parts: str,
        default: dict | None = None
    ) -> dict:
        """Обновление данных в файле с использованием функции.
        
        Args:
            updater: Функция, принимающая текущие данные и возвращающая новые
            parts: Части пути к файлу
            default: Значение по умолчанию для нового файла
            
        Returns:
            Обновленные данные
        """
        current = await self.read(*parts, default=default or {})
        updated = updater(current)
        await self.write(updated, *parts)
        return updated

