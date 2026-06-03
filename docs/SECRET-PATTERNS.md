# Secret Patterns — единый источник для scrub перед записью

> Единый список regex-паттернов потенциальных секретов. **Source of truth** для всех mm-скиллов, которые пишут пользовательский контент туда, откуда он может утечь (в claude.ai Project Knowledge или в долговременный vault).
>
> Используется:
> - `mm-init-project` — проверка `passport.md` перед тем как он попадёт в claude.ai.
> - `mm-handoff` — scrub `handoff.md` перед записью (он тоже едет в Project Knowledge).
> - `mm-save-session` — scrub заметки сессии перед записью в vault.
> - `mm-bridge` — scrub промпта перед отдачей в claude.ai (внешний сервис, copy-paste).
>
> Базовый набор вдохновлён context-mode; точные форматы ключей провайдеров сверены с **ruleset gitleaks** (`github.com/gitleaks/gitleaks`, `config/gitleaks.toml`, лицензия **MIT**). Раскладка имён полей — case-insensitive. Сверено с сетью 2026-06.

## Правило: маскировать, НЕ удалять

Найденный секрет **заменяй типизированным плейсхолдером с сохранением контекста**, чтобы заметка осталась осмысленной. Не вырезай строку целиком.

- `TELEGRAM_TOKEN=123456:ABC...` → `TELEGRAM_TOKEN=<REDACTED:telegram-token>`
- `Authorization: Bearer eyJ...` → `Authorization: Bearer <REDACTED:jwt>`
- `api_key: sk-abc...` → `api_key: <REDACTED:openai-key>`
- `postgres://u:p@host/db` → `postgres://<REDACTED:conn-creds>@host/db`

Тип в плейсхолдере (`telegram-token`, `jwt`, `aws-key`, `conn-creds`, …) — по классу совпавшего паттерна.

## Класс A — ВЫСОКОТОЧНЫЕ (маскировать молча)

Низкий риск ложного срабатывания → маскируй автоматически, без вопроса. Уведоми пользователя одной строкой по факту (что и сколько замаскировано).

Колонка **Источник**: `gitleaks` — regex взят/сверен с gitleaks ruleset (MIT); `context-mode` / `provider docs` — базовый набор.

| Pattern | Что ловит | Тип плейсхолдера | Источник |
|---|---|---|---|
| `[0-9]{5,16}:[A-Za-z0-9_-]{35}` | Telegram bot token (`bot_id:hash`, хэш 35 симв.) | `telegram-token` | gitleaks `telegram-bot-api-token` |
| `sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}` и `sk-(proj\|svcacct\|admin)-[A-Za-z0-9_-]{58,74}T3BlbkFJ[A-Za-z0-9_-]{58,74}` | OpenAI API keys (маркер `T3BlbkFJ`, вкл. project/service) | `openai-key` | gitleaks `openai-api-key` |
| `sk-ant-api03-[A-Za-z0-9_-]{93}AA` | Anthropic API keys | `anthropic-key` | gitleaks `anthropic-api-key` |
| `gh[posru]_[0-9A-Za-z]{36}` | GitHub tokens (pat `ghp_`, oauth `gho_`, app `ghu_`/`ghs_`, refresh `ghr_`) | `github-token` | gitleaks `github-pat`/`-oauth`/`-app-token`/`-refresh-token` |
| `(A3T[A-Z0-9]\|AKIA\|ASIA\|ABIA\|ACCA)[A-Z2-7]{16}` | AWS access key ID (вкл. ASIA temp creds) | `aws-key` | gitleaks `aws-access-token` |
| `[A-Za-z0-9/+]{40}` рядом с `aws_secret` | AWS secret access key | `aws-secret` | provider docs |
| `xoxb-[0-9]{10,13}-[0-9]{10,13}[A-Za-z0-9-]*` · `xox[pe](-[0-9]{10,13}){3}-[A-Za-z0-9-]{28,34}` · `xox[os]-\d+-\d+-\d+-[a-fA-F\d]+` | Slack tokens (bot / user / legacy) | `slack-token` | gitleaks `slack-bot-token`/`-user-token`/`-legacy-token` |
| `AIza[\w-]{35}` | Google / GCP API keys | `google-key` | gitleaks `gcp-api-key` |
| `ya29\.[A-Za-z0-9_-]+` | Google OAuth tokens | `google-oauth` | provider docs |
| `eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}` | JWT tokens | `jwt` | RFC 7519 |
| `-----BEGIN[ A-Z0-9_-]{0,100}PRIVATE KEY( BLOCK)?-----[\s\S]{64,}?-----END[ A-Z0-9_-]{0,100}PRIVATE KEY( BLOCK)?-----` | PEM приватный ключ (весь блок) | `private-key` | gitleaks `private-key` |
| `(?i)(authorization\|api[_-]?key\|secret\|password\|passwd\|token\|bearer\|credential\|creds\|private[_-]?key\|signature\|cookie)[\s:=>"']{1,5}[\w.=/+-]{10,150}` | Именованные ключи + generic high-entropy assignment (`api_key/token/secret = "…"`) | `secret` | gitleaks `generic-api-key` |
| `https?://[^\s]*:[^@\s/]+@` | URL'ы с inline credentials | `conn-creds` | context-mode |
| `(mongodb(\+srv)?\|postgres(ql)?\|redis)://[^\s/]+:[^@\s/]+@` | Connection strings с паролем (Mongo / Postgres / Redis) | `conn-creds` | context-mode |

> Generic-assignment паттерн (последняя строка) — keyword-anchored: маскирует значение только когда рядом есть имя поля-секрета (`api_key=…`, `password: …`). Низкий FP → Класс A. Бесконтекстная «просто длинная строка» — это Класс B ниже.

## Класс B — ШИРОКИЕ / WARN-ONLY (НЕ маскировать молча)

Высокий риск ложного срабатывания → **только предупредить** пользователя, ничего не маскировать автоматически. Решение оставить за человеком.

| Pattern | Что ловит | Почему warn-only |
|---|---|---|
| `[A-Za-z0-9_\-]{32,}` (есть и буквы, и цифры) | Длинные токены/хеши ≥32 символов | Задевает **git SHA-40, UUID, base64-блобы** — их полно в session-логах mm; молчаливая маскировка испортит заметку |

Формат предупреждения (одна строка на находку):
```
⚠️ возможный секрет/длинная строка в <файл/секция>, строка N: <первые 12 симв.>… — проверь вручную (не замаскировано).
```

В большинстве скиллов Класс B **не блокирует** запись — это подсказка, не стоп (исключение — `mm-bridge`, см. ниже).

## Политики применения по скиллам

Паттерны едины (этот файл), но **политика** зависит от того, куда уходит контент. Каждый скилл берёт свою строку отсюда — не дублируй ни паттерны, ни политику в теле скилла.

| Скилл | Куда пишет | Класс A | Класс B | Hard-stop? |
|---|---|---|---|---|
| `mm-handoff` | `handoff.md` → claude.ai Knowledge | mask молча | warn-only | нет |
| `mm-init-project` | `passport.md` → claude.ai | mask молча | warn-only | нет |
| `mm-save-session` | заметка сессии → vault | mask молча | warn-only | нет |
| `mm-bridge` | `next-prompt.md` → claude.ai (copy-paste, внешний сервис) | **mask** | **mask** | **ДА — стоп до явного подтверждения** |

`mm-bridge` строже всех: его вывод пользователь руками вставляет в claude.ai, поэтому маскируется И Класс A, И Класс B, и при любой находке — жёсткий стоп: вывод не отдаётся, пока пользователь явно не подтвердит.
