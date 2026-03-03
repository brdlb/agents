"""Web Search Executor - поиск информации через DuckDuckGo с извлечением контента."""

import asyncio
from typing import List, Dict, Any, Optional
import trafilatura
from duckduckgo_search import DDGS

from src.utils.logging import get_logger

logger = get_logger(__name__)


class WebSearchExecutor:
    """Класс для выполнения веб-поиска с извлечением контента."""

    def __init__(self, max_results: int = 3):
        self.max_results = max_results

    async def search(self, query: str) -> List[Dict[str, str]]:
        """
        Выполняет поиск в DuckDuckGo и извлекает контент с найденных страниц.
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список результатов (заголовок, ссылка, контент)
        """
        logger.info("web_search_executing", query=query)
        try:
            # Используем asyncio.to_thread для запуска синхронного поиска в отдельном потоке
            results = await asyncio.to_thread(self._sync_search_with_content, query)
            return results
        except Exception as e:
            logger.error("web_search_error", query=query, error=str(e))
            return [{"error": f"Search failed: {str(e)}"}]

    def _sync_search_with_content(self, query: str) -> List[Dict[str, str]]:
        """Синхронная обертка для поиска с извлечением контента."""
        with DDGS() as ddgs:
            # Получаем результаты поиска
            raw_results = ddgs.text(query, max_results=self.max_results)
            
            results = []
            for r in raw_results:
                url = r.get("href", "")
                title = r.get("title", "")
                
                if not url:
                    continue
                    
                # Извлекаем контент с страницы
                try:
                    downloaded = trafilatura.fetch_url(url)
                    if downloaded:
                        # Извлекаем чистый текст
                        text = trafilatura.extract(downloaded)
                        # Ограничиваем длину контента
                        if text and len(text) > 5000:
                            text = text[:5000] + "..."
                        
                        results.append({
                            "title": title,
                            "href": url,
                            "body": text or r.get("body", "")
                        })
                    else:
                        # Если не удалось скачать, используем описание из поиска
                        results.append({
                            "title": title,
                            "href": url,
                            "body": r.get("body", "")
                        })
                except Exception as e:
                    logger.warning("content_extraction_error", url=url, error=str(e))
                    # Используем описание из поиска при ошибке
                    results.append({
                        "title": title,
                        "href": url,
                        "body": r.get("body", "")
                    })
            
            return results
