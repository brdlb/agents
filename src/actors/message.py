"""Сообщения для Actor Framework."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class MessageType(Enum):
    """Типы сообщений для акторов."""
    DEFAULT = "default"
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    SPAWN_SUBAGENT = "spawn_subagent"
    EXECUTE_COMMAND = "execute_command"
    WEB_SEARCH = "web_search"
    DELEGATE_TASK = "delegate_task"


@dataclass
class ActorMessage:
    """Базовое сообщение для акторов."""
    id: str
    recipient: str
    payload: Any
    message_type: MessageType = MessageType.DEFAULT
    sender: Optional[str] = None
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "reply_to": self.reply_to,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActorMessage":
        """Создание сообщения из словаря."""
        return cls(
            id=data["id"],
            sender=data.get("sender"),
            recipient=data["recipient"],
            payload=data["payload"],
            reply_to=data.get("reply_to"),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_type=MessageType(data.get("message_type", "default"))
        )


@dataclass
class CommandResult:
    """Результат выполнения команды."""
    success: bool
    data: Any = None
    error: Optional[str] = None


@dataclass
class ExecuteCommand:
    """Сообщение для выполнения команды."""
    command: str
    timeout: float = 30.0


@dataclass
class WebSearchQuery:
    """Сообщение для веб-поиска."""
    query: str
    max_results: int = 5