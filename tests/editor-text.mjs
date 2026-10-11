import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { test } from 'node:test';
const js = ts.transpileModule(readFileSync(new URL('../src/editorText.ts', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText;
const { position, lineOffset, moveCursor, selectedText } = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));

test('selection preserves tabs, blank lines and backwards ranges', () => {
  const text = '\talpha=1  \n\nżółw=2\n';
  const range = { anchor: text.length - 1, head: 0 };
  assert.equal(selectedText(text, range), text.slice(0, -1));
  assert.equal(selectedText(text, { anchor: 2, head: 2 }), '\talpha=1  ');
  assert.equal(position(text, text.length).row, 3);
  assert.equal(lineOffset(text, 2, 200), text.length - 1);
});
test('controller selection crosses lines and collapses without RT', () => {
  const text = 'one\n  two\n';
  let cursor = { anchor: 1, head: 1 };
  cursor = moveCursor(text, cursor, 10, true);
  assert.deepEqual(cursor, { anchor: 1, head: 5 });
  assert.equal(selectedText(text, cursor), 'ne\n ');
  assert.deepEqual(moveCursor(text, cursor, 12, false), { anchor: 6, head: 6 });
  assert.deepEqual(moveCursor(text, { anchor: 0, head: 0 }, 11, true), { anchor: 0, head: 0 });
});
test('moving across emoji never splits a surrogate pair', () => {
  const text = 'a😀z\nxy😀';
  assert.equal(moveCursor(text, { anchor: 1, head: 1 }, 12, false).head, 3);
  assert.equal(moveCursor(text, { anchor: 3, head: 3 }, 11, false).head, 1);
  assert.equal(moveCursor(text, { anchor: 3, head: 3 }, 10, false).head, 7);
});
