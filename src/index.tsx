import { definePlugin } from '@decky/api';
import { DialogButton, DropdownItem, Navigation, PanelSection, PanelSectionRow, ToggleField, staticClasses } from '@decky/ui';
import { useEffect, useState } from 'react';
import { api, message, Settings, State } from './api';
import { closeAllDialogs, ConfirmDialog, EmptyTrashDialog, ErrorText, openDialog } from './dialogs';
import { startNotifications } from './notifications';
import { UpdatePanel } from './Updates';
import { Explorer } from './Explorer';
import { Icon } from './Icon';
import { css } from './style';
import { accents, appearanceStyle, defaultAppearance } from './appearance';
import authorLogo from '../images/logo60plus.png';
import { version } from '../package.json';

function SettingsPanel({ back }: { back: () => void }) {
  const [state, setState] = useState<State | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const refresh = () => api<State>('state').then(setState).catch(e => setError(message(e)));
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (state?.job?.status !== 'running') return;
    const timer = window.setInterval(() => void refresh(), 1000);
    return () => window.clearInterval(timer);
  }, [state?.job?.status]);
  async function change(changes: Partial<Settings>) {
    setBusy(true); setError('');
    try { setState(await api<State>('settings', { changes })); } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  return <PanelSection title="Settings"><PanelSectionRow><DialogButton onClick={back}>‹ Back</DialogButton></PanelSectionRow><ErrorText text={error} />
    {state && <>
      <PanelSectionRow><ToggleField label="Show hidden files" description="Include names starting with a dot and SMB hidden files." checked={state.settings.show_hidden} disabled={busy} onChange={value => void change({ show_hidden: value })} /></PanelSectionRow>
      <PanelSectionRow><ToggleField label="Folders first" checked={state.settings.folders_first} disabled={busy} onChange={value => void change({ folders_first: value })} /></PanelSectionRow>
      <PanelSectionRow><ToggleField label="Remember folders" checked={state.settings.remember_paths} disabled={busy} onChange={value => void change({ remember_paths: value })} /></PanelSectionRow>
      <PanelSectionRow><ToggleField label="Check for updates at startup" description="Check GitHub and notify once per OS boot if an update is available. Manual checks stay available in Update." checked={state.settings.check_updates_on_start} disabled={busy} onChange={value => void change({ check_updates_on_start: value })} /></PanelSectionRow>
      <PanelSectionRow><DropdownItem label="Sort by" rgOptions={[{ data: 'name', label: 'Name' }, { data: 'size', label: 'Size' }, { data: 'modified', label: 'Last modified' }]} selectedOption={state.settings.sort_by} onChange={option => void change({ sort_by: option.data })} disabled={busy} /></PanelSectionRow>
      <PanelSectionRow><DropdownItem label="Extraction limit" description="Maximum unpacked size per archive." rgOptions={[10, 50, 100, 500].map(n => ({ data: n, label: `${n} GiB` }))} selectedOption={state.settings.extraction_limit_gib} onChange={option => void change({ extraction_limit_gib: option.data })} disabled={busy} /></PanelSectionRow>
      <PanelSectionRow><div className="fe-appearance-preview" style={appearanceStyle(state.settings)}><strong>Appearance</strong><div className="fe-preview-row">Aa • Files and text</div><div className="fe-swatches">{Object.entries(accents).map(([name, color]) => <span key={name} style={{ background: color, outline: state.settings.accent === name ? '2px solid white' : undefined }} />)}</div></div></PanelSectionRow>
      <PanelSectionRow><DropdownItem label="Accent color" rgOptions={Object.keys(accents).map(data => ({ data, label: data[0].toUpperCase() + data.slice(1) }))} selectedOption={state.settings.accent} onChange={o => void change({ accent: o.data })} disabled={busy} /></PanelSectionRow>
      <PanelSectionRow><DropdownItem label="Panel opacity" description="Changes the background; text stays fully visible." rgOptions={[70, 85, 100].map(data => ({ data, label: `${data}%` }))} selectedOption={state.settings.opacity} onChange={o => void change({ opacity: o.data })} disabled={busy} /></PanelSectionRow>
      <PanelSectionRow><DropdownItem label="Text size" description="File rows and the text editor." rgOptions={[{ data: 12, label: 'Small' }, { data: 14, label: 'Default' }, { data: 16, label: 'Large' }, { data: 18, label: 'Extra large' }]} selectedOption={state.settings.text_size} onChange={o => void change({ text_size: o.data })} disabled={busy} /></PanelSectionRow>
      <PanelSectionRow><DialogButton disabled={busy} onClick={() => void change(defaultAppearance)}>Reset appearance</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton disabled={busy || state.job?.status === 'running'} onClick={() => openDialog(<EmptyTrashDialog submit={async () => { await api('start', { action: 'empty_trash', sources: [] }); await refresh(); }} />)}>Empty Trash…</DialogButton></PanelSectionRow>
      {state.job?.action === 'empty_trash' && <PanelSectionRow><div role="status" style={{ fontSize: 13 }}>{state.job.status === 'running' ? 'Emptying Trash…' : state.job.status === 'done' ? 'Trash emptied.' : state.job.error}</div></PanelSectionRow>}
      {state.connections.length > 0 && <PanelSectionRow><div className="fe-panel-stack"><div>Saved connections</div>{state.connections.map(c => <DialogButton key={c.id} onClick={() => openDialog(<ConfirmDialog title="Forget connection?" description={`${c.label}\nStored login details will be removed.`} action="Forget" submit={async () => { await api('forget', { key: c.id }); await refresh(); }} />)}>{c.label} • Forget</DialogButton>)}</div></PanelSectionRow>}
    </>}
  </PanelSection>;
}

function AboutPanel({ back }: { back: () => void }) {
  return <PanelSection title="About"><div className="fe-panel-stack"><PanelSectionRow><DialogButton onClick={back}>‹ Back</DialogButton></PanelSectionRow>
    <PanelSectionRow><div style={{ textAlign: 'center', padding: '12px 0', color: '#65d8e2' }}><Icon size={48} /><h3 style={{ color: 'white', margin: '10px 0 4px' }}>FileExplorer</h3><div style={{ color: '#a5b5c5', fontSize: 13 }}>Version {version}</div><div style={{ color: '#a5b5c5', fontSize: 13, marginTop: 14 }}>by</div><img src={authorLogo} alt="60plus" style={{ display: 'block', width: 144, height: 144, objectFit: 'contain', margin: '6px auto 0' }} /></div></PanelSectionRow>
    <PanelSectionRow><div style={{ fontSize: 13, lineHeight: 1.6 }}>Two panels. One controller.<br />Copy files, unpack archives and browse your network shares.</div></PanelSectionRow>
    <PanelSectionRow><DialogButton onClick={() => Navigation.NavigateToExternalWeb('https://github.com/60plus/Decky-FileExplorer')}>Source code on GitHub</DialogButton></PanelSectionRow>
  </div></PanelSection>;
}

function Content() {
  const [page, setPage] = useState<'home' | 'settings' | 'about' | 'update'>('home');
  return <><style>{css}</style>{page === 'update' ? <UpdatePanel back={() => setPage('home')} /> : page === 'settings' ? <SettingsPanel back={() => setPage('home')} /> : page === 'about' ? <AboutPanel back={() => setPage('home')} /> :
    <PanelSection><div className="fe-panel-stack">
      <PanelSectionRow><DialogButton onClick={() => { Navigation.CloseSideMenus(); openDialog(<Explorer />); }}>Launch FileExplorer</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton onClick={() => setPage('settings')}>Settings</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton onClick={() => setPage('update')}>Update</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton onClick={() => setPage('about')}>About</DialogButton></PanelSectionRow>
    </div></PanelSection>}</>;
}

export default definePlugin(() => {
  const stopNotifications = startNotifications();
  return { name: 'FileExplorer', titleView: <div className={staticClasses.Title}>FileExplorer</div>, content: <Content />, icon: <Icon />, onDismount: () => { stopNotifications(); closeAllDialogs(); } };
});
