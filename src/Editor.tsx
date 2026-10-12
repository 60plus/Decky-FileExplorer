import { DialogButton, DropdownItem, Focusable, GamepadButton, GamepadEvent, ModalRoot, findModuleExport, getFocusNavController } from '@decky/ui';
import { ComponentType, RefObject, TextareaHTMLAttributes, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { api, message, TextFile } from './api';
import { useAppearance, useModalStyle } from './appearance';
import { ConfirmDialog, ErrorText, openDialog } from './dialogs';
import { Cursor, lineOffset, moveCursor, position, selectedText } from './editorText';
import { Glyph } from './Glyph';
import { css } from './style';
import { useKeyboardSpace } from './useKeyboardSpace';
import { preserveBackgroundScroll } from './backgroundScroll';

// Steam's own multiline input supplies keyboard and controller integration.
type KeyboardHandle = { TakeFocusAndShowKeyboard: () => void; HideVirtualKeyboard: () => void };
const NativeTextArea = findModuleExport(value => value?.prototype?.InternalOnInput &&
  value.prototype.GetMaxHeight && value.prototype.OnPaste) as ComponentType<TextareaHTMLAttributes<HTMLTextAreaElement> & { refKeyboardHandle?: RefObject<KeyboardHandle>; noFocusRing?: boolean }> | undefined;
type Snapshot = { text: string; cursor: Cursor };
const stop = (event: Event) => { event.preventDefault(); event.stopPropagation(); };

export function Editor({ location, saved, closeModal }: { location: string; saved: () => void; closeModal?: () => void }) {
  const [file, setFile] = useState<TextFile | null>(null), [text, setText] = useState('');
  const [cursor, setCursor] = useState<Cursor>({ anchor: 0, head: 0 });
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [editing, setEditing] = useState(false);
  const [encoding, setEncoding] = useState('auto'), [notice, setNotice] = useState(''), [scroll, setScroll] = useState(0);
  const root = useRef<HTMLDivElement>(null), history = useRef<Snapshot[]>([]), selecting = useRef(false);
  const editStarted = useRef(false), pendingCursor = useRef<Cursor | null>(null);
  const keyboardHandle = useRef<KeyboardHandle>(null);
  const keyboardWasShown = useRef(false);
  const releaseBackgroundScroll = useRef<(() => void) | null>(null);
  const region = useRef<'text' | 'toolbar'>('text');
  const restoringFocus = useRef(false);
  const [toolbarFocused, setToolbarFocused] = useState(false);
  const [toolbarHidden, setToolbarHidden] = useState(false);
  const live = useRef({ text, cursor }); live.current = { text, cursor };
  const keyboard = useKeyboardSpace(root), appearance = useAppearance();
  useModalStyle(root, appearance);
  const lines = text.split('\n'), selected = position(text, cursor.head).row, dirty = !!file && text !== file.text;
  const TextArea = NativeTextArea || 'textarea';
  const input = () => root.current?.querySelector<HTMLTextAreaElement>('textarea');

  function takeFocus(element: HTMLElement | null | undefined) {
    const find = (node: any): any => {
      if (!node) return;
      if (node.Element === element) return node;
      for (const child of node.GetChildren?.() || []) { const result = find(child); if (result) return result; }
    };
    const node = find(getFocusNavController()?.GetActiveNavTree?.()?.Root);
    if (node) node.BTakeFocus(); else element?.focus();
  }
  function focusLine(row: number) {
    window.setTimeout(() => {
      if (region.current !== 'text') return;
      const element = root.current?.querySelector<HTMLElement>(`[data-line="${row}"]`);
      takeFocus(element); element?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      restoringFocus.current = false;
    }, 30);
  }
  function focusToolbar() {
    setToolbarHidden(false);
    restoringFocus.current = true; region.current = 'toolbar'; setToolbarFocused(true); selecting.current = false;
    if (editing) { keyboardHandle.current?.HideVirtualKeyboard(); setEditing(false); }
    window.setTimeout(() => { takeFocus(root.current?.querySelector<HTMLElement>('.fe-toolbar button:not(:disabled)')); restoringFocus.current = false; }, 30);
  }
  function focusText() { restoringFocus.current = true; region.current = 'text'; setToolbarFocused(false); focusLine(selected); }
  function toggleToolbar() {
    setToolbarHidden(hidden => !hidden);
    if (!toolbarHidden && region.current === 'toolbar') focusText();
  }
  useEffect(() => {
    const doc = root.current?.ownerDocument;
    const shortcut = (event: Event) => {
      const e = event as GamepadEvent;
      if (![GamepadButton.LSTICK_CLICK, GamepadButton.RSTICK_CLICK].includes(e.detail?.button) || e.detail.is_repeat) return;
      if (!root.current?.contains(e.target as Node) && !(editing && keyboard.visible)) return;
      stop(e);
      if (e.detail.button === GamepadButton.LSTICK_CLICK) { toggleToolbar(); return; }
      if (region.current === 'toolbar') focusText(); else focusToolbar();
    };
    // Capture also reaches the stick shortcuts while Steam's keyboard owns focus.
    doc?.addEventListener('vgp_onbuttondown', shortcut, true);
    return () => doc?.removeEventListener('vgp_onbuttondown', shortcut, true);
  });
  function keepCaretVisible() {
    const area = input(); if (!area) return;
    const styles = area.ownerDocument.defaultView!.getComputedStyle(area);
    const height = parseFloat(styles.lineHeight), row = position(area.value, area.selectionDirection === 'backward' ? area.selectionStart : area.selectionEnd).row;
    const top = row * height + parseFloat(styles.paddingTop);
    // A full-line margin on both sides can push the caret out of a short
    // viewport above Steam's keyboard, especially with the largest text size.
    const margin = Math.min(height, Math.max(0, (area.clientHeight - height) / 2));
    if (top < area.scrollTop + margin) area.scrollTop = Math.max(0, top - margin);
    else if (top + height > area.scrollTop + area.clientHeight - margin) area.scrollTop = top + height - area.clientHeight + margin;
    setScroll(area.scrollTop);
  }
  async function load(codec = encoding) {
    setBusy(true); setError('');
    try {
      const result = await api<TextFile>('read_text', { location, encoding: codec === 'auto' ? null : codec });
      setFile(result); setText(result.text); setCursor({ anchor: 0, head: 0 }); history.current = []; focusLine(0);
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, []);
  useEffect(() => () => releaseBackgroundScroll.current?.(), []);
  useEffect(() => {
    if (!editing) root.current?.querySelector(`[data-line="${selected}"]`)?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    else keepCaretVisible();
  }, [selected, editing, keyboard.visible, toolbarHidden]);
  useEffect(() => {
    const area = input(); if (!area) return;
    // The keyboard changes the surface directly on animation frames. Keep the
    // cursor visible as the textarea shrinks without rendering its document for
    // every new panel height.
    const observer = new ResizeObserver(keepCaretVisible);
    observer.observe(area);
    return () => observer.disconnect();
  }, [editing]);
  useLayoutEffect(() => {
    const area = input(), next = pendingCursor.current;
    if (!area || !next) return;
    area.setSelectionRange(Math.min(next.anchor, next.head), Math.max(next.anchor, next.head), next.head < next.anchor ? 'backward' : 'forward');
    pendingCursor.current = null; keepCaretVisible();
  });
  useEffect(() => {
    if (!editing) return;
    const initial = { ...live.current.cursor };
    const timer = window.setTimeout(() => {
      takeFocus(input()); input()?.focus(); keyboardHandle.current?.TakeFocusAndShowKeyboard();
      const area = input();
      if (area) { area.setSelectionRange(Math.min(initial.anchor, initial.head), Math.max(initial.anchor, initial.head), initial.head < initial.anchor ? 'backward' : 'forward'); readSelection(area); }
      keepCaretVisible();
    }, 50);
    return () => window.clearTimeout(timer);
  }, [editing]);
  useEffect(() => {
    if (editing && keyboard.visible) keyboardWasShown.current = true;
    else if (editing && keyboardWasShown.current) { keyboardWasShown.current = false; finishEditing(); }
    if (!editing) keyboardWasShown.current = false;
  }, [editing, keyboard.visible]);

  function pushHistory() {
    history.current.push({ text: live.current.text, cursor: { ...live.current.cursor } });
    if (history.current.length > 30) history.current.shift();
  }
  function update(next: string, nextCursor: Cursor) {
    if (next !== text) pushHistory();
    setText(next); setCursor(nextCursor); setNotice('');
    if (editing) pendingCursor.current = nextCursor; else focusLine(position(next, nextCursor.head).row);
  }
  function edit(row = selected) {
    if (!file || busy) return;
    region.current = 'text'; setToolbarFocused(false);
    if (row !== selected) { const offset = lineOffset(text, row); pendingCursor.current = { anchor: offset, head: offset }; setCursor(pendingCursor.current); }
    else pendingCursor.current = cursor;
    if (root.current && !releaseBackgroundScroll.current) releaseBackgroundScroll.current = preserveBackgroundScroll(root.current);
    editStarted.current = false; selecting.current = false; setEditing(true); setNotice('');
  }
  function finishEditing() { restoringFocus.current = true; keyboardHandle.current?.HideVirtualKeyboard(); setEditing(false); selecting.current = false; if (region.current === 'toolbar') focusToolbar(); else focusLine(selected); }
  function changed(area: HTMLTextAreaElement) {
    const value = area.value;
    if (value.length > 512 * 1024 || value.split('\n').length > 10000) {
      setError('The editor supports up to 512 KiB and 10,000 lines. This edit was not applied.');
      area.value = text; return;
    }
    if (value !== text && !editStarted.current) { pushHistory(); editStarted.current = true; }
    setText(value); setNotice(''); readSelection(area);
    window.setTimeout(keepCaretVisible, 0);
  }
  function readSelection(area: HTMLTextAreaElement) {
    const backwards = area.selectionDirection === 'backward';
    const next = { anchor: backwards ? area.selectionEnd : area.selectionStart, head: backwards ? area.selectionStart : area.selectionEnd };
    setCursor(old => old.anchor === next.anchor && old.head === next.head ? old : next);
  }
  function insert() {
    if (!file || busy) return;
    const indent = lines[selected]?.match(/^[\t ]*/)?.[0] || '', next = [...lines];
    next.splice(selected + 1, 0, indent); const value = next.join('\n'), offset = lineOffset(value, selected + 1, indent.length);
    update(value, { anchor: offset, head: offset });
  }
  function undo() {
    if (busy) return;
    const old = history.current.pop(); if (!old) return;
    setText(old.text); setCursor(old.cursor); setNotice('Undone.'); editStarted.current = false;
    if (editing) pendingCursor.current = old.cursor; else focusLine(position(old.text, old.cursor.head).row);
  }
  function copy() {
    const doc = root.current?.ownerDocument; if (!doc || !file) return;
    const value = selectedText(text, cursor), focus = doc.activeElement as HTMLElement;
    // Use the same native clipboard command as Steam's TextField copy action.
    const temporary = doc.createElement('textarea'); temporary.value = value; temporary.readOnly = true;
    temporary.style.cssText = 'position:fixed;left:-10000px;top:0'; doc.body.appendChild(temporary);
    temporary.select();
    try { if (!doc.execCommand('copy')) throw new Error('Copy is unavailable. Select text and use Ctrl+C.'); setNotice(cursor.head === cursor.anchor ? 'Line copied. Use Paste on the Steam keyboard.' : 'Selection copied. Use Paste on the Steam keyboard.'); }
    catch (e) { setError(message(e)); } finally { temporary.remove(); focus?.focus(); }
  }
  function direction(event: GamepadEvent, row: number) {
    if (busy || editing) return;
    const button = event.detail.button;
    if (![9, 10, 11, 12].includes(button)) return;
    if (button === 9 && row === 0 && !selecting.current) { stop(event); focusToolbar(); return; }
    stop(event);
    const next = moveCursor(live.current.text, live.current.cursor, button, selecting.current);
    live.current.cursor = next; setCursor(next); setNotice(''); focusLine(position(text, next.head).row);
  }
  function leave() {
    if (editing) { finishEditing(); return; }
    if (dirty) openDialog(<ConfirmDialog title="Discard unsaved changes?" description="The original file has not been changed." action="Discard" submit={async () => closeModal?.()} />);
    else closeModal?.();
  }
  async function save() {
    if (!file || busy || !dirty) return;
    setBusy(true); setError('');
    try {
      const result = await api<TextFile>('save_text', { location, text, revision: file.revision, encoding: file.encoding });
      setFile(result); history.current = []; editStarted.current = false; setNotice('Saved. Original formatting and encoding kept.'); saved();
      if (!editing) focusLine(selected);
    } catch (e) {
      const value = message(e); setError(value);
      const match = value.match(/at line (\d+)/);
      if (match) { const offset = lineOffset(text, Number(match[1]) - 1); setCursor({ anchor: offset, head: offset }); if (editing) pendingCursor.current = { anchor: offset, head: offset }; else focusLine(Number(match[1]) - 1); }
    } finally { setBusy(false); }
  }
  function renderedLine(line: string, row: number, offset: number) {
    const start = Math.max(0, Math.min(cursor.anchor, cursor.head) - offset), end = Math.min(line.length, Math.max(cursor.anchor, cursor.head) - offset);
    const caret = selected === row ? cursor.head - offset : -1;
    const points = [...new Set([0, line.length, ...(end > start ? [start, end] : []), ...(caret >= 0 ? [caret] : [])])].sort((a, b) => a - b);
    return points.map((point, i) => <span key={point}>{point === caret && <i className="fe-caret" />}{i < points.length - 1 && <span className={point >= start && point < end ? 'fe-selection' : undefined}>{line.slice(point, points[i + 1])}</span>}</span>);
  }
  let offset = 0;
  return <ModalRoot className="fe-modal fe-editor-modal" style={appearance} bAllowFullSize bHideCloseIcon onCancel={leave} closeModal={leave}><style>{css}</style>
    <Focusable className="fe-app fe-editor" ref={root} flow-children="column"
      onCancelButton={e => { stop(e); leave(); }}
      onSecondaryButton={e => { if (!keyboard.visible) { stop(e); insert(); } }}
      onOptionsButton={e => { if (!keyboard.visible) { stop(e); void save(); } }}
      onMenuButton={e => { if (!keyboard.visible) { stop(e); undo(); } }}
      onButtonDown={e => {
        if (keyboard.visible) return;
        if (e.detail.button === GamepadButton.TRIGGER_RIGHT && !editing) { stop(e); selecting.current = true; }
        if (e.detail.button === GamepadButton.SELECT) { stop(e); copy(); }
      }}
      onButtonUp={e => { if (e.detail.button === GamepadButton.TRIGGER_RIGHT) { selecting.current = false; stop(e); } }}
      onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); e.stopPropagation(); undo(); } }}
      actionDescriptionMap={{ [GamepadButton.START]: 'Undo', [GamepadButton.SELECT]: 'Copy text' }}
      onOKActionDescription={toolbarFocused ? 'Use button' : editing ? 'Keyboard' : 'Edit text'} onSecondaryActionDescription="Insert line" onOptionsActionDescription="Save file">
      <header className="fe-header"><div className="fe-editor-title"><strong>{file?.name || location.split('/').pop()}</strong><div className="fe-subtitle">{file ? `${file.encoding}${file.bom ? ' + BOM' : ''} • ${file.newline} • ${lines.length} lines${dirty ? ' • Unsaved changes' : ''}` : 'Text editor'}</div></div><DialogButton className="fe-btn fe-toolbar-toggle" onClick={toggleToolbar}>{toolbarHidden ? 'Show toolbar' : 'Hide toolbar'}</DialogButton></header>
      {!toolbarHidden && <Focusable className="fe-toolbar" flow-children="row" onGamepadFocus={() => { region.current = 'toolbar'; setToolbarFocused(true); }}
        onGamepadDirection={e => { if (e.detail.button === GamepadButton.DIR_DOWN) { stop(e); focusText(); } }}>
        <DialogButton className="fe-btn" disabled={!file || busy} onClick={() => editing ? finishEditing() : edit()}>{editing ? 'Done editing' : 'Edit text'}</DialogButton>
        <DialogButton className="fe-btn" disabled={!file || busy} onClick={insert}>Insert line</DialogButton>
        <DialogButton className="fe-btn" disabled={!file || busy} onClick={() => { const value = (lines.length > 1 ? lines.filter((_, i) => i !== selected) : ['']).join('\n'), p = lineOffset(value, selected); update(value, { anchor: p, head: p }); }}>Delete line</DialogButton>
        <DialogButton className="fe-btn" disabled={!file || busy} onClick={copy}>Copy text</DialogButton>
        <DialogButton className="fe-btn" disabled={!history.current.length || busy} onClick={undo}>Undo</DialogButton>
        <DialogButton className="fe-btn" disabled={!dirty || busy} onClick={() => void save()}>Save file</DialogButton>
        <DialogButton className="fe-btn" onClick={leave}>{editing ? 'Back' : 'Close'}</DialogButton>
      </Focusable>}
      {!file && <div className="fe-encoding"><DropdownItem label="File encoding" selectedOption={encoding} rgOptions={['auto', 'utf-8', 'utf-16-le', 'utf-16-be', 'cp1250', 'cp1252', 'latin-1'].map(data => ({ data, label: data === 'auto' ? 'Auto (UTF-8 / BOM)' : data }))} onChange={o => { setEncoding(o.data); void load(o.data); }} /></div>}
      <ErrorText text={error} />
      {editing ? <div className="fe-text-input">
        <div className="fe-editor-gutter" aria-hidden="true"><div style={{ transform: `translateY(${-scroll}px)` }}>{lines.map((_, row) => <div key={row} className={selected === row ? 'active' : ''}>{row + 1}</div>)}</div></div>
        <TextArea {...(NativeTextArea ? { refKeyboardHandle: keyboardHandle, noFocusRing: true } : {})} className="fe-editor-textarea" aria-label="File contents" value={text} wrap="off" spellCheck={false} autoCapitalize="off" autoCorrect="off" disabled={busy}
          onChange={e => changed(e.currentTarget)} onSelect={e => readSelection(e.currentTarget)} onScroll={e => setScroll(e.currentTarget.scrollTop)}
          onKeyUp={() => keepCaretVisible()} onClick={() => keepCaretVisible()} />
      </div> : <Focusable className="fe-code" flow-children="column" onGamepadFocus={() => { if (!restoringFocus.current) { region.current = 'text'; setToolbarFocused(false); } }}>
        {lines.map((line, row) => { const start = offset; offset += line.length + 1; return <Focusable noFocusRing key={row} data-line={row} preferredFocus={row === 0} className={`fe-code-line ${selected === row ? 'active' : ''}`}
          onGamepadDirection={e => direction(e, row)}
          onGamepadFocus={() => { if (!restoringFocus.current && position(live.current.text, live.current.cursor.head).row !== row) { const head = lineOffset(text, row); setCursor({ anchor: head, head }); } }}
          onClick={() => { region.current = 'text'; setToolbarFocused(false); const head = lineOffset(text, row); setCursor({ anchor: head, head }); }} onDoubleClick={() => edit(row)}
          onActivate={e => { stop(e); edit(row); }}><span className="fe-line-number">{row + 1}</span><code>{renderedLine(line, row, start)}</code></Focusable>; })}
      </Focusable>}
      <div className="fe-status">{busy ? 'Working…' : notice || `Line ${selected + 1}, column ${position(text, cursor.head).column + 1}${cursor.anchor !== cursor.head ? ` • ${Math.abs(cursor.head - cursor.anchor)} characters selected` : ''} • ${editing ? 'Steam keyboard: Paste inserts clipboard text at the cursor' : 'Directions move the cursor • Copy uses the selection or current line'}`}</div>
      <div className="fe-legend"><Glyph button={GamepadButton.LSTICK_CLICK} label={toolbarHidden ? 'Show toolbar' : 'Hide toolbar'} />{keyboard.visible ? <><span>Steam keyboard: Paste</span><span>Arrow keys: move cursor</span><Glyph button={GamepadButton.RSTICK_CLICK} label="Toolbar" /></> : <><Glyph button={GamepadButton.OK} label={toolbarFocused ? 'Use button' : editing ? 'Keyboard' : 'Edit text'} /><Glyph button={GamepadButton.CANCEL} label="Back" /><Glyph button={GamepadButton.SECONDARY} label="Insert line" /><Glyph button={GamepadButton.OPTIONS} label="Save" /><Glyph button={GamepadButton.START} label="Undo" /><Glyph button={GamepadButton.SELECT} label="Copy" /><Glyph button={GamepadButton.RSTICK_CLICK} label={toolbarFocused ? 'Text' : 'Toolbar'} />{!editing && <Glyph button={GamepadButton.TRIGGER_RIGHT} label="+ directions: select" />}</>}</div>
    </Focusable>
  </ModalRoot>;
}
