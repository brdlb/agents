# Структура проекта MVP агентной системы

## 1. Обзор

Документ описывает детальную структуру проекта для реализации MVP агентной системы согласно архитектурному документу и плану разработки.

## 2. Структура директорий

```
agents/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Точка входа
│   ├── config.py                  # Конфигурация приложения
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── bot.py                 # Telegram бот
│   │   ├── handlers.py            # Обработчики сообщений
│   │   └── callbacks.py           # Callback запросы
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # Базовый класс агента
│   │   ├── main_agent.py          # Главный агент
│   │   ├── subagent.py            # Сабагент
│   │   └── safety_agent.py        # Safety Agent
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Базовый интерфейс LLM
│   │   │   ├── openai.py          # OpenAI провайдер
│   │   │   ├── anthropic.py       # Anthropic провайдер
│   │   │   ├── openrouter.py      # OpenRouter провайдер
│   │   │   └── local.py           # Локальные модели
│   │   └── factory.py             # Фабрика провайдеров
│   ├── session/
│   │   ├── __init__.py
│   │   ├── manager.py             # Session Manager
│   │   ├── repository.py          # Репозиторий сессий
│   │   └── models.py              # Pydantic модели данных
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── json_store.py          # JSON хранилище
│   │   ├── file_lock.py           # Блокировки файлов
│   │   └── backup.py              # Стратегия бэкапов
│   ├── context/
│   │   ├── __init__.py
│   │   ├── manager.py             # Context Manager
│   │   ├── tokenizer.py           # Токенизатор
│   │   └── cache.py                # Кеш контекста
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── command.py             # Command Executor
│   │   └── security.py            # Проверка безопасности
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Настройка логирования
│       └── helpers.py             # Вспомогательные функции
├── data/                          # Директория для JSON файлов
│   ├── sessions/                  # Сессии пользователей
│   └── users/                     # Данные пользователей
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_agents/
│   ├── test_llm/
│   ├── test_session/
│   └── test_executor/
├── docs/
│   ├── architecture.md            # Архитектурный документ
│   ├── mvp-plan.md                # План реализации
│   └── project-structure.md       # Этот документ
├── configs/
│   ├── .env.example               # Пример конфигурации
│   └── settings.yaml              # YAML конфигурация
├── pyproject.toml                 # Конфигурация проекта
└── README.md
```

## 3. Модули и их ответственность

### 3.1 Telegram Interface (`src/telegram/`)

| Файл | Ответственность |
|------|-----------------|
| [`bot.py`](src/telegram/bot.py) | Инициализация и запуск Telegram бота, настройка webhook |
| [`handlers.py`](src/telegram/handlers.py) | Обработчики текстовых сообщений, команд /start, /help |
| [`callbacks.py`](src/telegram/callbacks.py) | Обработка callback-запросов от inline-кнопок |

**Паттерн:** Event-driven, Message Queue

### 3.2 LLM Providers (`src/llm/`)

| Файл | Ответственность |
|------|-----------------|
| [`providers/base.py`](src/llm/providers/base.py) | Абстрактный базовый класс LLM провайдера |
| [`providers/openai.py`](src/llm/providers/openai.py) | Реализация OpenAI провайдера (GPT-4, GPT-3.5) |
| [`providers/anthropic.py`](src/llm/providers/anthropic.py) | Реализация Anthropic провайдера (Claude) |
| [`providers/openrouter.py`](src/llm/providers/openrouter.py) | OpenRouter - унифицированный API |
| [`providers/local.py`](src/llm/providers/local.py) | Локальные модели (Ollama, LM Studio) |
| [`factory.py`](src/llm/factory.py) | Фабрика для создания провайдеров |

**Интерфейс LLM Provider:**
```python
class LLMProvider(ABC):
    async def generate(self, messages: list[Message], **kwargs) -> str
    async def get_token_count(self, text: str) -> int
    async def validate_connection(self) -> bool
```

**Паттерн:** Strategy, Adapter

### 3.3 Session Manager (`src/session/`)

| Файл | Ответственность |
|------|-----------------|
| [`models.py`](src/session/models.py) | Pydantic модели: Session, Message, User |
| [`repository.py`](src/session/repository.py) | Репозиторий для работы с JSON файлами |
| [`manager.py`](src/session/manager.py) | Бизнес-логика создания/восстановления сессий |

**Структура данных сессии:**
```json
{
  "id": "uuid-string",
  "user_id": 123456789,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z",
  "system_prompt": "You are a helpful assistant...",
  "context_tokens": 1000,
  "messages": [
    {"role": "user", "content": "Hello", "timestamp": "2026-01-01T00:00:00Z"}
  ]
}
```

**Паттерн:** Repository, File-based Storage

### 3.4 Context Manager (`src/context/`)

| Файл | Ответственность |
|------|-----------------|
| [`manager.py`](src/context/manager.py) | Загрузка markdown файлов, управление контекстом |
| [`tokenizer.py`](src/context/tokenizer.py) | Интеграция tiktoken для подсчета токенов |
| [`cache.py`](src/context/cache.py) | Кеширование загруженных файлов в памяти |

**Паттерн:** Lazy Loading, Cache-Aside

### 3.5 Agent System (`src/agents/`)

| Файл | Ответственность |
|------|-----------------|
| [`base.py`](src/agents/base.py) | Базовый класс агента с async логикой |
| [`main_agent.py`](src/agents/main_agent.py) | Главный агент - обработка запросов |
| [`subagent.py`](src/agents/subagent.py) | Сабагенты для специализированных задач |
| [`safety_agent.py`](src/agents/safety_agent.py) | Проверка безопасности команд |

**Паттерн:** Chain of Responsibility, Observer

### 3.6 Command Executor (`src/executor/`)

| Файл | Ответственность |
|------|-----------------|
| [`command.py`](src/executor/command.py) | Асинхронное выполнение команд |
| [`security.py`](src/executor/security.py) | Проверка паттернов, путей, лимитов |

**Паттерн:** Command, Proxy

### 3.7 Storage Layer (`src/storage/`)

| Файл | Ответственность |
|------|-----------------|
| [`json_store.py`](src/storage/json_store.py) | Базовые операции с JSON файлами |
| [`file_lock.py`](src/storage/file_lock.py) | Блокировки при одновременном доступе |
| [`backup.py`](src/storage/backup.py) | Стратегия бэкапов |

**Паттерн:** Atomic Write, File 3.8 Locking

### Utils (`src/utils/`)

| Файл | Ответственность |
|------|-----------------|
| [`logger.py`](src/utils/logger.py) | Настройка structlog, форматирование |
| [`helpers.py`](src/utils/helpers.py) | Вспомогательные функции |

## 4. Список файлов для Фазы 1

Фаза 1 включает задачи 1.1-1.9 из плана MVP. Ниже приведен полный список файлов для создания:

### 4.1 Базовая инфраструктура проекта

```
src/__init__.py
src/main.py                    # Точка входа, создание app
src/config.py                  # Конфигурация с pydantic-settings
```

### 4.2 Логирование

```
src/utils/__init__.py
src/utils/logger.py            # Настройка structlog
src/utils/helpers.py           # Утилиты
```

### 4.3 Storage Layer

```
src/storage/__init__.py
src/storage/json_store.py      # Базовый JSON storage
src/storage/file_lock.py      # Блокировки файлов
```

### 4.4 LLM Provider Layer

```
src/llm/__init__.py
src/llm/providers/__init__.py
src/llm/providers/base.py      # Абстрактный базовый класс
src/llm/providers/openai.py    # OpenAI провайдер
src/llm/factory.py             # Фабрика провайдеров
```

### 4.5 Модели данных

```
src/session/__init__.py
src/session/models.py          # Pydantic модели
```

### 4.6 Тесты Фазы 1

```
tests/__init__.py
tests/conftest.py              # Pytest fixtures
tests/test_llm/
tests/test_llm/__init__.py
tests/test_llm/test_openai_provider.py
tests/test_storage/
tests/test_storage/__init__.py
tests/test_storage/test_json_store.py
```

## 5. Зависимости для pyproject.toml

```toml
[project]
name = "agents"
version = "0.1.0"
description = "MVP Agent System with Telegram Interface"
requires-python = ">=3.11"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Developer", email = "dev@example.com"}
]

dependencies = [
    # Async фреймворк для Telegram
    "aiogram>=3.4.0",
    
    # Асинхронная работа с файлами
    "aiofiles>=23.2.1",
    
    # LLM провайдеры
    "openai>=1.12.0",
    "anthropic>=0.18.0",
    "aiohttp>=3.9.0",
    
    # Токенизация
    "tiktoken>=0.5.2",
    
    # Конфигурация
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.1",
    
    # Логирование
    "structlog>=24.1.0",
    "loguru>=0.7.2",
    
    # Утилиты
    "httpx>=0.26.0",
    "uvicorn>=0.27.0",
    "python-telegram-bot>=20.7",
]

[project.optional-dependencies]
dev = [
    # Тестирование
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    
    # Линтинг и форматтинг
    "ruff>=0.1.0",
    "mypy>=1.7.0",
    "black>=23.12.0",
    
    # Типизация
    "types-aiofiles>=23.2.1",
    "types-python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.ruff]
line-length = 100
target-version = "py311"
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "ASYNC", # flake8-async
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # do not perform function calls in argument defaults
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

## 6. Пример .env файла

```bash
# =============================================================================
# Telegram Bot Configuration
# =============================================================================
# Токен бота от @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789

# ID администраторов через запятую
TELEGRAM_ADMIN_IDS=123456789

# =============================================================================
# LLM Provider Configuration
# =============================================================================
# Доступные провайдеры: openai, anthropic, openrouter, local
LLM_PROVIDER=openai

# OpenAI API ключ (получить на https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Anthropic API ключ (получить на https://console.anthropic.com/)
# ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OpenRouter API ключ (получить на https://openrouter.ai/settings)
# OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Локальный LLM сервер (Ollama, LM Studio)
# LOCAL_LLM_URL=http://localhost:11434
# LOCAL_LLM_MODEL=llama2

# Модель по умолчанию
DEFAULT_MODEL=gpt-4o-mini

# =============================================================================
# Storage Configuration
# =============================================================================
# Директория для хранения JSON файлов
DATA_DIR=./data

# Время жизни сессии в секундах (по умолчанию 24 часа)
SESSION_TTL=86400

# Максимальное количество сессий на пользователя
MAX_SESSIONS_PER_USER=10

# =============================================================================
# Context Configuration
# =============================================================================
# Директория с markdown файлами контекста
CONTEXT_DIR=./context

# Максимальное количество токенов для контекста
MAX_CONTEXT_TOKENS=8000

# =============================================================================
# Command Executor Configuration
# =============================================================================
# Разрешенные команды (через запятую)
ALLOWED_COMMANDS=ls,cd,cat,grep,tail,head,pwd,echo,find

# Максимальное количество одновременных команд
MAX_CONCURRENT_COMMANDS=3

# Таймаут выполнения команды в секундах
COMMAND_TIMEOUT=30

# =============================================================================
# Logging Configuration
# =============================================================================
# Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Формат логов: json, console
LOG_FORMAT=json

# =============================================================================
# Rate Limiting (опционально)
# =============================================================================
# Максимальное количество запросов в минуту для одного пользователя
# RATE_LIMIT_PER_MINUTE=10
```

## 7. Диаграмма зависимостей модулей Фазы 1

```mermaid
graph TD
    subgraph Phase1["Фаза 1: Инфраструктура"]
        main[main.py] --> config[config.py]
        main --> logger[utils/logger.py]
        
        subgraph Storage["Storage Layer"]
            json_store[storage/json_store.py] --> file_lock[storage/file_lock.py]
        end
        
        subgraph LLM["LLM Provider Layer"]
            base[llm/providers/base.py] --> openai[llm/providers/openai.py]
            base --> factory[llm/factory.py]
        end
        
        subgraph Models["Data Models"]
            models[session/models.py]
        end
    end
    
    config --> models
    logger --> json_store
    factory --> openai
    
    classDef phase1 fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    class main,config,logger,json_store,file_lock,base,openai,factory,models phase1;
```

## 8. Структура данных в файловой системе

```
data/
├── sessions/
│   ├── {user_id}/
│   │   ├── session_{uuid1}.json
│   │   ├── session_{uuid2}.json
│   │   └── ...
│   └── ...
└── users/
    ├── {user_id}.json
    └── ...
```

## 9. Критерии готовности Фазы 1

- [ ] Проект запускается без ошибок (`python -m src.main`)
- [ ] Логирование работает корректно (структурированные логи в stdout)
- [ ] OpenAI провайдер генерирует текст (проверка через unit-тест)
- [ ] Конфигурация загружается из .env файла
- [ ] JSON storage работает (запись/чтение файлов)
- [ ] File locking работает при параллельном доступе
- [ ] Pydantic модели валидируют данные корректно

## 10. Следующие шаги

После завершения Фазы 1 переходить к Фазе 2:
1. Telegram Bot - Base (задачи 2.1-2.2)
2. Session Manager - Repository (задачи 2.3-2.4)
3. Интеграция Bot + Session (задачи 2.5-2.7)

---

*Документ создан: 2026-02-14*
*Версия: 1.0*