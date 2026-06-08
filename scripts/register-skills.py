#!/usr/bin/env python3
import os
import sys
import subprocess
import platform

def resolve_target(path):
    try:
        return os.readlink(path)
    except OSError:
        if platform.system() == 'Windows':
            try:
                parent = os.path.dirname(path)
                name = os.path.basename(path)
                out = subprocess.check_output(f'dir "{parent}"', shell=True, text=True)
                for line in out.splitlines():
                    if "<JUNCTION>" in line and name in line:
                        start = line.find('[')
                        end = line.find(']')
                        if start != -1 and end != -1:
                            return line[start+1:end]
            except Exception:
                pass
        return None

def main():
    repo_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    source_dir = os.path.join(repo_root, "skills")
    vendor_dir = os.path.join(repo_root, "vendor")
    
    home = os.path.expanduser("~")
    target_root = os.path.join(home, ".claude", "skills")
    
    print(f"Repo:   {repo_root}")
    print(f"Source: {source_dir}")
    print(f"Target: {target_root}")
    
    if not os.path.exists(source_dir):
        print(f"Error: Source dir not found: {source_dir}")
        sys.exit(1)
        
    if not os.path.exists(target_root):
        print(f"Target dir not found: {target_root}. Creating it...")
        os.makedirs(target_root, exist_ok=True)
        
    is_windows = (platform.system() == 'Windows')
    
    if is_windows:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
            try:
                val, _ = winreg.QueryValueEx(key, "MM_REPO_ROOT")
                if val.lower() != repo_root.lower():
                    winreg.SetValueEx(key, "MM_REPO_ROOT", 0, winreg.REG_SZ, repo_root)
                    print(f"[env] Updated MM_REPO_ROOT to {repo_root}")
                else:
                    print("[env] MM_REPO_ROOT already set correctly")
            except FileNotFoundError:
                winreg.SetValueEx(key, "MM_REPO_ROOT", 0, winreg.REG_SZ, repo_root)
                print(f"[env] Set MM_REPO_ROOT = {repo_root}")
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[env] Warning: Could not set Windows Registry Environment variable: {e}")
    else:
        shell = os.environ.get("SHELL", "")
        profile_path = None
        if "zsh" in shell:
            profile_path = os.path.join(home, ".zshrc")
        elif "bash" in shell:
            profile_path = os.path.join(home, ".bashrc")
        else:
            if platform.system() == 'Darwin':
                profile_path = os.path.join(home, ".zshrc")
            else:
                profile_path = os.path.join(home, ".bashrc")
            
        export_line = f'export MM_REPO_ROOT="{repo_root}"\n'
        
        if profile_path:
            if not os.path.exists(profile_path):
                try:
                    with open(profile_path, "w", encoding="utf-8") as f:
                        f.write("#!/bin/zsh\n" if "zsh" in profile_path else "#!/bin/bash\n")
                    print(f"[env] Created shell profile: {profile_path}")
                except Exception as e:
                    print(f"[env] Warning: Could not create shell profile {profile_path}: {e}")
            
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if 'export MM_REPO_ROOT=' not in content:
                    with open(profile_path, "a", encoding="utf-8") as f:
                        f.write(f"\n# markdown-memory repository path\n{export_line}")
                    print(f"[env] Added MM_REPO_ROOT to {profile_path}")
                elif f'MM_REPO_ROOT="{repo_root}"' not in content:
                    import re
                    new_content = re.sub(r'export MM_REPO_ROOT=.*', f'export MM_REPO_ROOT="{repo_root}"', content)
                    with open(profile_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"[env] Updated MM_REPO_ROOT in {profile_path} to {repo_root}")
                else:
                    print(f"[env] MM_REPO_ROOT already configured in {profile_path}")
            else:
                print(f"[env] Warning: Could not find or create profile path {profile_path}")

    skills = []
    if os.path.exists(source_dir):
        for name in os.listdir(source_dir):
            p = os.path.join(source_dir, name)
            if os.path.isdir(p):
                skills.append((name, p))
                
    if os.path.exists(vendor_dir):
         for name in os.listdir(vendor_dir):
            p = os.path.join(vendor_dir, name)
            if os.path.isdir(p):
                skills.append((name, p))
                
    created = 0
    skipped = 0
    relinked = 0
    errors = 0
    
    for name, source_path in skills:
        target_path = os.path.join(target_root, name)
        
        if os.path.exists(target_path) or os.path.islink(target_path):
            is_link = os.path.islink(target_path) or (is_windows and os.path.isdir(target_path))
            
            if is_link:
                existing_target = resolve_target(target_path)
                if not existing_target:
                    try:
                        existing_target = os.readlink(target_path)
                    except Exception:
                        pass
                
                if existing_target and os.path.abspath(existing_target).lower() == os.path.abspath(source_path).lower():
                    print(f"  [skip] {name} -> already linked correctly")
                    skipped += 1
                    continue
                else:
                    print(f"  [relink] {name} -> wrong target ({existing_target}), recreating")
                    try:
                        if is_windows:
                            subprocess.run(f'cmd /c rmdir "{target_path}"', shell=True, check=True)
                        else:
                            os.unlink(target_path)
                        relinked += 1
                    except Exception as e:
                        print(f"  [error] Failed to delete wrong link {target_path}: {e}")
                        errors += 1
                        continue
            else:
                print(f"  [error] {name} -> {target_path} exists and is NOT a link. Manual intervention needed.")
                errors += 1
                continue
        else:
            created += 1
            
        try:
            if is_windows:
                subprocess.run(f'cmd /c mklink /J "{target_path}" "{source_path}"', shell=True, check=True)
            else:
                os.symlink(source_path, target_path)
            print(f"  [ok]   {name}")
        except Exception as e:
            print(f"  [fail] {name} -> {e}")
            errors += 1
            
    # Register global instructions for Antigravity (Gemini) if directory exists
    antigravity_knowledge_dir = os.path.join(home, ".gemini", "antigravity", "knowledge")
    if os.path.exists(antigravity_knowledge_dir):
        global_inst_dest = os.path.join(antigravity_knowledge_dir, "mm-global-instructions.md")
        instructions_content = """# markdown-memory (mm) Global System Instructions

Эти инструкции загружаются глобально во все сессии агента Antigravity.

## Режим работы: Исключительно Планировщик (Planner / Architect)
1. **Роль и ограничения**:
   - Ты выступаешь **исключительно в роли проектировщика и партнера по планированию (как claude.ai)**.
   - Тебе **категорически запрещено самостоятельно изменять файлы проекта** (создавать новые файлы, модифицировать код с помощью инструментов редактирования) или запускать команды, меняющие состояние репозитория/проекта (такие как `git commit`, сборочные скрипты, инсталляция пакетов).
   - Всегда пиши предлагаемый код и команды текстом в чат в виде аккуратного, готового к копированию и самодостаточного промпта (self-contained prompt) или списка команд для запуска в CLI. Реальное выполнение и модификацию кода будет делать локальный CLI-агент без подтверждений.
2. **Полный доступ к чтению контекста (без подтверждений от пользователя)**:
   - Чтобы составлять качественные промпты, тебе необходим полный контекст. Ты **можешь и должен активно использовать инструменты чтения** (просмотр файлов `view_file`, поиск `grep_search`, просмотр содержимого директорий `list_dir`).
   - Ты **можешь и должен свободно запускать диагностические и информационные команды в CLI** (такие как `git status`, `git diff`, `git log`, просмотр логов сборки/запуска, запуск тестов) через `run_command` без предварительного согласования с пользователем.
   - Ты **можешь и должен свободно использовать поиск в интернете** (`search_web`, чтение веб-страниц), чтобы сверяться с документацией, логами ошибок и внешними библиотеками.

## Предотвращение зацикливания и обработка логов
1. **Запрет на опрос статуса в цикле (No-Polling)**:
   - При запуске долгих фоновых процессов (например, тестов через `pytest`, сборки проекта, деплоя) **никогда не устраивай циклов ожидания с ручным опросом статуса** (не используй `schedule` / таймеры для регулярного вызова `status`).
   - Вместо этого запусти задачу в фоновом режиме и сразу **заверши свой ход**, перестав вызывать инструменты. Система автоматически разбудит тебя сообщением с результатом выполнения, когда процесс завершится.
   - Не забивай контекст диалога однотипными промежуточными сообщениями вида "пройдено 10%... подожду еще", так как накопление одинаковых сообщений в истории приводит к зацикливанию (token repetition loop).
2. **Сжатие и фильтрация логов**:
   - Никогда не выводи в чат сырые простыни логов или полные списки успешных тестов.
   - Всегда сокращай вывод логов до краткого саммари (прошло/упало) и списка конкретных ошибок (не более 15–20 строк с трассировкой стека). Если ошибок слишком много, покажи только первые 3–5 ключевых проблем.
3. **Контроль повторений токенов**:
   - Если ты замечаешь, что генерируешь однотипные слова или повторяешь структуру предыдущих абзацев (особенно при пересказе системных логов или выводе длинных путей), немедленно измени стиль изложения или оборви подробное описание, перейдя к краткому выводу.

## Интеграция с Obsidian Knowledge Vault
1. При начале работы в сессии в рабочей директории (workspace), агент Antigravity должен проверить, подключен ли проект к Obsidian Knowledge Vault.
2. Проверка осуществляется по наличию папки `.vault/` в корне проекта или по секции `## Obsidian Knowledge Vault` в файле `CLAUDE.md`.
3. Если хранилище найдено:
   - Агент ДОЛЖЕН автоматически прочитать файлы `<vault_root>/00-home/index.md` и `<vault_root>/00-home/текущие приоритеты.md` для получения актуального контекста, Milestone и задач, а также для ознакомления со списком доступных заметок.
   - Если текущая задача пользователя касается определенных модулей, интеграций или архитектуры, агент должен найти в `<vault_root>/knowledge/` соответствующие заметки и прочитать их.
   - При завершении сессии (когда пользователь говорит "сохрани сессию", "закрываемся", "конец дня" и т.п.), агент должен выполнить процедуру сохранения сессии, соответствующую `/mm save` (описана в `skills/mm-save-session/SKILL.md`), включая автоматический экспорт решений/багов в знаниевые файлы и пересборку индекса.

## Обработка команд mm-системы
Когда пользователь вводит команду с префиксиом `/mm` (или запрашивает операции с контекстом, такие как "где мы", "восстанови контекст", "сохрани сессию", "сделай handoff"):

1. Найдите путь к репозиторию `markdown-memory` (из переменной окружения `MM_REPO_ROOT` или через целевую папку симлинка `~/.claude/skills/mm-bridge`).
2. Сопоставьте запрос с соответствующим скиллом:
   - `/mm` или `/mm help` или `/mm ?` -> `skills/mm/SKILL.md`
   - `/mm new`, `/mm init` или `/mm-init-project` -> `skills/mm-init-project/SKILL.md`
   - `/mm setup` или `/mm onboard` -> `skills/mm-setup/SKILL.md`
   - `/mm resume`, `/mm start` или `где мы` -> `skills/mm-resume/SKILL.md`
   - `/mm save`, `/mm end` или `сохрани сессию` -> `skills/mm-save-session/SKILL.md`
   - `/mm next` или `/mm handoff` -> `skills/mm-handoff/SKILL.md`
   - `/mm prompt` или `/mm bridge` -> `skills/mm-bridge/SKILL.md`
   - `/mm check`, `/mm doctor` или `проверь систему` -> `skills/mm-doctor/SKILL.md`
3. Прочитайте соответствующий файл `SKILL.md` из репозитория.
4. Выполните инструкции этого скилла точно и последовательно, используя локальные инструменты чтения файлов и запуска консольных команд (на macOS используйте `python3` вместо PowerShell для запуска скриптов репозитория).
"""
        try:
            with open(global_inst_dest, "w", encoding="utf-8") as f:
                f.write(instructions_content)
            print(f"[antigravity] Registered global instructions at {global_inst_dest}")
        except Exception as e:
            print(f"[antigravity] Warning: Could not register global instructions: {e}")
            
    print(f"\nSummary: created={created} relinked={relinked} skipped={skipped} errors={errors}")
    if errors > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
