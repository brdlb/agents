"""Актор для веб-поиска."""

import uuid
from typing import Any

from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType, WebSearchQuery, CommandResult
from src.executor.web_search import WebSearchExecutor
from src.utils.logging import get_logger


class WebSearchActor(Actor):
    """Актор для выполнения веб-поиска."""
    
    def __init__(self, 
                 executor: WebSearchExecutor,
                 actor_id: str = None):
        super().__init__(actor_id)
        self.executor = executor
        self.logger = get_logger(self.__class__.__name__)

    async def receive(self, message: ActorMessage):
        """Обработка сообщений."""
        if message.message_type == MessageType.WEB_SEARCH:
            await self._handle_web_search(message)
        else:
            self.logger.warning("unknown_message_type", 
                              actor_id=self.actor_id, 
                              message_type=message.message_type)

    async def _handle_web_search(self, message: ActorMessage):
        """Обработка запроса на веб-поиск."""
        if not isinstance(message.payload, WebSearchQuery):
            self.logger.error("invalid_payload", actor_id=self.actor_id)
            return

        query = message.payload.query
        max_results = message.payload.max_results

        try:
            # Выполняем поиск
            results = await self.executor.search(query)
            result = CommandResult(
                success=True,
                data={
                    "results": results,
                    "query": query,
                    "max_results": max_results
                }
            )
        except Exception as e:
            result = CommandResult(
                success=False,
                error=f"Web search failed: {str(e)}"
            )

        # Отправляем результат обратно
        if message.reply_to:
            reply_message = ActorMessage(
                id=f"reply_{uuid.uuid4().hex[:8]}",
                sender=self.actor_id,
                recipient=message.reply_to,
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id
            )
            await self.tell(reply_message)
        else:
            self.logger.info("no_reply_address", message_id=message.id)