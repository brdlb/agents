"""Web Search Actor - Agentic Search с анализом контента."""

import uuid
from typing import Any

from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType, WebSearchQuery, CommandResult
from src.executor.web_search import WebSearchExecutor
from src.actors.actors.content_analyzer_actor import ContentAnalyzerActor
from src.actors.actors.page_loader_actor import PageLoaderActor
from src.actors.actors.page_summarizer_actor import PageSummarizerActor
from src.llm.providers.base import LLMProvider
from src.utils.logging import get_logger


class WebSearchActor(Actor):
    """Актор для выполнения веб-поиска с агентным подходом.
    
    Поток:
    1. DuckDuckGo -> получает URL
    2. ContentAnalyzer -> выбирает релевантные URL
    3. PageLoader -> параллельно загружает контент
    4. PageSummarizer -> суммаризирует и формирует ответ
    """
    
    def __init__(self, 
                 executor: WebSearchExecutor,
                 llm_provider: LLMProvider = None,
                 actor_id: str = None):
        super().__init__(actor_id)
        self.executor = executor
        self.llm_provider = llm_provider
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
        self.logger.info("agentic_search_start", query=query)

        try:
            # Шаг 1: DuckDuckGo поиск
            self.logger.info("step1_ddg_search", query=query)
            search_results = await self.executor.search(query)
            
            if not search_results or all(r.get("error") for r in search_results):
                self.logger.warning("no_search_results", query=query)
                result = CommandResult(
                    success=False,
                    error="No search results found"
                )
                await self._send_response(message, result)
                return
            
            self.logger.info("search_results_found", count=len(search_results))
            
            # Если нет LLM провайдера, возвращаем простые результаты
            if not self.llm_provider:
                result = CommandResult(
                    success=True,
                    data={
                        "results": search_results,
                        "query": query,
                        "type": "simple"
                    }
                )
                await self._send_response(message, result)
                return
            
            # Шаг 2: Content Analyzer - выбираем URL
            self.logger.info("step2_content_analysis")
            content_analyzer = ContentAnalyzerActor(provider=self.llm_provider)
            await self.spawn_child(content_analyzer)
            
            analysis_result = await self._ask_child(
                content_analyzer,
                {
                    "query": query,
                    "results": search_results
                },
                "analyze_search_results"
            )
            
            selected_urls = analysis_result.payload.get("selected_urls", [])
            if not selected_urls:
                selected_urls = [r.get("href") for r in search_results[:3] if r.get("href")]
            
            self.logger.info("urls_selected", count=len(selected_urls))
            
            # Шаг 3: Page Loader - загружаем страницы параллельно
            self.logger.info("step3_page_loading")
            page_loader = PageLoaderActor()
            await self.spawn_child(page_loader)
            
            load_result = await self._ask_child(
                page_loader,
                {"urls": selected_urls},
                "load_pages"
            )
            
            loaded_pages = load_result.payload.get("pages", [])
            self.logger.info("pages_loaded", count=len(loaded_pages))
            
            # Шаг 4: Page Summarizer - суммаризация и финальный ответ
            self.logger.info("step4_summarization")
            page_summarizer = PageSummarizerActor(provider=self.llm_provider)
            await self.spawn_child(page_summarizer)
            
            summarize_result = await self._ask_child(
                page_summarizer,
                {"query": query, "pages": loaded_pages},
                "summarize_pages"
            )
            
            final_answer = summarize_result.payload.get("final_answer", "")
            summaries = summarize_result.payload.get("summaries", [])
            
            result = CommandResult(
                success=True,
                data={
                    "query": query,
                    "type": "agentic",
                    "final_answer": final_answer,
                    "summaries": summaries,
                    "urls_analyzed": selected_urls
                }
            )
            
        except Exception as e:
            self.logger.error("agentic_search_error", error=str(e))
            result = CommandResult(
                success=False,
                error=f"Agentic search failed: {str(e)}"
            )

        await self._send_response(message, result)

    async def _ask_child(self, child_actor: Actor, payload: dict, message_type: str) -> ActorMessage:
        """Вспомогательный метод для запроса к дочернему актору."""
        correlation_id = f"{message_type}_{uuid.uuid4().hex[:8]}"
        
        # Регистрируем Future в родителе (self)
        future = asyncio.Future()
        self._pending_futures[correlation_id] = future
        
        # Отправляем сообщение
        await self.tell(ActorMessage(
            id=correlation_id,
            sender=self.actor_id,
            recipient=child_actor.actor_id,
            payload=payload,
            message_type=message_type,
            reply_to=self.actor_id,
            correlation_id=correlation_id
        ))
        
        # Ждём ответ
        try:
            result = await asyncio.wait_for(future, timeout=120.0)
            if correlation_id in self._pending_futures:
                del self._pending_futures[correlation_id]
            return result
        except asyncio.TimeoutError:
            if correlation_id in self._pending_futures:
                del self._pending_futures[correlation_id]
            raise

    async def _send_response(self, message: ActorMessage, result: CommandResult):
        """Отправка результата обратно."""
        if message.reply_to:
            self.logger.info(
                "sending_response_back",
                actor_id=self.actor_id,
                reply_to=message.reply_to,
                original_sender=message.sender,
                correlation_id=message.correlation_id,
                payload_type=type(result).__name__
            )
            reply_message = ActorMessage(
                id=f"reply_{uuid.uuid4().hex[:8]}",
                sender=self.actor_id,
                recipient=message.reply_to,
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id,
                reply_to=message.sender
            )
            await self.tell(reply_message)
        else:
            self.logger.info("no_reply_address", message_id=message.id)


# Добавляем импорт asyncio
import asyncio
