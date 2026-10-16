import { definePlugin } from '@decky/api';
import { DialogButton, DropdownItem, Focusable, GamepadButton, Navigation, PanelSection, PanelSectionRow, QuickAccessTab, SliderField, ToggleField, staticClasses } from '@decky/ui';
import { ReactNode, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { api, message, Profile, Settings, State } from './api';
import { closeAllDialogs, ConfirmDialog, EmptyTrashDialog, ErrorText, openDialog } from './dialogs';
import { useMenuWrapping } from './navigation';
import { profileLabels, SetupDialog } from './Setup';
import { startNotifications } from './notifications';
import { UpdatePanel } from './Updates';
import { HeartIcon, SupportPanel } from './Support';
import { Explorer } from './Explorer';
import { installGameFolderButton } from './GameFolderButton';
import { Icon } from './Icon';
import { SettingHelp, settingHelp } from './SettingHelp';
import { SplashDialog } from './Splash';
import { css } from './style';
import { accents, appearanceStyle, defaultAppearance } from './appearance';
import authorLogo from '../images/logo60plus.png';
import { version } from '../package.json';

const legendModes = ['panel', 'steam', 'both', 'none'];
const legendLabels = ['Panel only', 'Steam bar only', 'Both', 'Hidden'];
const extractionLimits = [10, 50, 100, 500, 0];

function Setting({ name, help, children }: { name: string; help: ReactNode; children: ReactNode }) {
  return <PanelSectionRow><SettingHelp name={name} help={help}>{children}</SettingHelp></PanelSectionRow>;
}

function SettingsPanel({ back, focusExtraction = false }: { back: () => void; focusExtraction?: boolean }) {
  const [state, setState] = useState<State | null>(null), [error, setError] = useState('');
  const revision = useRef(0), writes = useRef(Promise.resolve());
  const root = useRef<HTMLDivElement>(null), focusedExtraction = useRef(false);
  const refresh = () => api<State>('state').then(setState).catch(e => setError(message(e)));
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!state || !focusExtraction || focusedExtraction.current) return;
    const owner = root.current?.ownerDocument.defaultView;
    if (!owner) return;
    const timer = owner.setTimeout(() => {
      const slider = root.current?.querySelector<HTMLElement>('[data-setting="Extraction limit"] [role="slider"]');
      if (!slider) return;
      // Focus the field, without entering Steam's nested slider editing mode.
      (slider.closest('[role="button"]') || slider).dispatchEvent(new owner.CustomEvent('vgp_requestfocus', { bubbles: true, cancelable: true, detail: { button: 1, source: 0 } }));
      slider.scrollIntoView({ block: 'center' });
      focusedExtraction.current = true;
    }, 250);
    return () => owner.clearTimeout(timer);
  }, [!!state, focusExtraction]);
  useEffect(() => {
    if (!state?.jobs?.some(j => ['running', 'queued', 'paused'].includes(j.status)) && state?.job?.status !== 'running') return;
    const timer = window.setInterval(() => void refresh(), 1000);
    return () => window.clearInterval(timer);
  }, [state?.job?.status, state?.jobs?.some(j => ['running', 'queued', 'paused'].includes(j.status))]);
  async function change(changes: Partial<Settings>) {
    const current = ++revision.current;
    setError('');
    setState(old => old && ({ ...old, settings: { ...old.settings, ...changes } }));
    // Keep slider input responsive and save rapid controller steps in order.
    const saved = writes.current.then(() => api<State>('settings', { changes }));
    writes.current = saved.then(() => {}, () => {});
    try { const next = await saved; if (current === revision.current) setState(next); }
    catch (e) { if (current === revision.current) { setError(message(e)); void refresh(); } }

  }
  return <PanelSection title="Settings"><div ref={root} className="fe-settings"><PanelSectionRow><DialogButton onClick={back}>‹ Back</DialogButton></PanelSectionRow><ErrorText text={error || state?.credential_error || ''} />
    {state && <>
      <Setting name="Show hidden files" help={settingHelp['Show hidden files']}><ToggleField label="Show hidden files" checked={state.settings.show_hidden} onChange={value => void change({ show_hidden: value })} /></Setting>
      <Setting name="Folders first" help={settingHelp['Folders first']}><ToggleField label="Folders first" checked={state.settings.folders_first} onChange={value => void change({ folders_first: value })} /></Setting>
      <Setting name="Remember folders" help={settingHelp['Remember folders']}><ToggleField label="Remember folders" checked={state.settings.remember_paths} onChange={value => void change({ remember_paths: value })} /></Setting>
      <Setting name="Startup update check" help={settingHelp['Startup update check']}><ToggleField label="Startup update check" checked={state.settings.check_updates_on_start} onChange={value => void change({ check_updates_on_start: value })} /></Setting>
      <Setting name="Sort by" help={settingHelp['Sort by']}><DropdownItem label="Sort by" rgOptions={[{ data: 'name', label: 'Name' }, { data: 'size', label: 'Size' }, { data: 'modified', label: 'Date modified' }]} selectedOption={state.settings.sort_by} onChange={option => void change({ sort_by: option.data })} /></Setting>
      <Setting name="Extraction limit" help="Maximum unpacked size per archive. Move fully right for Unlimited to remove the size cap. The destination and temporary storage still need enough free space."><SliderField label={<span className="fe-slider-label">Extraction limit <b>{state.settings.extraction_limit_gib ? `${state.settings.extraction_limit_gib} GiB` : 'Unlimited'}</b></span>} layout="below" value={Math.max(0, extractionLimits.indexOf(state.settings.extraction_limit_gib))} min={0} max={4} step={1} notchCount={5} notchTicksVisible showValue={false} onChange={value => void change({ extraction_limit_gib: extractionLimits[Math.round(value)] })} /></Setting>
      <PanelSectionRow><div className="fe-appearance-preview" style={appearanceStyle(state.settings)}><strong>Appearance</strong><div className="fe-preview-row">Aa • Files and text</div><div className="fe-swatches">{Object.entries(accents).map(([name, color]) => <span key={name} style={{ background: color, outline: state.settings.accent === name ? '2px solid white' : undefined }} />)}</div></div></PanelSectionRow>
      <Setting name="Accent color" help={settingHelp['Accent color']}><DropdownItem label="Accent color" rgOptions={Object.keys(accents).map(data => ({ data, label: data[0].toUpperCase() + data.slice(1) }))} selectedOption={state.settings.accent} onChange={o => void change({ accent: o.data })} /></Setting>
      <Setting name="Panel opacity" help={settingHelp['Panel opacity']}><SliderField label="Panel opacity" layout="below" value={state.settings.opacity} min={70} max={100} step={15} notchCount={3} notchTicksVisible showValue valueSuffix="%" onChange={value => void change({ opacity: Math.round(value) })} /></Setting>
      <Setting name="Interface scale" help={settingHelp['Interface scale']}><SliderField label="Interface scale" layout="below" value={state.settings.ui_scale ?? 100} min={70} max={100} step={10} notchCount={4} notchTicksVisible showValue valueSuffix="%" onChange={value => void change({ ui_scale: Math.round(value) })} /></Setting>
      <Setting name="Text size" help={settingHelp['Text size']}><DropdownItem label="Text size" rgOptions={[{ data: 12, label: 'Small' }, { data: 14, label: 'Default' }, { data: 16, label: 'Large' }, { data: 18, label: 'Extra large' }]} selectedOption={state.settings.text_size} onChange={o => void change({ text_size: o.data })} /></Setting>
      <Setting name="Controller legend" help={settingHelp['Controller legend']}><SliderField label={<span className="fe-slider-label">Controller legend <b>{legendLabels[Math.max(0, legendModes.indexOf(state.settings.legend_mode || 'both'))]}</b></span>} layout="below" value={Math.max(0, legendModes.indexOf(state.settings.legend_mode || 'both'))} min={0} max={3} step={1} notchCount={4} notchTicksVisible showValue={false} onChange={value => void change({ legend_mode: legendModes[Math.round(value)] })} /></Setting>
      <Setting name="Hide toolbar" help={settingHelp['Hide toolbar']}><ToggleField label="Hide toolbar" checked={!!state.settings.toolbar_hidden} onChange={value => void change({ toolbar_hidden: value })} /></Setting>
      <Setting name="Splash screen" help={settingHelp['Splash screen']}><ToggleField label="Splash screen" checked={!!state.settings.splash_enabled} onChange={value => void change({ splash_enabled: value })} /></Setting>
      <div className="fe-settings-actions">
      <Setting name="First-time setup" help={`Choose the Handheld or Steam PC profile again and review its settings before saving. Current profile: ${profileLabels[state.settings.profile as Profile] || 'none chosen yet'}.`}><DialogButton onClick={() => openSetup(() => void refresh())}>Run first-time setup…</DialogButton></Setting>
      <Setting name="Reset appearance" help="Restore the default accent color, opacity, interface scale and text size. Folder, network and transfer settings stay unchanged."><DialogButton onClick={() => void change(defaultAppearance)}>Reset appearance</DialogButton></Setting>
      <Setting name="Empty Trash" help="Empty the shared SteamOS Trash, including files trashed in Desktop Mode. A confirmation appears before anything is deleted."><DialogButton disabled={state.job?.status === 'running'} onClick={() => openDialog(<EmptyTrashDialog submit={async () => { await api('start', { action: 'empty_trash', sources: [] }); await refresh(); }} />)}>Empty Trash…</DialogButton></Setting>
      </div>
      {state.job?.action === 'empty_trash' && <PanelSectionRow><div role="status" style={{ fontSize: 13 }}>{state.job.status === 'running' ? 'Emptying Trash…' : state.job.status === 'done' ? 'Trash emptied.' : state.job.error}</div></PanelSectionRow>}
      {state.connections.length > 0 && <div className="fe-settings-connections"><Setting name="Saved connections" help="Saved passwords are encrypted for this device and user, using TPM when available or the system key without TPM. No unlock password. Session-only connections are not saved. Select a connection to forget it."><div className="fe-saved-profiles"><strong>Saved connections</strong><div className="fe-panel-stack">{state.connections.map(c => <PanelSectionRow key={c.id}><DialogButton onClick={() => openDialog(<ConfirmDialog title="Forget connection?" description={`${c.label}\n${c.saved ? c.password_storage === 'tpm' ? 'Password encrypted with TPM and the system key.' : c.password_storage === 'system' ? 'Password encrypted with the system key (no TPM).' : c.password_storage === 'legacy' ? 'Password migration is pending.' : c.password_storage === 'unavailable' ? 'Encrypted password is unavailable.' : 'No password stored.' : 'Session only; password is not saved.'}\nLogin details will be removed.`} action="Forget" submit={async () => { await api('forget', { key: c.id }); await refresh(); }} />)}>{c.label}{!c.saved ? ' (session)' : ''} • Forget</DialogButton></PanelSectionRow>)}</div></div></Setting></div>}
    </>}
  </div></PanelSection>;
}

function AboutPanel({ back }: { back: () => void }) {
  return <PanelSection title="About"><div className="fe-panel-stack"><PanelSectionRow><DialogButton onClick={back}>‹ Back</DialogButton></PanelSectionRow>
    <PanelSectionRow><div style={{ textAlign: 'center', padding: '12px 0', color: '#65d8e2' }}><Icon size={48} /><h3 style={{ color: 'white', margin: '10px 0 4px' }}>FileExplorer</h3><div style={{ color: '#a5b5c5', fontSize: 13 }}>Version {version}</div><div style={{ color: '#a5b5c5', fontSize: 13, marginTop: 14 }}>by</div><img src={authorLogo} alt="60plus" style={{ display: 'block', width: 144, height: 144, objectFit: 'contain', margin: '6px auto 0' }} /></div></PanelSectionRow>
    <PanelSectionRow><div className="fe-message" style={{ fontSize: 13, lineHeight: 1.6 }}>Two panels. One controller.<br />Copy files, unpack archives and browse your network shares.</div></PanelSectionRow>
    <PanelSectionRow><DialogButton onClick={() => Navigation.NavigateToExternalWeb('https://github.com/60plus/Decky-FileExplorer')}>Source code on GitHub</DialogButton></PanelSectionRow>
  </div></PanelSection>;
}

type SidebarPage = 'home' | 'settings' | 'about' | 'update' | 'support';
// Decky can remount the sidebar while a modal is open. Keep navigation outside
// the mounted component so the modal's Settings button targets the live sidebar.
let sidebar = { page: 'home' as SidebarPage, focusExtraction: false, homeFocus: 'launch' };
const sidebarListeners = new Set<() => void>();
const subscribeSidebar = (listener: () => void) => { sidebarListeners.add(listener); return () => { sidebarListeners.delete(listener); }; };
function navigateSidebar(page: SidebarPage, focusExtraction = false, homeFocus = sidebar.homeFocus) {
  sidebar = { page, focusExtraction, homeFocus };
  for (const listener of sidebarListeners) listener();
}

function openExplorer(initialPath?: string) {
  openDialog(<Explorer initialPath={initialPath} openSettings={() => { navigateSidebar('settings', true); Navigation.OpenQuickAccessMenu(QuickAccessTab.Decky); }} />, true);
}

// A second Launch press while the state request is pending or the setup is
// open must not open a second window. The flag is set synchronously before the
// modal opens and cleared by Steam's own close callback on every close path.
let launching = false, setupOpen = false;
function openSetup(saved: (state: State) => void) {
  if (setupOpen) return;
  setupOpen = true;
  try { openDialog(<SetupDialog saved={saved} />, false, () => { setupOpen = false; }); }
  catch (e) { setupOpen = false; throw e; }
}

function launchExplorer(initialPath?: string) {
  if (launching || setupOpen) return;
  launching = true;
  navigateSidebar('home', false, 'launch'); Navigation.CloseSideMenus();
  // The first launch runs the three-step setup. Cancelling it saves nothing and
  // leaves the file manager closed, so the next launch offers the setup again.
  void api<State>('state').then(async state => {
    const proceed = () => {
      launching = false;
      if (state.settings.setup_completed) openExplorer(initialPath);
      else openSetup(() => openExplorer(initialPath));
    };
    const { show } = await api<{ show: boolean }>('claim_splash');
    if (show) openDialog(<SplashDialog completed={proceed} />, false, () => { launching = false; });
    else proceed();
  }).catch(() => { launching = false; openExplorer(initialPath); });
}

function Content() {
  const { page, focusExtraction, homeFocus } = useSyncExternalStore(subscribeSidebar, () => sidebar);
  const home = useRef<HTMLDivElement>(null), marker = useRef<HTMLSpanElement>(null);
  useMenuWrapping(marker);
  useEffect(() => {
    if (page !== 'home') return;
    const owner = home.current?.ownerDocument.defaultView;
    if (!owner) return;
    const timer = owner.setTimeout(() => {
      const button = home.current?.querySelector<HTMLElement>(`[data-page="${homeFocus}"]`);
      button?.dispatchEvent(new owner.CustomEvent('vgp_requestfocus', { bubbles: true, cancelable: true, detail: { button: 1, source: 0 } }));
    }, 100);
    return () => owner.clearTimeout(timer);
  }, [page, homeFocus]);
  const back = () => navigateSidebar('home', false, page);
  return <Focusable className="fe-sidebar" noFocusRing onCancelActionDescription={page === 'home' ? undefined : 'Back'}
    onCancelButton={page === 'home' ? undefined : e => { e.preventDefault(); e.stopPropagation(); back(); }}>
    <style>{css}</style><span hidden ref={marker} />{page === 'support' ? <SupportPanel back={back} /> : page === 'update' ? <UpdatePanel back={back} /> : page === 'settings' ? <SettingsPanel back={back} focusExtraction={focusExtraction} /> : page === 'about' ? <AboutPanel back={back} /> :
    <PanelSection><div ref={home} className="fe-panel-stack">
      <PanelSectionRow><DialogButton data-page="launch" onClick={() => launchExplorer()}>Launch FileExplorer</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton data-page="settings" onClick={() => navigateSidebar('settings')}>Settings</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton data-page="update" onClick={() => navigateSidebar('update')}>Update</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton data-page="support" onClick={() => navigateSidebar('support')}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><HeartIcon />Support</span></DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton data-page="about" onClick={() => navigateSidebar('about')}>About</DialogButton></PanelSectionRow>
    </div></PanelSection>}</Focusable>;
}

export default definePlugin(() => {
  const stopNotifications = startNotifications(launchExplorer);
  const stopGameFolderButton = installGameFolderButton(launchExplorer);
  return { name: 'FileExplorer', titleView: <div className={staticClasses.Title}>FileExplorer</div>, content: <Content />, icon: <Icon />, onDismount: () => { stopNotifications(); stopGameFolderButton(); closeAllDialogs(); } };
});
