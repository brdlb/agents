"""Web Search Executor - поиск информации через DuckDuckGo."""

import asyncio
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS

from src.utils.logging import get_logger

logger = get_logger(__name__)

class WebSearchExecutor:
    """Класс для выполнения веб-поиска."""

    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    async def search(self, query: str) -> List[Dict[str, str]]:
        """
        Выполняет поиск в DuckDuckGo.
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список результатов (заголовок, ссылка, описание)
        """
        logger.info("web_search_executing", query=query)
        try:
            # Используем asyncio.to_thread для запуска синхронного поиска в отдельном потоке
            results = await asyncio.to_thread(self._sync_search, query)
            return results
        except Exception as e:
            logger.error("web_search_error", query=query, error=str(e))
            return [{"error": f"Search failed: {str(e)}"}]

    def _sync_search(self, query: str) -> List[Dict[str, str]]:
        """Синхронная обертка для поиска."""
        with DDGS() as ddgs:
            raw_results = ddgs.text(query, max_results=self.max_results)
            results = []
            for r in raw_results:
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
            return results
