"""Pydantic модели данных для сессий и сообщений."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Модель сообщения в сессии."""
    role: str = Field(..., description="Роль: user, assistant, system, tool")
    content: Optional[str] = Field(None, description="Текст сообщения")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Преобразование в словарь для JSON."""
        d = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


class Session(BaseModel):
    """Модель пользовательской сессии."""
    id: UUID = Field(default_factory=uuid4, description="Уникальный ID сессии")
    user_id: int = Field(..., description="ID пользователя Telegram")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    system_prompt: str = Field(default="You are a helpful assistant.")
    context_tokens: int = Field(default=0, description="Количество токенов в контексте")
    messages: list[Message] = Field(default_factory=list)

    def add_message(self, role: str, content: Optional[str] = None, tool_calls: Optional[list] = None, tool_call_id: Optional[str] = None) -> Message:
        """Добавление сообщения в сессию."""
        message = Message(role=role, content=content, tool_calls=tool_calls, tool_call_id=tool_call_id)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message

    def to_dict(self) -> dict:
        """Преобразование в словарь для JSON."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "system_prompt": self.system_prompt,
            "context_tokens": self.context_tokens,
            "messages": [m.to_dict() for m in self.messages]
        }


class User(BaseModel):
    """Модель пользователя."""
    user_id: int = Field(..., description="ID пользователя Telegram")
    username: Optional[str] = Field(default=None, description="Username Telegram")
    first_name: Optional[str] = Field(default=None, description="Имя пользователя")
    last_name: Optional[str] = Field(default=None, description="Фамилия пользователя")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_admin: bool = Field(default=False)

    def to_dict(self) -> dict:
        """Преобразование в словарь для JSON."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "created_at": self.created_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "is_admin": self.is_admin
        }

