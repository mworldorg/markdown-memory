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

BLOCKER, UNKNOWN, WARN, OK, NA = "blocker", "unknown", "warn", "ok", "na"

# Отставание handoff меньше этого порога — шум: /gsd-pause-work пишет handoff, а
# коммит идёт следом через секунды. Блокер на таком отставании приучает
# пролистывать вердикт, и гейт перестаёт работать там, где нужен.
HANDOFF_STALE_TOLERANCE_MIN = 5


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


def passport_field(passport, key):
    """Значение поля из frontmatter passport.md, иначе None."""
    if not os.path.isfile(passport):
        return None
    try:
        with open(passport, encoding="utf-8") as f:
            head = f.read(4000)
    except OSError:
        return None
    m = re.search(r"^%s:\s*(.+?)\s*$" % re.escape(key), head, re.M)
    return m.group(1).strip() if m else None


def project_name(proj):
    return passport_field(os.path.join(proj, "passport.md"), "project") or os.path.basename(proj)


def resolve_vault(proj, projects_root):
    """Найти vault проекта. Возвращает (path, how, note).

    path=None означает, что vault не определён — по how видно, это положительно
    установленное отсутствие ('none') или невозможность определить (остальное).
    """
    if not projects_root or not os.path.isdir(projects_root):
        return None, "no_root", projects_root or "путь obsidian_projects не задан в конфиге"

    # 1. passport.md в корне проекта называет имя папки vault
    name = passport_field(os.path.join(proj, "passport.md"), "project")
    if name:
        p = os.path.join(projects_root, name)
        if os.path.isdir(p):
            return p, "passport", name
        return None, "passport_no_dir", f"passport.md называет проект «{name}», папки {p} нет"

    # 2. артефакты внутри Projects/<vault>/ объявляют project_path — ищем свой.
    #    passport.md его не содержит (поле пишут handoff и файлы сессий), поэтому
    #    смотрим и там тоже, иначе связь проект↔vault не находится вовсе.
    target = os.path.normcase(os.path.abspath(proj))
    matches = []
    try:
        entries = sorted(os.listdir(projects_root))
    except OSError:
        entries = []
    for entry in entries:
        vdir = os.path.join(projects_root, entry)
        if not os.path.isdir(vdir):
            continue
        candidates = [os.path.join(vdir, "passport.md"), os.path.join(vdir, "handoff.md")]
        sessions = sorted(glob.glob(os.path.join(vdir, "sessions", "*.md")),
                          key=lambda p: os.path.getmtime(p), reverse=True)[:10]
        for src in candidates + sessions:
            declared = passport_field(src, "project_path")
            if declared and os.path.normcase(os.path.abspath(declared.strip('"'))) == target:
                matches.append(entry)
                break
    if len(matches) == 1:
        return os.path.join(projects_root, matches[0]), "project_path", matches[0]
    if len(matches) > 1:
        return None, "ambiguous", "этот project_path объявляют: " + ", ".join(matches)

    # 3. папка по имени проекта
    base = os.path.basename(proj)
    p = os.path.join(projects_root, base)
    if os.path.isdir(p):
        return p, "basename", base
    return None, "unlinked", base


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


UNRESOLVED = {
    "no_root": "каталог Projects не найден",
    "ambiguous": "этот путь объявляют несколько vault — какой из них наш, неизвестно",
    "unlinked": "в корне проекта нет passport.md, и ни один vault не объявляет этот путь — "
                "связь проект↔vault не установлена",
}


def check_vault(proj, projects_root):
    """Три исхода: проверено и чисто · проверено и есть проблема · НЕ ПРОВЕРЕНО.

    «Не проверено» — это не «не найдено»: гейт не смог посмотреть и потому не
    вправе утверждать, что всё записано.
    """
    vault, how, note = resolve_vault(proj, projects_root)

    if vault is None:
        if how == "passport_no_dir":
            # Отсутствие установлено положительно: паспорт называет проект,
            # значит имя vault известно — и такой папки нет.
            return Finding(WARN, "Vault не заведён — проекту некуда писать память",
                           details=[note], fix="/mm vault")
        return Finding(UNKNOWN,
                       f"Vault НЕ ПРОВЕРЕН — {UNRESOLVED.get(how, how)}. Состояние vault неизвестно",
                       details=[note], fix="/mm new (паспорт в корне проекта) либо /mm vault")

    vname = os.path.basename(vault)
    if not os.path.exists(os.path.join(vault, ".git")):
        # Блокер, а не предупреждение: без git у vault нет ни синхронизации с
        # Knowledge, ни истории, ни восстановления — потерять можно всё и молча.
        # Мягкая планка была вынужденной, пока часть vault'ов жила вне git.
        return Finding(BLOCKER, f"Vault {vname} не git-репозиторий — ни синхронизации, "
                                "ни истории, ни восстановления",
                       details=[vault], fix="/mm vault")

    rc_st, dirty = run(["git", "-C", vault, "status", "--porcelain", "--untracked-files=all"])
    if rc_st != 0:
        return Finding(UNKNOWN, f"Vault НЕ ПРОВЕРЕН — git status в {vname} не отработал. "
                                "Состояние vault неизвестно", details=[vault])
    lines = [l for l in dirty.splitlines() if l.strip()]

    rc_up, upstream = run(["git", "-C", vault, "rev-parse", "--abbrev-ref",
                           "--symbolic-full-name", "@{u}"])
    if rc_up != 0 or not upstream:
        return Finding(UNKNOWN, f"Vault НЕ ПРОВЕРЕН на запушенность — у ветки {vname} нет upstream. "
                                "Доехало ли записанное до Knowledge, неизвестно",
                       details=[f"незакоммичено файлов: {len(lines)}"] if lines else [],
                       fix="/mm vault")

    rc, out = run(["git", "-C", vault, "rev-list", "--left-right", "--count", "HEAD...@{u}"])
    try:
        ahead, behind = (int(x) for x in out.split())
    except ValueError:
        return Finding(UNKNOWN, f"Vault НЕ ПРОВЕРЕН — не удалось сравнить {vname} с {upstream}. "
                                "Состояние vault неизвестно", details=[vault])

    problems = []
    if lines:
        problems.append(f"незакоммичено {len(lines)} файл(ов)")
    if ahead:
        problems.append(f"не запушено {ahead} коммит(ов)")
    if problems:
        return Finding(BLOCKER, f"Vault {vname} расходится: " + ", ".join(problems),
                       details=lines[:10], fix="/mm save (закоммитит и запушит vault)")
    if behind:
        return Finding(WARN, f"Vault {vname} отстаёт от origin на {behind}", fix="git -C <vault> pull")
    return Finding(OK, f"Vault {vname}: чисто, синхронно (найден по {how})")


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
        lag_min = int((t_work - t_ho).total_seconds()) // 60
        if lag_min < HANDOFF_STALE_TOLERANCE_MIN:
            return Finding(OK, f"Handoff отстаёт на {delta(t_work, t_ho)} — в пределах порога "
                               f"{HANDOFF_STALE_TOLERANCE_MIN}м, не блокер")
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
    if not vault:
        return Finding(UNKNOWN, "Лог сессии НЕ ПРОВЕРЕН — vault не определён, искать логи негде",
                       fix="/mm new (паспорт в корне проекта) либо /mm vault")
    files = glob.glob(os.path.join(vault, "sessions", "*.md"))
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
    unknowns = [f for f in findings if f.level == UNKNOWN]
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

    if unknowns:
        out.append(f"❓ НЕ ПРОВЕРЕНО ({len(unknowns)}) — считается за блокер")
        for f in unknowns:
            out.append(f" • {f.title}")
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

    verdict = "НЕ ГОТОВО · exit 1" if (blockers or unknowns) else "ГОТОВО К /clear · exit 0"
    out.append(f"── ВЕРДИКТ: {verdict} ──")
    out.append(f"порог свежести handoff: {HANDOFF_STALE_TOLERANCE_MIN} мин "
               "(меньше — не блокер)")
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
    vault, _, _ = resolve_vault(proj, projects_root)

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

    findings = [handoff, check_vault(proj, projects_root), tree, push]
    if args.mode == "end":
        findings.append(check_session_log(proj, vault))
    findings.append(check_health(proj))

    print(render(name, args.mode, findings))
    return 1 if any(f.level in (BLOCKER, UNKNOWN) for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
