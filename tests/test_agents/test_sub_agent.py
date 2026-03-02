"""Тесты для SubAgent."""

import pytest
from unittest.mock import Mock, AsyncMock

from src.agents.sub_agent import SubAgent
from src.actors.message import ActorMessage, MessageType
from src.llm.providers.base import LLMProvider, LLMResponse, LLMMessage


@pytest.mark.asyncio
async def test_sub_agent_creation():
    """Тест создания SubAgent с LLMProvider."""
    # Создаём мок LLMProvider
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock()
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    # Создаём SubAgent
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    
    # Проверяем инициализацию
    assert agent.actor_id == "test_subagent"
    assert agent.provider is mock_provider
    assert agent.system_prompt == "You are a helpful assistant."


@pytest.mark.asyncio
async def test_sub_agent_creation_with_custom_system_prompt():
    """Тест создания SubAgent с кастомным system_prompt."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock()
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    custom_prompt = "You are a code assistant."
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent", system_prompt=custom_prompt)
    
    assert agent.system_prompt == custom_prompt


@pytest.mark.asyncio
async def test_sub_agent_delegate_task():
    """Тест обработки DELEGATE_TASK сообщения."""
    # Создаём мок LLMProvider
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock(return_value=LLMResponse(
        content="Результат выполнения задачи",
        model="test-model",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    ))
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    # Создаём SubAgent
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    agent.system = Mock()
    agent.system.send = AsyncMock()
    
    # Создаём сообщение с задачей
    message = ActorMessage(
        id="test_1",
        sender="parent",
        recipient=agent.actor_id,
        payload={"task": "Напиши скрипт"},
        message_type=MessageType.DELEGATE_TASK,
        reply_to="parent"
    )
    
    # Обрабатываем сообщение
    await agent.receive(message)
    
    # Проверяем вызов LLM
    mock_provider.generate.assert_called_once()
    
    # Проверяем, что был вызов с правильными сообщениями
    call_args = mock_provider.generate.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0].role == "system"
    assert call_args[0].content == "You are a helpful assistant."
    assert call_args[1].role == "user"
    assert call_args[1].content == "Напиши скрипт"
    
    # Проверяем отправку ответа
    assert agent.system.send.called
    
    # Получаем отправленное сообщение
    sent_message = agent.system.send.call_args[0][0]
    assert sent_message.recipient == "parent"
    assert sent_message.message_type == MessageType.RESPONSE
    assert sent_message.payload["result"] == "Результат выполнения задачи"
    assert sent_message.payload["success"] is True
    assert sent_message.correlation_id == "test_1"


@pytest.mark.asyncio
async def test_sub_agent_delegate_task_with_string_payload():
    """Тест обработки DELEGATE_TASK с строковым payload."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock(return_value=LLMResponse(
        content="Ответ на задачу",
        model="test-model",
        usage={"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    ))
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    agent.system = Mock()
    agent.system.send = AsyncMock()
    
    # Создаём сообщение со строковым payload
    message = ActorMessage(
        id="test_2",
        sender="parent",
        recipient=agent.actor_id,
        payload="Простая текстовая задача",
        message_type=MessageType.DELEGATE_TASK,
        reply_to="parent"
    )
    
    await agent.receive(message)
    
    # Проверяем вызов LLM
    mock_provider.generate.assert_called_once()
    call_args = mock_provider.generate.call_args[0][0]
    assert call_args[1].content == "Простая текстовая задача"
    
    # Проверяем отправку ответа
    assert agent.system.send.called


@pytest.mark.asyncio
async def test_sub_agent_delegate_task_with_dict_payload():
    """Тест обработки DELEGATE_TASK со словарём в payload."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock(return_value=LLMResponse(
        content="Результат",
        model="test-model",
        usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
    ))
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    agent.system = Mock()
    agent.system.send = AsyncMock()
    
    # Создаём сообщение с dict payload (ключ content)
    message = ActorMessage(
        id="test_3",
        sender="parent",
        recipient=agent.actor_id,
        payload={"content": "Задача из content"},
        message_type=MessageType.DELEGATE_TASK,
        reply_to="parent"
    )
    
    await agent.receive(message)
    
    # Проверяем вызов LLM с правильным текстом
    call_args = mock_provider.generate.call_args[0][0]
    assert call_args[1].content == "Задача из content"


@pytest.mark.asyncio
async def test_sub_agent_without_reply_to():
    """Тест обработки задачи без reply_to."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock(return_value=LLMResponse(
        content="Результат",
        model="test-model",
        usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
    ))
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    agent.system = Mock()
    agent.system.send = AsyncMock()
    
    # Создаём сообщение без reply_to
    message = ActorMessage(
        id="test_4",
        sender="parent",
        recipient=agent.actor_id,
        payload={"task": "Задача"},
        message_type=MessageType.DELEGATE_TASK,
        reply_to=None
    )
    
    await agent.receive(message)
    
    # LLM должен быть вызван
    mock_provider.generate.assert_called_once()
    
    # Ответ не должен быть отправлен (нет reply_to)
    agent.system.send.assert_not_called()


@pytest.mark.asyncio
async def test_sub_agent_error_handling():
    """Тест обработки ошибок при выполнении задачи."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    agent.system = Mock()
    agent.system.send = AsyncMock()
    
    # Создаём сообщение с задачей
    message = ActorMessage(
        id="test_5",
        sender="parent",
        recipient=agent.actor_id,
        payload={"task": "Задача"},
        message_type=MessageType.DELEGATE_TASK,
        reply_to="parent"
    )
    
    await agent.receive(message)
    
    # Проверяем, что LLM был вызван
    mock_provider.generate.assert_called_once()
    
    # Проверяем отправку сообщения об ошибке
    assert agent.system.send.called
    
    # Получаем отправленное сообщение об ошибке
    sent_message = agent.system.send.call_args[0][0]
    assert sent_message.message_type == MessageType.ERROR
    assert sent_message.payload["success"] is False
    assert "LLM Error" in sent_message.payload["error"]
    assert sent_message.correlation_id == "test_5"


@pytest.mark.asyncio
async def test_sub_agent_unsupported_message_type():
    """Тест обработки неподдерживаемого типа сообщения."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock()
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    agent.system = Mock()
    agent.system.send = AsyncMock()
    
    # Создаём сообщение с неподдерживаемым типом
    message = ActorMessage(
        id="test_6",
        sender="parent",
        recipient=agent.actor_id,
        payload={"data": "some data"},
        message_type=MessageType.REQUEST,
        reply_to="parent"
    )
    
    await agent.receive(message)
    
    # LLM не должен быть вызван
    mock_provider.generate.assert_not_called()
    
    # Сообщение не должно быть отправлено
    agent.system.send.assert_not_called()


@pytest.mark.asyncio
async def test_sub_agent_delegate_task_string_value():
    """Тест обработки DELEGATE_TASK со значением строки в payload (не dict)."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate = AsyncMock(return_value=LLMResponse(
        content="Результат",
        model="test-model",
        usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
    ))
    mock_provider.get_token_count = AsyncMock(return_value=10)
    mock_provider.validate_connection = AsyncMock(return_value=True)
    mock_provider.provider_name = "mock"
    
    agent = SubAgent(provider=mock_provider, actor_id="test_subagent")
    agent.system = Mock()
    agent.system.send = AsyncMock()
    
    # Payload - просто строка
    message = ActorMessage(
        id="test_7",
        sender="parent",
        recipient=agent.actor_id,
        payload="Простая строка как задача",
        message_type=MessageType.DELEGATE_TASK,
        reply_to="parent"
    )
    
    await agent.receive(message)
    
    # Проверяем вызов LLM
    mock_provider.generate.assert_called_once()
    call_args = mock_provider.generate.call_args[0][0]
    assert call_args[1].content == "Простая строка как задача"
    
    # Проверяем отправку ответа
    assert agent.system.send.called
