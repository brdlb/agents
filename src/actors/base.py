"""Базовый класс для акторов."""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Optional, Set, TYPE_CHECKING
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
        # Хранилище ожидающих ответов: correlation_id -> Future
        self._pending_futures: Dict[str, asyncio.Future] = {}

    @abstractmethod
    async def receive(self, message: ActorMessage):
        """Обработка входящего сообщения."""
        pass

    async def _handle_response(self, message: ActorMessage):
        """Обработка ответа на запрос (ask).
        
        Проверяет correlation_id и разрешает соответствующий Future.
        """
        correlation_id = message.correlation_id
        self.logger.info(
            "handle_response_check",
            actor_id=self.actor_id,
            message_id=message.id,
            correlation_id=correlation_id,
            pending_futures_keys=list(self._pending_futures.keys()) if self._pending_futures else [],
            has_pending_futures=correlation_id in self._pending_futures if correlation_id else False
        )
        
        if correlation_id and correlation_id in self._pending_futures:
            future = self._pending_futures[correlation_id]
            if not future.done():
                future.set_result(message)
                self.logger.info(
                    "future_resolved",
                    actor_id=self.actor_id,
                    correlation_id=correlation_id
                )
            else:
                self.logger.warning(
                    "future_already_done",
                    actor_id=self.actor_id,
                    correlation_id=correlation_id
                )
        else:
            self.logger.warning(
                "handle_response_no_future",
                actor_id=self.actor_id,
                correlation_id=correlation_id,
                reason="correlation_id not in _pending_futures"
            )

    async def tell(self, message: ActorMessage):
        """Отправка сообщения без ожидания ответа."""
        if self.system:
            await self.system.send(message)
        else:
            self.logger.error("actor_no_system", actor_id=self.actor_id)

    async def ask(self, message: ActorMessage, timeout: float = 30.0) -> ActorMessage:
        """Отправка сообщения с ожиданием ответа.
        
        NOTE: Future создаётся в контексте ВЫЗЫВАЮЩЕГО (того, кто ждёт ответ),
        а не в контексте получателя. Это позволяет вызывать ask() на дочерних
        акторах, но получать ответ в родительском контексте.
        """
        # Future создаётся в вызывающем акторе (self) - это критически важно!
        # Вызывающий актор - это тот, кто вызывает ask(), а не получатель message
        future = asyncio.Future()
        reply_id = f"reply_{uuid.uuid4().hex[:8]}"
        
        # DEBUG: Логируем создание Future
        self.logger.info(
            "ask_future_created",
            actor_id=self.actor_id,  # Это actor_id ВЫЗЫВАЮЩЕГО актора
            message_id=message.id,
            correlation_id=message.correlation_id,
            reply_to=message.reply_to,
            timeout=timeout
        )
        
        # DEBUG: Логируем состояние перед регистрацией
        self.logger.info(
            "ask_before_register",
            actor_id=self.actor_id,
            has_correlation_id=bool(message.correlation_id),
            current_pending_count=len(self._pending_futures)
        )
        
        # Регистрируем Future в вызывающем акторе (тот, кто ждёт ответ)
        if message.correlation_id:
            self._pending_futures[message.correlation_id] = future
            self.logger.info(
                "pending_future_registered",
                actor_id=self.actor_id,  # Регистрируем у ВЫЗЫВАЮЩЕГО
                correlation_id=message.correlation_id,
                total_pending=len(self._pending_futures)
            )
        else:
            self.logger.warning(
                "no_correlation_id_set",
                actor_id=self.actor_id,
                message_id=message.id
            )
        
        async def cleanup():
            """Очистка после завершения (успех или таймаут)."""
            if message.correlation_id and message.correlation_id in self._pending_futures:
                del self._pending_futures[message.correlation_id]
                self.logger.info(
                    "pending_future_cleaned",
                    actor_id=self.actor_id,
                    correlation_id=message.correlation_id
                )
        
        # Устанавливаем обработчик ответа
        if self.system:
            await self.system.send(message)
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
                await cleanup()
                # DEBUG: Логируем успешное получение ответа
                self.logger.info(
                    "ask_response_received",
                    actor_id=self.actor_id,
                    message_id=message.id,
                    correlation_id=message.correlation_id,
                    result_type=type(result.payload).__name__ if result.payload else "None"
                )
                return result
            except asyncio.TimeoutError:
                self.logger.error(
                    "ask_timeout",
                    actor_id=self.actor_id,
                    message_id=message.id,
                    correlation_id=message.correlation_id,
                    timeout=timeout
                )
                await cleanup()
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