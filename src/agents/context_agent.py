"""Context Agent - анализ и архивация контекста диалога."""

import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import aiofiles

from src.llm.providers.base import LLMProvider, LLMMessage
from src.utils.logging import get_logger

logger = get_logger(__name__)

class ContextAgent:
    """Агент для анализа смены контекста и архивации диалогов."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def analyze_and_archive(
        self, 
        history: List[Dict[str, Any]], 
        user_id: int, 
        user_dir: Path
    ) -> Optional[Dict[str, Any]]:
        """
        Анализирует историю на предмет смены контекста.
        Если контекст сменился, архивирует старый.
        """
        if len(history) < 4:  # Слишком мало сообщений для анализа смены контекста
            return None

        # Просим LLM определить, сменился ли контекст в последнем сообщении
        # и выделить предыдущую законченную тему.
        
        prompt = f"""Analyze the following dialogue history. Your task is to determine if the user has significantly changed the topic in the VERY LAST message compared to the previous messages.

Dialogue history:
{json.dumps(history, ensure_ascii=False, indent=2)}

If the topic has changed, identify all messages belonging to the PREVIOUS topic.
Respond ONLY with a JSON object in the following format:
{{
  "topic_changed": true,
  "previous_topic_title": "short_latin_slug",
  "previous_topic_summary": "Short description of what was discussed",
  "messages_to_archive_indices": [0, 1, 2, ...]
}}
If topic_changed is false, return the same structure with topic_changed: false."""

        try:
            response = await self.provider.generate([LLMMessage(role="system", content=prompt)])
            # Пытаемся извлечь JSON если модель добавила лишний текст
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            if result.get("topic_changed") and result.get("messages_to_archive_indices"):
                return await self._archive_topic(result, history, user_id, user_dir)
            
            return None
        except Exception as e:
            logger.error("context_analysis_error", error=str(e))
            return None

    async def _archive_topic(
        self, 
        analysis: Dict[str, Any], 
        history: List[Dict[str, Any]], 
        user_id: int, 
        user_dir: Path
    ) -> Dict[str, Any]:
        """Сохраняет старый контекст в MD файл."""
        title = analysis["previous_topic_title"]
        summary = analysis["previous_topic_summary"]
        indices = analysis["messages_to_archive_indices"]
        
        archive_dir = user_dir / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{title}.md"
        file_path = archive_dir / filename
        
        md_content = f"# Topic: {title}\n\nSummary: {summary}\n\n## Dialogue Details\n\n"
        for idx in indices:
            if idx < len(history):
                msg = history[idx]
                role = msg.get("role", "unknown").capitalize()
                content = msg.get("content") or "[Tool Call/Result]"
                md_content += f"**{role}**: {content}\n\n"
        
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(md_content)
            
        return {
            "filename": filename,
            "title": title,
            "summary": summary,
            "indices": indices
        }
