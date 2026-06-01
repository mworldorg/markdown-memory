---
name: mm-save-session
version: 0.4.0
description: Закрывает текущую Claude Code сессию — сохраняет лог в Obsidian/Claude/Sessions/, обновляет project note, обновляет INDEX.md, перегенерирует handoff.md (для Project Knowledge claude.ai) через /mm-handoff. Если в проекте есть GSD (.planning/ или .gsd/) — также вызывает /gsd-pause-work для technical state в HANDOFF.json. Use when user says "закругляемся", "сохрани", "до завтра", "конец дня", "save session", "/mm-save-session", "закрываемся".
---

# mm-save-session — End-of-Session Logger

Оформляет финал Claude Code сессии в три места: Sessions/, Projects/, INDEX.md. Реализует правила из `~/.claude/CLAUDE.md` как skill (раньше выполнялось вручную, теперь гарантированно).

## Конфиг

Загрузи `mm-config.json` по алгоритму из `<repo>/docs/CONFIG-LOADING.md`. Поддержка `mm-config.local.json` overlay обязательна.

Понадобятся:
- `paths.obsidian_sessions`
- `paths.obsidian_projects`
- `paths.obsidian_index`

## Процесс

### Шаг 1. Собери контекст сессии

**Из текущего разговора:**
- Что обсуждали (тема в 1-2 предложениях)
- Что было сделано (список фактов: что создано, изменено, исправлено)
- Какие решения приняты и почему
- Что осталось / открытые вопросы / следующие шаги

**Из git** (если репо):
```bash
git log --since="6 hours ago" --oneline
git status --short
git diff --stat HEAD~5 2>/dev/null || git diff --stat
```
Список изменённых файлов и коммитов сегодня.

**Из cwd**: имя проекта = имя корневой папки (или из `passport.md` если есть).

### Шаг 2. Определи целевые пути

- **Имя проекта**: из `passport.md` (если в cwd или его родителях есть) → frontmatter `project`. Иначе — имя папки cwd.
- **Файл сессии**: `<obsidian_sessions>/<YYYY-MM-DD-HHMM>-<тема-slug>.md`. Время — текущее, тему-slug сгенерируй из 3-5 слов на русском в kebab-case (транслит, нижний регистр).
  - Если файл уже существует — добавь суффикс `-2`, `-3`.

### Шаг 3. Создай файл сессии

```markdown
---
created: <YYYY-MM-DDTHH:MM>
project: <project_name>
project_path: <abs_path>
tags: [claude-session, проект-<project_name>, <topical-tags>]
---

# <Заголовок-человеческий>

**Дата:** <YYYY-MM-DD HH:MM>
**Проект:** [[../Projects/<project_name>|<project_name>]]
**Длительность:** примерно <Xм / Xч>

## Задача сессии
<1-2 предложения что собирались сделать>

## Что сделано
- <факт 1>
- <факт 2>
- <факт 3>

## Ключевые решения
- **<решение>** — <почему>

## Открытые вопросы / следующие шаги
- [ ] <q1>
- [ ] <q2>

## Затронутые файлы
- `<rel_path>` — <что>
- `<rel_path>` — <что>

## Git
<если был>
- Ветка: `<branch>`
- Коммитов сегодня: <N>
- `<hash> <subject>`
```

### Шаг 4. Обнови project note

Путь: `<obsidian_projects>/<project_name>.md` ИЛИ `<obsidian_projects>/<project_name>/dashboard.md` (если папка-стиль из mm-init-project).

**Если есть папка-стиль `<obsidian_projects>/<project_name>/`**:
- Открой `dashboard.md`
- Обнови секцию «Последние сессии» — добавь ссылку на новую сессию вверх списка, обрежь до 5
- Обнови `updated:` в frontmatter

**Если только файл `<obsidian_projects>/<project_name>.md`**:
- Открой
- В секцию «Сессии» добавь строку наверх: `- [[../Sessions/<file_basename>]] — <дата> — <тема>`
- Обнови «Текущее состояние» — кратко из этой сессии

**Если ни папки ни файла нет**:
- Создай файл `<obsidian_projects>/<project_name>.md`:

```markdown
---
project: <name>
created: <date>
updated: <date>
---

# <name>

## Описание
<если в cwd есть README.md — первый параграф; иначе "TODO">

## Текущее состояние
<из этой сессии>

## Сессии
- [[../Sessions/<this_session_file_basename>]] — <date> — <тема>

## Ссылки
- Код: `<abs_path>`
```

### Шаг 5. Обнови INDEX.md

Путь: `<obsidian_index>` (по дефолту `<obsidian_claude_root>/INDEX.md`).

Добавь строку **наверх** списка сессий:

```
- <YYYY-MM-DD HH:MM> · **<project_name>** · [[Sessions/<file_basename>|<тема>]]
```

Если INDEX.md нет — создай со скелетом:
```markdown
# Claude Index

> Хронологический индекс всех сессий и проектов.

## Сессии (новые сверху)

- <первая запись>

## Проекты

- [[Projects/<name>]]
```

Если проекта ещё нет в секции «Проекты» — добавь.

### Шаг 5.5. GSD-кооперация (если применимо)

**Цель:** mm и GSD не дублируются. mm пишет нарратив в Obsidian. GSD пишет technical state (file paths, last error, position) в `HANDOFF.json`. Оба нужны для разных задач при resume.

Алгоритм:
1. Проверь `<project_root>/.planning/` (GSD v1) или `<project_root>/.gsd/` (v2).
2. Если ни одного — пропусти этот шаг.
3. Если есть — спроси одной строкой: `Также вызвать /gsd-pause-work для technical handoff (HANDOFF.json)? (y/n, дефолт y)`.
4. На `y`:
   - **GSD v1**: вызови skill `/gsd-pause-work` (Claude Code сам найдёт его, не пиши `.planning/HANDOFF.json` сам — там охраняющий хук).
   - **GSD v2**: предложи юзеру выполнить в терминале `gsd handoff` (skill этот не запускает CLI).
5. На `n` — продолжай без GSD-handoff, упомяни в финальном отчёте: «GSD handoff пропущен по запросу».
6. Если `/gsd-pause-work` вернул ошибку — не падай, упомяни в отчёте: «GSD pause-work failed: <reason>», продолжай.

### Шаг 5.6. Обнови handoff.md (для claude.ai Project Knowledge)

**Цель:** `handoff.md` — это файл, который пользователь держит в Project Knowledge чата claude.ai. Он должен оставаться свежим после каждого закрытия сессии, без ручного `/mm next`.

Алгоритм:
1. Делегируй генерацию в `/mm-handoff` (он — единственный владелец формата handoff; не дублируй его логику здесь). Вызови skill `mm-handoff` — он прочитает только что записанную сессию + последние 3-5 + git + (если есть) GSD и **перезапишет** `<obsidian_projects>/<name>/handoff.md`.
2. Это поведение **по умолчанию включено** (пользователь явно его просил) — не спрашивай y/n.
3. Если `<obsidian_projects>/<name>/handoff.md` ещё скелет (после `/mm-init-project`) — `/mm-handoff` просто заменит его полноценной версией. Это нормально.
4. Если `/mm-handoff` упал (нет паспорта, vault недоступен) — не падай, упомяни в финальном отчёте: «handoff обновить не удалось: <reason>», сессия всё равно сохранена.

> Примечание: `/mm next` (= `/mm-handoff`) остаётся для ручного обновления handoff **посреди** работы, когда контекст забился, а сессию закрывать рано.

### Шаг 6. Подтверди

Выведи (короткий блок, без воды):

```
✅ Сессия сохранена

Проект: <name>
Файл: <abs_path>/<session_file>
Project note обновлён: <abs_path>
INDEX.md обновлён.
handoff.md обновлён: <да, через /mm-handoff | не удалось: <reason>>
GSD handoff: <выполнен через /gsd-pause-work | пропущен | n/a — нет GSD>

Открытых вопросов: <K>
Следующий шаг: <первый из открытых вопросов или "не указан">
```

## Edge cases

- **Очень короткая сессия** (один вопрос-ответ, ничего не делалось): спроси `Сессия короткая, всё равно сохранять? (y/n)`. Если да — сохрани с пометкой `короткая консультация`.
- **Несколько проектов в одной сессии** (редко): спроси какой считать главным, остальные упомяни в тегах.
- **Нет Obsidian vault по пути из конфига**: останови, скажи `Vault не найден: <path>. Проверь mm-config.json`.
- **Сессия в worktree**: имя проекта бери из основной папки репо, не из имени worktree (типа `crazy-galileo-...`).

## Что НЕ делать

- Не коммить ничего в git (это работа `/push` или ручная).
- Не делай длинные сессии-хроники — формат компактный, факты + решения + вопросы.
- Не тегируй случайно — теги только из реальных тем сессии.
- Не дублируй текст между Sessions/ и Projects/ — в Project note только ссылка + одна строка.
