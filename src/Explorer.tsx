import { DialogButton, Focusable, GamepadButton, GamepadEvent, ModalRoot, getFocusNavController } from '@decky/ui';
import { useEffect, useRef, useState } from 'react';
import { api, bytes, Entry, Job, Listing, message, Place, State } from './api';
import { CancelCopyDialog, ChoiceDialog, ConfirmDialog, EmptyTrashDialog, ExtractionLimitDialog, MenuDialog, openDialog, PlacesDialog, PreviewDialog, RecoveryDialog, TextDialog } from './dialogs';
import { Editor } from './Editor';
import { ImageViewer } from './ImageViewer';
import { MediaPlayer } from './MediaPlayer';
import { PackDialog, PackOptions } from './PackDialog';
import { CopyDialog, pendingJob, showTransfer, TransfersDialog } from './Transfers';
import { AddToSteamDialog, canAddToSteam } from './SteamIntegration';
import { isArchive, openKind } from './fileTypes';
import { explorerClosed, explorerOpened } from './activity';
import { FileIcon, Icon } from './Icon';
import { css } from './style';
import { appearanceStyle, useModalStyle } from './appearance';
import { Legend, stickHint } from './Legend';
import { version } from '../package.json';
import { showConflict } from './ConflictDialog';
import { focusControl } from './navigation';
import { ModifiedDate } from './ModifiedDate';

type Pane = { data: Listing | null; loading: boolean; error: string; selected: Set<string>; focused: string };
const empty = (): Pane => ({ data: null, loading: true, error: '', selected: new Set(), focused: '' });
function consume(e: Event) { e.preventDefault(); e.stopPropagation(); }
let shownLimitJob: string | undefined;
let shownRecoveryJob: string | undefined;

export function Explorer({ closeModal, openSettings, initialPath }: { closeModal?: () => void; openSettings: () => void; initialPath?: string }) {
  const [panes, setPanes] = useState<[Pane, Pane]>([empty(), empty()]);
  const [active, setActive] = useState(0), [jobs, setJobs] = useState<Job[]>([]), [notice, setNotice] = useState<Job | null>(null), [error, setError] = useState('');
  const seenJobs = useRef(new Map<string, Job>());
  const activeJobs = jobs.filter(j => j.status === 'running'), waitingJobs = jobs.filter(j => j.status !== 'running');
  const job = activeJobs[0] || notice;
  const [state, setState] = useState<State | null>(null), [busyAction, setBusyAction] = useState(false);
  const [recovery, setRecovery] = useState<Job | null>(null);
  const [toolbarHidden, setToolbarHidden] = useState(false), [toolbarFocused, setToolbarFocused] = useState(false);
  const [transfersFocused, setTransfersFocused] = useState(false);
  const region = useRef<'files' | 'toolbar' | 'transfers'>('files');
  const toolbarWrites = useRef(Promise.resolve());
  const restoringFocus = useRef(false);
  const root = useRef<HTMLDivElement>(null), generations = useRef([0, 0]), alive = useRef(true);
  useModalStyle(root, appearanceStyle(state?.settings));
  const snapshot = useRef({ panes, active, state, job }); snapshot.current = { panes, active, state, job };
  const running = jobs.some(pendingJob);
  const focusedEntry = panes[active].data?.entries.find(e => e.path === panes[active].focused);
  const canOpen = !focusedEntry || !!openKind(focusedEntry);

  function patch(index: number, update: Partial<Pane> | ((p: Pane) => Partial<Pane>)) {
    setPanes(prev => prev.map((p, i) => i === index ? { ...p, ...(typeof update === 'function' ? update(p) : update) } : p) as [Pane, Pane]);
  }
  async function load(index: number, path: string, remember = true, preserve = false) {
    const generation = ++generations.current[index];
    const restoreFocus = !preserve && index === snapshot.current.active && region.current === 'files';
    patch(index, { loading: true, error: '' });
    try {
      const data = await api<Listing>('list', { location: path });
      if (!alive.current || generation !== generations.current[index]) return;
      patch(index, p => ({ data, loading: false, selected: preserve ? new Set([...p.selected].filter(path => data.entries.some(e => e.path === path))) : new Set(), focused: preserve && data.entries.some(e => e.path === p.focused) ? p.focused : '..' }));
      if (restoreFocus && index === snapshot.current.active && region.current === 'files') focusPane(index);
      if (remember && snapshot.current.state?.settings.remember_paths) {
        void api('settings', { changes: { [index ? 'right' : 'left']: path } }).catch(() => {});
      }
    } catch (e) { if (alive.current && generation === generations.current[index]) patch(index, { loading: false, error: message(e) }); }
  }
  const refresh = () => snapshot.current.panes.forEach((p, i) => { if (p.data) void load(i, p.data.path, false, true); });
  function receiveJobs(result: Job[], initial = false) {
    const finished = result.filter(j => !pendingJob(j) && seenJobs.current.has(j.id) && pendingJob(seenJobs.current.get(j.id)!));
    seenJobs.current = new Map(result.map(j => [j.id, j]));
    setJobs(result.filter(pendingJob));
    const focused = getFocusNavController()?.GetActiveNavTree?.()?.GetLastFocusedNode?.()?.Element;
    if (focused && root.current?.contains(focused)) {
      for (const waiting of result.filter(j => j.status === 'running' && j.conflict)) if (showConflict(waiting, true)) break;
    }
    if (!initial && finished.length) { setNotice(finished[finished.length - 1]); refresh(); }
  }
  function trackJob(next: Job) {
    seenJobs.current.set(next.id, next);
    setJobs(prev => [...prev.filter(j => j.id !== next.id), ...(pendingJob(next) ? [next] : [])]);
    setNotice(pendingJob(next) ? null : next);
    setRecovery(null); setError('');
  }
  useEffect(() => {
    explorerOpened();
    alive.current = true;
    void api<State>('state').then(s => { if (!alive.current) return; setState(s); setToolbarHidden(!!s.settings.toolbar_hidden); receiveJobs(s.jobs || (s.job ? [s.job] : []), true); if (s.job?.recoverable && ['error', 'cancelled'].includes(s.job.status)) setRecovery(s.job); void load(0, initialPath || s.settings.left); void load(1, s.settings.right); }).catch(e => setError(message(e)));
    return () => { alive.current = false; explorerClosed(); };
  }, []);
  useEffect(() => {
    let pending = false;
    const id = window.setInterval(async () => {
      if (pending) return; pending = true;
      try { const next = await api<Job[]>('jobs'); if (alive.current) receiveJobs(next); }
      catch (e) { if (alive.current) setError(message(e)); } finally { pending = false; }
    }, 500);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => {
    if (!notice) return;
    const finishedId = notice.id;
    const timer = window.setTimeout(() => setNotice(current => current?.id === finishedId ? null : current), 6000);
    return () => window.clearTimeout(timer);
  }, [notice?.id, notice?.status]);
  useEffect(() => {
    if (!notice?.recoverable || !['error', 'cancelled'].includes(notice.status)) return;
    setRecovery(notice);
    // Keep the editor/player in control; failed copies remain in Interrupted copies.
    const focused = getFocusNavController()?.GetActiveNavTree?.()?.GetLastFocusedNode?.()?.Element;
    if (notice.status === 'error' && shownRecoveryJob !== notice.id && focused && root.current?.contains(focused)) { shownRecoveryJob = notice.id; showRecovery(notice); }
  }, [notice?.id, notice?.status]);

  async function retry(job: Job, mode: string) {
    const next = await api<Job>('retry', { job_id: job.id, mode });
    trackJob(next);
    return next;
  }
  function restart(job: Job) {
    openDialog(<ConfirmDialog title="Start the copy again?" description="All selected items will be copied from the beginning into a new FileExplorer retry folder in the original destination. Existing files and previous partial copies will be kept." action="Start again" submit={async () => { await retry(job, 'restart'); }} />);
  }
  function showRecovery(job: Job) {
    openDialog(<RecoveryDialog error={job.error} canResume={!!job.recoverable} resume={() => retry(job, 'resume')} restart={() => restart(job)} discard={() => openDialog(<ConfirmDialog title="Remove partial files?" description="Permanently remove this operation's unfinished files and folders. Completed copies already in the destination stay. This copy will no longer be resumable." action="Remove partial files" submit={async () => { trackJob(await api<Job>('discard_copy', { job_id: job.id })); }} />)} />);
  }
  async function interruptedCopies() {
    try {
      const copies = await api<Job[]>('interrupted_copies');
      openDialog(<MenuDialog title={copies.length ? 'Interrupted copies' : 'No interrupted copies'} actions={copies.length ? copies.map(copy => ({ label: `${copy.label || 'Copy'} • ${copy.cleanup_pending ? 'Cleanup needed' : 'Resume / remove'}`, keepOpen: true, run: () => showRecovery(copy) })) : [{ label: 'Close', run: () => {} }]} />);
    } catch (e) { setError(message(e)); }
  }
  function cancelCopy(job: Job) {
    if (!pendingJob(job)) return;
    const id = job.id;
    if (job.status !== 'running') openDialog(<ConfirmDialog title="Remove from queue?" description={`${job.label}\n\nThis item will not be started. Any previously saved partial data will be kept for later recovery.`} action="Remove from queue" submit={async () => { await api('cancel', { job_id: id }); }} />);
    else if (job.recoverable) openDialog(<CancelCopyDialog submit={async keep => { await api('cancel', { job_id: id, keep_partial: keep }); }} />);
    else openDialog(<ConfirmDialog title="Cancel this operation?" description="The operation will stop. Completed items will be kept." action="Cancel operation" submit={async () => { await api('cancel', { job_id: id }); }} />);
  }
  useEffect(() => {
    if (job?.status !== 'error' || !job.error.includes('exceeds extraction size limit (') || shownLimitJob === job.id) return;
    shownLimitJob = job.id;
    openDialog(<ExtractionLimitDialog description={job.error} openSettings={() => { closeModal?.(); openSettings(); }} />);
  }, [job?.id, job?.status]);

  function focusPane(index: number, explicit = false) {
    restoringFocus.current = true;
    region.current = 'files'; setToolbarFocused(false); setTransfersFocused(false);
    setActive(index);
    window.setTimeout(() => {
      if (!alive.current) return;
      const node = root.current?.querySelector<HTMLElement>(`.fe-pane[data-pane="${index}"] .fe-row[data-current="true"]`) || root.current?.querySelector<HTMLElement>(`.fe-pane[data-pane="${index}"] .fe-row`);
      if (node) {
        if (explicit) {
          // Use the target window's native focus request. Steam can keep its
          // active navigation tree in a different CEF context from this modal.
          const owner = node.ownerDocument.defaultView;
          if (owner) node.dispatchEvent(new owner.CustomEvent('vgp_requestfocus', { bubbles: true, cancelable: true, detail: { button: 1, source: 0 } }));
          node.scrollIntoView({ block: 'nearest' });
          restoringFocus.current = false;
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
      restoringFocus.current = false;
    }, 30);
  }
  function focusToolbar() {
    restoringFocus.current = true;
    region.current = 'toolbar'; setToolbarFocused(true); setTransfersFocused(false); setToolbarHidden(false);
    window.setTimeout(() => {
      if (!alive.current || region.current !== 'toolbar') { restoringFocus.current = false; return; }
      const node = root.current?.querySelector<HTMLElement>('.fe-toolbar button:not(:disabled)');
      const owner = node?.ownerDocument.defaultView;
      if (node && owner) node.dispatchEvent(new owner.CustomEvent('vgp_requestfocus', { bubbles: true, cancelable: true, detail: { button: 1, source: 0 } }));
      restoringFocus.current = false;
    }, 30);
  }
  function toggleToolbar() {
    const hidden = !toolbarHidden;
    setToolbarHidden(hidden);
    toolbarWrites.current = toolbarWrites.current.then(() => api('settings', { changes: { toolbar_hidden: hidden } })).then(() => {}, e => setError(message(e)));
    if (!toolbarHidden && region.current === 'toolbar') focusPane(snapshot.current.active, true);
  }
  function focusTransfers(last = false) {
    const nodes = Array.from(root.current?.querySelectorAll<HTMLElement>('.fe-status button:not(:disabled),.fe-transfer-grid button:not(:disabled)') || []);
    const actions = nodes.filter(node => !!node.closest('.fe-status'));
    const node = last ? actions[actions.length - 1] || nodes[nodes.length - 1] : nodes[0];
    if (!node) { focusPane(snapshot.current.active, true); return; }
    region.current = 'transfers'; setToolbarFocused(false); setTransfersFocused(true);
    focusControl(node);
  }
  // A completed last transfer must not leave focus on a removed button.
  useEffect(() => {
    const child = root.current?.ownerDocument.querySelector('.fe-dialog,.fe-editor,.fe-image-viewer,.fe-media-player');
    if (!running && region.current === 'transfers' && !child) focusPane(snapshot.current.active, true);
  }, [running]);
  useEffect(() => {
    const doc = root.current?.ownerDocument;
    const direction = (event: Event) => {
      const e = event as GamepadEvent, target = e.target as HTMLElement;
      if (e.defaultPrevented || !root.current?.contains(target)) return;
      const left = e.detail.button === GamepadButton.DIR_LEFT, right = e.detail.button === GamepadButton.DIR_RIGHT;
      if (!left && !right) return;
      const list = target.closest('.fe-list');
      if (list) {
        consume(e);
        const index = Number(list.closest<HTMLElement>('[data-pane]')?.dataset.pane);
        if (right && index === 0 || left && index === 1) focusPane(1 - index, true);
        else if (running) focusTransfers(left);
        else focusPane(1 - index, true);
        return;
      }
      const row = target.closest('.fe-status,.fe-transfer-grid');
      if (!row) return;
      const controls = Array.from(row.querySelectorAll<HTMLElement>('button:not(:disabled)'));
      const index = controls.findIndex(node => node === target || node.contains(target));
      if (index < 0) return;
      consume(e);
      const next = controls[index + (right ? 1 : -1)];
      if (next) focusControl(next);
      else focusPane(right ? 0 : 1, true);
    };
    const shortcut = (event: Event) => {
      const e = event as GamepadEvent;
      if (![GamepadButton.LSTICK_CLICK, GamepadButton.RSTICK_CLICK].includes(e.detail?.button) || !root.current?.contains(e.target as Node)) return;
      consume(e);
      if (e.detail.is_repeat) return;
      if (e.detail.button === GamepadButton.LSTICK_CLICK) toggleToolbar();
      else if (region.current === 'files') focusToolbar();
      else if (region.current === 'toolbar' && running) focusTransfers();
      else focusPane(snapshot.current.active, true);
    };
    doc?.addEventListener('vgp_ondirection', direction, true);
    doc?.addEventListener('vgp_onbuttondown', shortcut, true);
    return () => { doc?.removeEventListener('vgp_onbuttondown', shortcut, true); doc?.removeEventListener('vgp_ondirection', direction, true); };
  });
  function sources(): string[] {
    const p = snapshot.current.panes[snapshot.current.active];
    return p.selected.size ? [...p.selected] : p.focused && p.focused !== '..' ? [p.focused] : [];
  }
  function toggle() {
    const index = snapshot.current.active, p = snapshot.current.panes[index];
    if (!p.focused || p.focused === '..' || p.loading || !p.data?.entries.length) return;
    const at = p.data.entries.findIndex(entry => entry.path === p.focused);
    if (at < 0) return;
    const next = p.data.entries[(at + 1) % p.data.entries.length].path;
    patch(index, prev => { const selected = new Set(prev.selected); selected.has(p.focused) ? selected.delete(p.focused) : selected.add(p.focused); return { selected, focused: next }; });
    focusPane(index, true);
  }
  function wrapFiles(e: GamepadEvent) {
    if (e.detail.button !== GamepadButton.DIR_UP && e.detail.button !== GamepadButton.DIR_DOWN) return;
    const row = (e.target as HTMLElement).closest<HTMLElement>('.fe-row');
    const rows = Array.from(row?.parentElement?.querySelectorAll<HTMLElement>('.fe-row') || []);
    const first = e.detail.button === GamepadButton.DIR_UP;
    if (rows.length > 1 && row === rows[first ? 0 : rows.length - 1]) {
      consume(e); focusControl(rows[first ? rows.length - 1 : 0]);
    }
  }
  function back() {
    const p = panes[active];
    if (p.data && p.data.path !== p.data.parent) void load(active, p.data.parent);
    else closeModal?.();
  }
  async function start(action: string, chosen: string[], destination?: string, options?: PackOptions) {
    const next = await api<Job>('start', { action, sources: chosen, destination, options });
    trackJob(next);
  }
  const copy = () => transfer('copy');
  function transfer(action: 'copy' | 'move', chosen = sources(), index = snapshot.current.active, completed?: () => void) {
    const dest = panes[1 - index].data?.path;
    if (!chosen.length || !dest || (action === 'move' && running)) return;
    if (panes[1 - index].data?.archive) { setError('Choose a writable folder in the other panel. Archives are read-only.'); return; }
    if (action === 'copy') {
      openDialog(<CopyDialog count={chosen.length} destination={displayPath(dest)} existing={jobs} submit={async (mode, parallel) => {
        const created = await api<Job[]>('submit_copy', { sources: chosen, destination: dest, mode, parallel_limit: parallel });
        created.forEach(trackJob); completed?.();
      }} />);
      return;
    }
    const verb = action === 'move' ? 'Move' : panes[index].data?.archive ? 'Extract' : 'Copy';
    openDialog(<ConfirmDialog title={`${verb} ${chosen.length} item${chosen.length > 1 ? 's' : ''}?`} destination={displayPath(dest)} description={'Source items are removed only after a successful move.\nTransfers between disks or shares are verified first.\n\nIf a name already exists, choose overwrite, backup or cancel.'} action={verb} submit={async () => { await start(action, chosen, dest); completed?.(); }} />);
  }
  async function locations(completed?: () => void) {
    setBusyAction(true);
    try { const places = await api<Place[]>('locations'); const index = active; openDialog(<PlacesDialog places={places} choose={path => { void api<State>('state').then(setState); void load(index, path); completed?.(); }} />); }
    catch (e) { setError(message(e)); } finally { setBusyAction(false); }
  }
  function sortFiles(completed: () => void) {
    openDialog(<ChoiceDialog title="Sort by" description="Apply to both panels. Folders first follows your Settings choice. Dates use this device's local time." choices={[
      { key: 'name', label: 'Name (A–Z)' },
      { key: 'size', label: 'Size (largest first)' },
      { key: 'modified', label: 'Date modified (newest first)' },
    ].map(option => ({ label: `${snapshot.current.state?.settings.sort_by === option.key ? '✓ ' : ''}${option.label}`, run: async () => {
      setState(await api<State>('settings', { changes: { sort_by: option.key } }));
      await Promise.all(snapshot.current.panes.map((pane, index) => pane.data ? load(index, pane.data.path, false, true) : Promise.resolve()));
      completed();
    } }))} />);
  }
  function displayPath(path: string) {
    if (path.startsWith('archive://')) return panes.find(p => p.data?.path === path)?.data?.label || 'Archive';
    if (!path.startsWith('smb://')) return path;
    const match = path.match(/^smb:\/\/([^/]+)(.*)$/);
    const connection = state?.connections.find(c => c.id === match?.[1]);
    return connection ? `smb://${connection.host}/${connection.share}${decodeURIComponent(match![2])}` : path;
  }
  function options(context?: { index: number; entry: Entry }) {
    const active = context?.index ?? snapshot.current.active;
    const chosen = context && !panes[active].selected.has(context.entry.path) ? [context.entry.path] : context ? [...panes[active].selected] : sources();
    const current = panes[active].data?.entries.find(e => e.path === chosen[0]);
    const folder = panes[active].data?.path, dest = panes[1 - active].data?.path;
    const readOnly = !!panes[active].data?.archive, targetReadOnly = !!panes[1 - active].data?.archive;
    const finish = async (task: Promise<unknown>, closeMenu: () => void) => { await task; closeMenu(); };
    openDialog(<MenuDialog title={chosen.length > 1 ? `${chosen.length} items selected` : current?.name || 'Folder options'} sections={[{ title: 'Selected file / folder', actions: [
      { label: readOnly ? 'Extract selected to other panel' : 'Copy to other panel', keepOpen: true, run: closeMenu => transfer('copy', chosen, active, closeMenu), disabled: !chosen.length || targetReadOnly },
      { label: 'Move to other panel', keepOpen: true, run: closeMenu => transfer('move', chosen, active, closeMenu), disabled: readOnly || !chosen.length || !dest || running || targetReadOnly },
      { label: 'Create archive…', disabled: readOnly || !chosen.length || !folder || running, keepOpen: true, run: closeMenu => openDialog(<PackDialog count={chosen.length} initialName={chosen.length === 1 ? current?.name || 'Archive' : 'Archive'} folders={[{ data: folder!, label: 'Current panel' }, ...(!targetReadOnly && dest && dest !== folder ? [{ data: dest, label: 'Other panel' }] : [])]} submit={(destination, options) => finish(start('pack', chosen, destination, options), closeMenu)} />) },
      { label: 'Extract whole archive…', disabled: readOnly || targetReadOnly || !current || !isArchive(current.name) || chosen.length !== 1 || !dest || running, keepOpen: true, run: closeMenu => openDialog(<ConfirmDialog title="Extract archive?" destination={displayPath(dest!)} description="Create a new folder in the other panel.\nZIP, RAR, 7z and TAR are supported." action="Extract" submit={() => finish(start('extract', chosen, dest), closeMenu)} />) },
      { label: 'Rename', disabled: readOnly || chosen.length !== 1 || running, keepOpen: true, run: closeMenu => openDialog(<TextDialog title="Rename" initial={current?.name} submit={async name => { await api('rename', { location: chosen[0], name }); refresh(); closeMenu(); }} />) },
      { label: 'Edit file', disabled: readOnly || chosen.length !== 1 || !current || current.directory || current.link, keepOpen: true, run: () => openDialog(<Editor location={chosen[0]} saved={refresh} />) },
      { label: 'Add to Steam…', disabled: readOnly || chosen.length !== 1 || !current || !canAddToSteam(current), keepOpen: true, run: () => openDialog(<AddToSteamDialog location={chosen[0]} />) },
      { label: chosen[0]?.startsWith('smb://') ? 'Delete permanently…' : 'Move to Trash…', disabled: readOnly || !chosen.length || running, keepOpen: true, run: closeMenu => openDialog(<ConfirmDialog title={chosen[0]?.startsWith('smb://') ? 'Permanently delete?' : 'Move to Trash?'} description={`${chosen.length} item(s):\n${chosen.slice(0, 5).map(p => p.startsWith('smb://') ? decodeURIComponent(p.split('/').pop() || p) : p.split('/').pop()).join('\n')}${chosen.length > 5 ? '\n…' : ''}\n\n${chosen[0]?.startsWith('smb://') ? 'This cannot be undone.' : 'Restore from Trash in Desktop Mode. If Trash is unavailable, the operation stops.'}`} action={chosen[0]?.startsWith('smb://') ? 'Delete permanently' : 'Move to Trash'} submit={() => finish(start(chosen[0]?.startsWith('smb://') ? 'delete' : 'trash', chosen), closeMenu)} />) },
    ] }, { title: 'Current folder / FileExplorer', actions: [
      { label: 'New folder', disabled: readOnly || !folder || running, keepOpen: true, run: closeMenu => openDialog(<TextDialog title="New folder" submit={async name => { await api('mkdir', { location: folder, name }); refresh(); closeMenu(); }} />) },
      { label: panes[active].selected.size ? 'Clear selection' : 'Select all', run: () => patch(active, { selected: panes[active].selected.size ? new Set() : new Set(panes[active].data?.entries.map(e => e.path)) }) },
      { label: 'Locations / network shares', keepOpen: true, run: closeMenu => void locations(closeMenu) },
      { label: 'Sort by…', keepOpen: true, run: closeMenu => sortFiles(closeMenu) },
      { label: 'Transfers / queue…', keepOpen: true, run: () => openDialog(<TransfersDialog cancel={cancelCopy} />) },
      { label: 'Interrupted copies…', keepOpen: true, run: () => void interruptedCopies() },
      { label: 'Empty Trash…', disabled: running, keepOpen: true, run: closeMenu => openDialog(<EmptyTrashDialog submit={() => finish(start('empty_trash', []), closeMenu)} />) },
      { label: 'Refresh', run: refresh },
      { label: 'Close FileExplorer', run: () => closeModal?.() },
    ] }]} />);
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
      onCancelButton={e => { consume(e); back(); }} onSecondaryButton={e => { consume(e); if (!e.detail.is_repeat) toggle(); }} onOptionsButton={e => { consume(e); copy(); }}
      onOKActionDescription={toolbarFocused || transfersFocused ? 'Use' : canOpen ? 'Open' : undefined} onCancelActionDescription="Back" onSecondaryActionDescription="Select" onOptionsActionDescription={panes[active].data?.archive ? 'Extract' : 'Copy'}
      actionDescriptionMap={{ [GamepadButton.BUMPER_LEFT]: 'Left', [GamepadButton.BUMPER_RIGHT]: 'Right', [GamepadButton.START]: 'Options', [GamepadButton.SELECT]: 'Locations', [GamepadButton.LSTICK_CLICK]: stickHint(toolbarHidden ? 'Show bar' : 'Hide bar'), [GamepadButton.RSTICK_CLICK]: stickHint(toolbarFocused ? running ? 'Transfers' : 'Files' : transfersFocused ? 'Files' : 'Toolbar') }}>
      <header className="fe-header"><div className="fe-brand"><span style={{ color: '#69dce3' }}><Icon size={32} /></span><div>FileExplorer<div className="fe-subtitle">Two panels. One controller.</div></div></div><div style={{ color: '#8fa6bd', fontSize: 12 }}>{version}</div><DialogButton className="fe-btn fe-toolbar-toggle" onClick={toggleToolbar}>{toolbarHidden ? 'Show toolbar' : 'Hide toolbar'}</DialogButton></header>
      {!toolbarHidden && <Focusable className="fe-toolbar" flow-children="row" onGamepadFocus={() => { if (!restoringFocus.current) { region.current = 'toolbar'; setToolbarFocused(true); setTransfersFocused(false); } }} onGamepadDirection={e => { if (e.detail.button === GamepadButton.DIR_DOWN) { consume(e); focusPane(snapshot.current.active, true); } else if (e.detail.button === GamepadButton.DIR_UP && running) { consume(e); focusTransfers(); } }}><DialogButton className="fe-btn" disabled={busyAction} onClick={() => void locations()}>Locations</DialogButton>
        <DialogButton className="fe-btn" disabled={!sources().length} onClick={copy}>Copy {active ? '←' : '→'}</DialogButton>
        <DialogButton className="fe-btn" onClick={() => options()}>Options</DialogButton><DialogButton className="fe-btn" onClick={refresh}>Refresh</DialogButton><DialogButton className="fe-btn" onClick={closeModal}>Close</DialogButton></Focusable>}
      <Focusable className="fe-panes" flow-children="row">{panes.map((pane, index) => <div className={`fe-pane ${active === index ? 'active' : ''}`} data-pane={index} key={index}>
        <div className="fe-path"><div className="fe-path-title">{index ? 'Right' : 'Left'} panel {active === index ? ' • active' : ''}</div><div className="fe-path-value" title={displayPath(pane.data?.path || '')}>{displayPath(pane.data?.path || 'Loading…')}</div></div>
        <div className="fe-columns"><span className="fe-column-name">Name{state?.settings.sort_by === 'name' ? ' ↑' : ''}</span><span className="fe-size">Size{state?.settings.sort_by === 'size' ? ' ↓' : ''}</span><span className="fe-modified">Modified{state?.settings.sort_by === 'modified' ? ' ↓' : ''}</span></div>
        <Focusable className="fe-list" flow-children="column" onGamepadDirection={wrapFiles} onGamepadFocus={() => { if (!restoringFocus.current) { region.current = 'files'; setToolbarFocused(false); setTransfersFocused(false); setActive(index); } }}>
          {pane.loading && !pane.data ? <div className="fe-muted">Loading…</div> : <>
            <Focusable noFocusRing className={`fe-row ${active === index && pane.focused === '..' ? 'focused' : ''}`} preferredFocus={index === 0} data-current={pane.focused === '..'}
              onGamepadFocus={e => { patch(index, { focused: '..' }); setActive(index); (e.target as HTMLElement).scrollIntoView?.({ block: 'nearest' }); }}
              onActivate={e => { consume(e); if (pane.data && !pane.loading) void load(index, pane.data.parent); }} onClick={() => { setActive(index); if (pane.data && !pane.loading) void load(index, pane.data.parent); }}>
              <span className="fe-check" style={{ borderColor: 'transparent' }}>↑</span><FileIcon folder /><span className="fe-name">..</span><span className="fe-parent-label">Parent folder</span>
            </Focusable>
            {pane.error && <div className="fe-error">{pane.error}<br />Use Locations to choose another folder.</div>}
            {!pane.error && pane.data?.entries.map(entry => <Focusable noFocusRing key={entry.path} tabIndex={0}
              className={`fe-row ${pane.selected.has(entry.path) ? 'selected' : ''} ${active === index && pane.focused === entry.path ? 'focused' : ''}`}
              data-current={pane.focused === entry.path} onGamepadFocus={e => { patch(index, { focused: entry.path }); setActive(index); (e.target as HTMLElement).scrollIntoView?.({ block: 'nearest' }); }}
              onFocus={() => { patch(index, { focused: entry.path }); setActive(index); }}
              onContextMenu={e => { e.preventDefault(); e.stopPropagation(); patch(index, { focused: entry.path, ...(pane.selected.has(entry.path) ? {} : { selected: new Set() }) }); setActive(index); options({ index, entry }); }}
              onClick={() => { patch(index, { focused: entry.path }); setActive(index); }} onDoubleClick={() => { if (!pane.loading) void open(entry, index); }} onActivate={e => { consume(e); if (!pane.loading) void open(entry, index); }}>
              <span className="fe-check" onClick={e => { e.stopPropagation(); patch(index, p => { const s = new Set(p.selected); s.has(entry.path) ? s.delete(entry.path) : s.add(entry.path); return { selected: s, focused: entry.path }; }); setActive(index); }}>{pane.selected.has(entry.path) ? '✓' : ''}</span>
              <FileIcon folder={entry.directory} name={entry.name} /><span className="fe-name" title={entry.name}>{entry.name}{entry.link ? ' ↗' : ''}</span><span className="fe-size">{entry.directory ? 'Folder' : bytes(entry.size)}</span><ModifiedDate seconds={entry.modified} />
            </Focusable>)}
            {!pane.error && pane.data?.entries.length === 0 && <div className="fe-muted">This folder is empty.</div>}
          </>}
        </Focusable>
        <div className="fe-pane-status"><span>{pane.loading ? 'Loading…' : pane.selected.size ? `${pane.selected.size} selected` : `${pane.data?.entries.length ?? 0} items`}</span><span>{pane.data?.archive ? 'Archive • read-only' : pane.data?.free != null ? `${bytes(pane.data.free)} free` : 'Network share'}</span></div>
      </div>)}</Focusable>
      <Focusable className="fe-status" flow-children="row" onGamepadFocus={() => { region.current = 'transfers'; setToolbarFocused(false); setTransfersFocused(true); }} onGamepadDirection={e => { if (e.detail.button === GamepadButton.DIR_UP) { consume(e); focusPane(snapshot.current.active, true); } else if (e.detail.button === GamepadButton.DIR_DOWN) { consume(e); const card = root.current?.querySelector<HTMLElement>('.fe-transfer-grid button'); if (card) focusControl(card); else focusPane(snapshot.current.active, true); } }}><span className={`fe-status-text${error || job?.status === 'error' ? ' fe-status-error' : ''}`} title={error || job?.error || job?.current}>
        {error || (job ? `${job.status === 'running' ? `${job.phase} • ${job.percent}% • ${bytes(job.bytes)} / ${bytes(job.total_bytes)} • ${bytes(job.speed || 0)}/s • ${job.current.split('/').pop()}` : job.status === 'done' ? `Completed • ${job.completed} item(s) • ${bytes(job.bytes)}` : job.error}` : canOpen ? 'Select files, then copy them to the other panel.' : 'No preview for this type. Use Options → Edit file to try opening it as text.')}
      </span>{activeJobs.length === 1 && <DialogButton className="fe-btn" onClick={() => cancelCopy(activeJobs[0])}>Cancel</DialogButton>}{running && <DialogButton className="fe-btn" onClick={() => openDialog(<TransfersDialog cancel={cancelCopy} />)}>Transfers{waitingJobs.length ? ` (${waitingJobs.length} waiting)` : ''}</DialogButton>}</Focusable>
      {state?.credential_error && <div className="fe-error" role="alert">{state.credential_error}</div>}
      {activeJobs.length > 0 && <Focusable className="fe-transfer-grid" flow-children="row" onGamepadFocus={() => { region.current = 'transfers'; setToolbarFocused(false); setTransfersFocused(true); }} onGamepadDirection={e => { if (e.detail.button === GamepadButton.DIR_UP) { consume(e); focusTransfers(); } else if (e.detail.button === GamepadButton.DIR_DOWN) { consume(e); focusPane(snapshot.current.active, true); } }} style={{ gridTemplateColumns: `repeat(${activeJobs.length}, minmax(0, 1fr))` }}>{activeJobs.map(j => <DialogButton key={j.id} className={`fe-btn fe-transfer-card${j.conflict ? ' fe-transfer-conflict' : ''}`} onClick={() => showTransfer(j, cancelCopy)}><span className="fe-task-title">{j.label}</span><span className="fe-task-info">{j.conflict ? 'Name conflict • Choose' : `${j.percent}% · ${bytes(j.speed || 0)}/s`}</span><span className="fe-transfer-fill" style={{ width: `${j.percent || 0}%` }} /></DialogButton>)}</Focusable>}
      <Legend />
    </Focusable>
  </ModalRoot>;
}
