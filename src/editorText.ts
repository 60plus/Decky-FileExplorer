export type Cursor = { anchor: number; head: number };
export const clamp = (text: string, offset: number) => Math.max(0, Math.min(text.length, offset));
export function position(text: string, offset: number) {
  offset = clamp(text, offset);
  const before = text.slice(0, offset);
  return { row: before.split('\n').length - 1, column: offset - before.lastIndexOf('\n') - 1 };
}
export function lineOffset(text: string, row: number, column = 0) {
  const lines = text.split('\n');
  row = Math.max(0, Math.min(lines.length - 1, row));
  return lines.slice(0, row).reduce((n, line) => n + line.length + 1, 0) + Math.min(column, lines[row].length);
}
export function moveCursor(text: string, cursor: Cursor, direction: number, extend: boolean): Cursor {
  let head = clamp(text, cursor.head);
  if (direction === 11) {
    head -= head > 1 && /[\uDC00-\uDFFF]/.test(text[head - 1]) && /[\uD800-\uDBFF]/.test(text[head - 2]) ? 2 : 1;
  } else if (direction === 12) {
    head += (text.codePointAt(head) || 0) > 0xffff ? 2 : 1;
  } else {
    const p = position(text, head), row = p.row + (direction === 9 ? -1 : 1);
    if (row >= 0 && row < text.split('\n').length) head = lineOffset(text, row, p.column);
  }
  head = clamp(text, head);
  // A vertical move must not put the caret inside a surrogate pair.
  if (head > 0 && /[\uDC00-\uDFFF]/.test(text[head] || '') && /[\uD800-\uDBFF]/.test(text[head - 1])) head--;
  return { anchor: extend ? cursor.anchor : head, head };
}
export function selectedText(text: string, cursor: Cursor) {
  if (cursor.anchor !== cursor.head) return text.slice(Math.min(cursor.anchor, cursor.head), Math.max(cursor.anchor, cursor.head));
  return text.split('\n')[position(text, cursor.head).row];
}
