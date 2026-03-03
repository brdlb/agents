"""Gemini CLI LLM Provider - использование Gemini CLI для запросов."""

import asyncio
import json
import os
import subprocess
import sys
from typing import Any

from src.llm.providers.base import LLMMessage, LLMProvider, LLMResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _find_gemini_executable() -> str:
    """Поиск исполняемого файла gemini.
    
    Returns:
        Путь к исполняемому файлу
    """
    # Сначала пробуем найти в PATH
    # Определяем, какую команду использовать
    if sys.platform == "win32":
        # На Windows пробуем gemini.cmd
        for cmd in ["gemini.cmd", "gemini"]:
            try:
                result = subprocess.run(
                    ["where", cmd],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if result.returncode == 0:
                    return cmd
            except Exception:
                pass
        # Если не найден, возвращаем стандартную команду
        return "gemini.cmd"
    else:
        return "gemini"


class GeminiCLIProvider(LLMProvider):
    """Провайдер для Gemini CLI.
    
    Использует локально установленный gemini CLI для генерации ответов.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash-lite",
        **kwargs: Any
    ):
        """Инициализация Gemini CLI провайдера.
        
        Args:
            api_key: Не используется (CLI использует локальную аутентификацию)
            model: Модель для использования (по умолчанию gemini-2.5-flash-lite)
            **kwargs: Дополнительные параметры
        """
        super().__init__(api_key=api_key, model=model, **kwargs)
        self._gemini_cmd = _find_gemini_executable()
        logger.info("gemini_cli_provider_init", command=self._gemini_cmd)
        
    @property
    def provider_name(self) -> str:
        return "gemini-cli"
    
    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int | None = 2048,
        **kwargs: Any
    ) -> LLMResponse:
        """Генерация текста через Gemini CLI.
        
        Args:
            messages: Список сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            **kwargs: Дополнительные параметры
            
        Returns:
            LLMResponse с сгенерированным текстом
        """
        # Форматируем сообщения в текст для Gemini CLI
        prompt = self._format_messages(messages)
        
        logger.info(
            "gemini_cli_request_start",
            provider="gemini-cli",
            model=self.model,
            message_count=len(messages),
            prompt_length=len(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        try:
            # Формируем команду - используем stdin для промпта
            cmd = f'{self._gemini_cmd} --output-format json --approval-mode yolo'
            
            # На Windows используем shell=True
            shell = sys.platform == "win32"
            
            if shell:
                # Используем create_subprocess_shell для Windows
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                # На Unix используем create_subprocess_exec
                cmd_list = [
                    self._gemini_cmd,
                    "--output-format", "json",
                    "--approval-mode", "yolo"
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd_list,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            
            # Отправляем промпт через stdin
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode('utf-8')),
                    timeout=180  # 3 минуты timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise RuntimeError("Gemini CLI timed out")
            
            if process.returncode != 0:
                stderr_decoded = stderr.decode('utf-8', errors='replace') if stderr else ""
                stdout_decoded = stdout.decode('utf-8', errors='replace') if stdout else ""
                error_msg = stderr_decoded or stdout_decoded or "Unknown error"
                logger.error(
                    "gemini_cli_error",
                    provider="gemini-cli",
                    returncode=process.returncode,
                    error=error_msg[:500],
                    stdout_preview=stdout_decoded[:200],
                )
                raise RuntimeError(f"Gemini CLI error: {error_msg}")
            
            # Парсим JSON ответ
            response_text = stdout.decode('utf-8', errors='replace').strip()
            
            # Убираем служебные строки из вывода (предупреждения YOLO и т.д.)
            lines = response_text.split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                # Пропускаем служебные строки
                if 'YOLO mode' in line or 'Loaded cached' in line or line.strip() == '':
                    continue
                # Начинаем JSON
                if line.strip().startswith('{'):
                    in_json = True
                if in_json:
                    json_lines.append(line)
            
            json_text = '\n'.join(json_lines)
            
            try:
                response_json = json.loads(json_text)
            except json.JSONDecodeError:
                # Если не JSON, возвращаем как есть
                logger.warning(
                    "gemini_cli_non_json_response",
                    response=response_text[:500]
                )
                return LLMResponse(
                    content=response_text,
                    model=self.model,
                    usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    finish_reason="stop",
                    tool_calls=None
                )
            
            # Извлекаем ответ
            content = response_json.get("response", "")
            stats = response_json.get("stats", {})
            
            # Подсчитываем токены из статистики
            prompt_tokens = 0
            completion_tokens = 0
            if stats.get("models", {}).get(self.model, {}).get("tokens"):
                tokens_data = stats["models"][self.model]["tokens"]
                prompt_tokens = tokens_data.get("prompt", 0)
                completion_tokens = tokens_data.get("candidates", 0)
            
            logger.info(
                "gemini_cli_request_complete",
                provider="gemini-cli",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                content_length=len(content),
            )
            
            return LLMResponse(
                content=content,
                model=self.model,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                },
                finish_reason="stop",
                tool_calls=None
            )
            
        except Exception as e:
            logger.error(
                "gemini_cli_unexpected_error",
                provider="gemini-cli",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise
    
    def _format_messages(self, messages: list[LLMMessage]) -> str:
        """Форматирование сообщений в текстовый промпт для Gemini CLI.
        
        Args:
            messages: Список сообщений
            
        Returns:
            Текстовый промпт
        """
        prompt_parts = []
        
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"Система: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"Пользователь: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Ассистент: {msg.content}")
            elif msg.role == "tool":
                # Инструменты обычно не нужны для простого текстового промпта
                prompt_parts.append(f"Результат: {msg.content}")
        
        return "\n\n".join(prompt_parts)
    
    async def get_token_count(self, text: str) -> int:
        """Подсчет токенов (приблизительный).
        
        Args:
            text: Текст для подсчета
            
        Returns:
            Приблизительное количество токенов
        """
        # Простое приближение: ~4 символа на токен
        return len(text) // 4
    
    async def validate_connection(self) -> bool:
        """Проверка доступности Gemini CLI.
        
        Returns:
            True если CLI доступен
        """
        try:
            import sys
            shell = sys.platform == "win32"
            
            if shell:
                process = await asyncio.create_subprocess_shell(
                    f"{self._gemini_cmd} --version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    self._gemini_cmd, "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            
            await process.communicate()
            
            if process.returncode == 0:
                logger.info(
                    "gemini_cli_connection_check_success",
                    provider="gemini-cli"
                )
                return True
            return False
        except Exception as e:
            logger.error(
                "gemini_cli_connection_check_failed",
                provider="gemini-cli",
                error=str(e)
            )
            return False
    
    async def close(self) -> None:
        """Закрытие соединения (не требуется для CLI)."""
        pass
