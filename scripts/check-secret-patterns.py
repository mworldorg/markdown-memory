#!/usr/bin/env python3
"""check-secret-patterns — прогон config/secret-patterns.tests.json по канону паттернов.

Вердикт из exit code: 0 — всё сошлось, 1 — есть расхождение.
Пропуск в must_match страшнее лишнего срабатывания: это молчание на настоящей
утечке, поэтому такие расхождения печатаются первыми.

Только чтение: ничего не правит, ни в git, ни в файлах.
"""

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join(REPO, "config", "secret-patterns.json")
TESTS = os.path.join(REPO, "config", "secret-patterns.tests.json")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    with open(CANON, encoding="utf-8") as f:
        patterns = {p["id"]: p for p in json.load(f)["patterns"]}
    with open(TESTS, encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    missed, extra, checked = [], [], 0

    for case in cases:
        pid = case["pattern"]
        p = patterns.get(pid)
        if p is None:
            missed.append((pid, "—", f"паттерна {pid} нет в каноне"))
            continue
        flags = re.I if "i" in p.get("flags", "") else 0
        rx = re.compile(p["regex"], flags)
        for c in case.get("must_match", []):
            checked += 1
            if not rx.search(c["text"]):
                missed.append((pid, c["text"], c["why"]))
        for c in case.get("must_not_match", []):
            checked += 1
            if rx.search(c["text"]):
                extra.append((pid, c["text"], c["why"]))

    print(f"🔎 secret-patterns: проверено {checked} случаев по {len(cases)} паттерну(ам)\n")

    if missed:
        print(f"❌ ПРОПУЩЕНО ({len(missed)}) — паттерн молчит там, где обязан сработать")
        for pid, text, why in missed:
            print(f" • [{pid}] {why}\n   {text}")
        print()
    if extra:
        print(f"⚠️  ЛИШНЕЕ СРАБАТЫВАНИЕ ({len(extra)})")
        for pid, text, why in extra:
            print(f" • [{pid}] {why}\n   {text}")
        print()
    if not missed and not extra:
        print("✅ все случаи сошлись")

    return 1 if (missed or extra) else 0


if __name__ == "__main__":
    sys.exit(main())
