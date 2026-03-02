"""Пример использования Actor Framework."""

import asyncio
from src.actors.system import ActorSystem
from src.actors.actors.command_actor import CommandActor
from src.agents.safety_agent import SafetyAgent
from src.executor.command import CommandExecutor
from src.actors.message import ActorMessage, MessageType, ExecuteCommand


async def main():
    """Пример использования Actor Framework."""
    print("=== Пример использования Actor Framework ===")
    
    # Создаем глобальную систему акторов
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
    print(f"Запущен CommandActor с ID: {actor_id}")
    
    # Создаем сообщение для выполнения команды
    message = ActorMessage(
        id="example_cmd_1",
        sender="example_app",
        recipient=actor_id,
        payload=ExecuteCommand(command="echo 'Hello from Actor Framework!'"),
        message_type=MessageType.EXECUTE_COMMAND
    )
    
    # Отправляем сообщение актору
    print("Отправляем сообщение актору...")
    await system.send(message)
    
    # Ждем немного для выполнения команды
    await asyncio.sleep(1)
    
    # Останавливаем систему
    await system.stop_all()
    print("Система акторов остановлена.")


if __name__ == "__main__":
    asyncio.run(main())