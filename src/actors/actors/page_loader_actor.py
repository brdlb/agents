"""Page Loader Actor - загружает веб-страницы параллельно."""

import asyncio
import uuid
from typing import List, Dict, Any, Optional

import trafilatura

from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType
from src.utils.logging import get_logger


class PageLoaderActor(Actor):
    """Актор для параллельной загрузки веб-страниц."""
    
    def __init__(self, actor_id: str = None):
        super().__init__(actor_id)
        self.logger = get_logger(self.__class__.__name__)

    async def receive(self, message: ActorMessage):
        """Обработка сообщений."""
        if message.message_type == "load_pages":
            await self._handle_load_pages(message)
        else:
            self.logger.warning("unknown_message_type", 
                              actor_id=self.actor_id, 
                              message_type=message.message_type)

    async def _handle_load_pages(self, message: ActorMessage):
        """Загрузка списка страниц параллельно."""
        urls = message.payload.get("urls", [])
        self.logger.info("loading_pages", count=len(urls))
        
        # Загружаем все страницы параллельно
        tasks = [self._load_single_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Формируем результаты
        loaded_pages = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                self.logger.warning("page_load_error", url=url, error=str(result))
                loaded_pages.append({
                    "url": url,
                    "error": str(result)
                })
            else:
                loaded_pages.append(result)
        
        # Отправляем результат обратно
        if message.reply_to:
            reply_message = ActorMessage(
                id=f"reply_{uuid.uuid4().hex[:8]}",
                sender=self.actor_id,
                recipient=message.reply_to,
                payload={
                    "success": True,
                    "pages": loaded_pages
                },
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id
            )
            await self.tell(reply_message)

    async def _load_single_url(self, url: str) -> Dict[str, Any]:
        """Загрузка одной страницы."""
        try:
            downloaded = await asyncio.to_thread(trafilatura.fetch_url, url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                return {
                    "url": url,
                    "content": text,
                    "success": True
                }
            else:
                return {
                    "url": url,
                    "error": "Failed to download",
                    "success": False
                }
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "success": False
            }
