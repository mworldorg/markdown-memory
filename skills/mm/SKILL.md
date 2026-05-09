---
name: mm
version: 0.4.0
description: Диспетчер mm-системы — короткая команда вместо длинных. /mm без аргументов = список всех команд. /mm new = init project, /mm save = save session, /mm next = handoff, /mm prompt = bridge, /mm rules = instructions, /mm check = doctor. Use when user types "/mm" anything OR says "что есть в mm", "какие mm команды", "помощь по mm", "mm cheatsheet".
---

# mm — Dispatcher / Cheat Sheet

Короткие алиасы для длинных команд. Также — если юзер просто пишет `/mm`, выводи список.

## Карта команд

| Алиас | Полная команда | Что делает |
|---|---|---|
| `/mm new` | `/mm-init-project` | Init/update паспорт проекта + Obsidian-структуру |
| `/mm init` | `/mm-init-project` | (синоним new) |
| `/mm resume` | `/mm-resume` | Восстановить контекст: passport + dashboard + last session + git + GSD |
| `/mm start` | `/mm-resume` | (синоним resume — для начала сессии) |
| `/mm context` | `/mm-resume` | (синоним resume) |
| `/mm where` | `/mm-resume` | (синоним resume — «где мы») |
| `/mm save` | `/mm-save-session` | Сохранить лог сессии в Obsidian |
| `/mm end` | `/mm-save-session` | (синоним save) |
| `/mm next` | `/mm-handoff` | Сводка для нового чата claude.ai |
| `/mm handoff` | `/mm-handoff` | (синоним next) |
| `/mm prompt` | `/mm-bridge` | Промпт-мост в файл для PowerShell-Клода |
| `/mm bridge` | `/mm-bridge` | (синоним prompt) |
| `/mm rules` | `/mm-instructions` | Сгенерить Project Instructions для claude.ai |
| `/mm chat` | `/mm-instructions` | (синоним rules) |
| `/mm check` | `/mm-doctor` | Самопроверка системы |
| `/mm doctor` | `/mm-doctor` | (синоним check) |
| `/mm health` | `/mm-doctor` | (синоним check) |
| `/mm` | (этот skill) | Покажи cheat sheet (без выполнения) |
| `/mm help` | (этот skill) | (синоним) |
| `/mm ?` | (этот skill) | (синоним) |

## Как работаешь

### 1. Парсинг команды

Юзер пишет: `/mm <команда> [аргументы]`. Возьми `<команда>`, ищи в карте выше (case-insensitive). Опечатки толерируй (Levenshtein <= 2):
- `/mm seve` → save (расстояние 1)
- `/mm hando` → handoff
- `/mm doktor` → doctor

Если не нашёл — покажи cheat sheet с пометкой `Команда "<x>" не распознана. Возможно ты имел в виду:` + 1-2 ближайших варианта.

### 2. Если без аргументов или help

Выведи cheat-sheet — компактно (не всю карту, а сгруппированно):

```
/mm — диспетчер mm-системы

Старт нового / открытие проекта:
  /mm new          оформить или обновить паспорт проекта
  /mm resume       где мы (passport + last session + git + GSD)

Работа в сессии:
  /mm prompt       промпт-мост из claude.ai в PowerShell
  /mm save         закрыть сессию, лог в Obsidian
  /mm next         сводка для нового чата claude.ai (контекст забит)

Инфраструктура:
  /mm rules        сгенерить инструкции для claude.ai Project
  /mm check        диагностика системы (junction'ы, vault, паспорта)

Типичный цикл:
  утром / после /clear → /mm resume   ← подхватил контекст
  работаешь            → /mm prompt   (если задача из claude.ai)
  закончил день        → /mm save     (лог в Obsidian)
  контекст забит       → /mm save → /clear → /mm resume
  новый чат claude.ai  → /mm next     (handoff в Knowledge)

Полные имена тоже работают: /mm-init-project, /mm-save-session, и т.д.
```

### 3. Если команда распознана

Делегируй вызов соответствующему skill. Это значит:
- НЕ выполняй логику маппинг'нутого skill'а сам.
- Скажи коротко: `→ Запускаю /mm-<full-name>...`
- Дальше работа идёт в том skill (он подхватится автоматически).

В реальности Claude Code не «делегирует» программно — но в твоём ответе ты приступаешь к выполнению того skill, как если бы юзер написал его полное имя. То есть:

1. Скажи одной строкой: `→ /mm new = /mm-init-project, начинаю.`
2. Действуй как `mm-init-project` (читай его SKILL.md и исполняй).

### 4. Дополнительные удобства

- **`/mm new <name>`** — передай имя проекту, чтоб init не спрашивал. Пример: `/mm new filtrator`.
- **`/mm save "<тема>"`** — передай тему сессии вручную. Пример: `/mm save "рефакторинг роутинга"`.
- **`/mm prompt "<задача>"`** — короткая задача сразу. Пример: `/mm prompt "добавь команду /stats в бот"`.

Эти extra-аргументы передавай в подскилл как контекст.

## Edge cases

- **Юзер написал `/mm-new`** (с дефисом): тоже принимай — это не полное имя skill'а, но логично. Маппь как `/mm new`.
- **Юзер написал `/mm-init`**: алиас на `/mm-init-project`.
- **Юзер написал что-то совсем непонятное** (`/mm fluffy`): покажи cheat-sheet + предложи ближайшее.

## Что НЕ делать

- Не «упрощай» работу подскилла, к которому делегируешь — он сам знает как себя вести.
- Не предлагай команд которых нет (`/mm push` не существует).
- Не пиши свою реализацию save/init/handoff — только маршрутизация.
