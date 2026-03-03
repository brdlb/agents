"""Система управления акторами."""

import asyncio
from typing import Dict, Optional

from src.actors.base import Actor
from src.actors.message import ActorMessage
from src.utils.logging import get_logger


class ActorSystem:
    """Глобальная система акторов."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ActorSystem, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Защита от повторной инициализации
        if ActorSystem._initialized:
            return
        self.actors: Dict[str, Actor] = {}
        self._message_queue = asyncio.Queue()
        self.logger = get_logger(self.__class__.__name__)
        ActorSystem._initialized = True

    async def spawn(self, actor: Actor, parent_id: Optional[str] = None) -> str:
        """Создание нового актора."""
        self.actors[actor.actor_id] = actor
        actor.system = self
        actor.parent_id = parent_id
        if parent_id:
            parent = self.actors.get(parent_id)
            if parent:
                parent.children.add(actor.actor_id)
        
        # Запускаем актор в отдельной задаче
        asyncio.create_task(actor._run())
        self.logger.info("actor_spawned", actor_id=actor.actor_id, parent_id=parent_id)
        return actor.actor_id

    async def send(self, message: ActorMessage):
        """Отправка сообщения актору."""
        actor = self.actors.get(message.recipient)
        if actor:
            await actor.mailbox.put(message)
            
            # DEBUG: Логируем получение сообщения
            self.logger.info(
                "message_queued",
                recipient=message.recipient,
                sender=message.sender,
                message_id=message.id,
                message_type=message.message_type,
                correlation_id=message.correlation_id
            )
            
            # DEBUG: Диагностика маршрутизации ответа
            self.logger.info(
                "response_routing_check",
                has_correlation_id=bool(message.correlation_id),
                has_reply_to=bool(message.reply_to),
                reply_to_actor_exists=message.reply_to in self.actors if message.reply_to else False,
                message_type=str(message.message_type)
            )
            
            # ИСПРАВЛЕНИЕ: Вызываем _handle_response ТОЛЬКО для сообщений-ответов
            # (не для исходных запросов!). Проверяем message_type == RESPONSE
            if (message.correlation_id and message.reply_to and 
                message.message_type.value == "response"):
                sender_actor = self.actors.get(message.reply_to)
                if sender_actor:
                    # DEBUG: Логируем состояние pending_futures перед обработкой
                    self.logger.info(
                        "handling_response_debug",
                        sender_actor_id=sender_actor.actor_id,
                        correlation_id=message.correlation_id,
                        pending_futures_keys=list(sender_actor._pending_futures.keys())
                    )
                    # Вызываем _handle_response для обработки ответа
                    await sender_actor._handle_response(message)
                    self.logger.info(
                        "response_routed",
                        original_sender=message.reply_to,
                        correlation_id=message.correlation_id
                    )
        else:
            self.logger.warning("actor_not_found", actor_id=message.recipient)

    async def stop(self, actor_id: str):
        """Остановка актора."""
        actor = self.actors.get(actor_id)
        if actor:
            await actor.stop()
            # Удаляем из списка детей у родителя
            if actor.parent_id:
                parent = self.actors.get(actor.parent_id)
                if parent:
                    parent.children.discard(actor_id)
            del self.actors[actor_id]
            self.logger.info("actor_stopped", actor_id=actor_id)

    def get_actor(self, actor_id: str) -> Optional[Actor]:
        """Получение актора по ID."""
        return self.actors.get(actor_id)

    async def broadcast(self, message: ActorMessage, actor_ids: list[str]):
        """Рассылка сообщения нескольким акторам."""
        for actor_id in actor_ids:
            msg_copy = ActorMessage(
                id=message.id,
                sender=message.sender,
                recipient=actor_id,
                payload=message.payload,
                message_type=message.message_type,
                reply_to=message.reply_to,
                correlation_id=message.correlation_id,
                timestamp=message.timestamp
            )
            await self.send(msg_copy)

    async def stop_all(self):
        """Остановка всех акторов."""
        actor_ids = list(self.actors.keys())
        for actor_id in actor_ids:
            await self.stop(actor_id)