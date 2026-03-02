"""Тесты для CommandActor."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from src.actors.actors.command_actor import CommandActor
from src.actors.message import ActorMessage, MessageType, ExecuteCommand
from src.executor.command import CommandExecutor, CommandResult
from src.agents.safety_agent import SafetyAgent


@pytest.mark.asyncio
async def test_command_actor_execution():
    """Тест выполнения команды через CommandActor."""
    # Создаем моки для зависимостей
    safety_agent = Mock(spec=SafetyAgent)
    safety_agent.is_safe = Mock(return_value=(True, "Safe"))
    
    command_executor = Mock(spec=CommandExecutor)
    command_executor.execute = AsyncMock(return_value=CommandResult(
        stdout="test output", 
        stderr="", 
        exit_code=0
    ))
    
    # Создаем актор
    actor = CommandActor(safety_agent=safety_agent, executor=command_executor)
    
    # Мокаем систему акторов
    actor.system = Mock()
    actor.system.send = AsyncMock()
    
    # Создаем сообщение для выполнения команды
    message = ActorMessage(
        id="test_cmd_1",
        sender="test_sender",
        recipient=actor.actor_id,
        payload=ExecuteCommand(command="echo hello"),
        message_type=MessageType.EXECUTE_COMMAND,
        reply_to="test_reply_to"
    )
    
    # Обрабатываем сообщение
    await actor.receive(message)
    
    # Проверяем, что команда была выполнена
    command_executor.execute.assert_called_once_with("echo hello")
    safety_agent.is_safe.assert_called_once_with("echo hello")


@pytest.mark.asyncio
async def test_command_actor_safety_check():
    """Тест проверки безопасности команды."""
    # Создаем моки
    safety_agent = Mock(spec=SafetyAgent)
    safety_agent.is_safe = Mock(return_value=(False, "Not safe"))
    
    command_executor = Mock(spec=CommandExecutor)
    command_executor.execute = AsyncMock()  # Не должен быть вызван
    
    actor = CommandActor(safety_agent=safety_agent, executor=command_executor)
    actor.system = Mock()
    actor.system.send = AsyncMock()
    
    message = ActorMessage(
        id="test_cmd_2",
        sender="test_sender",
        recipient=actor.actor_id,
        payload=ExecuteCommand(command="rm -rf /"),
        message_type=MessageType.EXECUTE_COMMAND,
        reply_to="test_reply_to"
    )
    
    await actor.receive(message)
    
    # Проверяем, что команда не была выполнена из-за проверки безопасности
    command_executor.execute.assert_not_called()
    safety_agent.is_safe.assert_called_once_with("rm -rf /")


@pytest.mark.asyncio
async def test_command_actor_reply():
    """Тест отправки ответа после выполнения команды."""
    # Создаем моки
    safety_agent = Mock(spec=SafetyAgent)
    safety_agent.is_safe = Mock(return_value=(True, "Safe"))
    
    command_executor = Mock(spec=CommandExecutor)
    command_executor.execute = AsyncMock(return_value=CommandResult(
        stdout="success", 
        stderr="", 
        exit_code=0
    ))
    
    actor = CommandActor(safety_agent=safety_agent, executor=command_executor)
    actor.system = Mock()
    actor.system.send = AsyncMock()
    
    message = ActorMessage(
        id="test_cmd_3",
        sender="test_sender",
        recipient=actor.actor_id,
        payload=ExecuteCommand(command="ls"),
        message_type=MessageType.EXECUTE_COMMAND,
        reply_to="test_reply_to"
    )
    
    await actor.receive(message)
    
    # Проверяем, что отправлено сообщение с результатом
    assert actor.system.send.called
    call_args = actor.system.send.call_args[0][0]
    assert isinstance(call_args, ActorMessage)
    assert call_args.recipient == "test_reply_to"
    assert call_args.message_type == MessageType.RESPONSE