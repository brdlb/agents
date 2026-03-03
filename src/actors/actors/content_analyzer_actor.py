"""Content Analyzer Actor - анализирует поисковую выдачу и выбирает страницы для загрузки."""

import uuid
from typing import Any, List, Dict

from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType
from src.llm.providers.base import LLMProvider
from src.utils.logging import get_logger


class ContentAnalyzerActor(Actor):
    """Актор для анализа поисковой выдачи.
    
    Принимает результаты поиска и запрос пользователя.
    Возвращает список URL которые нужно загрузить для более детального анализа.
    """
    
    def __init__(self, provider: LLMProvider, actor_id: str = None):
        super().__init__(actor_id)
        self.provider = provider
        self.logger = get_logger(self.__class__.__name__)

    async def receive(self, message: ActorMessage):
        """Обработка сообщений."""
        if message.message_type == "analyze_search_results":
            await self._handle_analyze(message)
        else:
            self.logger.warning("unknown_message_type", 
                              actor_id=self.actor_id, 
                              message_type=message.message_type)

    async def _handle_analyze(self, message: ActorMessage):
        """Анализ поисковой выдачи и выбор URL для загрузки."""
        query = message.payload.get("query", "")
        search_results = message.payload.get("results", [])
        
        self.logger.info("analyzing_results", query=query, result_count=len(search_results))
        
        # Формируем контекст для LLM
        results_text = "\n".join([
            f"{i+1}. {r.get('title', 'No title')}\n   URL: {r.get('href', 'No URL')}\n   Description: {r.get('body', 'No description')}"
            for i, r in enumerate(search_results[:10])
        ])
        
        system_prompt = """Ты - аналитик поисковой выдачи. Твоя задача:
1. Проанализировать результаты поиска по запросу пользователя
2. Выбрать 3-5 наиболее релевантных URL которые стоит прочитать для ответа на запрос
3. Вернуть JSON массив выбранных URL

Отвечай ТОЛЬКО JSON массивом URL, например: ["url1", "url2", "url3"]"""
        
        user_prompt = f"""Запрос пользователя: {query}

Результаты поиска:
{results_text}

Какие URL нужно прочитать для полного ответа на запрос?"""
        
        try:
            response = await self.provider.generate(
                [{"role": "system", "content": system_prompt},
                 {"role": "user", "content": user_prompt}],
                max_tokens=500
            )
            
            # Парсим ответ - извлекаем URL из текста
            selected_urls = self._extract_urls(response.content)
            
            self.logger.info("analysis_complete", selected_count=len(selected_urls))
            
        except Exception as e:
            self.logger.error("analysis_error", error=str(e))
            # Fallback: возвращаем все URL
            selected_urls = [r.get("href", "") for r in search_results[:3] if r.get("href")]
        
        # Отправляем результат
        if message.reply_to:
            reply_message = ActorMessage(
                id=f"reply_{uuid.uuid4().hex[:8]}",
                sender=self.actor_id,
                recipient=message.reply_to,
                payload={
                    "success": True,
                    "query": query,
                    "selected_urls": selected_urls
                },
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id
            )
            await self.tell(reply_message)

    def _extract_urls(self, text: str) -> List[str]:
        """Извлечение URL из текста ответа."""
        import re
        # Ищем URL в тексте
        url_pattern = r'https?://[^\s"\]]+'
        urls = re.findall(url_pattern, text)
        # Убираем дубликаты
        return list(dict.fromkeys(urls))[:5]
