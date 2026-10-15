import { DialogButton, Focusable, ModalRoot, NavEntryPositionPreferences, TextField, ToggleField, showModal } from '@decky/ui';
import { cloneElement, useRef, useState } from 'react';
import { api, Job, message, Place } from './api';
import { rememberConflictIntent } from './conflictIntent';
import { css } from './style';
import { useMenuWrapping } from './navigation';

function NavigableDialog({ element, ...modalProps }: { element: React.ReactElement; closeModal?: () => void }) {
  const marker = useRef<HTMLSpanElement>(null);
  useMenuWrapping(marker);
  return <><span hidden ref={marker} />{cloneElement(element, modalProps)}</>;
}

const dialogs = new Set<{ Close: () => void }>();
const explorers = new Set<{ Close: () => void }>();
export function openDialog(element: React.ReactElement, explorer = false, onClosed?: () => void) {
  const modal = showModal(<NavigableDialog element={element} />, undefined, { bNeverPopOut: true, fnOnClose: () => { dialogs.delete(modal); explorers.delete(modal); onClosed?.(); } });
  dialogs.add(modal);
  if (explorer) explorers.add(modal);
  return modal;
}
export function closeAllDialogs() { for (const modal of [...dialogs]) modal.Close(); dialogs.clear(); explorers.clear(); }
export function revealExplorer(launch?: () => void) {
  for (const modal of [...dialogs].reverse()) if (!explorers.has(modal)) modal.Close();
  if (!explorers.size) launch?.();
}
export function ErrorText({ text }: { text: string }) { return text ? <div className="fe-error" role="alert">{text}</div> : null; }
export function DialogHeading({ children }: { children: React.ReactNode }) { return <h2 className="fe-info-heading"><span className="fe-info-icon" aria-hidden="true">i</span><span>{children}</span></h2>; }
export function DestinationInfo({ path }: { path: string }) { return <div className="fe-destination"><span>Destination</span><strong>{path}</strong></div>; }

export function TextDialog({ title, initial = '', description, submit, closeModal }: {
  title: string; initial?: string; description?: string; submit: (value: string) => Promise<void>; closeModal?: () => void;
}) {
  const [value, setValue] = useState(initial), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const save = async () => {
    if (busy) return;
    setBusy(true); setError('');
    try { await submit(value); closeModal?.(); } catch (e) { setError(message(e)); } finally { setBusy(false); }
  };
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column">
    <DialogHeading>{title}</DialogHeading>{description && <p className="fe-description">{description}</p>}
    <TextField value={value} onChange={e => setValue(e.target.value)} focusOnMount disabled={busy} />
    <ErrorText text={error} /><Focusable className="fe-actions" flow-children="row"><DialogButton disabled={busy || !value.trim()} onClick={() => void save()}>Save</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

export function ConfirmDialog({ title, description, action, submit, closeModal, danger, destination }: {
  title: string; description: string; action: string; submit: () => Promise<void>; closeModal?: () => void; danger?: string; destination?: string;
}) {
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  return <ModalRoot onCancel={busy ? undefined : closeModal} closeModal={busy ? undefined : closeModal}><style>{css}</style><Focusable className="fe-dialog fe-confirm-dialog" flow-children="column">
    <DialogHeading>{title}</DialogHeading>{danger && <div className="fe-danger" role="alert"><span aria-hidden="true">!</span><strong>{danger}</strong></div>}{destination && <DestinationInfo path={destination} />}<p className="fe-description">{description}</p><ErrorText text={error} />
    <Focusable className="fe-actions" flow-children="row"><DialogButton className={danger ? 'fe-destructive' : undefined} disabled={busy} onClick={async () => { setBusy(true); try { await submit(); closeModal?.(); } catch (e) { setError(message(e)); setBusy(false); } }}>{action}</DialogButton><DialogButton disabled={busy} onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

export function EmptyTrashDialog({ submit, closeModal }: { submit: () => Promise<void>; closeModal?: () => void }) {
  return <ConfirmDialog title="Empty Trash?" danger="This also empties your Desktop Mode Trash!" description="FileExplorer and the SteamOS desktop use the same Trash. All trashed files, including those on connected drives, will be permanently deleted. This cannot be undone." action="Empty Trash" submit={submit} closeModal={closeModal} />;
}

export function CancelCopyDialog({ submit, closeModal }: { submit: (keep: boolean) => Promise<void>; closeModal?: () => void }) {
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  async function stop(keep: boolean) {
    setBusy(true);
    try { await submit(keep); closeModal?.(); }
    catch (e) { setError(message(e)); setBusy(false); }
  }
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column">
    <h2>Stop copying?</h2><p className="fe-description">Keep unfinished copies to resume later, including after a restart. Or permanently remove the unfinished files and folders. Completed copies already in the destination stay.</p>
    <ErrorText text={error} /><Focusable className="fe-stack" flow-children="column">
      <DialogButton preferredFocus disabled={busy} onClick={() => void stop(true)}>Keep for later</DialogButton>
      <DialogButton disabled={busy} onClick={() => void stop(false)}>Remove partial files</DialogButton>
      <DialogButton disabled={busy} onClick={closeModal}>Continue copying</DialogButton>
    </Focusable>
  </Focusable></ModalRoot>;
}

export function ChoiceDialog({ title, description, choices, closeModal, dismiss }: { title: string; description: string; choices: { label: string; danger?: boolean; run: () => Promise<void> }[]; closeModal?: () => void; dismiss?: () => void }) {
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const cancel = () => { if (!busy) { dismiss?.(); closeModal?.(); } };
  return <ModalRoot onCancel={cancel} closeModal={cancel}><style>{css}</style><Focusable className="fe-dialog fe-confirm-dialog" flow-children="column">
    <DialogHeading>{title}</DialogHeading><p className="fe-description">{description}</p><ErrorText text={error} />
    <Focusable className="fe-stack" flow-children="column">{choices.map((choice, index) => <DialogButton key={choice.label} className={choice.danger ? 'fe-destructive' : undefined} preferredFocus={index === 0} disabled={busy} onClick={async () => {
      setBusy(true); try { await choice.run(); closeModal?.(); } catch (e) { setError(message(e)); setBusy(false); }
    }}>{choice.label}</DialogButton>)}</Focusable>
  </Focusable></ModalRoot>;
}

export function ExtractionLimitDialog({ description, openSettings, closeModal }: { description: string; openSettings: () => void; closeModal?: () => void }) {
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column">
    <h2>Extraction limit exceeded</h2><p className="fe-description">{description}</p>
    <Focusable className="fe-actions" flow-children="row"><DialogButton onClick={() => { closeModal?.(); openSettings(); }}>Open Settings</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

type MenuAction = { label: string; run: (closeMenu: () => void) => void; keepOpen?: boolean; disabled?: boolean; danger?: boolean };
export function MenuDialog({ title, actions = [], sections, closeModal }: { title: string; actions?: MenuAction[]; sections?: { title: string; actions: MenuAction[] }[]; closeModal?: () => void }) {
  const activate = (action: MenuAction) => {
    // Subdialogs keep this navigation level and its focused button alive.
    if (!action.keepOpen) closeModal?.();
    action.run(() => closeModal?.());
  };
  if (sections) return <ModalRoot className="fe-options-modal" onCancel={closeModal} closeModal={closeModal}><style>{css}</style>
    <Focusable className="fe-dialog fe-menu-dialog" flow-children="column"><DialogHeading>{title}</DialogHeading>
      <Focusable className="fe-menu-columns" flow-children="row">{sections.map(section => <Focusable key={section.title} className="fe-menu-section" flow-children="column" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_Y}>
        <h3>{section.title}</h3><Focusable className="fe-menu-items" flow-children="column">{section.actions.map(a => <DialogButton key={a.label} className={a.danger ? 'fe-destructive' : undefined} disabled={a.disabled} onClick={() => activate(a)}>{a.label}</DialogButton>)}</Focusable>
      </Focusable>)}</Focusable>
    </Focusable>
  </ModalRoot>;
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column"><h2>{title}</h2><Focusable className="fe-stack" flow-children="column">
    {actions.map(a => <DialogButton key={a.label} disabled={a.disabled} onClick={() => activate(a)}>{a.label}</DialogButton>)}
  </Focusable></Focusable></ModalRoot>;
}

export function RecoveryDialog({ error, resume, restart, closeModal, openExplorer, discard, canResume = true }: { error: string; resume: () => Promise<Job | void>; restart: () => void; closeModal?: () => void; openExplorer?: () => void; discard?: () => void; canResume?: boolean }) {
  const [failure, setFailure] = useState(''), [busy, setBusy] = useState(false);
  const nameConflict = /name conflict|already exists|destination.*exists/i.test(error);
  async function retry(intent?: 'rename' | 'overwrite') {
    setBusy(true); try { const next = await resume(); if (intent && next) rememberConflictIntent(next.id, intent); closeModal?.(); } catch (e) { setFailure(message(e)); setBusy(false); }
  }
  function cancel() {
    if (!discard) { closeModal?.(); return; }
    openDialog(<ChoiceDialog title="Keep the unfinished copy?" description="Keep saved progress for later, or remove this operation's unfinished files. Completed items stay." choices={[
      { label: 'Keep for later', run: async () => closeModal?.() },
      { label: 'Remove partial files…', run: async () => { closeModal?.(); discard(); } },
      { label: 'Back', run: async () => {} },
    ]} />);
  }
  return <ModalRoot onCancel={busy ? undefined : closeModal} closeModal={busy ? undefined : closeModal}><style>{css}</style><Focusable className="fe-dialog fe-confirm-dialog" flow-children="column">
    <DialogHeading>Copy interrupted</DialogHeading><p className="fe-description">{error}</p><p className="fe-description">Resume verifies saved data. Start again uses a new retry folder and keeps previous results.{nameConflict ? ' Change name or Overwrite reopens this conflict with the chosen action.' : ' Change name and Overwrite apply only to name conflicts.'}</p><ErrorText text={failure} />
    <Focusable className="fe-recovery-actions" flow-children="column">
      <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
        <DialogButton disabled={busy || !canResume} onClick={() => void retry()}>Resume</DialogButton>
        <DialogButton disabled={busy} onClick={() => { closeModal?.(); restart(); }}>Start again</DialogButton>
      </Focusable>
      <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
        <DialogButton disabled={busy || !canResume || !nameConflict} onClick={() => void retry('rename')}>Change name</DialogButton>
        <DialogButton className="fe-destructive" disabled={busy || !canResume || !nameConflict} onClick={() => void retry('overwrite')}>Overwrite</DialogButton>
      </Focusable>
      <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
        <DialogButton disabled={busy} onClick={cancel}>Cancel</DialogButton>
        <DialogButton disabled={busy} onClick={() => revealExplorer(openExplorer)}>Open FileExplorer</DialogButton>
      </Focusable>
    </Focusable>
  </Focusable></ModalRoot>;
}

export function PreviewDialog({ name, text, closeModal }: { name: string; text: string; closeModal?: () => void }) {
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column"><h2>{name}</h2><pre tabIndex={0}>{text}</pre><DialogButton onClick={closeModal}>Close</DialogButton></Focusable></ModalRoot>;
}

export function ConnectDialog({ connected, closeModal }: { connected: (path: string) => void; closeModal?: () => void }) {
  const [form, setForm] = useState({ label: '', host: '', share: '', username: '', password: '', domain: '', remember: false });
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('Find servers automatically or enter a server address below.');
  async function discover() {
    setBusy(true); setError(''); setStatus('Searching your local network…');
    try {
      const result = await api<{ servers: { host: string; name: string }[]; networks: string[]; limited: boolean }>('discover');
      setStatus(result.servers.length ? 'Select a server, then list its shares. Enter login details first if needed.' : 'No SMB servers found. You can still enter the server address manually.');
      if (result.servers.length) openDialog(<MenuDialog title="SMB servers" actions={result.servers.map(server => ({ label: server.name === server.host ? server.host : `${server.name} (${server.host})`, run: () => setForm(f => ({ ...f, host: server.host, share: '' })) }))} />);
    } catch (e) { setError(message(e)); setStatus('You can enter the server address manually.'); }
    finally { setBusy(false); }
  }
  async function listShares() {
    setBusy(true); setError(''); setStatus('Reading available shares…');
    try {
      const shares = await api<{ name: string; comment: string }[]>('shares', { profile: form });
      setStatus(shares.length ? 'Select a share, then connect.' : 'No disk shares were returned. You can enter a share name manually.');
      if (shares.length) openDialog(<MenuDialog title={`Shares on ${form.host}`} actions={shares.map(share => ({ label: share.name, run: () => setForm(f => ({ ...f, share: share.name })) }))} />);
    } catch (e) { setError(message(e)); setStatus('Check the username, password and domain, then try List shares again.'); }
    finally { setBusy(false); }
  }
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column"><h2>Connect to SMB share</h2>
    <Focusable className="fe-actions" flow-children="row"><DialogButton disabled={busy} onClick={() => void discover()}>Find servers</DialogButton><DialogButton disabled={busy || !form.host} onClick={() => void listShares()}>List shares</DialogButton></Focusable>
    <p className="fe-description" role="status">{status}</p>
    <Focusable className="fe-connection-form fe-stack" flow-children="column">
      {(['host', 'share', 'username', 'password', 'domain', 'label'] as const).map((key, i) => <TextField key={key}
        label={{host: 'Server / IP', share: 'Share name', username: 'Username (blank for guest)', password: 'Password', domain: 'Domain (optional)', label: 'Display name (optional)'}[key]}
        value={form[key]} bIsPassword={key === 'password'} focusOnMount={i === 0} disabled={busy} onChange={e => setForm({ ...form, [key]: e.target.value })} />)}
      <ToggleField label="Remember connection" description="Encrypts the password for this device and Steam user. No extra unlock password. If secure storage is unavailable, the connection stays session-only." checked={form.remember} onChange={remember => setForm({ ...form, remember })} disabled={busy} />
    </Focusable><ErrorText text={error} /><Focusable className="fe-actions" flow-children="row"><DialogButton disabled={busy || !form.host || !form.share} onClick={async () => {
      setBusy(true); setError(''); try { const r = await api<{ path: string }>('connect', { profile: form }); closeModal?.(); connected(r.path); } catch (e) { setError(message(e)); setBusy(false); }
    }}>{busy ? 'Connecting…' : 'Connect'}</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

export function PlacesDialog({ places, choose, closeModal }: { places: Place[]; choose: (path: string) => void; closeModal?: () => void }) {
  const select = (path: string) => { choose(path); closeModal?.(); };
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column"><h2>Locations</h2>
    <Focusable className="fe-places fe-stack" flow-children="column">{places.map(p => <DialogButton key={p.path} onClick={() => select(p.path)}>{p.name}</DialogButton>)}</Focusable>
    <Focusable className="fe-actions" flow-children="row"><DialogButton onClick={() => openDialog(<ConnectDialog connected={select} />)}>Add SMB share</DialogButton>
      <DialogButton onClick={() => openDialog(<TextDialog title="Go to folder" description="Enter an absolute local path. Mounted NFS and GVFS shares work as folders." submit={async path => select(path)} />)}>Enter path</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}
