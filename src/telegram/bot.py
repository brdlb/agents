"""Telegram Bot - основной класс бота."""

import asyncio
from typing import Optional

from telegram import Update, constants
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.agents.main_agent import MainAgent
from src.agents.actor_agent import ActorAgent
from src.llm.factory import LLMFactory
from src.session.manager import SessionManager
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """Класс для управления Telegram ботом."""

    def __init__(self, token: Optional[str] = None):
        """Инициализация бота.
        
        Args:
            token: Токен бота (если None, берется из настроек)
        """
        self.token = token or settings.telegram_bot_token
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in settings or provided")
        
        self.session_manager = SessionManager()
        self.llm_provider = LLMFactory.get_default()
        self.application: Optional[Application] = None

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        
        user = await self.session_manager.get_or_create_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        # Создаем новую сессию, если ее нет
        session = await self.session_manager.get_latest_session(user_id)
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        welcome_text = (
            f"Привет, {user.first_name or 'пользователь'}! 👋\n\n"
            "Я твоя агентная система. Я могу помогать тебе в решении задач, "
            "писать код, выполнять команды и работать с контекстом документов.\n\n"
            "Просто напиши мне свой запрос!"
        )
        await update.message.reply_text(welcome_text)

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений."""
        user_id = update.effective_user.id
        text = update.message.text
        chat_id = update.effective_chat.id
        
        if not text:
            return

        logger.info("message_received", user_id=user_id, text_length=len(text))
        
        # Получаем или создаем сессию
        session = await self.session_manager.get_latest_session(user_id)
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        # Инициализируем память пользователя если нужно
        await self.session_manager.ensure_user_memory(user_id)
        user_dir = self.session_manager.get_user_dir(user_id)
        
        # Отправляем сообщение о начале обработки
        progress_message = await update.message.reply_text("⏳ Обрабатываю запрос...")
        
        async def on_progress(msg: str):
            try:
                if msg != "🤖 Думаю...":
                    await progress_message.edit_text(msg)
            except Exception:
                pass

        # Задача для периодической отправки "петает..."
        async def send_typing_periodically():
            while True:
                try:
                    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                except Exception:
                    pass
                await asyncio.sleep(3)

        typing_task = asyncio.create_task(send_typing_periodically())

        try:
            # Создаем агента
            agent = ActorAgent(
                provider=self.llm_provider,
                on_progress=on_progress
            )
            
            # Подготавливаем историю
            history = [
                {"role": m.role, "content": m.content}
                for m in session.messages[-10:]  # Последние 10 сообщений
            ]
            
            # Запускаем агента
            response_text, new_messages = await agent.run(
                user_input=text, 
                history=history,
                user_id=user_id,
                user_dir=user_dir
            )
        finally:
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
        
        # Удаляем сообщение о прогрессе и отправляем финальный ответ
        try:
            await progress_message.delete()
        except Exception:
            pass
            
        await update.message.reply_text(response_text)
        
        # Сохраняем диалог (включая промежуточные сообщения)
        await self.session_manager.add_message(user_id, session.id, "user", text)
        for msg in new_messages:
            await self.session_manager.add_message(
                user_id=user_id,
                session_id=session.id,
                role=msg["role"],
                content=msg.get("content"),
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id")
            )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок."""
        logger.error("telegram_error", error=str(context.error), update=str(update))
        if isinstance(update, Update) and update.message:
            await update.message.reply_text("Произошла ошибка при обработке вашего запроса. Попробуйте позже.")

    def run(self):
        """Запуск бота."""
        logger.info("bot_starting")
        self.application = ApplicationBuilder().token(self.token).build()
        
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.start_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.message_handler))
        self.application.add_error_handler(self.error_handler)
        
        # Запуск (блокирующий вызов)
        self.application.run_polling()


if __name__ == "__main__":
    # Для отладки
    bot = TelegramBot()
    bot.run()
