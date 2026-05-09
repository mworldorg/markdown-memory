# louise-skills

Личная mm-система для **louise**: связка `claude.ai` ↔ Claude Code в PowerShell ↔ Obsidian, через kacтомные skills `mm-*`.

## Зачем

Решает четыре проблемы:

1. **«Забыла какие skills использовала ранее»** — все skills в этом git-репо, junction'ятся в `~/.claude/skills/`, на любой машине: `git clone` + `register-skills.ps1` = всё доступно.
2. **«Новый чат в claude.ai не знает про проект»** — `passport.md` живёт в Project Knowledge, `handoff.md` догружает контекст последних сессий.
3. **«claude.ai слушает идеи, PowerShell делает работу»** — `mm-bridge` пишет файл-мост в Obsidian, копипастишь оттуда в PowerShell.
4. **«Каждый проект приходится настраивать руками»** — `mm-init-project` за один раз создаёт паспорт, обсидиан-структуру, инструкции для claude.ai.

## Архитектура

```
louise-skills/  (этот репо — source of truth)
├── skills/
│   ├── mm/                 ← диспетчер (/mm new, /mm save, /mm bridge, ...)
│   ├── mm-init-project/    ← создать/обновить паспорт + Obsidian + claude.ai instructions
│   ├── mm-bridge/          ← промпт-мост в файл (claude.ai → PowerShell)
│   ├── mm-handoff/         ← сводка для нового чата claude.ai
│   ├── mm-save-session/    ← закрыть сессию, лог в Obsidian
│   ├── mm-instructions/    ← генерить Project Instructions
│   └── mm-doctor/          ← самопроверка системы (junction'ы, конфиг, паспорта)
├── templates/
│   ├── passport.md         ← стандарт паспорта (11 секций + privacy checklist)
│   └── project-instructions.md  ← шаблон для claude.ai Instructions
├── config/
│   ├── mm-config.json                ← committed: общие пути и дефолты
│   └── mm-config.local.example.json  ← пример overrides для конкретной машины
├── docs/
│   └── CONFIG-LOADING.md   ← как skills находят config (env / junction / fallback)
├── scripts/
│   └── register-skills.ps1 ← junction'ит skills/ + ставит MM_REPO_ROOT env var
└── MIGRATION.md            ← миграция со старой системы Claude Setup/
```

**Source of truth:** этот git-репо.
**Active location:** `~/.claude/skills/mm-*` через NTFS junction. Edit в репо — мгновенно везде.
**Портабельность:** skills находят config через `MM_REPO_ROOT` env var → не привязаны к `C:\Users\louise\...`.

## Setup на новой машине

```powershell
git clone <remote> <path>\louise-skills
cd <path>\louise-skills
pwsh scripts/register-skills.ps1
# Скрипт сам поставит MM_REPO_ROOT в User-scope env var
# Перезапусти терминал и Claude Code

# Если Obsidian живёт на другом пути:
copy config/mm-config.local.example.json config/mm-config.local.json
# Отредактируй mm-config.local.json (он gitignored)
```

После этого — все mm-* команды работают в любом проекте.

---

# Три сценария workflow

## A. Новый или существующий проект → инициализация

```
1. cd <папка проекта> && claude
2. /mm new          (синоним: /mm init или /mm-init-project)
   → Discovery: скилл сканирует *.md в проекте
   → Preview: показывает план «СОЗДАМ / ИЗМЕНЮ / НЕ ТРОНУ»
   → ты подтверждаешь y
   → secret-grep: проверяет паспорт на токены перед загрузкой в claude.ai
3. Открой passport.md, заполни секцию 8 «Контекст для промптов» — это критично
4. claude.ai → New Project «<имя>»
   → Knowledge: загрузи passport.md из Obsidian
   → Instructions: вставь текст из <obsidian>/Projects/<имя>/project-instructions.md
5. Готово. Описывай идеи в claude.ai → получай промпты для PowerShell
```

## B. Контекст в чате claude.ai заполнился

```
1. В Claude Code (PowerShell): /mm next   (синоним: /mm handoff)
   → создаст handoff.md в <obsidian>/Projects/<имя>/
2. claude.ai → этот же Project → Knowledge
   → удали старый handoff.md (если был)
   → загрузи новый
3. New Chat в Project
4. Первая реплика: «Прочитай handoff.md и passport.md, скажи где мы.»
5. Продолжаешь — passport уже знаком, handoff даёт последние 1-2 недели
```

## C. Конец сессии

```
В PowerShell-сессии: /mm save   (синоним: /mm-save-session)
→ запишет лог в Obsidian/Claude/Sessions/
→ обновит project note и dashboard
→ обновит INDEX.md
```

Триггерные слова тоже работают: «закругляемся», «сохрани», «до завтра», «конец дня».

---

# Skills cheat sheet

| Короткая | Полная | Когда |
|---|---|---|
| `/mm` | — | Список всех команд |
| `/mm new` | `/mm-init-project` | Инициализация / обновление проекта |
| `/mm resume` | `/mm-resume` | «Где мы» — passport + last session + git + GSD-фаза |
| `/mm prompt` | `/mm-bridge` | Промпт-мост в файл для PowerShell-Клода |
| `/mm next` | `/mm-handoff` | Контекст в claude.ai заполнен — сводка для нового чата |
| `/mm save` | `/mm-save-session` | Конец сессии — лог в Obsidian |
| `/mm rules` | `/mm-instructions` | Сгенерить Project Instructions для claude.ai |
| `/mm check` | `/mm-doctor` | Самопроверка: junction'ы, vault, конфиг, паспорта |

Полные имена тоже всегда работают.

## Типичный цикл работы

```
утром / после /clear  →  /mm resume    ← восстановил контекст за 2 секунды
работаешь             →  ... (или /mm prompt если из claude.ai)
закончил день         →  /mm save      ← лог в Obsidian
контекст забит        →  /mm save → /clear → /mm resume
новый чат claude.ai   →  /mm next      ← handoff в Project Knowledge
```

## /compact vs /clear vs exit&claude

| Ситуация | Лучшее действие |
|---|---|
| Контекст < 70%, задача та же | `/compact` |
| Контекст > 70%, та же задача — нужен свежий контекст | `/mm save` → `/clear` → `/mm resume` |
| Закончил веху, новая задача | `/mm save` → `/clear` |
| Странное поведение, что-то залипло | `exit` → `claude` → `/mm resume` |
| Меняешь проект (cd в другой) | `exit` → `claude` → `/mm resume` |

**Никогда** не делай `/clear` без `/mm save` сначала — потеряешь контекст текущей сессии. Лог в Obsidian = твоя страховка.

---

# mm vs Anthropic Memory vs GSD vs context-mode — что какое решает

Четыре слоя контекста, каждый решает своё. Не пересекаются, дополняют друг друга.

| Слой | Кто заполняет | Что хранит | Когда обновляется |
|---|---|---|---|
| **Anthropic Memory** | Anthropic auto (в claude.ai Project) | Долгосрочные факты о тебе и проекте, выводы | Сама учится из чатов |
| **Project Instructions** | `/mm rules` → копипаст | Правила: как Claude должен работать в этом Project | Один раз при создании Project + после крупных изменений паспорта |
| **Project Knowledge (Files)** | `/mm new` + `/mm next` → копипаст из Obsidian | `passport.md` (структура) + `handoff.md` (свежий контекст) | passport — раз в неделю; handoff — перед каждым новым чатом |
| **GSD** (`.planning/` или `.gsd/`) | `/gsd-*` команды | Пофазовое планирование внутри milestone | Активно во время разработки крупной фичи |
| **context-mode** (MCP, плагин) | Хуки автоматом → SQLite в `~/.claude/context-mode/` | События сессии по 15 категориям, restore после `/compact` и рестарта | Постоянно сама |
| **karpathy-guidelines** (плагин) | — (поведенческие правила) | 4 принципа кодинга | Применяются при каждом написании кода |
| **Telegram bridge** (опционально) | claude-code-telegram бот | Канал push'а задач из Telegram → новая Claude сессия | По запросу с телефона |

**Правила использования:**
- **Маленький / средний проект** — только mm. GSD оверкилл.
- **Крупная фича** — mm для chat ↔ code моста + GSD для разбиения на фазы. Не конфликтуют.
- **Любая длительная сессия** — context-mode работает сам в фоне (если установлен), сильно экономит токены.
- **Anthropic Memory** — оставь как есть, она работает сама. Не пытайся ей «помогать» — это не наша зона.

## Что устанавливать дополнительно (рекомендованные плагины)

```powershell
# Karpathy 4 принципа (применяются всегда, через global CLAUDE.md тоже продублировано)
claude plugin marketplace add forrestchang/andrej-karpathy-skills
claude plugin install andrej-karpathy-skills@karpathy-skills

# context-mode — экономия контекстного окна, persistent memory сессий, sandbox для кода
claude plugin marketplace add mksglu/context-mode
claude plugin install context-mode@context-mode

# Telegram bridge (опционально — push prompt с телефона, см. docs/TG-BRIDGE.md)
pwsh scripts/install-tg-bridge.ps1
# затем заполни external/claude-code-telegram/.env, см. инструкцию в скрипте
```

После установки `/mm check` подтвердит что всё подцепилось.

**context-mode хуки и GSD хуки сосуществуют** — context-mode подключает свои хуки через plugin manifest, GSD — через `~/.claude/settings.json`. Claude Code запускает оба набора параллельно для одного события. Никаких ручных правок не требуется.

## Telegram bridge — отдельный канал к Claude Code

Для push'а задач с телефона (новая Claude сессия в указанной папке) — поставь TG-бот:

```powershell
pwsh scripts/install-tg-bridge.ps1
```

Скрипт клонирует [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram), создаёт `.venv`, кладёт `.env` шаблон. Дальше — получаешь токен у @BotFather, узнаёшь свой user_id, заполняешь `.env`, запускаешь.

Когда использовать:
- 📱 На улице с телефоном — «обнови README», «прогон тестов»
- ⏰ Cron — например, ежедневный `/mm check`
- 🤖 Автономные задачи без надзора

Когда **не** использовать:
- 💬 Интерактивная работа в текущей PowerShell-сессии — копипаст эффективнее (warm контекст не теряется)
- 🔒 Чувствительные репо — Telegram-аккаунт можно угнать через SIM swap

Полная инструкция и архитектура: [docs/TG-BRIDGE.md](docs/TG-BRIDGE.md).

---

# Конфиг

Все пути и дефолты — в `config/mm-config.json` (committed). Машинно-специфичные overrides — в `config/mm-config.local.json` (gitignored, см. `mm-config.local.example.json`).

Подробности про портабельность и алгоритм поиска — [docs/CONFIG-LOADING.md](docs/CONFIG-LOADING.md).

---

## Добавить новый mm-skill

1. Создай `skills/mm-<name>/SKILL.md`. Frontmatter:
   ```yaml
   ---
   name: mm-<name>
   version: 0.2.0
   description: <короткое описание + триггер-фразы для авто-вызова>
   ---
   ```
2. В секции «Конфиг» сошлись на `docs/CONFIG-LOADING.md` (не хардкодь пути).
3. Запусти `pwsh scripts/register-skills.ps1`.
4. (Опционально) добавь в `/mm` диспетчер алиас.
5. Перезапусти Claude Code сессию.

## Git

Сейчас remote не настроен. Когда решишь:

```powershell
git remote add origin <url>
git push -u origin main
```

После этого можно использовать на других машинах через `git clone` + `register-skills.ps1`.

## См. также

- [`docs/CONFIG-LOADING.md`](docs/CONFIG-LOADING.md) — алгоритм поиска mm-config.json
- [`MIGRATION.md`](MIGRATION.md) — миграция со старой папки `Claude Setup/`
- [`templates/passport.md`](templates/passport.md) — формат паспорта проекта
- [`templates/project-instructions.md`](templates/project-instructions.md) — шаблон для claude.ai
