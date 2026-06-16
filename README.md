<div align="center">

# mm — markdown memory & workflow system

**A file-based memory and prompt bridge that connects claude.ai (where you think) ↔ Claude Code (where you build) ↔ Obsidian (shared long-term memory).**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Version](https://img.shields.io/badge/version-0.6.0-green.svg)
![Type: Agent Skills](https://img.shields.io/badge/type-Claude%20Agent%20Skills-8A2BE2.svg)
![Platform: Windows](https://img.shields.io/badge/platform-Windows%20(primary)-lightgrey.svg)

<!-- TODO: record a short terminal demo (asciinema / GIF) and drop it here -->
<!-- <img src="docs/assets/demo.gif" width="640" alt="mm in action" /> -->

</div>

---

## What is this?

When you build with Claude, your work is split across two places: you sketch ideas and plan in **claude.ai**, then do the real work in **Claude Code** in your terminal. Those two sides don't share memory, and context evaporates between sessions, between chats, and whenever the context window compacts.

**mm** closes that gap. It's a set of [Claude Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) plus a small PowerShell installer that gives you:

- **One shared memory** for every project, stored as plain markdown in an Obsidian vault (passport, handoff, session history).
- **A prompt bridge** so an idea worked out in claude.ai becomes a clean, self-contained task you paste into Claude Code.
- **A simple lifecycle** — start a project, resume it, save a session, hand off to a new chat — with no copy-pasting your whole history every time.

Everything is markdown and files. No database, no cloud, no lock-in.

---

## How it works

mm spans three environments that share state through files, not magic:

```mermaid
flowchart LR
    A["claude.ai<br/>(ideas, planning)<br/>mm-web-bridge skill"]
    B["Claude Code / PowerShell<br/>(real work)<br/>12 skills"]
    C["Obsidian vault<br/>(shared memory)<br/>passport · handoff · sessions"]

    A -- "self-contained prompt<br/>(copy-paste)" --> B
    B -- "writes notes" --> C
    C -- "passport + handoff<br/>loaded into Project Knowledge" --> A
    C -- "read on resume" --> B
```

- **claude.ai side** is a single skill (`mm-web-bridge`): it challenges your idea, checks fast-moving tech against the live web, and composes the prompt you'll run in Claude Code.
- **Claude Code side** is the `mm` dispatcher + 11 `mm-*` skills that do the work and keep the vault up to date.
- **Obsidian** is just the folder where the markdown lives. Obsidian indexes it for you; mm reads and writes the files directly.

---

## Quick start

### Prerequisites

- [Claude Code](https://docs.claude.com/en/docs/claude-code) CLI
- Python 3 (installed on macOS/Windows by default)
- Node.js (v16+ for `npx` installer)
- An Obsidian vault (any folder works; Obsidian itself is optional but recommended)

### [NPM / npx Installation (Recommended)](#npm-npx-installation)

The easiest way to install and configure the entire system across **Windows, macOS, and Linux** is using `npx`:

```bash
npx markdown-memory
```

This single command will:
1. Clone the repository into `~/.markdown-memory/` (or update it if already cloned).
2. Set the `MM_REPO_ROOT` environment variable in your shell profile (`.zshrc` / `.bashrc` on Mac/Linux) or Windows Registry.
3. Automatically register all skills (creating NTFS junctions on Windows or symlinks on macOS/Linux) under `~/.claude/skills/`.

*To update the skills and codebase at any time, simply run `npx markdown-memory` (or `/mm update` inside the agent session) again!*

---

### Manual Installation (Alternative)

```bash
# 1. Clone the repository
git clone https://github.com/mworldorg/markdown-memory.git
cd markdown-memory

# 2. Register skills:
# On Windows (PowerShell):
powershell scripts/register-skills.ps1
# On macOS / Linux (or Windows with Python):
python3 scripts/register-skills.py
```

---

### Post-Installation Setup

1. **Personalization**: Restart Claude Code (skills load at session start), then run the setup command:
   ```bash
   /mm setup
   ```
2. **Create Passport**: Navigate to your project folder and initialize it:
   ```bash
   /mm new
   ```

### Connect the claude.ai side

1. Create a Project in claude.ai for your work.
2. Add your project's `passport.md` and `handoff.md` to **Project Knowledge**.
3. Load the `mm-web-bridge` skill into that Project (claude.ai → Customize → Skills → Upload a skill). After `/mm setup`, upload your personalized copy from `claude-ai-skills/_generated/mm-web-bridge/` — the committed `claude-ai-skills/mm-web-bridge/` is a template with placeholder persona.
4. First message in a new chat:
   > *"Read handoff.md and passport.md, tell me where we are and suggest the next step."*

### The loop

```text
/mm resume   →   discuss in claude.ai   →   paste prompt into Claude Code   →   /mm save   →   /mm next
```

**On GSD projects**, when you finish a phase stage and want a clean context, run `/clear` then [`/mm-focus`](skills/mm-focus/SKILL.md) instead of a bare `/clear` — `mm-focus` reloads the current stage's files (STATE + CONTEXT/PLAN/SUMMARY) into the fresh context so you continue without losing your place.

---

## Skills

Twelve skills on the Claude Code side, plus one on the claude.ai side — and vendored external skills (see [Integrations](#integrations)).

| Skill | What it does |
|---|---|
| `mm` | Dispatcher — short aliases for everything below |
| `mm setup` | One-time personalization after cloning |
| `mm-init-project` | Create a project passport + structure in the vault |
| `mm-resume` | Load passport + dashboard + last session on start |
| `mm-projects` | One-screen overview of all projects (read-only) |
| `mm-bridge` | Wrap a task into a prompt framework for Claude Code |
| `mm-handoff` | Generate the cross-chat handoff summary |
| `mm-save-session` | Capture decisions and progress into the vault |
| `mm-instructions` | Manage project instructions |
| `mm-doctor` | Health checks, version sync, consistency with passport |
| `mm-update` | Self-update mm from the git remote (fetch, changelog, confirm, ff-only pull, re-register) |
| `mm-vault` | Bootstrap a private git repo for the project's memory vault, synced to claude.ai Knowledge (memory-sync) |
| `mm-web-bridge` *(claude.ai)* | Idea partner + prompt composer in the browser |
| `ecc-security-review` *(vendored — [ECC](https://github.com/affaan-m/everything-claude-code), MIT)* | Security checklist: secrets, input validation, SQLi, auth, XSS/CSRF, rate limiting |
| `ecc-search-first` *(vendored — [ECC](https://github.com/affaan-m/everything-claude-code), MIT)* | Research before coding: search existing tools/libs/MCP/skills, then adopt / extend / build |

---

## MCP-инструменты

mm ships a small local **stdio** MCP server (`mm-mcp`, TypeScript) that exposes two deterministic, read-only tools to local agents (Claude Code / Desktop / Antigravity):

- `mm_secret_scan` — scan text for secrets against the canonical `config/secret-patterns.json`; returns classes and counts only, never the raw secret value.
- `mm_health` — read-only health checks of the mm install (config, junctions, vault-git, passport/gsd); returns `checks[]` + `summary`.

Build, registration (`claude mcp add … mm-mcp …`), scope, and tests — see [`mcp/README.md`](mcp/README.md).

---

## Integrations

mm cooperates with several external tools and bodies of work. Where it builds on someone else's project, that project keeps its own license and attribution.

- **GSD** — phase-based planning framework. mm **reads** GSD state (`.planning/` / `.gsd/`) and cooperates with it; it never writes there. *(deepest integration)*
- **Karpathy guidelines** — four meta-principles (think before coding, simplicity first, surgical changes, goal-driven) applied across both the Claude Code and claude.ai sides. MIT. *(external Claude Code plugin — install separately, see Optional plugins below)*
- **[context-mode](https://github.com/mksglu/context-mode)** — in-session context optimization and continuity. See [Memory layers](#two-memory-layers) for how it relates to mm. Elastic License 2.0 (source-available). *(external Claude Code plugin — install separately, see Optional plugins below)*
- **prompt-frameworks** — CRISPE / XML / PERSONA / HYPOTHESIS templates used by `mm-bridge`. Inspired by [awesome-claude-prompts](https://github.com/langgptai/awesome-claude-prompts), MIT.
- **[claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)** — optional Telegram bridge, off by default. MIT.
- **Telegram Integration (UI/UX & Sessions)** — auto-detects Telegram bot and Telethon projects, copies safe session guidelines and UI/UX standards, injects constraints into passports, and automatically validates python codebase for ban-prone and UX bugs via `/mm check` (`mm-doctor`) (can be disabled via `telegram_ui_ux: false` in passport). See [docs/TELEGRAM-INTEGRATION.md](file:///C:/Users/louise/Desktop/louise-skills/docs/TELEGRAM-INTEGRATION.md). *(built-in)*
- **[ECC — everything-claude-code](https://github.com/affaan-m/everything-claude-code)** — two skills vendored per-piece into `vendor/`: `ecc-security-review` (markdown security checklist; renamed to avoid clashing with the built-in `/security-review`) and `ecc-search-first` (research-before-coding workflow). The rest of ECC (AgentShield, plugin, hooks, ~246 skills) is **not** included. MIT © Affaan Mustafa. *(per-skill vendoring mechanism — see [`vendor/README.md`](vendor/README.md))*

### Two memory layers

mm and context-mode solve **different** problems and don't overlap:

- **context-mode** keeps a *single session* alive — it survives auto-compaction and `--resume` by rebuilding your working state inside Claude Code.
- **mm** keeps *long-term project history* — decisions, handoffs, and session notes that persist across sessions and across chats, in the Obsidian vault.

If you use both, context-mode already handles compaction; mm doesn't try to.

### Optional plugins

Karpathy guidelines and context-mode are external Claude Code plugins (not bundled in this repo). mm cooperates with them but works without them. To install:

```text
# Karpathy coding guidelines (think-before-coding, simplicity, surgical, goal-driven)
/plugin marketplace add forrestchang/andrej-karpathy-skills
/plugin install andrej-karpathy-skills@karpathy-skills

# context-mode (in-session context optimization + continuity across compaction)
/plugin marketplace add mksglu/context-mode
/plugin install context-mode@context-mode
```

---

## Memory sync (claude.ai Knowledge через git)

Автоматическая синхронизация Obsidian-памяти проекта (паспорт, handoff, сессии) с веб-интерфейсом claude.ai через приватный git-репозиторий на GitHub. Полное руководство по настройке и использованию см. в [`docs/memory-sync.md`](docs/memory-sync.md).

---

## Cross-platform

mm is cross-platform! It is fully supported on Windows, macOS, and Linux:
- **Windows**: Use `powershell scripts/register-skills.ps1` for PowerShell or `python3 scripts/register-skills.py`.
- **macOS / Linux**: Use `python3 scripts/register-skills.py` (which sets up symlinks in `~/.claude/skills` and exports `MM_REPO_ROOT` in your shell profile like `.zshrc` or `.bashrc`).

For the optional Telegram bridge:
- **Windows**: Use `powershell scripts/install-tg-bridge.ps1`.
- **macOS / Linux**: Use `python3 scripts/install-tg-bridge.py`.

---

## Conventions

- **Personal data never lands in committed files.** Your name and paths live in a gitignored `mm-config.local.json` written by `/mm setup`. The committed config stays a generic template.
- **Single source of truth for versions** — `config.version`. Per-skill `version:` fields are intentionally granular.
- **Skills preview before they write**, and never write into GSD's `.planning/` / `.gsd/`.

---

## Documentation

- [`passport.md`](templates/passport.md) — the per-project source of truth (architecture, conventions, constraints)
- [`docs/memory-sync.md`](docs/memory-sync.md) — step-by-step guide to configure automatic memory sync with claude.ai Project Knowledge via Git (Recommended)
- [`docs/MCP-INTEGRATION.md`](docs/MCP-INTEGRATION.md) — step-by-step guide to connect your Obsidian Vault via Model Context Protocol (MCP) (Recommended)
- [`docs/TELEGRAM-INTEGRATION.md`](docs/TELEGRAM-INTEGRATION.md) — guide on automatic integration of session safety rules and UI/UX design standards for Telegram-based projects (Recommended)
- [`docs/`](docs/) — deeper guides (Telegram bridge, config loading, etc.)

---

## Contributing

Issues and PRs welcome. New skills go in `skills/your-skill/SKILL.md` with YAML frontmatter; claude.ai skills go in `claude-ai-skills/` (they are **not** junctioned into Claude Code).

## License

MIT — see [LICENSE](LICENSE). Integrated projects retain their own licenses (see [Integrations](#integrations)).
