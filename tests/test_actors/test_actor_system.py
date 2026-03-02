"""Тесты для Actor Framework."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from src.actors.system import ActorSystem
from src.actors.base import Actor
from src.actors.message import ActorMessage, MessageType


class TestActor(Actor):
    """Тестовый актор для проверки функционала."""
    
    def __init__(self, actor_id: str = None):
        super().__init__(actor_id)
        self.received_messages = []

    async def receive(self, message):
        """Сохраняем полученные сообщения для проверки."""
        self.received_messages.append(message)


@pytest.mark.asyncio
async def test_actor_system_spawn_and_communication():
    """Тест создания акторов и отправки сообщений между ними."""
    # Создаем систему акторов
    system = ActorSystem()
    
    # Создаем два тестовых актора
    actor1 = TestActor("test_actor_1")
    actor2 = TestActor("test_actor_2")
    
    # Регистрируем акторов в системе
    await system.spawn(actor1)
    await system.spawn(actor2)
    
    # Проверяем, что акторы зарегистрированы
    assert system.get_actor("test_actor_1") is not None
    assert system.get_actor("test_actor_2") is not None
    
    # Отправляем сообщение от одного актора другому
    message = ActorMessage(
        id="test_msg_1",
        sender="test_actor_1",
        recipient="test_actor_2",
        payload="hello from actor 1",
        message_type=MessageType.REQUEST
    )
    
    await system.send(message)
    
    # Даем время на обработку сообщения
    await asyncio.sleep(0.1)
    
    # Проверяем, что второй актор получил сообщение
    assert len(actor2.received_messages) == 1
    received_msg = actor2.received_messages[0]
    assert received_msg.sender == "test_actor_1"
    assert received_msg.recipient == "test_actor_2"
    assert received_msg.payload == "hello from actor 1"
    
    # Останавливаем систему
    await system.stop_all()


@pytest.mark.asyncio
async def test_actor_spawn_child():
    """Тест создания дочерних акторов."""
    system = ActorSystem()
    
    parent_actor = TestActor("parent_actor")
    await system.spawn(parent_actor)
    
    # Создаем дочерний актор через родительский
    child_actor = TestActor("child_actor")
    child_id = await parent_actor.spawn_child(child_actor)
    
    # Проверяем, что дочерний актор зарегистрирован
    assert child_id == "child_actor"
    assert "child_actor" in parent_actor.children
    assert system.get_actor("child_actor") is not None
    
    # Проверяем связь родитель-ребенок
    assert system.get_actor("child_actor").parent_id == "parent_actor"
    
    await system.stop_all()


@pytest.mark.asyncio
async def test_actor_tell_method():
    """Тест метода tell для отправки сообщений."""
    system = ActorSystem()
    
    sender_actor = TestActor("sender")
    receiver_actor = TestActor("receiver")
    
    await system.spawn(sender_actor)
    await system.spawn(receiver_actor)
    
    # Устанавливаем систему для отправителя
    sender_actor.system = system
    
    # Отправляем сообщение через метод tell
    message = ActorMessage(
        id="tell_test_msg",
        sender="sender",
        recipient="receiver",
        payload="tell test message"
    )
    
    await sender_actor.tell(message)
    
    # Даем время на обработку
    await asyncio.sleep(0.1)
    
    # Проверяем, что сообщение было получено
    assert len(receiver_actor.received_messages) == 1
    assert receiver_actor.received_messages[0].payload == "tell test message"
    
    await system.stop_all()