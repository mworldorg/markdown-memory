# mm-system Backlog

> Список рисков и улучшений, обнаруженных при дизайне mm-системы.
> Обновляется по ходу использования. Чтобы взять в работу — скажи «давай №N».

Приоритеты:
- 🔴 **Критично** — закрыть до первого настоящего проекта (риск потерять данные / получить кашу)
- 🟡 **Важно** — за 1-2 недели использования всплывут
- 🟢 **Полезно** — когда захочется

---

## 🔴 Критично

### 1. Портабельность путей в SKILL.md
Все mm-* skills сейчас хардкодят `C:\Users\louise\Desktop\louise-skills\config\mm-config.json`. Если username другой, второй ноут, переезд в `D:\` — всё ломается.
**Решение:** env var `MM_REPO_ROOT` + fallback автодетект через `git rev-parse --show-toplevel` от location SKILL.md (skill находится в репо или в junction которое указывает в репо).
**Эффект:** репо переезжает на любую машину без правок SKILL.md.

### 2. Конфликт `mm-handoff.md` vs Anthropic Memory
На скриншоте Project'а есть нативная **Memory** (Anthropic, заполняется сам). Наш `handoff.md` решает похожую задачу. Если пользоваться обоими — Claude может путаться.
**Решение:** разграничить в README:
- **Memory** — долгосрочные факты о тебе и проекте (Anthropic учится сам, мы не вмешиваемся)
- **Knowledge files** — паспорт (структура) + handoff (свежий контекст 1-2 недель)
- **Instructions** — как Claude должен работать в этом Project
Каждое решает разную задачу, не конкурирует.

### 3. Source-of-truth direction для passport.md
Сейчас skill пишет паспорт в **обе** копии (проект + Obsidian). Если ты правишь в Obsidian (через Obsidian app — удобнее) — проектная копия устаревает. Следующий `/mm-init-project --update` затрёт обсидиановские правки версией из проекта.
**Решение:** один source-of-truth + детектор рассинхрона. Варианты:
- A. Проект — source. Obsidian — read-only зеркало (генерируется skill'ом).
- B. Obsidian — source. В проекте только символ-линк или ничего.
- C. Нет дублирования: passport.md только в проекте, в Obsidian лежит ссылка/include.
Дефолт рекомендую: вариант A. Но `/mm-init-project` должен детектить рассинхрон по mtime / hash и спрашивать.

---

## 🟡 Важно

### 4. /mm-doctor — самопроверка системы
Skill, который проверяет:
- Junction'ы `~/.claude/skills/mm-*` существуют и указывают на актуальный репо
- `mm-config.json` валидный JSON, все пути существуют
- Obsidian vault достижим
- Все templates/ на месте
- Текущий проект (если в нём) имеет валидный passport.md (frontmatter parse, секции на месте)
**Эффект:** один вызов = «всё ок» или «вот что починить».

### 5. Privacy disclaimer для passport.md
`passport.md` загружается в **claude.ai Project Knowledge** = уезжает в сторонний сервис. Если ты случайно вписала туда токен / API key / приватный URL — это leak.
**Решение:** в шаблон passport'а добавить чек-лист «Перед загрузкой в claude.ai убедись:» + автоматический grep на `[A-Z0-9_]{20,}` (выглядит как токен) при `/mm-init-project` с предупреждением.

### 6. `mm-config.local.json` для машинно-специфичных переопределений
Сейчас один config на всех. Если на ноуте Obsidian в другом месте — приходится править gitи коммитить.
**Решение:** `mm-config.local.json` (в `.gitignore`) перекрывает поля основного конфига. Все skills читают слиянием.

### 7. Auto-cleanup старых bridge-архивов
`Obsidian/Claude/Bridge/archive/` будет копиться. Через год — сотни файлов мусора.
**Решение:** mini-skill `/mm-bridge-cleanup` или встроить в `/mm-doctor`: удалять архивы старше N дней (default 30).

### 8. Документация интеграции с GSD
В проектах где есть `.planning/` (GSD) — паспорт mm и GSD-документы пересекаются. Сейчас mm-init-project говорит «не конфликтуй», но не уточняет как уживаются.
**Решение:** секция в README «Когда использовать mm vs GSD vs оба»:
- mm-passport = высокоуровневый контекст (стек, конвенции, ограничения) — для всех проектов
- GSD = пофазовое планирование внутри milestone'а — для крупных проектов
- Используй оба: mm для chat ↔ code моста, GSD для разбиения работы

### 9. Shortcut `/mm` — диспетчер
Сейчас 5 команд `/mm-init-project`, `/mm-bridge`, `/mm-handoff`, `/mm-save-session`, `/mm-instructions`. Длинно.
**Решение:** добавить skill `/mm` который роутит: `/mm new` → init-project, `/mm save` → save-session, `/mm next-chat` → handoff, `/mm prompt` → bridge, `/mm rules` → instructions. С `/mm` без аргументов — список.

---

## 🟢 Полезно

### 10. Bash-эквивалент `register-skills.ps1`
Если когда-то понадобится macOS / Linux. Пока Windows-only, отложено.

### 11. Архивация старых сессий
После 6+ месяцев `Obsidian/Claude/Sessions/` распухнет. Архивировать в `Sessions/Archive/<year>/<month>/`.

### 12. Stale-passport detection
При `/mm-handoff` или `/mm-bridge`: если `passport.md` `updated:` старше 30-60 дней — предупреди «возможно стоит `/mm-init-project --update`».

### 13. Backup-стратегия для Obsidian vault
Сейчас vault на одном диске. Если диск упадёт — теряются все handoff'ы и история сессий.
**Рекомендация в README:** git'ить vault, либо использовать iCloud / OneDrive / Obsidian Sync.

### 14. Упростить `~/.claude/CLAUDE.md`
Сейчас глобальный CLAUDE.md дублирует правила сессий (Sessions/Projects/INDEX) с `mm-save-session`. Источников два — могут разъехаться.
**Решение:** в global CLAUDE.md оставить только ссылку «При закрытии сессии вызови `/mm-save-session`», правила убрать (уже в SKILL.md).

### 15. `/mm-context-pack` — для drag&drop в claude.ai
Упаковать `passport.md` + `handoff.md` + один опциональный файл задачи в `.zip` рядом с проектом. Удобно для быстрой загрузки в новый Project.

### 16. Git-hook `post-merge` — auto-register-skills
После `git pull` если появились новые `skills/mm-*/` — автоматом запустить `register-skills.ps1`. Сейчас юзер должен помнить.

### 17. Telegram-бот для bridge
Вместо копипаста — `mm-bridge` пушит prompt в Telegram-бот, ты на телефоне видишь. Бонус: история промптов синхронизирована.

### 18. Версионирование skills
В SKILL.md frontmatter `version: 0.2.0`. В финальном отчёте показывать «mm-init-project v0.2 — что нового». Помогает понять что устарело.

### 19. Eval-сценарии
Папка `tests/fixtures/`: 5-10 искусственных проектов (пустой, монорепо, с PROJECT_PASSPORT.md, с GSD, и т.п.). Скрипт прогоняет `/mm-init-project` на каждом, проверяет инварианты.

### 20. Шаблоны типовых проектов
`templates/project-bot/`, `templates/project-script/` — готовый скелет с `CLAUDE.md`, `passport.md` (заполненный для типа), `.gitignore`, `README.md`. Создание нового бота = `cp -r templates/project-bot ~/Projects/<name> && cd ~/Projects/<name> && claude && /mm-init-project`.

---

## Идеи, которые отвергнуты (для истории)

- **Skills читают config через переменные сразу из mm-config.json в RAM при старте Claude Code.** Невозможно — skills загружаются в момент использования, а не при старте сессии.
- **One mega-skill `/mm` который делает всё.** Хуже UX (`/mm` без чёткой команды непонятен в claude.ai контексте).
- **Использовать только Anthropic Memory без passport.md.** Memory медленно набирается; passport — мгновенный, структурированный, версионируемый в git.
