# install-tg-bridge.ps1
# Setup для Telegram bridge (RichardAtCT/claude-code-telegram).
# Опциональная интеграция: бот стартует свои Claude Code сессии по командам из Telegram.
#
# Что делает:
#   1. Проверяет Python 3.11+ и Claude Code в PATH
#   2. Клонирует репо в <MM_REPO_ROOT>/external/claude-code-telegram/ (если ещё нет)
#   3. Создаёт .venv и ставит зависимости
#   4. Копирует tg-bot-env.example → .env (если нет) и подсказывает что заполнить
#   5. Печатает следующие шаги (получить bot token, узнать user_id, запустить)
#
# Что НЕ делает (требует тебя):
#   - Запуск @BotFather и получение токена
#   - Узнавание твоего Telegram user_id
#   - Решение про hosting (локально / VPS / Docker)
#   - Запуск самого бота (ты делаешь руками первый раз чтобы увидеть логи)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExternalDir = Join-Path $RepoRoot "external"
$BotDir = Join-Path $ExternalDir "claude-code-telegram"
$EnvTemplate = Join-Path $RepoRoot "templates\tg-bot-env.example"
$EnvFile = Join-Path $BotDir ".env"

Write-Host "=== mm-tg-bridge installer ===" -ForegroundColor Cyan
Write-Host ""

# --- 1. Проверки окружения ---
Write-Host "[1/5] Проверка зависимостей..." -ForegroundColor Yellow

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Host "  ERROR: Python не найден в PATH." -ForegroundColor Red
    Write-Host "  Установи Python 3.11+: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

$pyVersion = & $python.Source --version 2>&1
Write-Host "  Python: $pyVersion"
if ($pyVersion -notmatch "Python 3\.(1[1-9]|[2-9][0-9])") {
    Write-Host "  ERROR: Нужен Python 3.11+, у тебя $pyVersion." -ForegroundColor Red
    exit 1
}

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
    Write-Host "  WARN: claude CLI не найден в PATH. Бот будет требовать его при работе." -ForegroundColor Yellow
} else {
    Write-Host "  Claude CLI: $($claude.Source)"
}

# --- 2. Клон репо ---
Write-Host ""
Write-Host "[2/5] Клонирование claude-code-telegram..." -ForegroundColor Yellow

if (-not (Test-Path $ExternalDir)) {
    New-Item -ItemType Directory -Path $ExternalDir | Out-Null
}

if (Test-Path $BotDir) {
    Write-Host "  Уже клонирован: $BotDir"
    Write-Host "  Делаю git pull для обновления..."
    Push-Location $BotDir
    try {
        git pull --ff-only 2>&1 | ForEach-Object { Write-Host "  $_" }
    } finally {
        Pop-Location
    }
} else {
    git clone https://github.com/RichardAtCT/claude-code-telegram.git $BotDir 2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: git clone упал." -ForegroundColor Red
        exit 1
    }
}

# --- 3. Виртуальное окружение и зависимости ---
Write-Host ""
Write-Host "[3/5] Виртуальное окружение и зависимости..." -ForegroundColor Yellow

$venvDir = Join-Path $BotDir ".venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "  Создаю .venv..."
    & $python.Source -m venv $venvDir
} else {
    Write-Host "  .venv уже есть."
}

$pipExe = Join-Path $venvDir "Scripts\pip.exe"
if (-not (Test-Path $pipExe)) {
    Write-Host "  ERROR: $pipExe не найден после создания venv." -ForegroundColor Red
    exit 1
}

$reqFile = Join-Path $BotDir "requirements.txt"
$pyprojectFile = Join-Path $BotDir "pyproject.toml"

if (Test-Path $reqFile) {
    Write-Host "  pip install -r requirements.txt..."
    & $pipExe install --upgrade pip *>&1 | Out-Null
    & $pipExe install -r $reqFile 2>&1 | Select-Object -Last 5 | ForEach-Object { Write-Host "  $_" }
} elseif (Test-Path $pyprojectFile) {
    Write-Host "  pip install -e . (через pyproject.toml)..."
    & $pipExe install --upgrade pip *>&1 | Out-Null
    & $pipExe install -e $BotDir 2>&1 | Select-Object -Last 5 | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  WARN: ни requirements.txt ни pyproject.toml не найдены. Установи зависимости вручную." -ForegroundColor Yellow
}

# --- 4. .env файл ---
Write-Host ""
Write-Host "[4/5] Конфигурация (.env)..." -ForegroundColor Yellow

if (Test-Path $EnvFile) {
    Write-Host "  .env уже есть: $EnvFile (НЕ перезаписываю)"
} elseif (Test-Path $EnvTemplate) {
    Copy-Item $EnvTemplate $EnvFile
    Write-Host "  Создан: $EnvFile (из шаблона)"
    Write-Host "  ОТКРОЙ И ЗАПОЛНИ: TELEGRAM_BOT_TOKEN, ALLOWED_USERS, APPROVED_DIRECTORY" -ForegroundColor Yellow
} else {
    Write-Host "  WARN: шаблон не найден ($EnvTemplate). Создай .env вручную." -ForegroundColor Yellow
}

# --- 5. Финальные подсказки ---
Write-Host ""
Write-Host "[5/5] Готово." -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги (вручную):" -ForegroundColor Cyan
Write-Host "  1. Создай Telegram-бота: @BotFather → /newbot → получи token"
Write-Host "  2. Узнай свой Telegram user_id: @userinfobot → /start"
Write-Host "  3. Открой $EnvFile и впиши:"
Write-Host "     - TELEGRAM_BOT_TOKEN=<токен от @BotFather>"
Write-Host "     - ALLOWED_USERS=<твой user_id>"
Write-Host "     - APPROVED_DIRECTORY=C:\Users\louise\Desktop  (или где лежат проекты)"
Write-Host "     - CLAUDE_MAX_COST_PER_USER=10  (USD/день, защита от runaway)"
Write-Host "  4. Запусти бота:"
Write-Host "     cd $BotDir"
Write-Host "     .\.venv\Scripts\python.exe -m bot  (или см. README репо)"
Write-Host "  5. В Telegram: открой своего бота → /start → /help"
Write-Host ""
Write-Host "После настройки — впиши URL бота в config/mm-config.local.json:"
Write-Host '  { "tg_bridge": { "enabled": true, "bot_username": "@my_claude_bot" } }'
Write-Host ""
Write-Host "См. полную документацию: docs/TG-BRIDGE.md" -ForegroundColor Cyan
