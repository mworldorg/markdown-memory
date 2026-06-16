# Secret Patterns — пояснитель к канону scrub

> ⚠️ **Канонический источник паттернов — `config/secret-patterns.json`.**
> Этот markdown — **человеческий пояснитель**, а не источник истины. Regex здесь не дублируются.
> Чтобы **добавить / изменить / удалить** паттерн — правь `config/secret-patterns.json`, НЕ этот файл.
> Обзор паттернов ниже — иллюстративный (id + класс + описание); точные regex живут только в json.

`config/secret-patterns.json` читают оба пути скана:
- **MCP-инструмент `mm_secret_scan`** (stdio, `mcp/`) — приоритетный путь, когда доступен в сессии.
- **Fallback** в скиллах — прямое применение паттернов из того же json, когда инструмент недоступен.

Оба пути используют один и тот же json → результат идентичен.

## Зачем нужен секрет-скан

mm-скиллы пишут пользовательский контент туда, откуда он может утечь: в claude.ai Project Knowledge или в долговременный vault (в т.ч. в публичный/приватный GitHub-репозиторий). Токен, случайно попавший из кода или git-вывода в заметку/промпт, утечёт наружу. Поэтому собранный текст прогоняется через секрет-скан **до** записи/отдачи.

Используется в:
- `mm-init-project` — проверка `passport.md` перед тем как он попадёт в claude.ai.
- `mm-handoff` — scrub `handoff.md` перед записью (он тоже едет в Project Knowledge).
- `mm-save-session` — scrub заметки сессии перед записью/пушем в vault.
- `mm-bridge` — scrub промпта перед отдачей в claude.ai (внешний сервис, copy-paste).

Базовый набор вдохновлён context-mode; точные форматы ключей провайдеров сверены с **ruleset gitleaks** (`github.com/gitleaks/gitleaks`, лицензия **MIT**). Раскладка имён полей — case-insensitive. Сверено с сетью 2026-06.

## Класс A и Класс B — что значат

- **Класс A — ВЫСОКОТОЧНЫЕ.** Низкий риск ложного срабатывания → это считается реальным секретом. Маркер `class: "A"` в json.
- **Класс B — ШИРОКИЕ / WARN-ONLY.** Высокий риск ложного срабатывания (задевает git SHA-40, UUID, base64-блобы, которых полно в session-логах) → только предупреждение, решение за человеком. Маркер `class: "B"`.

**Политика реакции зависит от скилла** (куда уходит контент) — см. таблицу «Политики применения» ниже. Политику Класса A для `mm-save-session` («средний путь»: hard-stop → показать → маскировка только по явному подтверждению пользователя → ре-скан → push) **не дублируем здесь** — она описана в `skills/mm-save-session/SKILL.md`, Шаг 5.7.

## Правило: маскировать, НЕ удалять

Когда политика скилла предписывает маскировку — найденный секрет **заменяется типизированным плейсхолдером с сохранением контекста**, чтобы заметка осталась осмысленной. Строка целиком не вырезается.

- `TELEGRAM_TOKEN=123456:ABC...` → `TELEGRAM_TOKEN=<REDACTED:telegram-token>`
- `Authorization: Bearer eyJ...` → `Authorization: Bearer <REDACTED:jwt>`
- `api_key: sk-abc...` → `api_key: <REDACTED:openai-key>`
- `postgres://u:p@host/db` → `postgres://<REDACTED:conn-string>@host/db`

Тип в плейсхолдере (`<REDACTED:<id>>`) берётся из `id` совпавшего паттерна.

## Схема `config/secret-patterns.json`

```jsonc
{
  "version": <число>,
  "patterns": [
    {
      "id":          "telegram-token",   // машинный идентификатор; используется в <REDACTED:<id>>
      "description": "…",                 // человеческое однострочное описание
      "class":       "A" | "B",           // A — высокоточный; B — широкий/warn-only
      "regex":       "…",                 // ЕДИНСТВЕННЫЙ источник истины для совпадений
      "flags":       "g" | "gi" | …,      // флаги RegExp
      "source":      "gitleaks … | provider docs | context-mode | RFC …"
    }
  ]
}
```

Чтобы добавить паттерн — допиши объект в `patterns[]` json. Этот markdown править не нужно (обзор ниже можно при желании дополнить, но он не авторитетный).

## Обзор паттернов (иллюстративный — НЕ источник истины)

> Точные regex — только в `config/secret-patterns.json`. Таблица ниже служит навигацией для человека.

### Класс A — высокоточные

| id | Что ловит | Источник |
|---|---|---|
| `telegram-token` | Telegram bot token (`bot_id:hash`, хэш 35 симв.) | gitleaks `telegram-bot-api-token` |
| `openai-key` | OpenAI API keys (маркер `T3BlbkFJ`, вкл. project/service-account) | gitleaks `openai-api-key` |
| `anthropic-key` | Anthropic API keys | gitleaks `anthropic-api-key` |
| `github-token` | GitHub tokens (`ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`) | gitleaks `github-pat`/`-oauth`/`-app-token`/`-refresh-token` |
| `aws-key` | AWS access key ID (вкл. ASIA temp creds) | gitleaks `aws-access-token` |
| `aws-secret` | AWS secret access key (40 base64 рядом с `aws_secret`) | provider docs |
| `slack-token` | Slack tokens (bot / user / legacy) | gitleaks `slack-bot-token`/`-user-token`/`-legacy-token` |
| `google-key` | Google / GCP API keys | gitleaks `gcp-api-key` |
| `google-oauth` | Google OAuth tokens | provider docs |
| `jwt` | JWT tokens (`header.payload.signature`) | RFC 7519 |
| `private-key` | PEM приватный ключ (весь блок BEGIN…END) | gitleaks `private-key` |
| `generic-secret` | Именованные ключи + generic high-entropy assignment (`api_key/token/secret = "…"`), keyword-anchored | gitleaks `generic-api-key` |
| `url-creds` | URL с inline credentials (`user:pass@host`) | context-mode |
| `conn-string` | Connection strings с паролем (Mongo / Postgres / Redis) | context-mode |

`generic-secret` — keyword-anchored: совпадает только когда рядом есть имя поля-секрета (`api_key=…`, `password: …`). Низкий FP → Класс A. Бесконтекстная «просто длинная строка» — это Класс B ниже.

### Класс B — широкие / warn-only

| id | Что ловит | Почему warn-only |
|---|---|---|
| `long-token` | Длинные токены/хеши ≥32 символов (буквы + цифры): git SHA, UUID, base64 | Задевает git SHA-40, UUID, base64-блобы — их полно в session-логах mm; молчаливая маскировка испортит заметку |

Формат предупреждения Класса B (одна строка на находку):
```
⚠️ возможный секрет/длинная строка в <файл/секция>, строка N: <первые 12 симв.>… — проверь вручную (не замаскировано).
```

В большинстве скиллов Класс B **не блокирует** запись — это подсказка, не стоп (исключение — `mm-bridge`, см. ниже).

## Политики применения по скиллам

Паттерны едины (`config/secret-patterns.json`), но **политика** зависит от того, куда уходит контент. Каждый скилл берёт свою строку отсюда — не дублируй ни паттерны, ни политику в теле скилла.

| Скилл | Куда пишет | Класс A | Класс B | Hard-stop? |
|---|---|---|---|---|
| `mm-handoff` | `handoff.md` → claude.ai Knowledge | mask молча | warn-only | нет |
| `mm-init-project` | `passport.md` → claude.ai | mask молча | warn-only | нет |
| `mm-save-session` | заметка сессии → vault | «средний путь» — см. Шаг 5.7 (hard-stop + маскировка по подтверждению) | warn-only | **ДА — стоп до подтверждения/ручной правки** |
| `mm-bridge` | `next-prompt.md` → claude.ai (copy-paste, внешний сервис) | **mask** | **mask** | **ДА — стоп до явного подтверждения** |

`mm-bridge` строже всех: его вывод пользователь руками вставляет в claude.ai, поэтому маскируется И Класс A, И Класс B, и при любой находке — жёсткий стоп: вывод не отдаётся, пока пользователь явно не подтвердит.
