# 🚀 QUICK START: AI Dev Workflow

Два файла — одна система. Настраивается за 10 минут для любого проекта.

---

## Что у тебя есть

| Файл | Куда | Зачем |
|------|------|-------|
| CLAUDE_CODE_SETUP.md | Claude Code (терминал) | Создаёт паспорт, Obsidian-интеграцию, Git, команды автоматизации |
| CLAUDE_CHAT_INSTRUCTIONS.md | claude.ai → Projects → Instructions | Учит Claude генерировать промпты на основе паспорта |

---

## Одноразовая подготовка

1. Создай Obsidian vault (например AI-Projects). Запомни путь.
2. Сохрани оба файла куда удобно.

---

## Новый проект

### Шаг 1: Claude Code — настройка

```
cd путь/к/проекту
claude
```

Вставь содержимое CLAUDE_CODE_SETUP.md. Ответь на 5 вопросов (путь vault, имя проекта, remote, ветка).

Claude Code автоматически:
- Создаст PROJECT_PASSPORT.md
- Создаст структуру в Obsidian
- Создаст skills: /save-session, /update-passport, /push, /save-all
- Сохранит конфиг в CLAUDE.md

⚠️ После создания skills — **перезапусти сессию** (exit → claude). Skills загружаются при старте.

### Шаг 2: Claude Chat — создай Project

1. claude.ai → Projects → Create Project
2. Project Knowledge → загрузи PROJECT_PASSPORT.md
3. Project Instructions → вставь содержимое CLAUDE_CHAT_INSTRUCTIONS.md

Готово.

---

## Рабочий процесс

```
1. Claude Chat: опиши задачу → получи промпт с GSD-командой
2. Claude Code: вставь промпт → GSD делает работу
3. Claude Code: /save-all → паспорт + сессия + push
```

### Команды автоматизации

| Команда | Что делает | Когда |
|---------|------------|-------|
| /save-all | Паспорт + сессия + push | Конец работы |
| /save-session | Лог сессии в Obsidian | Конец дня |
| /update-passport | Обновить паспорт | После крупных изменений |
| /push | Commit + push | Сохранить в remote |

### GSD-команды (через дефис!)

| Команда | Когда |
|---------|-------|
| /gsd-fast "текст" | Мелкий фикс, 1-2 файла |
| /gsd-quick "текст" | Средняя задача |
| /gsd-quick --discuss | Неясный скоуп |
| /gsd-discuss-phase N | Новая фича — обсуждение |
| /gsd-plan-phase N | Планирование |
| /gsd-execute-phase N | Выполнение |
| /gsd-verify-work N | Проверка |
| /gsd-autonomous | Автопрогон всех фаз |
| /gsd-new-milestone | Новый milestone |
| /gsd-progress | Текущий статус |
| /gsd-pause-work | Сохранить состояние перед закрытием |
| /gsd-resume-work | Восстановить после перезапуска |

---

## Контекст заполнился

### Claude Chat
Нажми New Chat внутри того же Project. Паспорт и инструкции загрузятся автоматически.

### Claude Code
```
Контекст < 80%  →  /compact
Контекст > 80%  →  /save-session → exit → claude → /gsd-resume-work
Конец дня        →  /save-all
```

---

## Обновление паспорта в Claude Chat

После крупных изменений:
1. Claude Code: /update-passport
2. claude.ai: Project Knowledge → удали старый → загрузи новый PROJECT_PASSPORT.md

---

## Структура Obsidian (создаётся автоматически)

```
AI-Projects/Projects/МойПроект/
├── passport.md          ← актуальный паспорт
├── dashboard.md         ← статус проекта
├── sessions/            ← логи сессий
├── prompts/             ← удачные промпты (вручную)
└── context-snapshots/   ← снапшоты при сбросе
```

---

## FAQ

**Можно без GSD?** — Да. Claude Chat выдаёт прямые промпты. Skills работают без GSD.

**Можно без Obsidian?** — Да, но потеряешь историю. /push работает отдельно.

**Можно без Git remote?** — Да. /push будет только коммитить локально.

**Unknown skill после /clear?** — Перезапусти сессию: exit → claude.

**Как добавить второй проект?** — Повтори Шаг 1 + Шаг 2 в другой папке. Vault общий.
