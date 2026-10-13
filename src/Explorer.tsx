import { DialogButton, Focusable, GamepadButton, GamepadEvent, ModalRoot, getFocusNavController } from '@decky/ui';
import { useEffect, useRef, useState } from 'react';
import { api, bytes, Entry, Job, Listing, message, Place, State } from './api';
import { ConfirmDialog, EmptyTrashDialog, ExtractionLimitDialog, MenuDialog, openDialog, PlacesDialog, PreviewDialog, RecoveryDialog, TextDialog } from './dialogs';
import { Editor } from './Editor';
import { ImageViewer } from './ImageViewer';
import { MediaPlayer } from './MediaPlayer';
import { isArchive, openKind } from './fileTypes';
import { explorerClosed, explorerOpened } from './activity';
import { FileIcon, Icon } from './Icon';
import { css } from './style';
import { appearanceStyle, useModalStyle } from './appearance';
import { Legend } from './Legend';
import { version } from '../package.json';

type Pane = { data: Listing | null; loading: boolean; error: string; selected: Set<string>; focused: string };
const empty = (): Pane => ({ data: null, loading: true, error: '', selected: new Set(), focused: '' });
function consume(e: Event) { e.preventDefault(); e.stopPropagation(); }
let shownLimitJob: string | undefined;
let shownRecoveryJob: string | undefined;

export function Explorer({ closeModal, openSettings }: { closeModal?: () => void; openSettings: () => void }) {
  const [panes, setPanes] = useState<[Pane, Pane]>([empty(), empty()]);
  const [active, setActive] = useState(0), [job, setJob] = useState<Job | null>(null), [error, setError] = useState('');
  const [state, setState] = useState<State | null>(null), [busyAction, setBusyAction] = useState(false);
  const [recovery, setRecovery] = useState<Job | null>(null);
  const root = useRef<HTMLDivElement>(null), generations = useRef([0, 0]), alive = useRef(true);
  useModalStyle(root, appearanceStyle(state?.settings));
  const snapshot = useRef({ panes, active, state, job }); snapshot.current = { panes, active, state, job };
  const running = job?.status === 'running';
  const focusedEntry = panes[active].data?.entries.find(e => e.path === panes[active].focused);
  const canOpen = !focusedEntry || !!openKind(focusedEntry);

  function patch(index: number, update: Partial<Pane> | ((p: Pane) => Partial<Pane>)) {
    setPanes(prev => prev.map((p, i) => i === index ? { ...p, ...(typeof update === 'function' ? update(p) : update) } : p) as [Pane, Pane]);
  }
  async function load(index: number, path: string, remember = true) {
    const generation = ++generations.current[index];
    const restoreFocus = index === snapshot.current.active;
    patch(index, { loading: true, error: '' });
    try {
      const data = await api<Listing>('list', { location: path });
      if (!alive.current || generation !== generations.current[index]) return;
      patch(index, { data, loading: false, selected: new Set(), focused: '..' });
      if (restoreFocus) focusPane(index);
      if (remember && snapshot.current.state?.settings.remember_paths) {
        void api('settings', { changes: { [index ? 'right' : 'left']: path } }).catch(() => {});
      }
    } catch (e) { if (alive.current && generation === generations.current[index]) patch(index, { loading: false, error: message(e) }); }
  }
  const refresh = () => snapshot.current.panes.forEach((p, i) => { if (p.data) void load(i, p.data.path, false); });
  useEffect(() => {
    explorerOpened();
    alive.current = true;
    void api<State>('state').then(s => { if (!alive.current) return; setState(s); setJob(s.job?.status === 'running' ? s.job : null); if (s.job?.recoverable && ['error', 'cancelled'].includes(s.job.status)) setRecovery(s.job); void load(0, s.settings.left); void load(1, s.settings.right); }).catch(e => setError(message(e)));
    return () => { alive.current = false; explorerClosed(); };
  }, []);
  useEffect(() => {
    if (!running) return;
    let pending = false;
    const id = window.setInterval(async () => {
      if (pending) return; pending = true;
      try { const next = await api<Job>('job'); if (alive.current) { setJob(next); if (next.status !== 'running') refresh(); } }
      catch (e) { if (alive.current) setError(message(e)); } finally { pending = false; }
    }, 500);
    return () => window.clearInterval(id);
  }, [running]);
  useEffect(() => {
    if (!job || job.status === 'running') return;
    const finishedId = job.id;
    const timer = window.setTimeout(() => setJob(current => current?.id === finishedId && current.status !== 'running' ? null : current), 6000);
    return () => window.clearTimeout(timer);
  }, [job?.id, job?.status]);
  useEffect(() => {
    if (!job?.recoverable || !['error', 'cancelled'].includes(job.status)) return;
    setRecovery(job);
    if (job.status === 'error' && shownRecoveryJob !== job.id) { shownRecoveryJob = job.id; showRecovery(job); }
  }, [job?.id, job?.status]);

  async function retry(job: Job, mode: string) {
    const next = await api<Job>('retry', { job_id: job.id, mode });
    setJob(next); setRecovery(null); setError('');
  }
  function restart(job: Job) {
    openDialog(<ConfirmDialog title="Start the copy again?" description="All selected items will be copied from the beginning into a new FileExplorer retry folder in the original destination. Existing files and previous partial copies will be kept." action="Start again" submit={() => retry(job, 'restart')} />);
  }
  function showRecovery(job: Job) {
    openDialog(<RecoveryDialog error={job.error} resume={() => retry(job, 'resume')} restart={() => restart(job)} />);
  }
  function cancelCopy() {
    if (!job || !running) return;
    const id = job.id;
    openDialog(<ConfirmDialog title="Cancel this operation?" description={job.recoverable ? 'The copy will stop. Completed files and partial data will be kept so you can resume from Options.' : 'The operation will stop. Completed items will be kept.'} action="Cancel operation" submit={async () => { await api('cancel', { job_id: id }); }} />);
  }
  useEffect(() => {
    if (job?.status !== 'error' || !job.error.includes('exceeds extraction size limit (') || shownLimitJob === job.id) return;
    shownLimitJob = job.id;
    openDialog(<ExtractionLimitDialog description={job.error} openSettings={() => { closeModal?.(); openSettings(); }} />);
  }, [job?.id, job?.status]);

  function focusPane(index: number, explicit = false) {
    setActive(index);
    window.setTimeout(() => {
      const node = root.current?.querySelector<HTMLElement>(`.fe-pane[data-pane="${index}"] .fe-row[data-current="true"]`) || root.current?.querySelector<HTMLElement>(`.fe-pane[data-pane="${index}"] .fe-row`);
      if (node) {
        if (explicit) {
          // Use the target window's native focus request. Steam can keep its
          // active navigation tree in a different CEF context from this modal.
          const owner = node.ownerDocument.defaultView;
          if (owner) node.dispatchEvent(new owner.CustomEvent('vgp_requestfocus', { bubbles: true, cancelable: true, detail: { button: 1, source: 0 } }));
          node.scrollIntoView({ block: 'nearest' });
          return;
        }
        const controller = getFocusNavController();
        const findNode = (n: any): any => {
          if (!n) return undefined;
          if (n.Element === node) return n;
          for (const child of n.GetChildren?.() || []) { const found = findNode(child); if (found) return found; }
          return undefined;
        };
        const tree = controller?.GetActiveNavTree?.()?.Root;
        const nav = findNode(tree);
        // A refresh after saving must not steal focus from an open editor/dialog.
        if (nav) nav.BTakeFocus(); else if (!tree) node.focus();
        node.scrollIntoView({ block: 'nearest' });
      }
    }, 0);
  }
  function sources(): string[] {
    const p = snapshot.current.panes[snapshot.current.active];
    return p.selected.size ? [...p.selected] : p.focused && p.focused !== '..' ? [p.focused] : [];
  }
  function toggle() {
    if (running) return;
    const p = panes[active];
    if (!p.focused || p.focused === '..') return;
    patch(active, prev => { const selected = new Set(prev.selected); selected.has(prev.focused) ? selected.delete(prev.focused) : selected.add(prev.focused); return { selected }; });
  }
  function back() {
    const p = panes[active];
    if (p.data && p.data.path !== p.data.parent) void load(active, p.data.parent);
    else closeModal?.();
  }
  async function start(action: string, chosen: string[], destination?: string) {
    const next = await api<Job>('start', { action, sources: chosen, destination });
    setJob(next); setRecovery(null); setError('');
  }
  function copy() {
    const chosen = sources(), dest = panes[1 - active].data?.path;
    if (!chosen.length || !dest || running) return;
    if (panes[1 - active].data?.archive) { setError('Choose a writable folder in the other panel. Archives are read-only.'); return; }
    const verb = panes[active].data?.archive ? 'Extract' : 'Copy';
    openDialog(<ConfirmDialog title={`${verb} ${chosen.length} item${chosen.length > 1 ? 's' : ''}?`} description={`From the ${active ? 'right' : 'left'} panel to:\n${displayPath(dest)}\n\nExisting files will not be overwritten.`} action={verb} submit={() => start('copy', chosen, dest)} />);
  }
  async function locations() {
    setBusyAction(true);
    try { const places = await api<Place[]>('locations'); const index = active; openDialog(<PlacesDialog places={places} choose={path => { void api<State>('state').then(setState); void load(index, path); }} />); }
    catch (e) { setError(message(e)); } finally { setBusyAction(false); }
  }
  function displayPath(path: string) {
    if (path.startsWith('archive://')) return panes.find(p => p.data?.path === path)?.data?.label || 'Archive';
    if (!path.startsWith('smb://')) return path;
    const match = path.match(/^smb:\/\/([^/]+)(.*)$/);
    const connection = state?.connections.find(c => c.id === match?.[1]);
    return connection ? `smb://${connection.host}/${connection.share}${decodeURIComponent(match![2])}` : path;
  }
  function options() {
    const chosen = sources(), current = panes[active].data?.entries.find(e => e.path === chosen[0]);
    const folder = panes[active].data?.path, dest = panes[1 - active].data?.path;
    const readOnly = !!panes[active].data?.archive, targetReadOnly = !!panes[1 - active].data?.archive;
    openDialog(<MenuDialog title={chosen.length > 1 ? `${chosen.length} items selected` : current?.name || 'Folder options'} actions={[
      ...(recovery ? [{ label: 'Resume interrupted copy…', disabled: running, run: () => showRecovery(recovery) }, { label: 'Start interrupted copy again…', disabled: running, run: () => restart(recovery) }] : []),
      { label: readOnly ? 'Extract selected to other panel' : 'Copy to other panel', run: copy, disabled: !chosen.length || running || targetReadOnly },
      { label: 'Extract whole archive to other panel', disabled: readOnly || targetReadOnly || !current || !isArchive(current.name) || chosen.length !== 1 || !dest || running, run: () => openDialog(<ConfirmDialog title="Extract archive?" description={`Create a new folder in:\n${displayPath(dest!)}\n\nZIP, RAR, 7z and TAR are supported. Links and unsafe paths are rejected.`} action="Extract" submit={() => start('extract', chosen, dest)} />) },
      { label: 'Rename', disabled: readOnly || chosen.length !== 1 || running, run: () => openDialog(<TextDialog title="Rename" initial={current?.name} submit={async name => { await api('rename', { location: chosen[0], name }); refresh(); }} />) },
      { label: 'Edit file', disabled: readOnly || chosen.length !== 1 || !current || current.directory || current.link, run: () => openDialog(<Editor location={chosen[0]} saved={refresh} />) },
      { label: chosen[0]?.startsWith('smb://') ? 'Delete permanently…' : 'Move to Trash…', disabled: readOnly || !chosen.length || running, run: () => openDialog(<ConfirmDialog title={chosen[0]?.startsWith('smb://') ? 'Permanently delete?' : 'Move to Trash?'} description={`${chosen.length} item(s):\n${chosen.slice(0, 5).map(p => p.startsWith('smb://') ? decodeURIComponent(p.split('/').pop() || p) : p.split('/').pop()).join('\n')}${chosen.length > 5 ? '\n…' : ''}\n\n${chosen[0]?.startsWith('smb://') ? 'This cannot be undone.' : 'Restore from Trash in Desktop Mode. If Trash is unavailable, the operation stops.'}`} action={chosen[0]?.startsWith('smb://') ? 'Delete permanently' : 'Move to Trash'} submit={() => start(chosen[0]?.startsWith('smb://') ? 'delete' : 'trash', chosen)} />) },
      { label: 'New folder', disabled: readOnly || !folder || running, run: () => openDialog(<TextDialog title="New folder" submit={async name => { await api('mkdir', { location: folder, name }); refresh(); }} />) },
      { label: panes[active].selected.size ? 'Clear selection' : 'Select all', run: () => patch(active, { selected: panes[active].selected.size ? new Set() : new Set(panes[active].data?.entries.map(e => e.path)) }) },
      { label: 'Locations / network shares', run: () => void locations() },
      { label: 'Empty Trash…', disabled: running, run: () => openDialog(<EmptyTrashDialog submit={() => start('empty_trash', [])} />) },
      { label: 'Refresh', run: refresh },
      { label: 'Close FileExplorer', run: () => closeModal?.() },
    ]} />);
  }
  async function open(entry: Entry, index: number) {
    const kind = openKind(entry);
    if (!kind) return;
    if (entry.directory) { await load(index, entry.path); return; }
    setBusyAction(true);
    try {
      if (kind === 'image') { openDialog(<ImageViewer entries={panes[index].data?.entries || [entry]} selected={entry.path} folder={displayPath(panes[index].data?.path || '')} />); return; }
      if (kind === 'media') { openDialog(<MediaPlayer entries={panes[index].data?.entries || [entry]} selected={entry.path} />); return; }
      if (isArchive(entry.name)) { const result = await api<{ path: string }>('open_archive', { location: entry.path }); await load(index, result.path); return; }
      if (!entry.path.startsWith('archive://')) { openDialog(<Editor location={entry.path} saved={refresh} />); return; }
      const preview = await api<{ text: string | null; message: string }>('preview', { location: entry.path }); openDialog(<PreviewDialog name={entry.name} text={preview.text ?? preview.message} />);
    }
    catch (e) { setError(message(e)); } finally { setBusyAction(false); }
  }
  const keydown = (e: GamepadEvent) => {
    if (e.detail.button === GamepadButton.BUMPER_LEFT) { consume(e); focusPane(0, true); }
    else if (e.detail.button === GamepadButton.BUMPER_RIGHT) { consume(e); focusPane(1, true); }
    else if (e.detail.button === GamepadButton.START) { consume(e); options(); }
    else if (e.detail.button === GamepadButton.SELECT) { consume(e); void locations(); }
  };
  return <ModalRoot onCancel={closeModal} closeModal={closeModal} bAllowFullSize bHideCloseIcon className="fe-modal" style={appearanceStyle(state?.settings)}>
    <style>{css}</style><Focusable className="fe-app" flow-children="column" ref={root} onButtonDown={keydown}
      onCancelButton={e => { consume(e); back(); }} onSecondaryButton={e => { consume(e); toggle(); }} onOptionsButton={e => { consume(e); copy(); }}
      onOKActionDescription={canOpen ? 'Open' : undefined} onCancelActionDescription="Back" onSecondaryActionDescription="Select" onOptionsActionDescription={panes[active].data?.archive ? 'Extract' : 'Copy'}
      actionDescriptionMap={{ [GamepadButton.BUMPER_LEFT]: 'Left panel', [GamepadButton.BUMPER_RIGHT]: 'Right panel', [GamepadButton.START]: 'Options', [GamepadButton.SELECT]: 'Locations' }}>
      <header className="fe-header"><div className="fe-brand"><span style={{ color: '#69dce3' }}><Icon size={32} /></span><div>FileExplorer<div className="fe-subtitle">Two panels. One controller.</div></div></div><div style={{ color: '#8fa6bd', fontSize: 12 }}>{version}</div></header>
      <Focusable className="fe-toolbar" flow-children="row"><DialogButton className="fe-btn" disabled={busyAction} onClick={() => void locations()}>Locations</DialogButton>
        <DialogButton className="fe-btn" disabled={running || !sources().length} onClick={copy}>Copy {active ? '←' : '→'}</DialogButton>
        <DialogButton className="fe-btn" onClick={options}>Options</DialogButton><DialogButton className="fe-btn" onClick={refresh}>Refresh</DialogButton><DialogButton className="fe-btn" onClick={closeModal}>Close</DialogButton></Focusable>
      <Focusable className="fe-panes" flow-children="row">{panes.map((pane, index) => <div className={`fe-pane ${active === index ? 'active' : ''}`} data-pane={index} key={index}>
        <div className="fe-path"><div className="fe-path-title">{index ? 'Right' : 'Left'} panel {active === index ? ' • active' : ''}</div><div className="fe-path-value" title={displayPath(pane.data?.path || '')}>{displayPath(pane.data?.path || 'Loading…')}</div></div>
        <div className="fe-columns"><span>Name</span><span>Size</span></div>
        <Focusable className="fe-list" flow-children="column" onGamepadFocus={() => setActive(index)}>
          {pane.loading && !pane.data ? <div className="fe-muted">Loading…</div> : <>
            <Focusable noFocusRing className={`fe-row ${active === index && pane.focused === '..' ? 'focused' : ''}`} preferredFocus={index === 0} data-current={pane.focused === '..'}
              onGamepadFocus={e => { patch(index, { focused: '..' }); setActive(index); (e.target as HTMLElement).scrollIntoView?.({ block: 'nearest' }); }}
              onActivate={e => { consume(e); if (pane.data && !pane.loading) void load(index, pane.data.parent); }} onClick={() => { setActive(index); if (pane.data && !pane.loading) void load(index, pane.data.parent); }}>
              <span className="fe-check" style={{ borderColor: 'transparent' }}>↑</span><FileIcon folder /><span className="fe-name">..</span><span className="fe-size">Parent folder</span>
            </Focusable>
            {pane.error && <div className="fe-error">{pane.error}<br />Use Locations to choose another folder.</div>}
            {!pane.error && pane.data?.entries.map(entry => <Focusable noFocusRing key={entry.path} tabIndex={0}
              className={`fe-row ${pane.selected.has(entry.path) ? 'selected' : ''} ${active === index && pane.focused === entry.path ? 'focused' : ''}`}
              data-current={pane.focused === entry.path} onGamepadFocus={e => { patch(index, { focused: entry.path }); setActive(index); (e.target as HTMLElement).scrollIntoView?.({ block: 'nearest' }); }}
              onFocus={() => { patch(index, { focused: entry.path }); setActive(index); }}
              onClick={() => { patch(index, { focused: entry.path }); setActive(index); }} onDoubleClick={() => { if (!pane.loading) void open(entry, index); }} onActivate={e => { consume(e); if (!pane.loading) void open(entry, index); }}>
              <span className="fe-check" onClick={e => { e.stopPropagation(); patch(index, p => { const s = new Set(p.selected); s.has(entry.path) ? s.delete(entry.path) : s.add(entry.path); return { selected: s, focused: entry.path }; }); setActive(index); }}>{pane.selected.has(entry.path) ? '✓' : ''}</span>
              <FileIcon folder={entry.directory} name={entry.name} /><span className="fe-name">{entry.name}{entry.link ? ' ↗' : ''}</span><span className="fe-size">{entry.directory ? 'Folder' : bytes(entry.size)}</span>
            </Focusable>)}
            {!pane.error && pane.data?.entries.length === 0 && <div className="fe-muted">This folder is empty.</div>}
          </>}
        </Focusable>
        <div className="fe-pane-status"><span>{pane.loading ? 'Loading…' : pane.selected.size ? `${pane.selected.size} selected` : `${pane.data?.entries.length ?? 0} items`}</span><span>{pane.data?.archive ? 'Archive • read-only' : pane.data?.free != null ? `${bytes(pane.data.free)} free` : 'Network share'}</span></div>
      </div>)}</Focusable>
      <div className="fe-status"><span className={`fe-status-text${error || job?.status === 'error' ? ' fe-status-error' : ''}`} title={error || job?.error || job?.current}>
        {error || (job ? `${job.status === 'running' ? `${job.phase} • ${job.percent}% • ${bytes(job.bytes)} / ${bytes(job.total_bytes)} • ${bytes(job.speed || 0)}/s • ${job.current.split('/').pop()}` : job.status === 'done' ? `Completed • ${job.completed} item(s) • ${bytes(job.bytes)}` : job.error}` : canOpen ? 'Select files, then copy them to the other panel.' : 'No preview for this type. Use Options → Edit file to try opening it as text.')}
      </span>{running && <DialogButton className="fe-btn" onClick={cancelCopy}>Cancel</DialogButton>}</div>
      {running && <div className="fe-progress"><div style={{ width: `${job?.percent || 0}%` }} /><span>You can close this window. The operation continues in the background.</span></div>}
      <Legend />
    </Focusable>
  </ModalRoot>;
}
