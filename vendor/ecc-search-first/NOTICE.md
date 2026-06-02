# NOTICE — ecc-search-first (vendored)

- **Source:** ECC — everything-claude-code · https://github.com/affaan-m/everything-claude-code
- **Original path in source:** `.kiro/skills/search-first/SKILL.md` (branch `main`)
- **License:** MIT — Copyright (c) 2026 Affaan Mustafa (see `LICENSE` in this folder)
- **Vendored:** 2026-06-02

## Что взято и что изменено

- Взят **только** `SKILL.md` (markdown research-before-coding workflow). Тело — **дословно (verbatim)**.
- **Единственное изменение:** в frontmatter `name: search-first` → `name: ecc-search-first`, чтобы имя скилла совпадало с папкой vendor и не путалось с собственными. Добавлен HTML-комментарий с атрибуцией сразу под frontmatter. MIT разрешает модификацию при сохранении notice.
- **НЕ взято / не тронуто иное:** никаких других частей ECC (AgentShield, плагин, hooks, npm, прочие скиллы).

## ⚠️ Неактуальные для mm отсылки (НЕ вырезаны намеренно)

Секция **«Integration Points»** ссылается на ECC-специфичных агентов, которых **в mm НЕТ**:
- `planner agent`, `architect agent`, `researcher agent`, `iterative-retrieval skill`.

Они оставлены в тексте дословно (не кромсаем чужой скилл), но **в mm их следует игнорировать**. Для mm работает суть скилла: «Quick Mode» (мысленный чеклист: есть ли уже в репо / npm-PyPI / MCP / skill / GitHub — до написания кода) и «Full Mode» (делегировать research обычному субагенту Claude Code через Agent/Task). Конкретные ECC-агенты — informational, не требование.

## Как обновлять

Вендоренная копия (philosophy mm: self-contained, no lock-in). Обновлять вручную: сверить с upstream по ссылке выше, перенести изменения, сохранив `name: ecc-search-first` и этот NOTICE. Без автоустановки/`npx`/сети в рантайме.
