import { DialogButton, Focusable, ModalRoot, NavEntryPositionPreferences, TextField, ToggleField, showModal } from '@decky/ui';
import { useState } from 'react';
import { api, message, Place } from './api';
import { css } from './style';

const dialogs = new Set<{ Close: () => void }>();
export function openDialog(element: React.ReactElement) {
  const modal = showModal(element, undefined, { bNeverPopOut: true, fnOnClose: () => dialogs.delete(modal) });
  dialogs.add(modal);
  return modal;
}
export function closeAllDialogs() { for (const modal of [...dialogs]) modal.Close(); dialogs.clear(); }
export function ErrorText({ text }: { text: string }) { return text ? <div className="fe-error" role="alert">{text}</div> : null; }

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
    <h2>{title}</h2>{description && <p className="fe-description">{description}</p>}
    <TextField value={value} onChange={e => setValue(e.target.value)} focusOnMount disabled={busy} />
    <ErrorText text={error} /><Focusable className="fe-actions" flow-children="row"><DialogButton disabled={busy || !value.trim()} onClick={() => void save()}>Save</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

export function ConfirmDialog({ title, description, action, submit, closeModal, danger }: {
  title: string; description: string; action: string; submit: () => Promise<void>; closeModal?: () => void; danger?: string;
}) {
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column">
    <h2>{title}</h2>{danger && <div className="fe-danger" role="alert"><span aria-hidden="true">!</span><strong>{danger}</strong></div>}<p className="fe-description">{description}</p><ErrorText text={error} />
    <Focusable className="fe-actions" flow-children="row"><DialogButton disabled={busy} onClick={async () => { setBusy(true); try { await submit(); closeModal?.(); } catch (e) { setError(message(e)); setBusy(false); } }}>{action}</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

export function EmptyTrashDialog({ submit, closeModal }: { submit: () => Promise<void>; closeModal?: () => void }) {
  return <ConfirmDialog title="Empty Trash?" danger="This also empties your Desktop Mode Trash!" description="FileExplorer and the SteamOS desktop use the same Trash. All trashed files, including those on connected drives, will be permanently deleted. This cannot be undone." action="Empty Trash" submit={submit} closeModal={closeModal} />;
}

export function ExtractionLimitDialog({ description, openSettings, closeModal }: { description: string; openSettings: () => void; closeModal?: () => void }) {
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column">
    <h2>Extraction limit exceeded</h2><p className="fe-description">{description}</p>
    <Focusable className="fe-actions" flow-children="row"><DialogButton onClick={() => { closeModal?.(); openSettings(); }}>Open Settings</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

export function MenuDialog({ title, actions, closeModal }: { title: string; actions: { label: string; run: () => void; disabled?: boolean }[]; closeModal?: () => void }) {
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column"><h2>{title}</h2><Focusable className="fe-stack" flow-children="column">
    {actions.map(a => <DialogButton key={a.label} disabled={a.disabled} onClick={() => { closeModal?.(); a.run(); }}>{a.label}</DialogButton>)}
  </Focusable></Focusable></ModalRoot>;
}

export function RecoveryDialog({ error, resume, restart, closeModal, openExplorer }: { error: string; resume: () => Promise<void>; restart: () => void; closeModal?: () => void; openExplorer?: () => void }) {
  const [failure, setFailure] = useState(''), [busy, setBusy] = useState(false);
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column">
    <h2>Copy interrupted</h2><p className="fe-description">{error}</p><p className="fe-description">Resume verifies saved data and continues the partial file. Start again copies everything into a new retry folder. Previous results are kept.</p><ErrorText text={failure} />
    <Focusable className="fe-recovery-actions" flow-children="column">
      <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
        <DialogButton disabled={busy} onClick={async () => { setBusy(true); try { await resume(); closeModal?.(); } catch (e) { setFailure(message(e)); setBusy(false); } }}>Resume</DialogButton>
        <DialogButton disabled={busy} onClick={() => { closeModal?.(); restart(); }}>Start again…</DialogButton>
      </Focusable>
      <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
        <DialogButton onClick={closeModal}>{openExplorer ? 'Cancel' : 'Later'}</DialogButton>
        {openExplorer && <DialogButton disabled={busy} onClick={() => { closeModal?.(); openExplorer(); }}>Open FileExplorer</DialogButton>}
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
      <ToggleField label="Remember connection" description="Saves credentials in a private file readable by your Steam user. Otherwise kept for this session only." checked={form.remember} onChange={remember => setForm({ ...form, remember })} disabled={busy} />
    </Focusable><ErrorText text={error} /><Focusable className="fe-actions" flow-children="row"><DialogButton disabled={busy || !form.host || !form.share} onClick={async () => {
      setBusy(true); setError(''); try { const r = await api<{ path: string }>('connect', { profile: form }); closeModal?.(); connected(r.path); } catch (e) { setError(message(e)); setBusy(false); }
    }}>{busy ? 'Connecting…' : 'Connect'}</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}

export function PlacesDialog({ places, choose, closeModal }: { places: Place[]; choose: (path: string) => void; closeModal?: () => void }) {
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column"><h2>Locations</h2>
    <Focusable className="fe-places fe-stack" flow-children="column">{places.map(p => <DialogButton key={p.path} onClick={() => { closeModal?.(); choose(p.path); }}>{p.name}</DialogButton>)}</Focusable>
    <Focusable className="fe-actions" flow-children="row"><DialogButton onClick={() => { closeModal?.(); openDialog(<ConnectDialog connected={choose} />); }}>Add SMB share</DialogButton>
      <DialogButton onClick={() => { closeModal?.(); openDialog(<TextDialog title="Go to folder" description="Enter an absolute local path. Mounted NFS and GVFS shares work as folders." submit={async path => choose(path)} />); }}>Enter path</DialogButton></Focusable>
  </Focusable></ModalRoot>;
}
