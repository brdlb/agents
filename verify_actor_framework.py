#!/usr/bin/env python3
"""Скрипт для проверки работоспособности Actor Framework."""

import asyncio
from src.actors.system import ActorSystem
from src.actors.actors.command_actor import CommandActor
from src.agents.safety_agent import SafetyAgent
from src.executor.command import CommandExecutor
from src.actors.message import ActorMessage, MessageType, ExecuteCommand


async def verify_actor_framework():
    """Проверка основного функционала Actor Framework."""
    print("Verifying Actor Framework...")
    
    # Создаем систему акторов
    system = ActorSystem()
    
    # Создаем зависимости для CommandActor
    safety_agent = SafetyAgent()
    command_executor = CommandExecutor()
    
    # Создаем актор для выполнения команд
    command_actor = CommandActor(
        safety_agent=safety_agent,
        executor=command_executor
    )
    
    # Регистрируем актор в системе
    actor_id = await system.spawn(command_actor)
    print(f"+ CommandActor spawned with ID: {actor_id}")
    # Проверяем, что актор зарегистрирован
    registered_actor = system.get_actor(actor_id)
    assert registered_actor is not None
    print("+ Actor registration verified")
    
    # Останавливаем систему
    await system.stop_all()
    print("+ Actor system stopped successfully")
    
    print("\n+ All Actor Framework components working correctly!")
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_actor_framework())
    if success:
        print("\nVerification completed successfully!")
    else:
        print("\nVerification failed!")
        exit(1)