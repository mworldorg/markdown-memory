# claude.ai Skills (НЕ для Claude Code)

Скиллы в этой папке предназначены для загрузки в **claude.ai** (веб): `Customize → Skills → + → Upload a skill` (или `Write skill instructions` и вставить тело SKILL.md).

**Важно:** это НЕ Claude Code скиллы.
- Они НЕ должны лежать в `<repo>/skills/` — иначе `register-skills.ps1` заджанкшенит их в `~/.claude/skills/` и они попытаются работать в Claude Code, где им не место.
- Они работают в песочнице claude.ai (нет доступа к локальному vault/git/PowerShell). Их вывод — **текст** (промпты, сводки), который louise копирует в PowerShell-Клода.

## Скиллы

- **mm-web-bridge** — партнёр louise в claude.ai: обсуждает идеи, ставит их под сомнение, проверяет актуальность в интернете, оформляет self-contained промпты для PowerShell-Клода. Глобальная замена ручной вставки Project Instructions (но per-project Instructions можно оставить для жёстких правил из секции 8 паспорта).

## Как загрузить

1. Заархивируй папку скилла (например `mm-web-bridge/`) в zip — или используй `Write skill instructions` и вставь содержимое `SKILL.md`.
2. claude.ai → Customize → Skills → + → Upload a skill.
3. Проверь, что скилл включён (тумблер).
4. Обнови, когда меняешь поведение: перезалей.
