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