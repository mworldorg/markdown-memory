#!/usr/bin/env python3
"""clear-gate — read-only проверка «всё ли записано» перед /clear.

Вердикт даёт exit code, а не текст: 0 — можно чистить, 1 — нельзя.
Только чтение: git status/rev-list/log, mtime файлов, validate.health без --repair.
Ничего не коммитит, не пушит, git fetch не выполняет.

Режимы:
  mid (дефолт) — между этапами GSD. Жёстко: устаревший handoff, расхождение vault.
  end          — конец сессии. Дополнительно: незакоммиченное, непушенное, лог сессии.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

BLOCKER, WARN, OK, NA = "blocker", "warn", "ok", "na"


class Finding:
    def __init__(self, level, title, details=None, fix=None):
        self.level = level
        self.title = title
        self.details = details or []
        self.fix = fix


def run(args, cwd=None):
    """Запустить команду, вернуть (rc, stdout). Никогда не бросает."""
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout.strip()
    except (OSError, ValueError):
        return 1, ""


def deep_merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(repo_root):
    cfg = {}
    for name in ("mm-config.json", "mm-config.local.json"):
        path = os.path.join(repo_root, "config", name)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    deep_merge(cfg, json.load(f))
            except (OSError, ValueError):
                pass
    return cfg


def project_name(proj):
    passport = os.path.join(proj, "passport.md")
    if os.path.isfile(passport):
        try:
            with open(passport, encoding="utf-8") as f:
                head = f.read(2000)
            m = re.search(r"^project:\s*(.+?)\s*$", head, re.M)
            if m:
                return m.group(1).strip()
        except OSError:
            pass
    return os.path.basename(proj)


def mtime_of(path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).astimezone()
    except OSError:
        return None


def newest(paths):
    """(datetime, path) самого свежего существующего файла, иначе (None, None)."""
    best, best_path = None, None
    for p in paths:
        t = mtime_of(p)
        if t and (best is None or t > best):
            best, best_path = t, p
    return best, best_path


def git_iso(out):
    try:
        return datetime.fromisoformat(out.strip())
    except ValueError:
        return None


def fmt(dt):
    return dt.strftime("%d.%m %H:%M") if dt else "—"


def delta(a, b):
    """Человекочитаемая разница a-b."""
    secs = int((a - b).total_seconds())
    h, m = divmod(max(secs, 0) // 60, 60)
    return f"{h}ч{m:02d}м" if h else f"{m}м"


# ─────────────────────────── проверки ───────────────────────────

def check_tree(proj):
    rc, out = run(["git", "-C", proj, "status", "--porcelain", "--untracked-files=all"])
    if rc != 0:
        return Finding(WARN, "Дерево проекта: git недоступен")
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return Finding(OK, "Дерево проекта чисто")
    untracked = sum(1 for l in lines if l.startswith("??"))
    f = Finding(WARN, f"Незакоммичено: {len(lines)} файл(ов), из них untracked {untracked}",
                details=lines, fix="git add -A && git commit")
    return f


def check_push(proj):
    rc_rem, remotes = run(["git", "-C", proj, "remote"])
    if rc_rem != 0 or not remotes:
        return Finding(WARN, "Remote не настроен — пуш неприменим")
    rc_up, upstream = run(["git", "-C", proj, "rev-parse", "--abbrev-ref",
                           "--symbolic-full-name", "@{u}"])
    if rc_up != 0 or not upstream:
        return Finding(BLOCKER, "У ветки нет upstream — запушенность не установить",
                       fix="git push -u origin <branch>")
    rc, out = run(["git", "-C", proj, "rev-list", "--left-right", "--count", "HEAD...@{u}"])
    if rc != 0:
        return Finding(WARN, "Не удалось сравнить с origin")
    try:
        ahead, behind = (int(x) for x in out.split())
    except ValueError:
        return Finding(WARN, "Не удалось разобрать вывод rev-list")
    if ahead:
        return Finding(WARN, f"Не запушено: HEAD впереди {upstream} на {ahead} коммит(ов)",
                       details=[f"отстаёт на {behind}"] if behind else [],
                       fix="git push origin " + upstream.split("/")[-1])
    if behind:
        return Finding(WARN, f"Отстаёт от {upstream} на {behind} коммит(ов)", fix="git pull")
    return Finding(OK, f"Запушено: HEAD == {upstream}")


def check_vault(vault):
    if not vault or not os.path.isdir(vault):
        return Finding(WARN, "Vault-папка не найдена", details=[vault or "путь не определён"],
                       fix="/mm vault")
    if not os.path.exists(os.path.join(vault, ".git")):
        return Finding(WARN, "Vault не git-репозиторий — записанное никуда не едет",
                       fix="/mm vault")
    _, dirty = run(["git", "-C", vault, "status", "--porcelain", "--untracked-files=all"])
    lines = [l for l in dirty.splitlines() if l.strip()]
    rc, out = run(["git", "-C", vault, "rev-list", "--left-right", "--count", "HEAD...@{u}"])
    ahead = behind = 0
    if rc == 0:
        try:
            ahead, behind = (int(x) for x in out.split())
        except ValueError:
            pass
    problems = []
    if lines:
        problems.append(f"незакоммичено {len(lines)} файл(ов)")
    if ahead:
        problems.append(f"не запушено {ahead} коммит(ов)")
    if problems:
        return Finding(BLOCKER, "Vault расходится: " + ", ".join(problems),
                       details=lines[:10], fix="/mm save (закоммитит и запушит vault)")
    if behind:
        return Finding(WARN, f"Vault отстаёт от origin на {behind}", fix="git -C <vault> pull")
    return Finding(OK, "Vault: чисто, синхронно")


HANDOFF_EXCLUDES = [
    ":(exclude).planning/HANDOFF.json",
    ":(exclude).planning/phases/*/.continue-here.md",
    ":(exclude).planning/continue-here.md",
]


def check_handoff(proj):
    planning = os.path.join(proj, ".planning")
    if not os.path.isdir(planning):
        return Finding(NA, "Handoff: проект не под GSD")
    rc, out = run(["git", "-C", proj, "log", "-1", "--format=%cI", "--", "."] + HANDOFF_EXCLUDES)
    t_work = git_iso(out) if rc == 0 else None
    if not t_work:
        return Finding(NA, "Handoff: рабочих коммитов нет")
    candidates = [os.path.join(planning, "HANDOFF.json"),
                  os.path.join(planning, "continue-here.md")]
    candidates += glob.glob(os.path.join(planning, "phases", "*", ".continue-here.md"))
    t_ho, path = newest(candidates)
    if not t_ho:
        return Finding(BLOCKER, "Handoff не создавался — состояние работы нигде не записано",
                       fix="/gsd-pause-work")
    if t_ho < t_work:
        return Finding(BLOCKER,
                       f"Handoff устарел: {fmt(t_ho)}, работа до {fmt(t_work)} "
                       f"(+{delta(t_work, t_ho)})",
                       details=[os.path.relpath(path, proj).replace("\\", "/")],
                       fix="/gsd-pause-work")
    return Finding(OK, f"Handoff свежий: {fmt(t_ho)} ≥ работа {fmt(t_work)}")


def check_session_log(proj, vault):
    rc, out = run(["git", "-C", proj, "log", "-1", "--format=%cI"])
    t_commit = git_iso(out) if rc == 0 else None
    if not t_commit:
        return Finding(NA, "Лог сессии: коммитов нет")
    sessions = os.path.join(vault, "sessions") if vault else None
    files = glob.glob(os.path.join(sessions, "*.md")) if sessions else []
    t_log, path = newest(files)
    if not t_log:
        return Finding(BLOCKER, "Лог сессии не найден", fix="/mm save")
    if t_log < t_commit:
        return Finding(BLOCKER,
                       f"Лог сессии не записан: последний {fmt(t_log)}, "
                       f"работа до {fmt(t_commit)} (+{delta(t_commit, t_log)})",
                       details=[os.path.basename(path)], fix="/mm save")
    return Finding(OK, f"Лог сессии свежий: {fmt(t_log)}")


def check_health(proj):
    if not os.path.isdir(os.path.join(proj, ".planning")):
        return Finding(NA, "Health: проект не под GSD")
    tools = os.path.join(os.path.expanduser("~"), ".claude", "gsd-core", "bin", "gsd-tools.cjs")
    if os.path.isfile(tools):
        cmd = ["node", tools, "query", "validate.health"]
    elif shutil.which("gsd-tools"):
        cmd = ["gsd-tools", "query", "validate.health"]
    else:
        return Finding(WARN, "Health: gsd-tools не найден")
    rc, out = run(cmd, cwd=proj)
    try:
        data = json.loads(out[out.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return Finding(WARN, "Health: вывод validate.health не разобран")
    status = data.get("status", "?")
    if status == "healthy":
        return Finding(OK, "Health: .planning healthy")
    ne, nw = len(data.get("errors", [])), len(data.get("warnings", []))
    return Finding(WARN, f"Health: .planning {status} ({ne} errors, {nw} warnings)",
                   fix="/gsd-health · глубокий аудит: /gsd-progress --forensic")


# ─────────────────────────── вывод ───────────────────────────

def render(name, mode, findings):
    mode_label = ("MID (между этапами GSD)" if mode == "mid"
                  else "END (конец сессии)")
    out = [f"🚦 /mm gate · {name} · режим {mode_label}", ""]

    blockers = [f for f in findings if f.level == BLOCKER]
    warns = [f for f in findings if f.level == WARN]
    passed = [f for f in findings if f.level in (OK, NA)]

    if blockers:
        out.append(f"⛔ БЛОКЕРЫ ({len(blockers)}) — чистить нельзя")
        for i, f in enumerate(blockers, 1):
            out.append(f" {i}. {f.title}")
            out.extend(f"    {d}" for d in f.details)
            if f.fix:
                out.append(f"    → {f.fix}")
        out.append("")

    if warns:
        out.append(f"⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(warns)}) — на вердикт НЕ влияют")
        for f in warns:
            out.append(f" • {f.title}")
            out.extend(f"    {d}" for d in f.details)
            if f.fix:
                out.append(f"    → {f.fix}")
        out.append("")

    if passed:
        out.append("✅ ПРОЙДЕНО")
        for f in passed:
            out.append(f" • {f.title}")
        out.append("")

    verdict = "НЕ ГОТОВО · exit 1" if blockers else "ГОТОВО К /clear · exit 0"
    out.append(f"── ВЕРДИКТ: {verdict} ──")
    out.append("fetch не выполнялся (read-only): behind-состояние может быть устаревшим")
    return "\n".join(out)


def main():
    # Windows-консоль по умолчанию cp1252 — эмодзи в выводе её роняют.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--mode", choices=["mid", "end"], default="mid")
    ap.add_argument("--project", default=os.getcwd())
    args = ap.parse_args()

    rc, root = run(["git", "-C", args.project, "rev-parse", "--show-toplevel"])
    proj = os.path.normpath(root) if rc == 0 and root else os.path.abspath(args.project)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = load_config(repo_root)
    name = project_name(proj)
    projects_root = cfg.get("paths", {}).get("obsidian_projects")
    vault = os.path.join(projects_root, name) if projects_root else None

    handoff = check_handoff(proj)
    tree = check_tree(proj)
    push = check_push(proj)

    # Поправка А/Б: в mid дерево и ahead — предупреждения; дерево становится
    # блокером только вместе с красным handoff (незаписанное + грязное = потеря).
    if args.mode == "end":
        if tree.level == WARN and tree.fix:
            tree.level = BLOCKER
        if push.level == WARN and push.fix and "push origin" in (push.fix or ""):
            push.level = BLOCKER
    elif handoff.level == BLOCKER and tree.level == WARN and tree.fix:
        tree.level = BLOCKER
        tree.title += " — при устаревшем handoff это потеря"

    findings = [handoff, check_vault(vault), tree, push]
    if args.mode == "end":
        findings.append(check_session_log(proj, vault))
    findings.append(check_health(proj))

    print(render(name, args.mode, findings))
    return 1 if any(f.level == BLOCKER for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
