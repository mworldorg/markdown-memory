# 🧠 Контекст заполнился — что делать

---

## Claude Chat (claude.ai)

Нажми **New Chat** внутри того же Project. Всё. Паспорт и инструкции загружаются автоматически.

---

## Claude Code (терминал)

### Контекст < 80%

```
/compact
```

Сжимает историю, продолжаешь в той же сессии.

---

### Контекст > 80%

```
/save-session          ← сессия в Obsidian
/gsd-pause-work        ← состояние GSD (если используешь)
exit                   ← закрыть
claude                 ← открыть заново
/gsd-resume-work       ← восстановить (если GSD)
```

Без GSD:
```
/save-session
exit
claude
Прочитай CLAUDE.md и PROJECT_PASSPORT.md, скажи что понял и жди команды.
```

---

### Конец дня

```
/save-all
```

---

### Почему контекст не теряется

| Что | Где | Как восстанавливается |
|-----|-----|----------------------|
| Правила | CLAUDE.md | Автоматически при старте |
| Состояние GSD | .planning/STATE.md | /gsd-resume-work |
| Незаконченная работа | HANDOFF.json | /gsd-resume-work |
| Лог сессии | Obsidian | /save-session |
| Паспорт | PROJECT_PASSPORT.md | Project Knowledge (Chat) |

---

### Шпаргалка

```
Работаешь     →  /compact
Контекст 80%  →  /save-session → exit → claude → /gsd-resume-work
Конец дня     →  /save-all
```
