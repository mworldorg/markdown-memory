#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { scan } from './scan.js';
import { loadPatterns } from './patterns.js';
import { runHealth, type CheckStatus } from './health.js';

const patterns = loadPatterns();

const server = new McpServer({ name: 'mm-mcp', version: '0.1.0' });

server.registerTool(
  'mm_secret_scan',
  {
    title: 'Secret scanner',
    description:
      'Детерминированно сканирует текст на секреты по канону config/secret-patterns.json. ' +
      'Возвращает только классы (A — высокоточные, B — warn-only) и счётчики. ' +
      'НИКОГДА не возвращает сырое значение секрета.',
    inputSchema: { text: z.string() },
  },
  async ({ text }) => {
    const result = scan(text, patterns);
    const aFindings = result.findings.filter((f) => f.class === 'A');

    let summary: string;
    if (aFindings.length > 0 || result.classBCount > 0) {
      const parts: string[] = [];
      if (aFindings.length > 0) {
        parts.push(`🔒 Класс A: ${aFindings.map((f) => `${f.id}×${f.count}`).join(', ')}`);
      }
      if (result.classBCount > 0) {
        parts.push(`⚠️ Класс B (warn): ${result.classBCount}`);
      }
      summary = parts.join('; ');
    } else {
      summary = '🔒 секретов не найдено';
    }

    return {
      content: [{ type: 'text', text: summary }],
      structuredContent: result as unknown as Record<string, unknown>,
    };
  },
);

server.registerTool(
  'mm_health',
  {
    title: 'mm system health',
    description:
      'Детерминированный read-only движок проверок здоровья mm-системы: config + junction-ссылки всегда; ' +
      'vault-git + passport/gsd — если передан projectRoot. ' +
      'Ничего не чинит и не пишет — возвращает только факты. Суждение и авто-фиксы — в скилле mm-doctor.',
    inputSchema: { projectRoot: z.string().optional() }, // для групп vault-git и passport/gsd
  },
  async ({ projectRoot }) => {
    const result = runHealth(projectRoot);
    const icon = (s: CheckStatus): string =>
      s === 'ok' ? '✅' : s === 'warn' ? '⚠️' : s === 'na' ? '➖' : '❌';
    const lines = result.checks.map((c) => `${icon(c.status)} ${c.id}: ${c.detail}`);
    lines.push(
      `— итог: ✅ ${result.summary.ok} · ⚠️ ${result.summary.warn} · ❌ ${result.summary.fail} · ➖ ${result.summary.na}`,
    );
    return {
      content: [{ type: 'text', text: lines.join('\n') }],
      structuredContent: result as unknown as Record<string, unknown>,
    };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
