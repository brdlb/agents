"""Session Manager - управление сессиями пользователей."""

import json
from pathlib import Path
from typing import Optional
from uuid import UUID

import aiofiles

from src.session.models import Message, Session, User
from src.storage.json_store import JSONStore
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Менеджер сессий и пользователей."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Инициализация менеджера.
        
        Args:
            data_dir: Базовая директория для данных
        """
        self.data_dir = data_dir or settings.data_dir
        self.sessions_store = JSONStore(self.data_dir / "sessions")
        self.users_store = JSONStore(self.data_dir / "users")

    def get_user_dir(self, user_id: int) -> Path:
        """Получение директории данных пользователя."""
        user_dir = self.data_dir / "users" / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def get_user_memory_path(self, user_id: int, filename: str) -> Path:
        """Получение пути к файлу памяти пользователя (soul.md, user.md)."""
        return self.get_user_dir(user_id) / filename

    def get_user_history_path(self, user_id: int) -> Path:
        """Получение пути к файлу истории пользователя."""
        return self.get_user_dir(user_id) / "history.jsonl"

    # --- User Management ---

    async def get_user(self, user_id: int) -> Optional[User]:
        """Получение данных пользователя."""
        data = await self.users_store.read(f"{user_id}.json")
        if data:
            return User(**data)
        return None

    async def save_user(self, user: User) -> None:
        """Сохранение данных пользователя."""
        await self.users_store.write(user.to_dict(), f"{user.user_id}.json")

    async def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Получение или создание нового пользователя."""
        user = await self.get_user(user_id)
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=user_id in settings.get_admin_ids()
            )
            await self.save_user(user)
            logger.info("user_created", user_id=user_id, username=username)
        return user

    # --- Session Management ---

    async def create_session(self, user_id: int, system_prompt: Optional[str] = None) -> Session:
        """Создание новой сессии для пользователя."""
        session = Session(user_id=user_id)
        if system_prompt:
            session.system_prompt = system_prompt
        
        await self.save_session(session)
        logger.info("session_created", user_id=user_id, session_id=str(session.id))
        return session

    async def get_session(self, user_id: int, session_id: UUID) -> Optional[Session]:
        """Получение сессии по ID."""
        data = await self.sessions_store.read(str(user_id), f"session_{session_id}.json")
        if data:
            return Session(**data)
        return None

    async def save_session(self, session: Session) -> None:
        """Сохранение сессии."""
        await self.sessions_store.write(
            session.to_dict(),
            str(session.user_id),
            f"session_{session.id}.json"
        )

    async def list_user_sessions(self, user_id: int) -> list[Session]:
        """Список всех сессий пользователя."""
        files = await self.sessions_store.list_files(str(user_id))
        sessions = []
        for file_path in files:
            data = await self.sessions_store.read(str(user_id), file_path.name)
            if data:
                sessions.append(Session(**data))
        
        # Сортировка по времени обновления (новые сверху)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def get_latest_session(self, user_id: int) -> Optional[Session]:
        """Получение последней активной сессии пользователя."""
        sessions = await self.list_user_sessions(user_id)
        return sessions[0] if sessions else None

    async def add_message(
        self, 
        user_id: int, 
        session_id: UUID, 
        role: str, 
        content: Optional[str] = None,
        tool_calls: Optional[list] = None,
        tool_call_id: Optional[str] = None
    ) -> Message:
        """Добавление сообщения в сессию и сохранение."""
        session = await self.get_session(user_id, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found for user {user_id}")
        
        message = session.add_message(role, content, tool_calls, tool_call_id)
        await self.save_session(session)
        
        # Аппенд в историю конкретного пользователя
        history_file = self.get_user_history_path(user_id)
        try:
            async with aiofiles.open(history_file, "a", encoding="utf-8") as f:
                entry = {
                    "session_id": str(session_id),
                    **message.to_dict()
                }
                await f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("history_append_error", user_id=user_id, error=str(e))
            
        return message

    async def ensure_user_memory(self, user_id: int) -> None:
        """Инициализация файлов памяти пользователя, если они не существуют."""
        soul_path = self.get_user_memory_path(user_id, "soul.md")
        user_md_path = self.get_user_memory_path(user_id, "user.md")
        
        if not soul_path.exists():
            async with aiofiles.open(soul_path, "w", encoding="utf-8") as f:
                await f.write("You are a helpful and efficient assistant. This is your 'soul' - your identity and behavioral guidelines.")
        
        if not user_md_path.exists():
            async with aiofiles.open(user_md_path, "w", encoding="utf-8") as f:
                await f.write(f"Information about User {user_id} will be stored here.")

    async def delete_session(self, user_id: int, session_id: UUID) -> bool:
        """Удаление сессии."""
        success = await self.sessions_store.delete(str(user_id), f"session_{session_id}.json")
        if success:
            logger.info("session_deleted", user_id=user_id, session_id=str(session_id))
        return success
