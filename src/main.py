"""Main entry point for the Agent System."""

import asyncio
import sys

from src.telegram.bot import TelegramBot
from src.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


def main():
    """Основная функция запуска системы."""
    setup_logging()
    logger.info("application_starting")
    
    try:
        bot = TelegramBot()
        bot.run()
    except Exception as e:
        logger.critical("application_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("application_stopped_by_user")
    except Exception as e:
        logger.critical("unhandled_exception", error=str(e))
        sys.exit(1)
