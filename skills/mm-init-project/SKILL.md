---
name: mm-init-project
version: 0.2.0
description: Инициализирует или обновляет проект для mm-системы — создаёт passport.md в корне, копию в Obsidian, dashboard.md, project-instructions.md для claude.ai. Use when user says "оформи проект", "сделай паспорт", "init project", "/mm-init", "/mm-init-project", "обнови паспорт", "регистрирую проект". Работает на пустой папке (новый проект) и на существующем коде с любыми .md файлами (auto-discovery + dry-run preview перед записью). Включает secret-grep и детектор рассинхрона между копиями паспорта.
---

# mm-init-project — Project Bootstrap & Refresh (safe edition)

Создаёт «паспорт» проекта — единый источник контекста для claude.ai Project Knowledge и для всех mm-* skills. **Всегда показывает план перед записью**, никогда не уничтожает чужие .md файлы.

## Контракт безопасности (это важно — соблюдай дословно)

**Skill ПИШЕТ только в эти файлы:**
- `<project_root>/passport.md` — создаёт или обновляет
- `<project_root>/CLAUDE.md` — **только** добавляет секцию `## mm-system` если её нет; **никогда** не редактирует существующие секции
- `<obsidian_projects>/<name>/passport.md` — копия
- `<obsidian_projects>/<name>/dashboard.md` — создаёт если нет; в режиме update обновляет только `updated:` в frontmatter и секцию «Последние сессии»
- `<obsidian_projects>/<name>/project-instructions.md` — пересоздаёт (это деривативный файл)

**Skill ТОЛЬКО ЧИТАЕТ (никогда не редактирует):**
- README.md, ARCHITECTURE.md, NOTES.md, OVERVIEW.md, CONTEXT.md, DESIGN.md, ROADMAP.md, TODO.md, BUGS.md, DECISIONS.md, и любые другие *.md в проекте
- package.json, pyproject.toml, requirements.txt, go.mod, Cargo.toml, pom.xml
- .env.example (не .env!)
- Dockerfile, docker-compose.yml, railway.json, vercel.json
- .git/config, git log, git status

**Skill НЕ ТРОГАЕТ ВООБЩЕ:**
- `.env`, `*.key`, `*.pem`, `secrets/` — даже не читает значения
- node_modules/, .venv/, dist/, build/, target/
- Файлы вне `<project_root>` за исключением Obsidian-папки из конфига

**Перед любой записью** — обязательная фаза Preview (см. ниже). Без подтверждения `y` — ничего не пишется.

## Конфиг

Загрузи `mm-config.json` по алгоритму из `<repo>/docs/CONFIG-LOADING.md`. Поддержка `mm-config.local.json` overlay обязательна. `<repo>` берётся из `_repo_root` инжектированного loader'ом.

Понадобятся:
- `paths.obsidian_projects`
- `_repo_root` (для `templates/passport.md` и `templates/project-instructions.md`)
- `bot_defaults.*`
- `default_language`

## Фаза 0. Определи целевую папку (worktree-aware)

**Целевая папка** = «корень проекта», не «cwd как есть».

Алгоритм:
1. Возьми `cwd`.
2. Если в пути есть подстрока `\.claude\worktrees\` или `/.claude/worktrees/` — это worktree. Найди корневой репо:
   - Прочитай `<cwd>/.git` (это файл-указатель, не папка). Извлеки `gitdir: <path>`. Из него выведи main repo path.
   - Если не получилось — спроси: `Это git worktree. Какую папку считать корнем проекта? <предложи: ...>`.
3. Иначе — поднимись от `cwd` пока не найдёшь `.git/` (папку, не файл) или `package.json` / `pyproject.toml` / любой явный маркер корня. Если ничего нет — `cwd` и есть корень.

**Имя проекта** = basename целевой папки. Покажи: `Имя проекта: <name> (целевая папка: <path>). Ок? (y/n или новое имя)`.

## Фаза 1. Discovery (что уже есть в проекте)

Просканируй и **выведи отчёт пользователю** перед любыми действиями.

### 1a. Существующие паспорта (миграция)

Поищи (case-insensitive) в `<project_root>` и `<project_root>/docs/`:
- `passport.md`, `PASSPORT.md`, `Passport.md`, `passport.MD` — варианты case
- `PROJECT_PASSPORT.md`, `project_passport.md` — старая louise-система (`Claude Setup/`)
- `*_passport.md`, `passport_*.md`

Любой найденный — **кандидат на миграцию**, не конфликт-блокер.

### 1b. Документы которые могут содержать контекст

Просканируй `*.md` в:
- `<project_root>/` (корень)
- `<project_root>/docs/`, `<project_root>/notes/`, `<project_root>/_docs/`
- `<project_root>/.planning/` (GSD-документы)

Распознай семантически по имени (case-insensitive substring):
| В имени есть | Категория |
|---|---|
| `readme` | Описание / overview |
| `architecture`, `design`, `arch` | Архитектура |
| `overview`, `context`, `intro` | Контекст |
| `notes`, `ideas` | Заметки |
| `decisions`, `adr`, `rfc` | Решения |
| `roadmap`, `plan` | Планы |
| `todo`, `tasks`, `backlog` | Задачи |
| `bugs`, `issues`, `known-issues` | Проблемы |
| `changelog`, `history` | История |
| `claude` (CLAUDE.md, claude-rules.md) | Правила для AI |

Прочитай **первые 50 строк** каждого найденного файла — для понимания.

### 1c. Маркеры стека

Прочитай если есть:
- `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`
- `Dockerfile`, `docker-compose.yml`, `railway.json`, `vercel.json`
- `.env.example`, `.env.template` (не `.env`!)

### 1d. Git-контекст

```bash
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git log --oneline -10
```

### 1e. Системы которые могут конфликтовать

- `.planning/` → проект использует GSD. Не конфликтуй, дополняй (паспорт mm = высокоуровневый, GSD-документы = пофазовые).
- `CLAUDE.md` → читай, оценивай размер: маленький (< 30 строк) — добавим секцию; большой — спросим перед добавлением.
- `passport.md` (точное совпадение) → режим update, см. фазу 3.

### 1f. Sync-check между копиями паспорта

Если есть и `<project_root>/passport.md` И `<obsidian>/Projects/<name>/passport.md`:
- Сравни sha256 содержимого (или хотя бы mtime + size).
- Если **расходятся** — это значит юзер редактировал одну из копий (например в Obsidian app). Покажи в Discovery:
  ```
  ⚠️ Рассинхрон: passport.md в проекте и в Obsidian отличаются.
     Проект:  updated <date>, sha <hex8>
     Obsidian: updated <date>, sha <hex8>

     Какую версию считать source-of-truth?
     [1] Проект (Obsidian перезапишется) — дефолт
     [2] Obsidian (проект перезапишется)
     [3] Show diff first
     [4] Cancel
  ```
- Запомни выбор для фазы 4 (write).

### 1f. Вывод фазы Discovery (покажи пользователю)

```
🔍 Discovery: <project_name>

Целевая папка: <abs_path>
Git: <branch>, <N> коммитов, remote: <url или local>

Найдено существующих паспортов:
  • PROJECT_PASSPORT.md  ← старая louise-система, можно мигрировать
  • passport.md          ← текущий формат, режим update
  (или: «не найдено»)

Найдено документов с контекстом:
  • README.md (описание)
  • docs/architecture.md (архитектура)
  • NOTES.md (заметки)
  • .planning/ (GSD: 3 фазы)
  (используются ТОЛЬКО для чтения — не будут изменены)

Стек определён:
  • Язык: Python 3.12
  • Фреймворк: aiogram 3.x
  • DB: SQLite
  • Тип: bot

Существующий CLAUDE.md: <нет / <N> строк, добавлю секцию mm-system / большой — спрошу>
```

## Фаза 2. Решения (если нужны)

Задай только реально неопределённые вопросы (максимум 3-4):

1. **Если найден PROJECT_PASSPORT.md** или другой кандидат миграции:
   `Найден старый паспорт <file>. Мигрировать его контент в новый passport.md? (y = мигрировать, переименую старый в .legacy / n = игнорировать)`

2. **Если есть passport.md И он явно устарел** (mtime старше 30 дней или git log показывает много коммитов после updated):
   Просто переходи в режим update без вопроса.

3. **Если CLAUDE.md > 30 строк**:
   `CLAUDE.md существует и непустой (<N> строк). Добавить секцию ## mm-system в конец? (y/n)`

4. **Если папка пустая** (новый проект):
   - Тип: bot / web / lib / script?
   - Язык / фреймворк? (для bot — дефолт `aiogram` из bot_defaults)
   - Назначение в одном предложении?

5. **Если в Obsidian уже есть `<obsidian_projects>/<name>/`**:
   `Папка в Obsidian уже есть (<N файлов). Update (y) / Создать <name>-2 (n) / Отмена (c)?`

Если пользователь говорит «решай сам» — выбирай разумный дефолт, отмечай в финальном отчёте `<assumed: ...>`.

## Фаза 3. План записи (Preview / Dry-run)

**Это обязательная фаза. Без подтверждения — НИЧЕГО не пишется.**

Покажи пользователю полный план в формате:

```
📋 План записи

СОЗДАМ:
  + <project>/passport.md (новый файл, <N> секций)
    Источники контента: README.md (overview), package.json (стек),
                        docs/architecture.md (раздел 3),
                        PROJECT_PASSPORT.md (миграция: разделы 8, 10, 11)
  + <obsidian>/Projects/<name>/passport.md (копия)
  + <obsidian>/Projects/<name>/dashboard.md (новый, скелет)
  + <obsidian>/Projects/<name>/project-instructions.md (для claude.ai)
  + <obsidian>/Projects/<name>/sessions/ (пустая папка)

ИЗМЕНЮ:
  ~ <project>/CLAUDE.md (добавлю секцию ## mm-system в конец, +12 строк)

ПЕРЕИМЕНУЮ:
  → PROJECT_PASSPORT.md → PROJECT_PASSPORT.md.legacy
    (после миграции содержимого; оригинал не удаляется)

НЕ ТРОНУ (для справки):
  README.md, docs/architecture.md, NOTES.md, .planning/*, .env, src/

Continue? (y / n / edit)
```

`edit` → дай возможность изменить план: «Не переименовывай PROJECT_PASSPORT» / «Не трогай CLAUDE.md» / «Не создавай dashboard» — пользователь редактирует список через простой dialog, ты применяешь.

`n` → останови, ничего не пиши.

`y` → переходи к фазе 4.

## Фаза 4. Запись (atomic: всё или ничего)

Делай в этом порядке. Если хоть один шаг падает — **откати уже сделанное** (удали созданные файлы, восстанови переименованный):

### 4.1. Сгенерируй текст passport.md в памяти

Возьми шаблон `<skills_repo>/templates/passport.md`. Заполни:

- **Секции 1-7, 9** — из discovery (стек, архитектура, команды, конвенции из README, ENV из .env.example).
- **Секция 8 «Контекст для промптов»**:
  - Если миграция из PROJECT_PASSPORT.md и там есть аналогичный раздел — перенеси.
  - Иначе оставь шаблон + `<!-- TODO louise: заполни секцию 8 — это критично, читается каждым промптом -->`.
- **Секция 10 «Текущее состояние»**:
  - Init: пустой шаблон.
  - Update (есть passport.md): сохрани существующий текст 1:1.
  - Migration: если в старом паспорте была секция «Текущее состояние / Status / Now» — перенеси.
- **Секция 11 «История»**:
  - Init: одна строка «<date> Initial».
  - Update: добавь строку «<date> Refresh: <что обновилось>».
  - Migration: «<date> Migrated from PROJECT_PASSPORT.md».

Frontmatter: `created` из существующего файла или сегодня; `updated` = сегодня; `mm_version` из mm-config.

### 4.2. Сгенерируй dashboard.md и project-instructions.md в памяти

Шаблон dashboard см. ниже в Appendix.
project-instructions: возьми `<skills_repo>/templates/project-instructions.md`, подставь `<PROJECT_NAME>`, добавь секцию «Особенности этого проекта» с топ-3 пунктами из секции 8 паспорта.

### 4.3. Сгенерируй патч для CLAUDE.md (если нужен)

Если CLAUDE.md существует **и** в нём нет строки `## mm-system` — добавь в конец:

```markdown

## mm-system

Этот проект подключён к mm-системе.
- Паспорт: `passport.md` (актуальный source-of-truth)
- Obsidian: `<obsidian>/Projects/<name>/`
- Skills: глобальные `mm-*` (см. `~/.claude/skills/`)
- Конец сессии: `/mm-save-session`
- Перед новым чатом claude.ai: `/mm-handoff`
```

Если CLAUDE.md нет — создай минимальный с этой секцией + первой строкой `# <name>`.

### 4.4. Запиши всё

В строгом порядке (с откатом при падении):
1. Создай Obsidian-папку и подпапки sessions/.
2. Запиши `<project>/passport.md`.
3. Запиши `<obsidian>/.../passport.md` (копия).
4. Запиши `<obsidian>/.../dashboard.md` (если не было).
5. Запиши `<obsidian>/.../project-instructions.md`.
6. Если есть PROJECT_PASSPORT.md и пользователь подтвердил миграцию — переименуй в `.legacy`.
7. Применили патч к CLAUDE.md (если планировали).

При ошибке на шагах 4-7: удали созданные файлы шагов 2-5, верни переименованный.

### 4.5. Проверка инвариантов + secret-grep

После записи проверь:
- `passport.md` содержит все 11 секций.
- Frontmatter валидный (parse YAML).
- В Obsidian нет файлов с похожими именами (`passport.md` vs `passport_old.md`) — если есть, предупреди.

**Secret-grep (критично — passport едет в claude.ai):**

Прогони passport.md через regex-поиск потенциальных секретов:

| Pattern | Что ловит |
|---|---|
| `[A-Za-z0-9_\-]{32,}` где есть и буквы и цифры | API tokens, hash'и |
| `(?i)(api[_-]?key|secret|password|token|bearer)[\s:=]+\S+` | Явные ключи |
| `[0-9]{8,12}:[A-Za-z0-9_\-]{30,}` | Telegram bot tokens |
| `sk-[A-Za-z0-9]{20,}` | OpenAI keys |
| `ghp_[A-Za-z0-9]{30,}` / `gho_` / `ghs_` | GitHub tokens |
| `xox[baprs]-[A-Za-z0-9-]{10,}` | Slack tokens |
| `https?://[^\s]*:[^@\s/]+@` | URL'ы с inline credentials |

Если что-то нашёл — **не молчи, не удаляй сам**. Покажи:
```
⚠️ В passport.md найдено что выглядит как секрет:
   Строка 47: TELEGRAM_TOKEN=12345...
   Строка 53: api_key: sk-abc123...

   passport.md загружается в claude.ai Project Knowledge → попадёт во внешний сервис.

   Действия:
   [1] Удалю секреты сам, оставлю плейсхолдер `<REDACTED>` — рекомендуется
   [2] Покажу строки, я отредактирую вручную, перезапусти /mm-init-project
   [3] Игнорировать (например это пример из docs)
```

Только после ответа юзера продолжай.

## Фаза 5. Финальный отчёт

```
✅ mm-init-project завершён

Режим: <init | update | migration>
Проект: <name>
Тип: <type> | Язык: <lang> | Стек: <главное>

Записано:
  ✓ <project>/passport.md
  ✓ <obsidian>/Projects/<name>/passport.md
  ✓ <obsidian>/Projects/<name>/dashboard.md
  ✓ <obsidian>/Projects/<name>/project-instructions.md
  ✓ <project>/CLAUDE.md (добавлена секция mm-system)

Перенесено из старого паспорта (если миграция):
  ✓ Секция «Контекст для промптов» (5 правил)
  ✓ Секция «Текущее состояние» (3 пункта)
  Старый файл переименован: PROJECT_PASSPORT.md.legacy

Не тронуто:
  README.md, docs/, NOTES.md, .planning/, .env

Следующие шаги:
  1. Открой passport.md, проверь секции 1-7 (заполнены автоматически — могут быть неточны)
  2. Заполни секцию 8 «Контекст для промптов» — это критично
  3. claude.ai → New Project «<name>»
  4. Knowledge → загрузи passport.md и dashboard.md из Obsidian
  5. Instructions → скопируй из project-instructions.md
```

## Edge cases

- **Папка пустая, но git initialized без коммитов**: спрашивай как новый проект.
- **Имя папки с пробелами / кириллицей**: используй для отображения как есть; для slug в Obsidian (имя папки) — транслит в kebab-case.
- **Несколько языков** (моно-репо): тип = `multi`, перечисляй через запятую.
- **Symlinks / junctions в проекте**: не следуй по ним (Get-Item Attributes & ReparsePoint).
- **Скрытые .md** (`.DS_Store.md` или подобное мусорное): игнорируй файлы начинающиеся с точки (кроме `.planning/`).
- **Очень большой проект** (> 1000 .md файлов): сканируй только корень + 1 уровень глубже + `docs/`. Не углубляйся.
- **Vault недоступен** (путь из конфига не существует): останови, скажи `Obsidian vault не найден: <path>. Проверь mm-config.json или создай папку.`
- **Существующий passport.md в Obsidian отличается от проекта** (рассинхрон): предупреди — какую версию считать source-of-truth? Дефолт: проектная версия выигрывает.

## Что НЕ делать

- Не делать `git init`, `git add`, `git commit`, `git push` — никаких git-операций.
- Не читать значения из `.env`, `*.key`, `*.pem`, `secrets/`.
- Не редактировать README.md, ARCHITECTURE.md и любые другие .md проекта (только passport.md и CLAUDE.md).
- Не удалять файлы (только переименование с суффиксом `.legacy` при миграции).
- Не пропускать фазу Preview — даже если кажется «и так всё ясно».
- Не задавать больше 3-4 вопросов; для остального — разумные дефолты с пометкой `<assumed: ...>`.

## Appendix: шаблон dashboard.md

```markdown
---
project: <name>
updated: <date>
---

# <name> — Dashboard

## Сейчас
<пусто на старте — обновляется через /mm-save-session>

## Последние сессии
- <будут появляться после /mm-save-session>

## Открытые вопросы
- [ ] см. passport.md секция 10

## Ссылки
- Код: `<абсолютный путь к проекту>`
- Паспорт: [[passport]]
- Sessions: [[sessions/]]
- Handoff (для нового чата claude.ai): [[handoff]]
```
