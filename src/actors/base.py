"""Базовый класс для акторов."""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Set, TYPE_CHECKING
from enum import Enum

from src.actors.message import ActorMessage
from src.utils.logging import get_logger

# Import ActorSystem для обратной совместимости
if TYPE_CHECKING:
    from src.actors.system import ActorSystem


class ActorState(Enum):
    """Состояния актора."""
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Actor(ABC):
    """Абстрактный базовый класс для всех акторов."""
    
    def __init__(self, actor_id: Optional[str] = None):
        self.actor_id = actor_id or f"actor_{uuid.uuid4().hex[:8]}"
        self.mailbox = asyncio.Queue()
        self.system = None  # type: ignore[assignment]  # будет установлен при спавне
        self.parent_id: Optional[str] = None
        self.children: Set[str] = set()
        self.state = ActorState.IDLE
        self._running = False
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def receive(self, message: ActorMessage):
        """Обработка входящего сообщения."""
        pass

    async def tell(self, message: ActorMessage):
        """Отправка сообщения без ожидания ответа."""
        if self.system:
            await self.system.send(message)
        else:
            self.logger.error("actor_no_system", actor_id=self.actor_id)

    async def ask(self, message: ActorMessage, timeout: float = 30.0) -> ActorMessage:
        """Отправка сообщения с ожиданием ответа."""
        future = asyncio.Future()
        reply_id = f"reply_{uuid.uuid4().hex[:8]}"
        
        def reply_handler(reply_msg: ActorMessage):
            if not future.done():
                future.set_result(reply_msg)
        
        # Устанавливаем обработчик ответа
        # В реальной реализации это будет более сложным
        if self.system:
            await self.system.send(message)
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                self.logger.error("ask_timeout", actor_id=self.actor_id, message_id=message.id)
                raise
        else:
            self.logger.error("actor_no_system", actor_id=self.actor_id)
            raise RuntimeError("Actor has no system")

    async def spawn_child(self, actor):
        """Создание дочернего актора."""
        self.logger.info(
            "spawn_child_called",
            actor_id=self.actor_id,
            has_system=bool(self.system),
            system_id=id(self.system) if self.system else None,
            child_actor_id=actor.actor_id
        )
        if self.system:
            result = await self.system.spawn(actor, parent_id=self.actor_id)
            self.logger.info("spawn_child_success", child_actor_id=result)
            return result
        else:
            self.logger.error("actor_no_system", actor_id=self.actor_id)
            raise RuntimeError("Actor has no system")

    async def _run(self):
        """Внутренний цикл работы актора."""
        self._running = True
        self.state = ActorState.RUNNING
        
        while self._running:
            try:
                # Ждем сообщение с таймаутом
                message = await asyncio.wait_for(self.mailbox.get(), timeout=1.0)
                await self.receive(message)
            except asyncio.TimeoutError:
                # Продолжаем цикл, если нет сообщений
                continue
            except Exception as e:
                await self._handle_error(e)
                
        self.state = ActorState.STOPPED

    async def _handle_error(self, error: Exception):
        """Обработка ошибок в акторе."""
        self.logger.error("actor_error", actor_id=self.actor_id, error=str(error))
        self.state = ActorState.ERROR
        
        # Отправляем сообщение о ошибке родителю
        if self.parent_id and self.system:
            error_message = ActorMessage(
                id=f"error_{uuid.uuid4().hex[:8]}",
                sender=self.actor_id,
                recipient=self.parent_id,
                payload={"actor_id": self.actor_id, "error": str(error)},
                message_type="child_error"
            )
            await self.system.send(error_message)

    async def stop(self):
        """Остановка актора."""
        self._running = False
        # Останавливаем всех детей
        for child_id in list(self.children):
            if self.system:
                await self.system.stop(child_id)