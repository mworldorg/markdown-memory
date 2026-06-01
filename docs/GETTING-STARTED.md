# Getting Started — как переходить на mm

> Гайд для **louise**: как взять любой проект (новый или давно разрабатываемый) и поставить его на mm-рельсы за 15-30 минут, не сломав то что уже работает.

## TL;DR — какой ты сценарий?

```
Это новый проект (пустая папка)?
  └─ Да → См. §A. Новый проект с нуля
  └─ Нет → У тебя уже есть код, история, чаты в claude.ai
       │
       ├─ Есть PROJECT_PASSPORT.md (старая Claude Setup система)?
       │    └─ Да → См. §B1. Миграция со старого паспорта
       │    └─ Нет → продолжай ↓
       │
       ├─ Есть .planning/ (GSD)?
       │    └─ Да → См. §B2. Миграция проекта с GSD
       │    └─ Нет → продолжай ↓
       │
       └─ Есть только код + опционально CLAUDE.md → См. §B3. Миграция голого проекта
```

Каждый сценарий ниже — пошаговый, с конкретными ответами на вопросы которые скилл задаст, и со списком «что НЕ ломается».

---

# §A. Новый проект с нуля

**Когда:** только создал папку, кода ещё нет (или 1-2 файла).

## Шаги

```powershell
# 1. Создай и зайди в папку проекта
mkdir C:\Users\louise\Desktop\Scripts\<имя>
cd C:\Users\louise\Desktop\Scripts\<имя>

# 2. (Опционально) git init если хочешь версионирование сразу
git init

# 3. Запусти Claude Code и инициализируй
claude
/mm new
```

## Что будет спрашивать `/mm new`

| Вопрос | Что ответить |
|---|---|
| `Имя проекта: <basename>. Ок?` | `y` (либо введи кастомное имя) |
| `Папка пустая. Тип: bot / web / lib / script?` | Выбери (для Telegram-бота — `bot`) |
| `Язык / фреймворк?` | Дефолт из `bot_defaults` (aiogram 3.x) или укажи свой |
| `Назначение в одном предложении?` | Кратко: «Бот для уведомлений по расписанию» |
| Preview плана | `y` если устраивает |

## Что создастся

| Где | Что |
|---|---|
| `<project>/passport.md` | Скелет паспорта (11 секций, секции 1-7, 9 заполнены автоматом, секция 8 — TODO для тебя) |
| `<project>/CLAUDE.md` | Минимальный с секцией `## mm-system` |
| `<obsidian>/Projects/<name>/passport.md` | Копия |
| `<obsidian>/Projects/<name>/dashboard.md` | Скелет: «Сейчас в работе: пусто на старте» |
| `<obsidian>/Projects/<name>/project-instructions.md` | Текст для claude.ai |
| `<obsidian>/Projects/<name>/sessions/` | Пустая папка для будущих логов |

## Дальше — заполни секцию 8 (критично)

Открой `<project>/passport.md`, найди раздел **«8. Контекст для промптов»**. Там сейчас TODO-маркер. Впиши 5-8 жёстких правил проекта:
- Что **никогда не трогать** (пути / файлы / модули)
- Какие конвенции обязательны (стиль ошибок, async vs sync, DB-доступ)
- Какие зависимости фиксированные (версии)
- Чего НЕ добавлять (новые ORM, новые libs)

**Эта секция читается каждым промптом из mm-bridge.** Без неё claude.ai будет генерить промпты «как ему хочется».

## Подключи к claude.ai

```
1. claude.ai → Projects → New Project «<имя>»
2. Settings → Instructions:
   - Открой <obsidian>/Projects/<name>/project-instructions.md
   - Скопируй ВСЁ → вставь → Save
3. Knowledge → +Add Files:
   - passport.md из <obsidian>/Projects/<name>/
   - dashboard.md из той же папки
4. Готово
```

После этого New Chat в этом Project уже знает кто ты, как с тобой работать и что за проект.

---

# §B. Миграция существующего проекта

Базовая идея: mm **дополняет** то что уже работает, не заменяет. Код не трогается, GSD не трогается, чаты в claude.ai продолжают жить.

## §B1. Миграция со старого PROJECT_PASSPORT.md

**Если** в корне проекта есть `PROJECT_PASSPORT.md` (от старой Claude Setup системы).

```powershell
cd <project>
claude
/mm new
```

В Discovery скилл найдёт `PROJECT_PASSPORT.md` и спросит:

| Вопрос | Ответ | Что произойдёт |
|---|---|---|
| `Найден старый паспорт PROJECT_PASSPORT.md. Мигрировать в passport.md?` | **`y`** | Прочитает старый, перенесёт стек/конвенции/контекст-промптов/текущее состояние в новый 11-секционный формат. Старый файл переименует в `PROJECT_PASSPORT.md.legacy` (НЕ удалит). |
| `Найден CLAUDE.md (N строк). Добавить секцию mm-system в конец?` | **`y`** (если CLAUDE.md маленький) или **`n`** (если решил руками) | Только append, существующие секции не трогает |

**После миграции:**
- `passport.md` (новый, активный)
- `PROJECT_PASSPORT.md.legacy` (backup, можно удалить через 2-3 недели)
- Существующие записи в Obsidian — см. §C ниже

## §B2. Миграция проекта с GSD (.planning/)

**Если** в проекте есть `.planning/PROJECT.md`, `STATE.md`, фазы.

```powershell
cd <project>
claude
/mm new
```

mm детектит GSD автоматом. В Discovery увидишь:

```
GSD detection:
  • Версия: v1 (.planning/)
  • PROJECT.md: есть (240 строк) — могу импортировать vision и audience
  • REQUIREMENTS.md: есть (REQ-001..N)
  • Текущий milestone: M1 «<...>», phase 03/07 (in-progress)
  • codebase/: STACK.md, ARCHITECTURE.md, CONVENTIONS.md
```

| Вопрос | Ответ | Почему |
|---|---|---|
| `Найден .planning/PROJECT.md. Импортировать в секции 1, 3 паспорта (y) / только сослаться (n)?` | **`n`** (рекомендуется) | Source-of-truth для scope = `.planning/PROJECT.md`. Дублирование в passport приведёт к рассинхрону. mm-passport напишет «см. .planning/PROJECT.md» |

**Что точно безопасно:**
- mm **только читает** `.planning/*` — никогда не пишет туда напрямую (там file-lock'и и `gsd-workflow-guard` хук)
- GSD-команды (`/gsd-execute-phase`, `/gsd-progress`) работают как раньше
- В `passport.md` появится секция 9 строка `gsd_version: v1`, текущий milestone/phase

## §B3. Миграция голого проекта (только код + CLAUDE.md)

```powershell
cd <project>
claude
/mm new
```

В Discovery скилл просканирует `*.md` в корне + `docs/`, найдёт README/ARCHITECTURE/NOTES/etc, **прочитает их**, но не отредактирует (только passport.md и CLAUDE.md изменятся).

Auto-detect стека (по `package.json` / `pyproject.toml` / `Cargo.toml` / etc.) определит фреймворк, тип, версии. Если уверенно — заполнит секции 2, 3, 5 паспорта без вопросов.

## Безопасность во ВСЕХ сценариях миграции

| Что mm пишет | Что mm только читает | Что mm НЕ ТРОГАЕТ |
|---|---|---|
| `<project>/passport.md` | README, ARCHITECTURE.md, NOTES.md, любые .md в корне и docs/ | `.env`, `*.key`, `*.pem`, `secrets/` |
| `<project>/CLAUDE.md` (только append секции `## mm-system`) | `package.json`, `pyproject.toml`, `requirements.txt` и т.п. | `node_modules/`, `.venv/`, `dist/`, `build/` |
| `<obsidian>/Projects/<name>/...` | `.env.example` (только имена ENV) | `.planning/` (только чтение, никакой записи) |
| Переименование `PROJECT_PASSPORT.md → .legacy` (не удаление) | git log, git status | Любые файлы вне `<project>` и `<obsidian>` |

**Перед записью — обязательная фаза Preview** с подтверждением `y/n/edit`. Без `y` ничего не пишется.

---

# §C. Что куда в claude.ai

После `/mm new` нужно подключить проект к claude.ai. Три слота на странице Project (см. скриншот в README):

| Слот | Что туда | Кто заполняет |
|---|---|---|
| **Memory** | Ничего | Anthropic учится сама из чатов |
| **Instructions** | Текст из `<obsidian>/Projects/<name>/project-instructions.md` | Ты, один раз через копипаст. Обновлять при сильных изменениях паспорта. |
| **Files (Knowledge)** | `passport.md` + `dashboard.md` + `handoff.md` (создаётся скелетом при `/mm new`, обновляется при каждом `/mm save`) | Ты, через UI. passport обновлять раз в неделю, handoff перезагружать когда садишься за новый чат |

## Что НЕ грузить в Files и почему

| ❌ Не грузить | Почему |
|---|---|
| Код проекта (`bot.py`, `main.py` и т.д.) | Слишком много, быстро меняется. Реальный код — работа PowerShell-Клода |
| Все sessions из `Obsidian/Sessions/` | Дублируют то что уже в `handoff.md`, раздувают контекст |
| `.planning/*` файлы (PROJECT.md, STATE.md, ROADMAP.md) | Это для GSD внутри Claude Code. Их выжимка идёт в `handoff.md` через `/mm next` |
| `accounts.json`, `.env`, `*.key` | **Секреты!** Никогда. mm secret-grep тоже их ловит |
| `PROJECT_PASSPORT.md.legacy` | Это backup, не актуальная версия |

## Если у тебя УЖЕ есть Project в claude.ai с этим проектом

(Типичный случай при миграции долгого проекта.)

1. **Не создавай новый Project** — используй существующий
2. Files: удали старые (например `PROJECT_PASSPORT.md`) → загрузи новые `passport.md` + `dashboard.md`
   - Anthropic **не оверрайдит** файлы при upload — нужно сначала **удалить** одноимённые
3. Instructions: удали старый текст → вставь новый из `project-instructions.md` → Save
4. **Старые чаты в этом Project оставь как есть** — они уже завершены контекстуально, новых не будет
5. New Chat в Project — будет работать на новых правилах

---

# §D. Повседневный workflow

После миграции/инициализации — цикл одинаковый для всех проектов.

```
🌅 Открыл сессию (утром или после /clear)
   /mm resume
   → читает passport + dashboard + git + GSD STATE/HANDOFF + последнюю сессию
   → выводит: «Где мы, что в работе, что брать следующим»

💼 Работаешь
   - Если задача из claude.ai (обсудил там, нужно делать в коде):
     /mm prompt "..."  ИЛИ просто опиши — bridge сам напишет файл
   - Если GSD-фаза:
     /gsd-execute-phase N
   - Просто кодинг:
     ничего не нужно, работаешь как обычно

🌇 Конец сессии (или контекст близок к 70%)
   /mm save
   → лог в Obsidian/Projects/<name>/sessions/
   → обновит dashboard.md
   → обновит handoff.md (для Project Knowledge claude.ai)
   → если есть GSD: спросит вызвать /gsd-pause-work (скажи y)

📲 Хочу новый чат claude.ai (контекст забит, сессию закрывать рано)
   /mm next
   → обновит handoff.md прямо сейчас, не закрывая сессию
   → claude.ai → Project → Files → удали старый handoff.md → загрузи новый
   → New Chat в Project → "Прочитай handoff.md и passport.md, скажи где мы"

🔥 Что-то странно работает
   /mm check
   → диагностика всей системы (junction'ы, vault, паспорт, GSD)
```

## /compact vs /clear vs exit&claude

| Ситуация | Лучшее |
|---|---|
| Контекст < 70%, та же задача | `/compact` (сжать историю в той же сессии) |
| Контекст > 70%, та же задача — нужен свежий | `/mm save` → `/clear` → `/mm resume` |
| Закончил веху, новая задача | `/mm save` → `/clear` |
| Странное поведение, что-то залипло | `exit` → `claude` → `/mm resume` |
| Меняешь проект (cd в другой) | `exit` → `claude` → `/mm resume` |

**Никогда** `/clear` без `/mm save` сначала — потеряешь контекст текущей сессии.

---

# §E. Когда что обновлять

| Артефакт | Триггер обновления | Команда |
|---|---|---|
| `passport.md` (структура) | Сменился стек / конвенции / hot-paths | `/mm new` (режим update) |
| `dashboard.md` (текущий статус) | Само через `/mm save` | — |
| `handoff.md` (свежий контекст) | Авто при каждом `/mm save`; вручную — посреди работы | `/mm save` (авто) / `/mm next` (вручную) |
| `project-instructions.md` для claude.ai | Сильно поменялся паспорт | `/mm rules` → копипаст в Project Instructions |
| GSD `.planning/*` | Через GSD-команды | `/gsd-*` |
| Sessions log | Каждый раз в конце сессии | `/mm save` |

---

# §F. Risks & Rollback

## Когда **НЕ** мигрировать прямо сейчас

| Состояние | Можно? |
|---|---|
| Между планами в фазе, deploy verified, pytest зелёный | ✅ Да, идеальный момент |
| Внутри плана, RED-тесты не закрыты | ❌ Подожди — доделай RED→GREEN→docs |
| Только что зашёл, ничего не трогал | ✅ Да |
| Сейчас тестируешь production-фикс с пользователями | ❌ Подожди до уверенности в фиксе |
| Закрыл день, выходной | ✅✅ Утром в выходной — лучший момент |

## Realistic risks (по убыванию)

### 🟡 Старые чаты в claude.ai не понимают новый формат
**Что:** старые чаты с прежними Knowledge продолжат работать в своём контексте, но новый формат паспорта они не увидят пока не New Chat.
**Митигация:** не трогай старые. Пусть доживут естественно.

### 🟡 Anthropic Memory помнит старое имя `PROJECT_PASSPORT.md`
**Что:** в новых чатах Memory может ссылаться на старое имя.
**Митигация:** через 2-3 чата привыкнет. В первом чате можешь явно сказать «теперь файл называется passport.md».

### 🟢 Параллельно живут файл и папка в Obsidian
**Что:** старый `Projects/<name>.md` (если был) и новая `Projects/<name>/`. Obsidian не сломается.
**Митигация:** через 2-3 дня перенеси полезное из старого файла в новый dashboard, старый архивируй.

### 🟢 Sessions в двух локациях
**Что:** старые в `Obsidian/Sessions/`, новые в `Projects/<name>/sessions/`. mm-resume читает обе.
**Митигация:** через 3-5 новых сессий handoff насытится из новой локации, старые остаются доступны через ссылки.

### 🔴 Прерывание в середине RED→GREEN коммита
**Что:** mm-init-project занимает ~15 минут — контекст-свитч в незакрытом цикле может потерять нить.
**Митигация:** сначала закрой цикл (RED→GREEN→docs), потом мигрируй.

## 5-минутный rollback (если совсем не пошло)

mm не делает ничего необратимого:

```powershell
cd <project>

# Восстанови старый паспорт
mv PROJECT_PASSPORT.md.legacy PROJECT_PASSPORT.md
rm passport.md

# Удали из CLAUDE.md секцию ## mm-system (12 строк в конце)
# Через любой редактор

# Удали Obsidian-папку
rm -r "$env:USERPROFILE\Documents\Obsidian Vault\Claude\Projects\<имя>"
```

`.planning/` и код не трогались — никаких rollback'ов там не нужно.

В claude.ai:
- Files: удали `passport.md` и `dashboard.md`, верни старые
- Instructions: удали mm-текст, верни старые
- Старые чаты как работали, так и работают

---

# §G. FAQ / Частые ситуации

### Q: У меня в проекте уже есть `passport.md` (не от mm). Что будет?
**A:** mm-init-project детектит и переходит в режим **update** — сохранит секции 8 (контекст для промптов) и 10 (текущее состояние) как есть, обновит секции 1-7 (стек, архитектура, команды) если изменились.

### Q: А если я редактирую `passport.md` руками между запусками `/mm new`?
**A:** Это нормально. Секции 8 и 10 — для ручного редактирования. mm уважает их при update. Если редактируешь секции 1-7 — это рисково (`/mm new` их перезапишет из автоматического сканирования).

### Q: А если я редактирую `passport.md` в Obsidian (через obsidian-app — удобнее), не в проекте?
**A:** Сейчас рассинхрон обнаружится при следующем `/mm new` — увидишь предупреждение «Рассинхрон: passport.md в проекте и в Obsidian отличаются. Какую версию считать source-of-truth?». По умолчанию — проектная версия выигрывает. Лучшая практика: **редактируй только проектную копию**, Obsidian-копия деривативная.

### Q: GSD сам перезаписывает `.planning/STATE.md` всё время. Не сломается ли mm-resume?
**A:** Нет. mm только **читает** `.planning/*`, никогда не пишет. file-lock'и GSD не страдают.

### Q: Я случайно вписал секрет в passport.md. Что будет?
**A:** При следующем `/mm new` (любой режим) сработает **secret-grep** перед записью в Obsidian — покажет «найдено что выглядит как токен», предложит redact / показать строки / игнорировать. Не молчит, не пускает в claude.ai automatically.

### Q: Можно ли использовать mm без Obsidian?
**A:** Сейчас — нет. Все skills читают/пишут в Obsidian (vault путь в `mm-config.json`). Если когда-то понадобится — можно сделать backend-абстракцию. Пока Obsidian — обязательный.

### Q: Если у меня несколько проектов одновременно (нет одного «текущего»)?
**A:** mm работает per-project — `cd <project>` определяет какой паспорт грузить. В одной Claude Code сессии работаешь с одним проектом. В Obsidian каждый проект — своя папка `Projects/<name>/`.

### Q: Как добавить новый mm-skill?
**A:** Создай `<repo>/skills/mm-<name>/SKILL.md`, запусти `pwsh scripts/register-skills.ps1`, перезапусти Claude Code. Опционально добавь алиас в `skills/mm/SKILL.md` (диспетчер).

### Q: Что если GSD v2 появится в проекте?
**A:** mm детектит и `.planning/` (v1), и `.gsd/` (v2). В passport frontmatter поле `gsd_version: v1|v2|none`. mm-resume ветвится автоматически.

### Q: Я работаю с двух машин. Как синхронизировать?
**A:** Запушь `louise-skills` в git remote (приватный). На второй машине: `git clone` → `pwsh scripts/register-skills.ps1` → создай `config/mm-config.local.json` с путями к Obsidian/coupling-папкам этой машины. Obsidian sync (через Obsidian Sync, iCloud, OneDrive) перенесёт паспорта/sessions.

---

# §H. Чек-лист: всё ли готово после миграции

После `/mm new` пройдись:

- [ ] `<project>/passport.md` существует, frontmatter валидный, секция 8 заполнена осмысленно (не TODO-маркер)
- [ ] `<obsidian>/Projects/<name>/` папка существует с 3 файлами (passport, dashboard, project-instructions)
- [ ] `<project>/CLAUDE.md` содержит секцию `## mm-system` в конце
- [ ] (Если был) `PROJECT_PASSPORT.md` переименован в `.legacy`
- [ ] (Если есть GSD) В passport секция 9 указывает `gsd_version: v1` (или v2) и текущий milestone/phase
- [ ] claude.ai → Project: Instructions обновлены, Files содержат `passport.md` + `dashboard.md`
- [ ] `/mm check` выводит «0 ошибок»
- [ ] `/mm resume` показывает осмысленную сводку «где мы»

Если хоть один пункт ❌ — открой `/mm check`, он скажет что подкрутить.

---

# §I. Куда дальше

- Полный список команд: `/mm` (cheat sheet) или [README.md](../README.md#skills-cheat-sheet)
- Архитектура и установка плагинов: [README.md](../README.md)
- Что куда грузить в claude.ai (детально): [README.md секция «mm vs Memory vs GSD»](../README.md#mm-vs-anthropic-memory-vs-gsd-vs-context-mode--что-какое-решает)
- Telegram-бот для push с телефона (опционально): [docs/TG-BRIDGE.md](TG-BRIDGE.md)
- Алгоритм поиска config: [docs/CONFIG-LOADING.md](CONFIG-LOADING.md)
- Если что-то не работает: `/mm check` → читает все диагностики и говорит что чинить
