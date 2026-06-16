// Детерминированный read-only движок проверок здоровья mm-системы.
// Раунд 1: группы config (загрузка mm-config) и junctions (проводка ~/.claude/skills → repo).
// Раунд 2 (требует projectRoot): группы vault-git и passport/gsd.
// Ничего не чинит и не пишет. Суждение и авто-фиксы — в скилле mm-doctor.

import fs from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import matter from 'gray-matter';
import { loadMmConfig, type LoadedConfig, type MmConfig } from './config-loader.js';

export type CheckStatus = 'ok' | 'warn' | 'fail' | 'na';

export interface HealthCheck {
  id: string;
  status: CheckStatus;
  detail: string;
}

export interface HealthResult {
  checks: HealthCheck[];
  summary: { ok: number; warn: number; fail: number; na: number };
}

// Нормализация пути ссылки для сравнения: снять NT-префиксы (\\?\, \??\),
// привести к абсолютному, убрать хвостовой слэш, на win32 — регистронезависимо.
export function normalizeLinkPath(p: string): string {
  let s = String(p);
  s = s.replace(/^\\\\\?\\/, ''); // \\?\
  s = s.replace(/^\\\?\?\\/, ''); // \??\
  s = path.resolve(s);
  s = s.replace(/[\\/]+$/, '');
  if (process.platform === 'win32') s = s.toLowerCase();
  return s;
}

// Совпадает ли target junction-ссылки с ожидаемым путём (после нормализации обоих).
export function junctionMatches(actual: string, expected: string): boolean {
  return normalizeLinkPath(actual) === normalizeLinkPath(expected);
}

function configChecks(): {
  checks: HealthCheck[];
  repoRoot: string | null;
  config: MmConfig | null;
} {
  const checks: HealthCheck[] = [];
  let loaded: LoadedConfig;
  try {
    loaded = loadMmConfig();
  } catch (e) {
    // Мягкая деградация: сбой загрузки — это check со status fail, не краш наверх.
    checks.push({
      id: 'config.load',
      status: 'fail',
      detail: `mm-config не загружен: ${(e as Error).message}`,
    });
    return { checks, repoRoot: null, config: null };
  }

  checks.push({
    id: 'config.load',
    status: 'ok',
    detail: `mm-config загружен (source: ${loaded.source}, repoRoot: ${loaded.repoRoot})`,
  });

  // Overlay: если local есть — loadMmConfig уже распарсил и смержил его (иначе кинул бы выше).
  const localPath = path.join(loaded.repoRoot, 'config', 'mm-config.local.json');
  checks.push({
    id: 'config.overlay',
    status: 'ok',
    detail: fs.existsSync(localPath)
      ? 'mm-config.local.json присутствует, валиден и смержен (local wins)'
      : 'mm-config.local.json отсутствует (overlay не требуется)',
  });

  // Ключевые пути: obsidian_* присутствуют + _repo_root инъектирован.
  const paths = (loaded.config.paths ?? {}) as Record<string, unknown>;
  const obsidianKeys = Object.keys(paths).filter((k) => k.startsWith('obsidian_'));
  const missing: string[] = [];
  if (obsidianKeys.length === 0) missing.push('paths.obsidian_*');
  if (!loaded.config._repo_root) missing.push('_repo_root');

  checks.push(
    missing.length === 0
      ? {
          id: 'config.keys',
          status: 'ok',
          detail: `ключевые пути присутствуют: obsidian_* (${obsidianKeys.length}), _repo_root инъектирован`,
        }
      : {
          id: 'config.keys',
          status: 'warn',
          detail: `отсутствуют ключи: ${missing.join(', ')}`,
        },
  );

  return { checks, repoRoot: loaded.repoRoot, config: loaded.config };
}

// Собирает целевые каталоги: skills/mm-* и vendor/* (каждый каталог).
function junctionTargets(repoRoot: string): {
  targets: { name: string; expected: string }[];
  checks: HealthCheck[];
} {
  const checks: HealthCheck[] = [];
  const targets: { name: string; expected: string }[] = [];

  const skillsDir = path.join(repoRoot, 'skills');
  try {
    for (const e of fs.readdirSync(skillsDir, { withFileTypes: true })) {
      if (e.isDirectory() && (e.name === 'mm' || e.name.startsWith('mm-'))) {
        targets.push({ name: e.name, expected: path.join(skillsDir, e.name) });
      }
    }
  } catch (err) {
    checks.push({
      id: 'junctions.skills.scan',
      status: 'fail',
      detail: `не прочитать skills/: ${(err as Error).message}`,
    });
  }

  const vendorDir = path.join(repoRoot, 'vendor');
  try {
    if (fs.existsSync(vendorDir)) {
      for (const e of fs.readdirSync(vendorDir, { withFileTypes: true })) {
        if (e.isDirectory()) {
          targets.push({ name: e.name, expected: path.join(vendorDir, e.name) });
        }
      }
    }
  } catch (err) {
    checks.push({
      id: 'junctions.vendor.scan',
      status: 'fail',
      detail: `не прочитать vendor/: ${(err as Error).message}`,
    });
  }

  return { targets, checks };
}

function junctionChecks(repoRoot: string): HealthCheck[] {
  const { targets, checks } = junctionTargets(repoRoot);

  for (const { name, expected } of targets) {
    const linkPath = path.join(homedir(), '.claude', 'skills', name);
    const id = `junction.${name}`;

    // lstat: существование + тип reparse-point (junction на win32 даёт isSymbolicLink()===true).
    let st: fs.Stats;
    try {
      st = fs.lstatSync(linkPath);
    } catch (err) {
      const code = (err as NodeJS.ErrnoException).code;
      checks.push({
        id,
        status: 'fail',
        detail:
          code === 'ENOENT'
            ? `ссылка отсутствует: ${linkPath}`
            : `lstat ошибка (${code ?? 'UNKNOWN'}): ${(err as Error).message}`,
      });
      continue;
    }

    if (!st.isSymbolicLink()) {
      checks.push({
        id,
        status: 'fail',
        detail: `не symlink/junction (reparse-point): ${linkPath}`,
      });
      continue;
    }

    let target: string;
    try {
      target = fs.readlinkSync(linkPath);
    } catch (err) {
      // EINVAL/UNKNOWN на экзотических reparse-point'ах → fail этого элемента, не краш.
      const code = (err as NodeJS.ErrnoException).code;
      checks.push({
        id,
        status: 'fail',
        detail: `readlink ошибка (${code ?? 'UNKNOWN'}): ${(err as Error).message}`,
      });
      continue;
    }

    checks.push(
      junctionMatches(target, expected)
        ? { id, status: 'ok', detail: `→ ${expected}` }
        : {
            id,
            status: 'fail',
            detail: `target не совпал: ${normalizeLinkPath(target)} ≠ ${normalizeLinkPath(expected)}`,
          },
    );
  }

  return checks;
}

// --- Раунд 2: vault-git и passport/gsd (требуют projectRoot) ---

// Запуск git read-only через child_process (без git-библиотеки). Никогда не кидает.
function git(cwd: string, args: string[]): { ok: boolean; stdout: string } {
  try {
    const stdout = execFileSync('git', ['-C', cwd, ...args], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    return { ok: true, stdout };
  } catch {
    return { ok: false, stdout: '' };
  }
}

interface PassportInfo {
  exists: boolean;
  data?: Record<string, unknown>;
  parseError?: string;
}

// Читает <projectRoot>/passport.md и парсит frontmatter gray-matter. Не кидает.
function readPassport(projectRoot: string): PassportInfo {
  const passportPath = path.join(projectRoot, 'passport.md');
  if (!fs.existsSync(passportPath)) return { exists: false };
  try {
    const raw = fs.readFileSync(passportPath, 'utf8');
    const parsed = matter(raw);
    return { exists: true, data: parsed.data as Record<string, unknown> };
  } catch (e) {
    return { exists: true, parseError: (e as Error).message };
  }
}

// Извлекает путь vault из секции `## Obsidian Knowledge Vault` (строка `Хранилище знаний: <path>`).
function vaultFromClaudeMd(projectRoot: string): string | null {
  const claudeMd = path.join(projectRoot, 'CLAUDE.md');
  try {
    if (!fs.existsSync(claudeMd)) return null;
    const txt = fs.readFileSync(claudeMd, 'utf8');
    const section = txt.match(/##\s+Obsidian Knowledge Vault([\s\S]*?)(?:\n##\s|$)/);
    if (!section) return null;
    const line = section[1].match(/Хранилище\s+знаний:\s*(.+)/);
    return line ? line[1].trim() : null;
  } catch {
    return null;
  }
}

// Резолв vault в порядке mm-resume: CLAUDE.md секция → <projectRoot>/.vault → <obsidian_projects>/<name>.
function resolveVault(
  projectRoot: string,
  projectName: string,
  config: MmConfig | null,
): string | null {
  const fromClaude = vaultFromClaudeMd(projectRoot);
  if (fromClaude && fs.existsSync(fromClaude)) return fromClaude;

  const dotVault = path.join(projectRoot, '.vault');
  if (fs.existsSync(dotVault)) return dotVault;

  const obsProjects = config?.paths?.obsidian_projects;
  if (typeof obsProjects === 'string') {
    const candidate = path.join(obsProjects, projectName);
    if (fs.existsSync(candidate)) return candidate;
  }

  return null;
}

function vaultChecks(
  projectRoot: string,
  projectName: string,
  config: MmConfig | null,
): HealthCheck[] {
  const checks: HealthCheck[] = [];
  const vault = resolveVault(projectRoot, projectName, config);

  if (!vault) {
    checks.push({
      id: 'vault.resolve',
      status: 'warn',
      detail: 'vault не найден (CLAUDE.md секция / .vault / obsidian_projects)',
    });
    return checks;
  }
  checks.push({ id: 'vault.resolve', status: 'ok', detail: `vault: ${vault}` });

  const insideWorkTree = git(vault, ['rev-parse', '--is-inside-work-tree']);
  if (!insideWorkTree.ok || insideWorkTree.stdout.trim() !== 'true') {
    checks.push({
      id: 'vault.git',
      status: 'warn',
      detail: 'vault не git-репо → /mm vault',
    });
    return checks;
  }

  const remote = git(vault, ['remote']);
  const remotes = remote.stdout
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (!remotes.includes('origin')) {
    checks.push({
      id: 'vault.git',
      status: 'warn',
      detail: 'git-репо без origin — handoff не запушится (причина тихого пропуска в save-session)',
    });
    return checks;
  }

  checks.push({ id: 'vault.git', status: 'ok', detail: 'git-репо с origin' });
  return checks;
}

function passportChecks(projectRoot: string, passport: PassportInfo): HealthCheck[] {
  const checks: HealthCheck[] = [];

  if (!passport.exists) {
    checks.push({
      id: 'passport.exists',
      status: 'na',
      detail: 'проект не инициализирован для mm (нет passport.md)',
    });
    return checks;
  }

  if (passport.parseError) {
    checks.push({
      id: 'passport.frontmatter',
      status: 'fail',
      detail: `невалидный YAML frontmatter: ${passport.parseError}`,
    });
    return checks;
  }
  checks.push({ id: 'passport.frontmatter', status: 'ok', detail: 'frontmatter валиден' });

  const data = passport.data ?? {};
  if (data.gsd_version === undefined || data.gsd_version === null) {
    checks.push({ id: 'passport.gsd_version', status: 'warn', detail: 'нет поля gsd_version' });
    return checks;
  }

  // Forward-check консистентности: passport заявляет версию → соответствующая папка должна быть.
  const v = String(data.gsd_version);
  const planning = path.join(projectRoot, '.planning');
  const gsd = path.join(projectRoot, '.gsd');

  if (v === 'v1' || v === 'core') {
    if (!fs.existsSync(planning)) {
      checks.push({
        id: 'passport.gsd',
        status: 'fail',
        detail: `passport gsd_version: ${v}, но .planning/ не найдена`,
      });
    } else if (v === 'core' && !fs.existsSync(path.join(planning, 'config.json'))) {
      checks.push({
        id: 'passport.gsd',
        status: 'fail',
        detail: 'passport gsd_version: core, но .planning/config.json не найден',
      });
    } else {
      checks.push({
        id: 'passport.gsd',
        status: 'ok',
        detail: `gsd_version: ${v}, .planning/ на месте`,
      });
    }
  } else if (v === 'v2') {
    checks.push(
      fs.existsSync(gsd)
        ? { id: 'passport.gsd', status: 'ok', detail: 'gsd_version: v2, .gsd/ на месте' }
        : {
            id: 'passport.gsd',
            status: 'fail',
            detail: 'passport gsd_version: v2, но .gsd/ не найдена',
          },
    );
  } else if (v === 'none') {
    checks.push({
      id: 'passport.gsd',
      status: 'ok',
      detail: 'gsd_version: none (GSD-папок не требуется)',
    });
  } else {
    checks.push({
      id: 'passport.gsd',
      status: 'warn',
      detail: `неизвестное gsd_version: ${v}`,
    });
  }

  return checks;
}

// Прогоняет все проверки. Никогда не кидает: сбои отражаются как checks со status fail/warn.
// Без projectRoot группы vault и passport помечаются na; config+junctions работают всегда.
export function runHealth(projectRoot?: string): HealthResult {
  const checks: HealthCheck[] = [];

  const cfg = configChecks();
  checks.push(...cfg.checks);

  if (cfg.repoRoot) {
    checks.push(...junctionChecks(cfg.repoRoot));
  } else {
    checks.push({
      id: 'junctions.skipped',
      status: 'warn',
      detail: 'проверка junction пропущена — repoRoot не определён (config.load failed)',
    });
  }

  if (!projectRoot) {
    checks.push({
      id: 'vault.skipped',
      status: 'na',
      detail: 'projectRoot не передан — vault не проверено',
    });
    checks.push({
      id: 'passport.skipped',
      status: 'na',
      detail: 'projectRoot не передан — passport не проверено',
    });
  } else {
    const passport = readPassport(projectRoot);
    const projectName =
      passport.exists && typeof passport.data?.name === 'string' && passport.data.name
        ? String(passport.data.name)
        : path.basename(projectRoot);
    checks.push(...vaultChecks(projectRoot, projectName, cfg.config));
    checks.push(...passportChecks(projectRoot, passport));
  }

  const summary = {
    ok: checks.filter((c) => c.status === 'ok').length,
    warn: checks.filter((c) => c.status === 'warn').length,
    fail: checks.filter((c) => c.status === 'fail').length,
    na: checks.filter((c) => c.status === 'na').length,
  };

  return { checks, summary };
}
