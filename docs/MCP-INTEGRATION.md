# Интеграция Obsidian через MCP (Model Context Protocol)

Подключение вашего Obsidian Vault напрямую через MCP — это самый современный и надежный способ дать агентам (Claude Code и Antigravity IDE) прямой доступ к вашей долговременной памяти без использования консольных команд.

## Что это дает?
* **Нативный доступ**: Агенты получают специализированные инструменты (`read_file`, `write_file`, `search_grep`) для работы с файлами вашего Obsidian Vault.
* **Высокая скорость**: Исполнение происходит мгновенно в рамках протокола MCP, без лишнего спавна процессов bash/zsh.
* **Безопасность**: Доступ ограничивается строго одной папкой вашего сейфа Obsidian.

---

## Шаг 1. Получите путь к Obsidian Vault
Найдите абсолютный путь к вашему сейфу. Например:
* **macOS**: `/Users/nikolaimoskot/Documents/Obsidian Vault`
* **Windows**: `D:\Sync\ObsidianVault`

---

## Шаг 2. Настройка в Claude Code

Конфигурация MCP для Claude Code хранится в глобальном файле настроек:
* Path: `~/.claude/config.json` (или создайте его, если его нет).

Добавьте официальный файловый MCP-сервер в секцию `mcpServers` (замените путь на ваш реальный путь к Obsidian Vault):

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/nikolaimoskot/Documents/Obsidian Vault"
      ]
    }
  }
}
```

*После сохранения перезапустите Claude Code. Проверить подключение можно командой `/mcp` внутри сессии Claude Code — там должен появиться сервер `obsidian-vault`.*

---

## Шаг 3. Настройка в Antigravity IDE (Gemini)

В Antigravity IDE конфигурация MCP-серверов подключается аналогично:
* Добавьте ту же конфигурацию сервера в файл настроек MCP клиента Antigravity: `~/.gemini/antigravity/mcp_config.json`.

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/nikolaimoskot/Documents/Obsidian Vault"
      ]
    }
  }
}
```

---

## Как использовать в чате

Когда сервер подключен, вы можете давать агентам команды на естественном языке, например:

* *"Найди в моем Obsidian последние решения по архитектуре проекта"* (агент сам выполнит grep по сейфу через MCP).
* *"Создай в Obsidian новый лог сессии по проекту x с темой рефакторинга"* (агент запишет markdown-файл напрямую через инструмент записи MCP).
* *"Прочитай passport.md текущего проекта в Obsidian"* (агент мгновенно вытащит данные).

Это делает связку `markdown-memory` и AI-агентов бесшовной и невероятно быстрой!
