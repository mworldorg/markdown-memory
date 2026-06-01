---
name: mm-doctor
version: 0.5.0
description: Самопроверка mm-системы — junction'ы, конфиг, vault, паспорта, bridge-архив, GSD-консистентность (passport vs PROJECT.md), наличие сторонних плагинов (karpathy, context-mode). Auto-fix очевидного. Use when user says "проверь систему", "почему не работает", "/mm-doctor", "mm-status", "что-то сломалось", "проверь mm", "mm health". Запускать перед началом работы на новой машине ИЛИ когда что-то странно себя ведёт.
---

# mm-doctor — System Health Check & Auto-Fix

Прогон диагностики всей mm-системы. Не пишет ничего без подтверждения.

## Конфиг

Загрузи `mm-config.json` по алгоритму из `<repo>/docs/CONFIG-LOADING.md`. Поддержка `mm-config.local.json` overlay обязательна. Loader должен инжектировать `_repo_root`.

Если loader падает — это уже первая ошибка, выведи её и предложи фикс из CONFIG-LOADING.md.

## Чек-лист (выполнять по порядку, помечать ✅ / ⚠️ / ❌)

### 1. Конфиг

- ✅ `mm-config.json` найден (откуда: env / junction / fallback)
- ✅ Валидный JSON
- ⚠️ Если использован legacy fallback (см. `docs/CONFIG-LOADING.md`) — предложи `[Environment]::SetEnvironmentVariable("MM_REPO_ROOT", "<repo>", "User")`
- ✅ `mm-config.local.json` (если есть) валидный, deep-merged
- ✅ Ключевые пути присутствуют: `obsidian_*`, `_repo_root`

### 2. Repo integrity

- ✅ `<repo>/templates/passport.md` существует
- ✅ `<repo>/templates/project-instructions.md` существует
- ✅ `<repo>/skills/mm-bridge/SKILL.md`, `mm-init-project`, `mm-resume`, `mm-handoff`, `mm-save-session`, `mm-instructions`, `mm-doctor`, `mm` существуют (8 skills)
- ✅ `<repo>/scripts/register-skills.ps1` существует

### 3. Junction'ы (`~/.claude/skills/mm-*`)

Для каждого `mm-*` в `<repo>/skills/`:
- ✅ Junction `~/.claude/skills/mm-<name>` существует
- ✅ Является reparse-point (junction, не папка)
- ✅ Target указывает на `<repo>/skills/mm-<name>` (case-insensitive сравнение)
- ❌ Battery: target указывает на удалённую/несуществующую папку → битый junction

PowerShell-проверка:
```powershell
$item = Get-Item "$env:USERPROFILE\.claude\skills\mm-bridge" -Force
$item.Attributes -band [System.IO.FileAttributes]::ReparsePoint  # должно быть != 0
$item.Target  # должно совпадать с <repo>/skills/mm-bridge
Test-Path $item.Target  # должно быть true
```

При ошибках предложи: `Запустить scripts/register-skills.ps1 для пере-создания junction'ов? (y/n)`. Если y — запусти.

### 4. Obsidian vault

Из конфига возьми `paths.obsidian_*` пути:
- ✅ `obsidian_vault` существует
- ✅ `obsidian_claude_root` существует
- ✅ `obsidian_bridge` существует (создай если нет — это безопасно)
- ✅ `obsidian_bridge_archive` существует (создай если нет)
- ✅ `obsidian_sessions` существует (создай если нет)
- ✅ `obsidian_projects` существует (создай если нет)
- ⚠️ `obsidian_index` файл есть; если нет — предупреди но не падай

### 5. Bridge state

- ✅ `<obsidian_bridge>/next-prompt.md` — info: есть/нет, дата
- ⚠️ Если есть и старше 7 дней — намекни: `Старый бридж-промпт от <date>. Уже использован?`
- ⚠️ Архив старше 30 дней: посчитай файлы в `<obsidian_bridge_archive>` старше 30 дней. Если > 0:
  ```
  В архиве bridge-промптов: <N> файлов, <M> старше 30 дней.
  Удалить старые? (y/n)
  ```

### 6. Текущий проект (если cwd внутри проекта)

Если в `cwd` или родителях есть `passport.md`:
- ✅ Frontmatter валидный YAML
- ✅ Все 11 секций присутствуют
- ✅ Frontmatter содержит `gsd_version: <none|v1|v2>`
- ⚠️ `updated:` старше 30 дней → предложи `/mm-init-project --update`
- ⚠️ Секция 8 «Контекст для промптов» содержит маркер `<!-- TODO louise: заполни секцию 8 -->` → намекни заполнить
- ✅ Sync с Obsidian-копией (sha256): совпадают?

Также проверь:
- ⚠️ Есть `PROJECT_PASSPORT.md` (старый формат) → предложи мигрировать `/mm-init-project`
- ✅ `<obsidian_projects>/<name>/handoff.md` существует (создаётся на `/mm-init-project`, обновляется на `/mm-save-session`). Если нет → `⚠️ handoff.md отсутствует — запусти /mm save (или /mm next) чтобы создать; он нужен для Project Knowledge claude.ai.`

### 6.1. GSD ↔ passport консистентность (если есть GSD)

Если passport `gsd_version` ≠ none, прогони cross-check:

**Проверка 1: версия в passport совпадает с реальностью**
- Если в passport `gsd_version: v1`, проверь что `<project_root>/.planning/` существует.
- Если `gsd_version: v2` — проверь `<project_root>/.gsd/`.
- Если расходится → `❌ passport говорит gsd_version: v1, но .planning/ не найдена. Запусти /mm-init-project --update.`

**Проверка 2: scope не разъехался**
- Если есть `.planning/PROJECT.md` (v1):
  - Прочитай первые 30 строк и сравни с секцией 1 («Назначение») паспорта.
  - Если **ключевые слова не пересекаются** (jaccard < 0.3 на нормализованных tokens) → `⚠️ passport.md секция 1 и .planning/PROJECT.md описывают разное. Возможно scope изменился. Обнови passport через /mm-init-project --update.`
- Если есть `.gsd/STATE.md` или AGENTS.md → аналогично.

**Проверка 3: текущая фаза не устарела в паспорте**
- В passport секция 9 строка `Текущий milestone / phase: <X>`.
- В `.planning/STATE.md` или `.gsd/STATE.md` — фактический current.
- Если расходятся → `⚠️ passport.md секция 9 говорит фаза «X», STATE.md показывает «Y». Обнови.`

**Проверка 4: source-of-truth direction**
- В passport секция 9 строка `Source-of-truth для scope/requirements: <X>`.
- Должна быть `.planning/PROJECT.md` (если GSD есть) или `passport.md` (если GSD нет).
- Иначе → `⚠️ Source-of-truth не указан явно — две системы могут разъехаться. Заполни секцию 9.`

**Проверка 5: mm не пишет в .planning/**
- Если git log показывает что любой mm-skill коммитил файлы в `.planning/*` за последние 30 дней → `❌ mm писал в .planning/ — это нарушение контракта. Откатить вручную.`
- (это защита от будущих багов; mm-skills не должны это делать)

**Проверка 6: GSD-директива есть в CLAUDE.md** (ретро-детектор)
- Если `gsd_version != none`, проверь что `<project_root>/CLAUDE.md` содержит подблок `### GSD в этом проекте` (его добавляет `/mm-init-project` с версии 0.5.0).
- Если блока нет → `⚠️ В проекте есть GSD, но в CLAUDE.md нет GSD-директивы (проект инициализирован старой версией mm). Запусти /mm-init-project (update) — добавит правило маршрутизации работы через GSD.`
- Это закрывает вопрос «какие старые проекты надо обновить под новую GSD-интеграцию» — doctor находит их сам.

### 7. Версии

**Единый источник версии mm-системы — `config.version`** в `mm-config.json` (repo-wide release). Per-skill `version:` в каждом `SKILL.md` — гранулярная история конкретного скилла; **разные per-skill версии это норма, не рассинхрон.**

Для каждого `mm-*/SKILL.md`:
- ✅ Имеет `version:` в frontmatter
- ✅ `name:` совпадает с папкой

Версионная консистентность:
- ✅ `config.version` присутствует и валиден (semver).
- ⚠️ Если у текущего проекта `passport.mm_version` **старше** `config.version` → `⚠️ Паспорт проштампован mm <passport.mm_version>, актуальная <config.version>. Прогони /mm-init-project (update) для refresh.`
- (Файл `.mm-versions.json` больше не используется — игнорируй, если встретишь.)

### 8. Глобальный CLAUDE.md (опционально)

Прочитай `~/.claude/CLAUDE.md` если есть:
- ⚠️ Если содержит дублирующие правила Sessions/Projects/INDEX (старая ручная инструкция) — намекни упростить через ссылку на `/mm-save-session`
- ✅ Иначе — ok

### 9. Сторонние интеграции (плагины, MCP)

Проверь установлены ли рекомендованные плагины:

- **karpathy-skills** (`~/.claude/plugins/marketplaces/karpathy-skills/`) — 4 принципа кодинга
  - ✅ установлен / ⚠️ нет — `claude plugin marketplace add forrestchang/andrej-karpathy-skills && claude plugin install andrej-karpathy-skills@karpathy-skills`
  - ✅ В `~/.claude/CLAUDE.md` есть секция Karpathy Guidelines (4 принципа продублированы текстом для всех проектов)

- **context-mode** (`~/.claude/plugins/marketplaces/context-mode/`) — MCP-сервер экономии контекста
  - ✅ установлен / ⚠️ нет — `claude plugin marketplace add mksglu/context-mode && claude plugin install context-mode@context-mode`
  - Если установлен:
    - ✅ Каталог сессий `~/.claude/context-mode/sessions/` существует и есть `.db` файлы
    - ⚠️ База старше 90 дней без cleanup → намекни `/ctx-purge`
    - ⚠️ Хуки контекст-мода работают параллельно с GSD-хуками — это норм, оба независимы. Если видишь медленный PostToolUse — это сумма обоих, не баг.
    - 💡 Для расширенной диагностики используй `/ctx-doctor` (skill самого context-mode)
  - 📊 Опционально показать накопленную статистику: `~/.context-mode/stats.json` (если есть)

- **GSD hooks** в `~/.claude/hooks/` — должны быть в `settings.json` SessionStart/PreToolUse/PostToolUse. Уже проверено в этих секциях выше.

- **Telegram bridge** (claude-code-telegram, опционально):
  - Если в `mm-config.local.json` `tg_bridge.enabled = true`:
    - ✅ `<repo>/external/claude-code-telegram/` существует
    - ✅ `<repo>/external/claude-code-telegram/.env` существует
    - ✅ В `.env` заполнены `TELEGRAM_BOT_TOKEN`, `ALLOWED_USERS`, `APPROVED_DIRECTORY` (НЕ читай значения — только проверь не пустые)
    - ⚠️ Если `CLAUDE_MAX_COST_PER_USER` не задан — предупреди (риск runaway costs)
    - ⚠️ Если `APPROVED_DIRECTORY = C:\` или другой слишком широкий путь — предупреди про безопасность
    - 💡 Проверка процесса: `Get-Process python` — если ни одного `python.exe` процесса нет, бот может быть не запущен. Это просто намёк, не ошибка.
  - Если `tg_bridge.enabled = false` или нет — пропусти. Это опциональная фича.

## Финальный отчёт

```
🩺 mm-doctor отчёт

✅ Конфиг: загружен через <env|junction|fallback>, valid
✅ Repo integrity: все templates и SKILL.md на месте
✅ Junction'ы: 8/8 OK
⚠️ Obsidian: vault найден, bridge_archive не было — создал
✅ Bridge state: next-prompt.md от <date> (свежий)
⚠️ Bridge archive: 47 файлов старше 30 дней — предложил удалить
✅ Текущий проект: <name>, passport валидный (gsd_version: <none|v1|v2>), sync OK
✅ handoff.md: на месте <или ⚠️ отсутствует — /mm save>
✅ GSD-директива в CLAUDE.md: есть <или ⚠️ нет — /mm new для retrofit; или n/a если GSD нет>
⚠️ Секция 8 паспорта: TODO-маркер не убран
✅ Skills frontmatter: 8/8 имеют version и name
✅ Версии: config.version <X.Y.Z>, passport.mm_version <X.Y.Z> <совпадают | паспорт старше — /mm new>
✅ karpathy-skills plugin: установлен
✅ context-mode plugin: установлен, sessions/ есть
⚠️ Telegram bridge: не установлен (опционально — см. docs/TG-BRIDGE.md)

Итого: 3 предупреждения, 0 ошибок.

Что предлагаю сделать сейчас:
1. Удалить 47 старых bridge-архивов (одна команда)
2. Заполнить секцию 8 в C:\<path>\passport.md
3. (опционально) упростить ~/.claude/CLAUDE.md через ссылку на /mm-save-session

Согласовать каждое отдельно? (y / только 1 / только 2 / skip)
```

## Auto-fixes (требуют подтверждения)

С разрешения юзера:
- Создать недостающие папки в Obsidian (`bridge`, `archive`, `sessions`, `projects`)
- Пере-запустить `register-skills.ps1` при битых junction'ах
- Удалить bridge-архивы старше N дней
- Установить `MM_REPO_ROOT` env var

**Никогда без подтверждения:**
- Удаление файлов в Obsidian (кроме архивов с явным yes)
- Правка `~/.claude/CLAUDE.md` (это вне репо, чувствительный файл)
- Правка чужих passport.md
- `git` операции

## Edge cases

- **Запуск без интернета**: всё локально, должно работать.
- **Запуск из worktree**: используй ту же worktree-detection логику что и mm-init-project (resolve до main repo).
- **Несколько mm-config.json в разных папках** (по ошибке клонировали репо дважды): обнаружь и предупреди.
- **Junction указывает на старый репо** (после переезда): предложи запустить register-skills.ps1 в новой локации.

## Что НЕ делать

- Не молчать при ошибках — всегда показывай конкретную команду фикса.
- Не «чинить» вещи без подтверждения юзера.
- Не отчитываться победно если есть ⚠️/❌ — отчёт должен быть честным.
