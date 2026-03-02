"""Актор для выполнения команд."""

import uuid
from typing import Any

from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType, ExecuteCommand, CommandResult
from src.executor.command import CommandExecutor
from src.agents.safety_agent import SafetyAgent
from src.utils.logging import get_logger


class CommandActor(Actor):
    """Актор для выполнения shell-команд."""
    
    def __init__(self, 
                 safety_agent: SafetyAgent,
                 executor: CommandExecutor,
                 actor_id: str = None):
        super().__init__(actor_id)
        self.safety_agent = safety_agent
        self.executor = executor
        self.logger = get_logger(self.__class__.__name__)

    async def receive(self, message: ActorMessage):
        """Обработка сообщений."""
        if message.message_type == MessageType.EXECUTE_COMMAND:
            await self._handle_execute_command(message)
        else:
            self.logger.warning("unknown_message_type", 
                              actor_id=self.actor_id, 
                              message_type=message.message_type)

    async def _handle_execute_command(self, message: ActorMessage):
        """Обработка запроса на выполнение команды."""
        if not isinstance(message.payload, ExecuteCommand):
            self.logger.error("invalid_payload", actor_id=self.actor_id)
            return

        command_str = message.payload.command
        timeout = message.payload.timeout

        # Проверяем безопасность команды
        is_safe, reason = self.safety_agent.is_safe(command_str)
        if not is_safe:
            result = CommandResult(
                success=False,
                error=f"Command rejected by safety agent. Reason: {reason}"
            )
        else:
            # Выполняем команду
            try:
                # Временно увеличиваем таймаут для внутреннего выполнения
                result_data = await self.executor.execute(command_str)
                result = CommandResult(
                    success=True,
                    data={
                        "stdout": result_data.stdout,
                        "stderr": result_data.stderr,
                        "exit_code": result_data.exit_code,
                        "timeout": result_data.timeout
                    }
                )
            except Exception as e:
                result = CommandResult(
                    success=False,
                    error=f"Command execution failed: {str(e)}"
                )

        # Отправляем результат обратно
        if message.reply_to:
            reply_message = ActorMessage(
                id=f"reply_{uuid.uuid4().hex[:8]}",
                sender=self.actor_id,
                recipient=message.reply_to,
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id
            )
            await self.tell(reply_message)
        else:
            self.logger.info("no_reply_address", message_id=message.id)