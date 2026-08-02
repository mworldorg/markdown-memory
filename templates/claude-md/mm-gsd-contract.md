<!-- правки внутри блока затираются; источник — templates/claude-md/mm-gsd-contract.md -->

## Контракт mm ↔ GSD

Если в проекте есть `.planning/` (GSD v1) или `.gsd/` (v2):
- mm-skills **только читают** GSD-файлы. Никогда не пишут в них напрямую (там file-lock'и и охраняющие хуки).
- При закрытии сессии (`/mm save`) — также вызывай `/gsd-pause-work` для technical handoff в HANDOFF.json (mm пишет нарратив, GSD — file paths и position).
- При восстановлении (`/mm resume`) — читай `STATE.md` + `ROADMAP.md` + `phases/<current>/CONTEXT.md` + `HANDOFF.json` если он свежее последней mm-сессии.
- mm-passport ссылается на `.planning/PROJECT.md`, не дублирует scope.
