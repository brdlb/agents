# Рефакторинг MainAgent для использования Actor Framework

## Проблема
Текущий `MainAgent` в `src/agents/main_agent.py` использует прямые вызовы инструментов, что нарушает принципы Actor System.

## Цель
Переписать `MainAgent` так, чтобы он создавал акторов для выполнения инструментов, а не вызывал их напрямую.

## Текущая архитектура (плохо)
```python
# В src/agents/main_agent.py
async def handle_tool_call(tool_call):
    if tool_name == "run_command":
        # Прямой вызов без изоляции
        is_safe, reason = self.safety_agent.is_safe(command)
        res = await self.command_executor.execute(command)
    elif tool_name == "web_search":
        results = await self.web_search_executor.search(query)
```

## Новая архитектура (хорошо)
```python
# В обновленном MainAgent
async def handle_tool_call(tool_call):
    if tool_name == "run_command":
        # Создание актора для выполнения команды
        command_actor = CommandActor(
            safety_agent=self.safety_agent,
            executor=self.command_executor
        )
        await self.system.spawn(command_actor, parent_id=self.actor_id)
        
        # Отправка сообщения актору
        result = await command_actor.ask(ActorMessage(
            recipient=command_actor.actor_id,
            payload=ExecuteCommand(command=command),
            message_type=MessageType.EXECUTE_COMMAND
        ))
    elif tool_name == "web_search":
        # Создание актора для веб-поиска
        search_actor = WebSearchActor(executor=self.web_search_executor)
        await self.system.spawn(search_actor, parent_id=self.actor_id)
        
        # Отправка сообщения актору
        result = await search_actor.ask(ActorMessage(
            recipient=search_actor.actor_id,
            payload=WebSearchQuery(query=query),
            message_type=MessageType.WEB_SEARCH
        ))
```

## План рефакторинга

1. Создать абстрактный класс `ActorAgent`, который наследуется от `Actor` и `BaseAgent`
2. Переписать `MainAgent` как `ActorAgent`
3. Заменить прямые вызовы инструментов на создание акторов
4. Обеспечить правильную передачу результатов обратно в LLM

## Преимущества
- Изоляция выполнения инструментов
- Возможность масштабирования
- Лучшая обработка ошибок
- Соответствие принципам Actor System