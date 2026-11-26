#!/usr/bin/env python3
"""check-backlog-next — прогон scripts/backlog-next.py по фикстурам.

Вердикт из exit code: 0 — всё сошлось, 1 — есть расхождение.
Фикстуры собираются во временном каталоге и удаляются после прогона;
в репозитории и в git ничего не меняется.

  python scripts/check-backlog-next.py
"""

import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "backlog-next.py")

ROADMAP = """# Roadmap

### Phase 3: Обычная фаза вехи

## Backlog

### Phase 999.1: Кнопка выхода выкидывает со всех устройств (BACKLOG — ЗАКРЫТ 14.10)

#### Подзаголовок внутри пункта

Сверка подзаголовка.

### Phase 19.2: Вставленная фаза внутри бэклога (INSERTED)

Тело чужой фазы: ротация логов сервера.

### Phase 999.3: Обзор рынка — другие студии и модельные школы (BACKLOG)

### Phase 999.3: Повтор номера (BACKLOG)
"""

BACKLOG = """# Backlog

## 1. P2 — первый пункт

## 🟢 2. RESOLVED — второй пункт
"""

# (имя, {файл: текст}, --about, ожидаемый код, строки, которые обязаны быть,
#  строки, которых быть не должно)
CASES = [
    ("ROADMAP без BACKLOG.md: серия 999.N, пропуск, повтор, похожие",
     {"ROADMAP.md": ROADMAP}, "обзор рынка студии школы", 0,
     ["СЛЕДУЮЩИЙ НОМЕР: #999.4", "Пропуски в серии (1): #999.2",
      "Повторы номера (1)", "#999.3 [открыт] Обзор рынка"],
     ["#19.2", "#3 "]),
    ("ROADMAP: тело чужой фазы не приписано пункту бэклога",
     {"ROADMAP.md": ROADMAP}, "ротация логов сервера", 0,
     ["похожего нет, заводи #999.4"], []),
    ("ROADMAP: текст под '####' остаётся в пункте",
     {"ROADMAP.md": ROADMAP}, "сверка подзаголовка", 0,
     ["#999.1 [закрыт] Кнопка выхода"], []),
    ("BACKLOG.md рядом с ROADMAP.md — источник BACKLOG.md",
     {"ROADMAP.md": ROADMAP, "BACKLOG.md": BACKLOG}, "", 0,
     ["BACKLOG.md", "СЛЕДУЮЩИЙ НОМЕР: #3 "], ["#999."]),
    ("ни BACKLOG.md, ни ROADMAP.md — ненулевой код",
     {}, "", 1, ["Заводить пункт некуда"], ["СЛЕДУЮЩИЙ НОМЕР"]),
    ("ROADMAP.md без пунктов 999.N — ненулевой код",
     {"ROADMAP.md": "# Roadmap\n\n### Phase 1: Фаза\n"}, "", 1,
     ["Заводить пункт некуда"], ["СЛЕДУЮЩИЙ НОМЕР"]),
]


def run_case(tmp, files, about):
    planning = os.path.join(tmp, ".planning")
    os.makedirs(planning)
    for name, text in files.items():
        with open(os.path.join(planning, name), "w", encoding="utf-8") as f:
            f.write(text)
    # git не должен подняться выше фикстуры и найти чужой .planning.
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=os.path.dirname(tmp),
               PYTHONIOENCODING="utf-8")
    cmd = [sys.executable, SCRIPT, "--project", tmp]
    if about:
        cmd += ["--about", about]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return p.returncode, p.stdout + p.stderr


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    failed = []
    for name, files, about, code, must, must_not in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = run_case(tmp, files, about)
        problems = []
        if rc != code:
            problems.append(f"код {rc}, ожидался {code}")
        problems += [f"нет строки: {s!r}" for s in must if s not in out]
        problems += [f"лишняя строка: {s!r}" for s in must_not if s in out]
        if problems:
            failed.append((name, problems, out))

    print(f"🔎 backlog-next: проверено {len(CASES)} случаев\n")
    for name, problems, out in failed:
        print(f"❌ {name}")
        for pr in problems:
            print(f"   {pr}")
        print("   --- вывод ---")
        print("   " + out.strip().replace("\n", "\n   "))
        print()
    if not failed:
        print("✅ все случаи сошлись")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
