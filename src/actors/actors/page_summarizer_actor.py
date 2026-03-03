"""Page Summarizer Actor - делает summarization контента страниц."""

import uuid
from typing import Any, List, Dict

from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType
from src.llm.providers.base import LLMProvider
from src.utils.logging import get_logger


class PageSummarizerActor(Actor):
    """Актор для суммаризации контента страниц.
    
    Принимает загруженные страницы и запрос пользователя.
    Возвращает краткое изложение каждой страницы и итоговый ответ.
    """
    
    def __init__(self, provider: LLMProvider, actor_id: str = None):
        super().__init__(actor_id)
        self.provider = provider
        self.logger = get_logger(self.__class__.__name__)

    async def receive(self, message: ActorMessage):
        """Обработка сообщений."""
        if message.message_type == "summarize_pages":
            await self._handle_summarize(message)
        else:
            self.logger.warning("unknown_message_type", 
                              actor_id=self.actor_id, 
                              message_type=message.message_type)

    async def _handle_summarize(self, message: ActorMessage):
        """Суммаризация страниц и формирование ответа."""
        query = message.payload.get("query", "")
        pages = message.payload.get("pages", [])
        
        self.logger.info("summarizing_pages", page_count=len(pages), query=query)
        
        # Суммаризируем каждую страницу
        summaries = []
        for page in pages:
            if not page.get("success"):
                continue
                
            url = page.get("url", "")
            content = page.get("content", "")
            
            if not content:
                continue
            
            # Ограничиваем контент для LLM
            if len(content) > 8000:
                content = content[:8000] + "..."
            
            summary = await self._summarize_page(query, content, url)
            summaries.append({
                "url": url,
                "summary": summary
            })
        
        # Формируем финальный ответ
        final_answer = await self._make_final_answer(query, summaries)
        
        # Отправляем результат
        if message.reply_to:
            reply_message = ActorMessage(
                id=f"reply_{uuid.uuid4().hex[:8]}",
                sender=self.actor_id,
                recipient=message.reply_to,
                payload={
                    "success": True,
                    "query": query,
                    "summaries": summaries,
                    "final_answer": final_answer
                },
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id
            )
            await self.tell(reply_message)

    async def _summarize_page(self, query: str, content: str, url: str) -> str:
        """Суммаризация одной страницы."""
        system_prompt = """Ты - эксперт по анализу веб-контента. Твоя задача:
1. Кратко изложить содержание страницы (2-3 предложения)
2. Выделить информацию релевантную запросу пользователя

Отвечай на русском языке, кратко и по существу."""
        
        user_prompt = f"""Запрос пользователя: {query}

URL страницы: {url}

Содержимое страницы:
{content}

Краткое изложение:"""
        
        try:
            response = await self.provider.generate(
                [{"role": "system", "content": system_prompt},
                 {"role": "user", "content": user_prompt}],
                max_tokens=300
            )
            return response.content.strip()
        except Exception as e:
            self.logger.error("summarize_error", url=url, error=str(e))
            return f"Ошибка при суммаризации: {str(e)}"

    async def _make_final_answer(self, query: str, summaries: List[Dict]) -> str:
        """Формирование финального ответа на основе суммаризаций."""
        if not summaries:
            return "Не удалось получить информацию из найденных страниц."
        
        summaries_text = "\n\n".join([
            f"Источник: {s['url']}\n{s['summary']}"
            for s in summaries
        ])
        
        system_prompt = """Ты - AI ассистент. На основе предоставленных источников ответь на вопрос пользователя.
Отвечай на русском языке, структурированно и подробно.
Если информации недостаточно - укажи это явно."""
        
        user_prompt = f"""Запрос: {query}

Найденная информация:
{summaries_text}

Твой ответ:"""
        
        try:
            response = await self.provider.generate(
                [{"role": "system", "content": system_prompt},
                 {"role": "user", "content": user_prompt}],
                max_tokens=1500
            )
            return response.content.strip()
        except Exception as e:
            self.logger.error("final_answer_error", error=str(e))
            return f"Не удалось сформировать ответ: {str(e)}"
