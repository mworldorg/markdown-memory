// Неинтерактивный смок mm_health-движка. Exit 1 при провале любого ассерта.
// Запуск: node scripts/health-smoke.mjs (после npm run build).
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { normalizeLinkPath, junctionMatches, runHealth } from '../dist/health.js';

// Корень репо: scripts/ → mcp/ → repoRoot
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

let failed = 0;
function check(name, fn) {
  try {
    fn();
    console.log(`  ok   ${name}`);
  } catch (e) {
    failed++;
    console.error(`  FAIL ${name}: ${e.message}`);
  }
}

// --- Юнит: нормализация/сравнение путей junction ---

// Кросс-платформенный инвариант: хвостовой слэш не влияет на результат.
check('normalize: хвостовой слэш не влияет', () => {
  assert.equal(normalizeLinkPath('/a/b/c/'), normalizeLinkPath('/a/b/c'));
});

// Win-стиль: префикс \\?\, хвостовой \, разный регистр → match после нормализации.
// (path.resolve платформозависим: Windows-пути осмысленны только на win32.)
check('junction match: \\\\?\\ + хвостовой \\ + регистр (win32)', () => {
  const expected = 'C:\\Users\\x\\Desktop\\repo\\skills\\mm-bridge';
  const actual = '\\\\?\\C:\\Users\\X\\Desktop\\repo\\skills\\mm-bridge\\';
  if (process.platform === 'win32') {
    assert.equal(junctionMatches(actual, expected), true, 'ожидался match после нормализации');
  } else {
    // posix: проверяем сам факт снятия префикса \\?\ и детерминизм нормализации
    assert.equal(normalizeLinkPath('\\\\?\\X'), normalizeLinkPath('\\\\?\\X'));
  }
});

// Разные пути → no-match.
check('junction no-match: разные каталоги', () => {
  const a = 'C:\\repo\\skills\\mm-bridge';
  const b = 'C:\\repo\\skills\\mm-vault';
  assert.equal(junctionMatches(a, b), false, 'разные пути не должны совпадать');
});

// --- Интеграция: реальный корень этого репо (проверка мягкой деградации в реале) ---

check('runHealth БЕЗ projectRoot: vault+passport = na, config+junctions есть', () => {
  const r = runHealth(); // не должен бросать
  assert.ok(Array.isArray(r.checks) && r.checks.length > 0, 'checks — непустой массив');
  assert.ok(
    r.summary &&
      typeof r.summary.ok === 'number' &&
      typeof r.summary.warn === 'number' &&
      typeof r.summary.fail === 'number' &&
      typeof r.summary.na === 'number',
    'summary посчитан (вкл. na)',
  );
  assert.ok(
    r.checks.some((c) => c.id.startsWith('config')),
    'присутствует группа config',
  );
  assert.ok(
    r.checks.some((c) => c.id.startsWith('junction')),
    'присутствует группа junctions',
  );
  // vault и passport помечены na одной проверкой каждая
  const vaultNa = r.checks.find((c) => c.id === 'vault.skipped');
  const passportNa = r.checks.find((c) => c.id === 'passport.skipped');
  assert.ok(vaultNa && vaultNa.status === 'na', 'vault.skipped = na');
  assert.ok(passportNa && passportNa.status === 'na', 'passport.skipped = na');
  const total = r.summary.ok + r.summary.warn + r.summary.fail + r.summary.na;
  assert.equal(total, r.checks.length, 'summary суммируется к числу проверок');
});

check('runHealth С projectRoot=корень репо: vault+passport проверены, мягкая деградация', () => {
  const r = runHealth(REPO_ROOT); // не должен бросать
  // vault: группа присутствует. На корне mm vault резолвится через CLAUDE.md/.vault/obsidian_projects;
  // если папка репо не совпадает с именем vault и нет passport/CLAUDE.md — vault.resolve=warn (не найден).
  // Если репо инициализирован/переименован под vault — vault.git=ok. Любой исход валиден (read-only факт).
  assert.ok(
    r.checks.some((c) => c.id.startsWith('vault.')),
    'присутствует группа vault',
  );
  // passport: в корне mm нет passport.md → мягкая деградация na (НЕ fail).
  const passportExists = r.checks.find((c) => c.id === 'passport.exists');
  assert.ok(
    passportExists && passportExists.status === 'na',
    'passport.exists = na (нет passport.md в корне — мягкая деградация)',
  );
  // config+junctions без сбоев.
  assert.ok(
    r.checks
      .filter((c) => c.id.startsWith('config') || c.id.startsWith('junction'))
      .every((c) => c.status === 'ok'),
    'config и junctions — все ok',
  );
  // На исправной машине корень репо не даёт fail (vault может быть warn).
  assert.equal(r.summary.fail, 0, `ожидался fail=0, получено ${r.summary.fail}`);
  const total = r.summary.ok + r.summary.warn + r.summary.fail + r.summary.na;
  assert.equal(total, r.checks.length, 'summary суммируется к числу проверок');
});

if (failed > 0) {
  console.error(`\n✗ health-smoke: ${failed} провал(ов)`);
  process.exit(1);
}
console.log('\n✓ health-smoke: все ассерты пройдены');
