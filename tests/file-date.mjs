import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { test } from 'node:test';
const source = readFileSync(new URL('../src/fileDate.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText;
const { fileDate } = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));

test('filesystem seconds become a calendar date and time, not milliseconds', () => {
  process.env.TZ = 'Etc/UTC';
  const value = fileDate(Date.parse('2026-10-15T04:12:00Z') / 1000);
  assert.equal(value.date, '2026-10-15');
  assert.equal(value.time, '04:12');
  assert.equal(value.iso, '2026-10-15T04:12:00.000Z');
});
test('missing archive timestamps and invalid values do not produce fake dates', () => {
  for (const value of [0, NaN, Infinity, 9e15]) {
    assert.equal(fileDate(value).date, '—');
    assert.equal(fileDate(value).iso, undefined);
  }
});
test('local dates cross midnight correctly and follow daylight saving time', () => {
  process.env.TZ = 'Europe/Warsaw';
  assert.equal(fileDate(Date.parse('2026-10-14T23:30:00Z') / 1000).date, '2026-10-15');
  assert.equal(fileDate(Date.parse('2026-10-14T23:30:00Z') / 1000).time, '01:30');
  assert.equal(fileDate(Date.parse('2026-12-14T23:30:00Z') / 1000).time, '00:30');
});
