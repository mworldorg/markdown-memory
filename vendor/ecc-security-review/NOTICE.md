# NOTICE — ecc-security-review (vendored)

- **Source:** ECC — everything-claude-code · https://github.com/affaan-m/everything-claude-code
- **Original path in source:** `.agents/skills/security-review/SKILL.md` (branch `main`)
- **License:** MIT — Copyright (c) 2026 Affaan Mustafa (see `LICENSE` in this folder)
- **Vendored:** 2026-06-02

## Что взято и что изменено

- Взят **только** `SKILL.md` (markdown-чеклист безопасности). Содержимое сохранено дословно.
- **Изменение:** в frontmatter `name: security-review` → `name: ecc-security-review`, чтобы не конфликтовать со встроенной командой `/security-review` Claude Code. Добавлен HTML-комментарий с атрибуцией сразу под frontmatter. MIT разрешает модификацию при сохранении notice.
- **НЕ взято:** соседний `agents/openai.yaml` (interface-конфиг для не-Claude среды) и любые другие части ECC (AgentShield, `/security-scan`, плагин `ecc@ecc`, hooks, npm-пакеты, остальные ~246 скиллов).

## Как обновлять

Это вендоренная копия (philosophy mm: self-contained, no lock-in). Чтобы обновить — сверить с upstream-файлом по ссылке выше, перенести изменения вручную, сохранив `name:` и этот NOTICE. Никакой автоустановки/`npx`/сети в рантайме.
