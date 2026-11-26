#!/usr/bin/env python3
"""backlog-next — следующий номер для BACKLOG.md и поиск похожих пунктов.

Делает ровно то, что нельзя доверить памяти: номер от фактического максимума
и проверку «а не заводили ли уже это». Формулировку находки пишет модель.

Источник серии: `.planning/BACKLOG.md`, а если его нет — бэклог GSD в
`.planning/ROADMAP.md` (разделы `### Phase 999.N: …`, номер пункта — 999.N).

Только чтение: файлы не правятся, git не трогается, ничего не создаётся.
Exit code: 0 — номер выдан; 1 — серии нет (ни BACKLOG.md, ни пунктов 999.N
в ROADMAP.md) или формат не распознан. Код 0 при «заводить некуда» прятал
отказ от вызывающего: номер в таком случае брали грепом, мимо проверки повторов.

  python backlog-next.py --project <путь> --about "текст находки"
"""

import argparse
import math
import os
import re
import subprocess
import sys
from collections import Counter

# Заголовок пункта: '## 12. P2 — ...' либо '## 🟢 83. RESOLVED — ...' (эмодзи
# перед номером встречается). Варианты '## 146-старое.' намеренно не ловим:
# это помеченные версии одной записи, а не отдельные номера серии.
HEADING = re.compile(r"^##\s+(?:(\S+)\s+)?(\d+)\.\s*(.*)$")
# Второй формат, которым заводятся новые пункты: '### #634 — ...'. Подзаголовки
# внутри пункта ('### ⊕ ...', '### Что известно') сюда не попадают: нужен '#' и номер.
HEADING_HASH = re.compile(r"^###\s+#(\d+)\b\s*(?:—\s*)?(.*)$")
# Бэклог GSD в ROADMAP.md: '### Phase 999.12: ... (BACKLOG)'. Так он живёт у
# проектов без BACKLOG.md (ModelSearch: коммиты 'docs(backlog): #999.N — …').
HEADING_ROADMAP = re.compile(r"^###\s+Phase\s+999\.(\d+):\s*(.*)$")
# В ROADMAP.md любой другой заголовок до третьего уровня закрывает пункт:
# фазы вехи ('### Phase 19.2: …') и разделы не должны попасть в тело пункта.
ANY_HEADING = re.compile(r"^#{1,3}\s")
ROADMAP_PREFIX = "999."

CLOSED = re.compile(r"✅|🟢|FIXED|RESOLVED|CLOSED|ЗАКРЫТ|DONE")

# Слова, которые есть почти в каждом пункте и потому ничего не различают.
STOP = {
    "или", "если", "как", "что", "чем", "это", "этот", "эта", "эти", "тот",
    "для", "при", "над", "под", "без", "про", "изза", "того", "чтобы", "так",
    "уже", "ещё", "еще", "все", "всё", "всех", "был", "была", "было", "были",
    "есть", "нет", "туда", "сюда", "там", "тут", "где", "когда", "который",
    "которая", "которые", "него", "неё", "them", "and", "the", "for", "not",
    "баг", "бага", "задач", "пункт", "фаза", "фазы", "фазе",
}

MIN_TOKEN = 3
STEM = 5          # обрезка токена под грубый стеммер
TOP_N = 5
BODY_WEIGHT = 0.3

# Ниже этого — совпадение по служебным словам, а не по смыслу. На замерах:
# перефразированный существующий пункт даёт 0.49 и 0.43, заведомо новая
# находка — 0.08. Показывать хвост шума и советовать «дополни существующий»
# хуже, чем промолчать: совет к слиянию, которого нет, стоит дороже.
SIMILAR_FLOOR = 0.20


def norm(text):
    return text.lower().replace("ё", "е")


def stems(text):
    """Множество огрублённых основ. Русский без стеммера иначе не сходится:
    «замер» и «замеры», «ротация» и «ротации» — разные строки, одно понятие."""
    out = set()
    for tok in re.findall(r"[а-яa-z0-9]+", norm(text)):
        if len(tok) < MIN_TOKEN or tok in STOP:
            continue
        out.add(tok[:STEM])
    return out


def trigrams(text):
    t = re.sub(r"[^а-яa-z0-9]+", " ", norm(text)).strip()
    return {t[i:i + 3] for i in range(len(t) - 2)} if len(t) >= 3 else set()


def dice(a, b):
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def find_backlog(project):
    """(путь, вид) источника серии, иначе (None, None). Вид — 'backlog' для
    BACKLOG.md, 'roadmap' для ROADMAP.md. Если в <project> нет ни того, ни
    другого — пробуем корень git-репозитория: команду часто зовут из подкаталога."""
    bases = [project]
    try:
        p = subprocess.run(["git", "-C", project, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if p.returncode == 0 and p.stdout.strip():
            bases.append(os.path.normpath(p.stdout.strip()))
    except (OSError, ValueError):
        pass
    for base in bases:
        for fname, kind in (("BACKLOG.md", "backlog"), ("ROADMAP.md", "roadmap")):
            cand = os.path.join(base, ".planning", fname)
            if os.path.isfile(cand):
                return cand, kind
    return None, None


def parse(path, kind="backlog"):
    """[(номер, заголовок, closed, тело)] по секциям файла."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    items, cur, body = [], None, []
    for line in lines:
        if kind == "roadmap":
            r = HEADING_ROADMAP.match(line)
            if r or ANY_HEADING.match(line):
                if cur:
                    items.append(cur + ("\n".join(body),))
                cur = ((int(r.group(1)), r.group(2).strip(),
                        bool(CLOSED.search(r.group(2)))) if r else None)
                body = []
            elif cur:
                body.append(line)
            continue
        m = HEADING.match(line)
        h = None if m else HEADING_HASH.match(line)
        if m or h:
            if cur:
                items.append(cur + ("\n".join(body),))
            if m:
                marker, num, title = m.group(1) or "", m.group(2), m.group(3)
            else:
                marker, num, title = "", h.group(1), h.group(2)
            cur = (int(num), title.strip(), bool(CLOSED.search(marker + " " + title)))
            body = []
        elif cur:
            body.append(line)
    if cur:
        items.append(cur + ("\n".join(body),))
    return items


def similar(items, about):
    """Кандидаты на слияние, отсортированные по убыванию.

    Совпадение подстроки не годится: находку переформулируют, и «врущий
    комментарий» в заголовке не совпал с «Врущий комментарий» из SUMMARY ни
    одним общим куском. Поэтому: пересечение огрублённых основ, взвешенное по
    редкости основы (частая основа вроде «вступ» есть у половины пунктов и
    ничего не различает), плюс триграммы заголовка как разрешение ничьих.
    Тело секции считается с меньшим весом — формулировка живёт в заголовке,
    но пропустить пункт, у которого совпадение только в теле, дороже.
    """
    want = stems(about)
    if not want:
        return []

    docs = [(stems(t), stems(b)) for _, t, _, b in items]
    df = Counter()
    for head, body in docs:
        for s in head | body:
            df[s] += 1
    n = len(items) or 1
    idf = {s: math.log(n / (1 + df.get(s, 0))) + 1.0 for s in want}
    total = sum(idf.values()) or 1.0

    about_tri = trigrams(about)
    scored = []
    for (num, title, closed, _body), (head, body) in zip(items, docs):
        hit = sum(idf[s] for s in want & head)
        hit += sum(idf[s] * BODY_WEIGHT for s in (want & body) - head)
        if hit <= 0:
            continue
        score = min(hit / total, 1.0) * 0.85 + dice(about_tri, trigrams(title)) * 0.15
        if score >= SIMILAR_FLOOR:
            scored.append((score, num, title, closed))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[:TOP_N]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--project", default=os.getcwd())
    ap.add_argument("--about", default="")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    path, kind = find_backlog(project)
    items = parse(path, kind) if path else []
    if not items:
        planning = os.path.join(project, ".planning")
        if path and kind == "backlog":
            print(f"📕 {path}")
            print("   Заголовков вида '## N.' или '### #N' не найдено — файл пуст или формат иной.")
        else:
            print(f"📕 Серия номеров не найдена: нет {os.path.join(planning, 'BACKLOG.md')}")
            print(f"   и нет пунктов '### Phase 999.N:' в {path or os.path.join(planning, 'ROADMAP.md')}")
            print("   Заводить пункт некуда.")
        return 1

    pfx = ROADMAP_PREFIX if kind == "roadmap" else ""
    nums = sorted(i[0] for i in items)
    uniq = sorted(set(nums))
    closed_n = sum(1 for i in items if i[2])
    nxt = f"{pfx}{uniq[-1] + 1}"

    print(f"📕 {path}")
    print(f"   пунктов: {len(items)} · номеров уникальных: {len(uniq)} · "
          f"закрытых по маркеру: {closed_n}")
    print()
    print(f"➡️  СЛЕДУЮЩИЙ НОМЕР: #{nxt}   (максимум серии #{pfx}{uniq[-1]})")
    print()

    gaps = [n for n in range(uniq[0], uniq[-1]) if n not in set(uniq)]
    if gaps:
        print(f"🕳  Пропуски в серии ({len(gaps)}): " + ", ".join(f"#{pfx}{g}" for g in gaps))
        print("   Свободные номера не переиспользуются: на них могли ссылаться.")
        print()

    dups = [n for n, c in Counter(nums).items() if c > 1]
    if dups:
        print(f"♻️  Повторы номера ({len(dups)}):")
        for d in sorted(dups):
            for num, title, closed, _ in items:
                if num == d:
                    mark = "закрыт" if closed else "открыт"
                    print(f"   #{pfx}{d} [{mark}] {title[:88]}")
        print()

    if args.about:
        cands = similar(items, args.about)
        print(f"🔎 Похожие пункты на «{args.about[:70]}»")
        if not cands:
            print(f"   ничего выше порога {SIMILAR_FLOOR:.2f} — похожего нет, "
                  f"заводи #{nxt}")
        else:
            for score, num, title, closed in cands:
                mark = "закрыт" if closed else "открыт"
                print(f"   {score:.2f}  #{pfx}{num} [{mark}] {title[:80]}")
            print()
            print("   Прочитай кандидатов: если находка ложится в существующий пункт — "
                  "дополни его,")
            print(f"   нового номера не заводи. Если не ложится — #{nxt}.")
    else:
        print("ℹ️  Поиск похожих не выполнялся — передай --about \"<текст находки>\".")

    return 0


if __name__ == "__main__":
    sys.exit(main())
