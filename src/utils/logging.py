"""Конфигурация логирования с использованием structlog."""

import logging
import sys
from typing import Any

import structlog

from src.utils.config import settings


def setup_logging() -> None:
    """Настройка structlog согласно конфигурации."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Настройка processing
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
            if settings.log_format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Настройка стандартного логирования
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Silence verbose logs from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.bot").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING)


def get_logger(name: str | None = None, **initial_context: Any) -> structlog.BoundLogger:
    """Получение логера с контекстом."""
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


