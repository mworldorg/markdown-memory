# Telegram Bridge — claude-code-telegram

> Опциональная интеграция: Telegram-бот, оборачивающий Claude Code.
> Источник: https://github.com/RichardAtCT/claude-code-telegram (MIT)
> Атрибуция: автор RichardAtCT, mm-система использует его проект как external dependency.

## Что это даёт

| Возможность | Доступно через |
|---|---|
| Push prompt с телефона → новая Claude сессия в проекте | ✅ нативно |
| Получать tool-use в реальном времени в Telegram | ✅ нативно |
| Голосовой ввод (Whisper/Voxtral) | ✅ опционально |
| GitHub webhook events → Telegram | ✅ опционально |
| Cron-задачи (например, ежедневный `/mm-doctor`) | ✅ опционально |
| Передать prompt в **уже запущенную PowerShell-сессию** | ❌ архитектурный mismatch (см. ниже) |

## Что это НЕ заменяет

`mm-bridge` пишет файл-мост в Obsidian; ты копипастишь из файла в **существующую** PowerShell-сессию Claude Code. Это сохраняет твой warm контекст, skills, недавние решения.

`claude-code-telegram` бот **запускает свой** процесс Claude Code на каждый запрос. Это другая модель: zero copy-paste, но новая сессия = чистый контекст, нет твоего экспириенса в текущем чате.

**Когда какое использовать:**

| Ситуация | Лучше |
|---|---|
| Я в текущей сессии, обсуждаю с claude.ai → нужен промпт для PowerShell | `mm-bridge` (копипаст) |
| Я на улице с телефоном, хочу запустить «обнови README» | TG-бот |
| Многошаговая интерактивная работа | `mm-bridge` (warm session) |
| Автономные задачи без надзора («запусти тесты, отчитайся») | TG-бот (или GSD-autonomous) |
| Cron: каждое утро `/mm-doctor` | TG-бот с cron |

Они **дополняют**, не конкурируют.

## Архитектура

```
┌─────────────────┐         ┌──────────────────────────┐
│ Telegram (твой  │ message │ claude-code-telegram bot │
│ телефон)        ├────────►│ (Python, локально/VPS)   │
└─────────────────┘         └────────────┬─────────────┘
                                         │ spawn `claude --print "..."`
                                         │ в APPROVED_DIRECTORY
                                         ▼
                            ┌──────────────────────────┐
                            │ Новая Claude Code сессия │
                            │ (читает CLAUDE.md,        │
                            │  загружает mm-* skills)   │
                            └──────────────────────────┘
```

Бот владеет жизненным циклом своих Claude процессов. Он не lazy-attach в твою PowerShell.

## Установка

### Шаг 1. Запусти setup-скрипт (автоматическое)

```powershell
cd C:\Users\louise\Desktop\louise-skills
pwsh scripts/install-tg-bridge.ps1
```

Скрипт:
- Проверит Python 3.11+ и `claude` в PATH
- Склонирует https://github.com/RichardAtCT/claude-code-telegram в `external/claude-code-telegram/`
- Создаст `.venv` и поставит зависимости
- Скопирует `templates/tg-bot-env.example` → `external/claude-code-telegram/.env`

### Шаг 2. Получи Telegram credentials (вручную)

1. Открой [@BotFather](https://t.me/BotFather) → `/newbot` → следуй инструкциям → получи **token** (формат `1234567:ABC...`).
2. Открой [@userinfobot](https://t.me/userinfobot) → `/start` → получи **твой user_id** (число типа `123456789`).
3. Запомни оба.

### Шаг 3. Заполни .env

Открой `C:\Users\louise\Desktop\louise-skills\external\claude-code-telegram\.env`, впиши:

```
TELEGRAM_BOT_TOKEN=<токен от BotFather>
ALLOWED_USERS=<твой user_id>
APPROVED_DIRECTORY=C:\Users\louise\Desktop      # сужь до конкретной папки если хочешь
CLAUDE_MAX_COST_PER_USER=10                      # USD/день, защита от runaway
```

Остальное оставь как есть для начала.

### Шаг 4. Запусти бота

```powershell
cd C:\Users\louise\Desktop\louise-skills\external\claude-code-telegram
.\.venv\Scripts\python.exe -m bot
```

(Точная команда — см. README репо. Может быть `python main.py` или `python -m claude_code_telegram`.)

В Telegram открой своего бота → `/start` → должен ответить.

### Шаг 5. (Опционально) автозапуск

**Windows Task Scheduler** — самый простой:

```powershell
$action = New-ScheduledTaskAction -Execute "C:\Users\louise\Desktop\louise-skills\external\claude-code-telegram\.venv\Scripts\python.exe" -Argument "-m bot" -WorkingDirectory "C:\Users\louise\Desktop\louise-skills\external\claude-code-telegram"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "mm-tg-bridge" -Action $action -Trigger $trigger -Settings $settings
```

**Альтернативы:** NSSM (Windows service), pm2 (Node-style), либо запускать вручную когда нужно.

### Шаг 6. Подключи к mm-системе

Открой `C:\Users\louise\Desktop\louise-skills\config\mm-config.local.json` (создай из `mm-config.local.example.json` если нет):

```json
{
  "tg_bridge": {
    "enabled": true,
    "bot_username": "@my_claude_bot",
    "approved_directory": "C:\\Users\\louise\\Desktop"
  }
}
```

Теперь:
- `/mm doctor` будет проверять что бот стоит и .env заполнен
- `/mm bridge --tg` (если добавишь флаг) — попросит подсказку «открой бота с командой» вместо файла
- `/mm` cheat-sheet упомянет TG-бот как канал

## Безопасность — критично

- **Whitelist обязателен.** Без `ALLOWED_USERS` любой кто узнает username = доступ к твоим репам.
- **Telegram-аккаунт можно угнать через SIM swap.** Не клади бота в открытый доступ.
- **Path sandboxing.** Сужай `APPROVED_DIRECTORY` до минимума (например `C:\Users\louise\Desktop\Projects`, не `C:\`).
- **Cost cap.** `CLAUDE_MAX_COST_PER_USER` защищает от runaway. Проверь логи.
- **Не клади токен в репо.** `.env` в `.gitignore` бота И в `.gitignore` louise-skills.

## Когда **не** использовать TG-бот

- Работа с большим контекстом (загрузка файлов, длинные диалоги) — копипаст в существующую PowerShell-сессию эффективнее
- Чувствительные репозитории — не доверяй удалённый запуск через мобильный канал
- Отладка с интерактивными решениями — текстовый Telegram-чат хуже терминала

## Известные ограничения

1. Каждое сообщение = новая Claude сессия = деньги. Cost cap обязателен.
2. Один мейнтейнер репо (RichardAtCT) — если abandoned, может потребоваться форк.
3. Windows-инструкции в их README ограничены, systemd-only для service-режима.
4. SQLite база сессий растёт — периодически чистить.

## Удаление

```powershell
# Останови бота (Task Scheduler или процесс)
# Удали из mm:
# в config/mm-config.local.json: "tg_bridge.enabled": false

# Удали папку:
Remove-Item -Recurse -Force C:\Users\louise\Desktop\louise-skills\external\claude-code-telegram

# Опционально — удали бота в @BotFather: /deletebot
```
