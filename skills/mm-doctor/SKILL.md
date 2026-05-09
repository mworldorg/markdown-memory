---
name: mm-doctor
version: 0.2.0
description: Самопроверка mm-системы — junction'ы, конфиг, vault, паспорта, bridge-архив. Auto-fix очевидного. Use when user says "проверь систему", "почему не работает", "/mm-doctor", "mm-status", "что-то сломалось", "проверь mm", "mm health". Запускать перед началом работы на новой машине ИЛИ когда что-то странно себя ведёт.
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
- ⚠️ Если использован legacy fallback `C:\Users\louise\Desktop\louise-skills` — предложи `[Environment]::SetEnvironmentVariable("MM_REPO_ROOT", "<repo>", "User")`
- ✅ `mm-config.local.json` (если есть) валидный, deep-merged
- ✅ Ключевые пути присутствуют: `obsidian_*`, `_repo_root`

### 2. Repo integrity

- ✅ `<repo>/templates/passport.md` существует
- ✅ `<repo>/templates/project-instructions.md` существует
- ✅ `<repo>/skills/mm-bridge/SKILL.md`, `mm-init-project`, `mm-handoff`, `mm-save-session`, `mm-instructions`, `mm-doctor`, `mm` существуют
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
- ⚠️ `updated:` старше 30 дней → предложи `/mm-init-project --update`
- ⚠️ Секция 8 «Контекст для промптов» содержит маркер `<!-- TODO louise: заполни секцию 8 -->` → намекни заполнить
- ✅ Sync с Obsidian-копией (sha256): совпадают?

Также проверь:
- ⚠️ Есть `PROJECT_PASSPORT.md` (старый формат) → предложи мигрировать `/mm-init-project`

### 7. Skills frontmatter

Для каждого `mm-*/SKILL.md`:
- ✅ Имеет `version:` в frontmatter
- ✅ `name:` совпадает с папкой
- ⚠️ Версия старше актуальной (если в `<repo>/.mm-versions.json` указана) → предложи `git pull`

### 8. Глобальный CLAUDE.md (опционально)

Прочитай `~/.claude/CLAUDE.md` если есть:
- ⚠️ Если содержит дублирующие правила Sessions/Projects/INDEX (старая ручная инструкция) — намекни упростить через ссылку на `/mm-save-session`
- ✅ Иначе — ok

## Финальный отчёт

```
🩺 mm-doctor отчёт

✅ Конфиг: загружен через <env|junction|fallback>, valid
✅ Repo integrity: все templates и SKILL.md на месте
✅ Junction'ы: 7/7 OK
⚠️ Obsidian: vault найден, bridge_archive не было — создал
✅ Bridge state: next-prompt.md от <date> (свежий)
⚠️ Bridge archive: 47 файлов старше 30 дней — предложил удалить
✅ Текущий проект: <name>, passport валидный, sync OK
⚠️ Секция 8 паспорта: TODO-маркер не убран
✅ Skills frontmatter: 7/7 v0.2.0
⚠️ Global CLAUDE.md: дублирует mm-save-session — рекомендую упростить

Итого: 4 предупреждения, 0 ошибок.

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
