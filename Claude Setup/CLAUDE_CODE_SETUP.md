# CLAUDE CODE SETUP — вставь в Claude Code для настройки автоматизации

Настрой полную систему автоматизации для этого проекта: GSD, паспорт, Obsidian-интеграция, Git, управление сессиями.

## Шаг 0: Проверка GSD

Проверь наличие GSD. Проверяй ВСЕ пути — GSD может быть установлен глобально или локально:

Локально:
- .planning/
- .claude/skills/gsd-*
- .claude/commands/gsd/

Глобально (проверь домашнюю директорию пользователя):
- ~/.claude/skills/gsd-*
- ~/.claude/commands/gsd/

На Windows ~ это %USERPROFILE% (например C:\Users\louise\.claude\skills\).

Также попробуй: выполни bash команду "ls ~/.claude/skills/ 2>/dev/null | grep gsd | head -3" чтобы быстро проверить глобальную установку.

Если GSD найден (локально ИЛИ глобально) — скажи "GSD установлен ✅" и переходи к Шагу 1.

Если GSD НЕ найден нигде — скажи:

"GSD не установлен. Рекомендую установить — это система планирования и выполнения задач для Claude Code.

Для установки выполни в терминале (не здесь, а в отдельном терминале):
```
npx get-shit-done-cc@latest
```
Выбери: Claude Code → Global (чтобы работал во всех проектах).

После установки перезапусти сессию Claude Code (exit → claude) и вставь этот промпт заново.

Если не хочешь GSD — напиши 'без GSD' и я продолжу настройку без него."

Если GSD установлен или пользователь сказал "без GSD" — переходи к Шагу 1.

## Шаг 1: Сбор информации

Задай мне эти вопросы (жди ответа на каждый):

1. Полный путь к Obsidian vault (например C:\Users\me\Documents\Obsidian\AI-Projects)
2. Как называть этот проект в Obsidian? (имя папки, например Filtrator)
3. Git remote для push (например origin, или "нет" если не нужно)
4. Git ветка по умолчанию (например main)

GSD определи сам по результату Шага 0.

## Шаг 2: Сохрани конфиг

Добавь в CLAUDE.md секцию (создай CLAUDE.md если нет):

## Automation Config
OBSIDIAN_VAULT=(ответ 1)
OBSIDIAN_PROJECT=(ответ 2)
GIT_REMOTE=(ответ 3)
GIT_BRANCH=(ответ 4)
HAS_GSD=(true/false)

## Шаг 3: Создай структуру в Obsidian

Создай директории (если не существуют):
- {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/
- {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/sessions/
- {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/prompts/
- {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/context-snapshots/

## Шаг 4: Создай PROJECT_PASSPORT.md

Проведи полное ревью проекта и создай PROJECT_PASSPORT.md в корне. Секции:

1. ИДЕНТИФИКАЦИЯ — таблица: название, тип, назначение, стадия, языки, менеджер пакетов, GSD статус
2. СТЕК — таблица: фреймворк, DB/ORM, auth, тесты, линтер, CI/CD с версиями. Ключевые зависимости. Внешние сервисы.
3. АРХИТЕКТУРА — паттерн, tree директорий 2-3 уровня, поток данных, точки входа, абстракции
4. МОДЕЛИ ДАННЫХ — таблица: сущность, хранилище, поля, связи. Где схема.
5. КОНВЕНЦИИ — именование (таблица), паттерны ошибок/валидации/состояния, тесты
6. API (если есть) — тип, роуты, формат ответов
7. ФРОНТЕНД (если есть) — фреймворк, рендеринг, стейт, стилизация
8. КОНФИГУРАЦИЯ — ENV (имена без значений), команды запуска, Docker
9. GSD-КОНТЕКСТ (если есть) — CLAUDE.md, .planning/, milestone, phase
10. ПРОБЛЕМНЫЕ ЗОНЫ — метрики, топ-5 проблем, god-objects, модули без тестов
11. КОНТЕКСТ ДЛЯ ПРОМПТОВ — 5-8 правил что обязательно учитывать

Требования: компактно, таблицы, N/A если не применимо, читай реальные файлы.

## Шаг 5: Скопируй паспорт в Obsidian

Скопируй PROJECT_PASSPORT.md в {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/passport.md

## Шаг 6: Создай кастомные skills

ВАЖНО: после создания skills нужно перезапустить сессию Claude Code (exit → claude) чтобы они загрузились.

Создай 4 файла:

### Файл: .claude/skills/save-session/SKILL.md

Команда /save-session — сохранить текущую сессию в Obsidian.

Прочитай Automation Config из CLAUDE.md для путей.

Действия:
1. Прочитай git log --oneline --since="today" для списка коммитов
2. Если есть .planning/ — прочитай STATE.md и все SUMMARY.md за сегодня
3. Сгенерируй markdown файл сессии с frontmatter (project, date, status, gsd_milestone) и секциями: Что сделано, Ключевые решения, Git
4. Сохрани в {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/sessions/YYYY-MM-DD.md (если существует — суффикс -2, -3)
5. Обнови или создай {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/dashboard.md
6. Выведи: "Сессия сохранена: {путь к файлу}"

### Файл: .claude/skills/update-passport/SKILL.md

Команда /update-passport — обновить паспорт проекта.

Прочитай Automation Config из CLAUDE.md для путей.

Действия:
1. Перегенерируй PROJECT_PASSPORT.md в корне проекта (полное ревью, тот же формат)
2. Скопируй в {OBSIDIAN_VAULT}/Projects/{OBSIDIAN_PROJECT}/passport.md
3. Покажи краткий diff: что изменилось
4. Выведи: "Паспорт обновлён: проект + Obsidian"

### Файл: .claude/skills/push/SKILL.md

Команда /push — закоммитить и запушить изменения.

Прочитай Automation Config из CLAUDE.md для GIT_REMOTE и GIT_BRANCH.

Действия:
1. git status — покажи что изменилось
2. git add -A
3. Сгенерируй commit-сообщение (английский, conventional commits)
4. git commit
5. git push {GIT_REMOTE} {GIT_BRANCH}
6. Если есть теги — git push --tags
7. Выведи результат

Если GIT_REMOTE = "нет" — только коммит, сообщи.

### Файл: .claude/skills/save-all/SKILL.md

Команда /save-all — полное сохранение.

Прочитай Automation Config из CLAUDE.md для всех путей.

Действия по порядку:
1. Выполни то что делает /update-passport
2. Выполни то что делает /save-session
3. Выполни то что делает /push
4. Выведи итог: Паспорт ✅, Сессия ✅, Git ✅

## Шаг 7: Проверка

1. Выведи список созданных skills
2. Проверь что пути в Obsidian существуют
3. Проверь что CLAUDE.md содержит Automation Config
4. Скажи: "Настройка завершена. Перезапусти сессию (exit → claude) чтобы skills загрузились. После перезапуска попробуй /save-all"
5. Если GSD установлен — напомни: "GSD команды: /gsd-help для списка"

## Требования
- Все пути из CLAUDE.md Automation Config — ничего хардкодить
- UTF-8 для всех файлов
- Windows-совместимые пути
- SKILL.md формат для Claude Code 2.1.88+
- Каждый skill самодостаточный
