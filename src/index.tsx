import { definePlugin } from '@decky/api';
import { DialogButton, DropdownItem, Focusable, GamepadButton, Navigation, PanelSection, PanelSectionRow, QuickAccessTab, SliderField, ToggleField, staticClasses } from '@decky/ui';
import { ReactNode, useEffect, useRef, useState, useSyncExternalStore } from 'react';
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

const legendModes = ['panel', 'steam', 'both', 'none'];
const legendLabels = ['Panel only', 'Steam bar only', 'Both', 'Hidden'];
const extractionLimits = [10, 50, 100, 500, 0];

function Setting({ name, help, children }: { name: string; help: string; children: ReactNode }) {
  const [expanded, setExpanded] = useState(false);
  const description = useRef<HTMLDivElement>(null);
  useEffect(() => { if (expanded) description.current?.scrollIntoView({ block: 'nearest' }); }, [expanded]);
  return <PanelSectionRow><div className="fe-setting" data-setting={name}>
    <Focusable className="fe-setting-row" noFocusRing onSecondaryActionDescription={expanded ? 'Hide help' : 'Help'}
      onButtonDown={e => { if (e.detail.button === GamepadButton.DIR_UP || e.detail.button === GamepadButton.DIR_DOWN) setExpanded(false); }}
      onKeyDown={e => { if (e.key === 'ArrowUp' || e.key === 'ArrowDown') setExpanded(false); }}
      onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setExpanded(false); }}
      onSecondaryButton={e => { e.preventDefault(); e.stopPropagation(); setExpanded(value => !value); }}>
      <div className="fe-setting-control">{children}</div>
    </Focusable>
    {expanded && <div ref={description} className="fe-setting-help" role="note">{help}</div>}
  </div></PanelSectionRow>;
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
    if (state?.job?.status !== 'running') return;
    const timer = window.setInterval(() => void refresh(), 1000);
    return () => window.clearInterval(timer);
  }, [state?.job?.status]);
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
  return <PanelSection title="Settings"><div ref={root} className="fe-settings"><PanelSectionRow><DialogButton onClick={back}>‹ Back</DialogButton></PanelSectionRow><ErrorText text={error} />
    {state && <>
      <Setting name="Show hidden files" help="Include names starting with a dot and SMB files marked as hidden."><ToggleField label="Show hidden files" checked={state.settings.show_hidden} onChange={value => void change({ show_hidden: value })} /></Setting>
      <Setting name="Folders first" help="Group folders before files in both panels."><ToggleField label="Folders first" checked={state.settings.folders_first} onChange={value => void change({ folders_first: value })} /></Setting>
      <Setting name="Remember folders" help="Restore each panel's last folder when FileExplorer opens. When disabled, both panels start at Home."><ToggleField label="Remember folders" checked={state.settings.remember_paths} onChange={value => void change({ remember_paths: value })} /></Setting>
      <Setting name="Startup update check" help="Check GitHub and notify once per OS boot if a newer release is available. Manual checks in Update stay available when this is off."><ToggleField label="Startup update check" checked={state.settings.check_updates_on_start} onChange={value => void change({ check_updates_on_start: value })} /></Setting>
      <Setting name="Sort by" help="Sort names alphabetically, sizes from largest to smallest, or modification dates from newest to oldest."><DropdownItem label="Sort by" rgOptions={[{ data: 'name', label: 'Name' }, { data: 'size', label: 'Size' }, { data: 'modified', label: 'Last modified' }]} selectedOption={state.settings.sort_by} onChange={option => void change({ sort_by: option.data })} /></Setting>
      <Setting name="Extraction limit" help="Maximum unpacked size per archive. Move fully right for Unlimited to remove the size cap. The destination and temporary storage still need enough free space."><SliderField label={<span className="fe-slider-label">Extraction limit <b>{state.settings.extraction_limit_gib ? `${state.settings.extraction_limit_gib} GiB` : 'Unlimited'}</b></span>} layout="below" value={Math.max(0, extractionLimits.indexOf(state.settings.extraction_limit_gib))} min={0} max={4} step={1} notchCount={5} notchTicksVisible showValue={false} onChange={value => void change({ extraction_limit_gib: extractionLimits[Math.round(value)] })} /></Setting>
      <PanelSectionRow><div className="fe-appearance-preview" style={appearanceStyle(state.settings)}><strong>Appearance</strong><div className="fe-preview-row">Aa • Files and text</div><div className="fe-swatches">{Object.entries(accents).map(([name, color]) => <span key={name} style={{ background: color, outline: state.settings.accent === name ? '2px solid white' : undefined }} />)}</div></div></PanelSectionRow>
      <Setting name="Accent color" help="Choose the highlight color for panels, selections and the editor."><DropdownItem label="Accent color" rgOptions={Object.keys(accents).map(data => ({ data, label: data[0].toUpperCase() + data.slice(1) }))} selectedOption={state.settings.accent} onChange={o => void change({ accent: o.data })} /></Setting>
      <Setting name="Panel opacity" help="Change the background opacity. Text and icons stay fully visible. Reopen FileExplorer to apply."><SliderField label="Panel opacity" layout="below" value={state.settings.opacity} min={70} max={100} step={15} notchCount={3} notchTicksVisible showValue valueSuffix="%" onChange={value => void change({ opacity: Math.round(value) })} /></Setting>
      <Setting name="Interface scale" help="Smaller controls fit more content in the same window. Applies to the file manager, editor and image viewer after reopening. 100% is the default."><SliderField label="Interface scale" layout="below" value={state.settings.ui_scale ?? 100} min={70} max={100} step={10} notchCount={4} notchTicksVisible showValue valueSuffix="%" onChange={value => void change({ ui_scale: Math.round(value) })} /></Setting>
      <Setting name="Text size" help="Change the size of file names and editor text separately from the overall interface scale."><DropdownItem label="Text size" rgOptions={[{ data: 12, label: 'Small' }, { data: 14, label: 'Default' }, { data: 16, label: 'Large' }, { data: 18, label: 'Extra large' }]} selectedOption={state.settings.text_size} onChange={o => void change({ text_size: o.data })} /></Setting>
      <Setting name="Controller legend" help="Show matching controller hints on the FileExplorer panel, on Steam's bottom bar, on both, or hide both. Reopen FileExplorer to apply."><SliderField label={<span className="fe-slider-label">Controller legend <b>{legendLabels[Math.max(0, legendModes.indexOf(state.settings.legend_mode || 'both'))]}</b></span>} layout="below" value={Math.max(0, legendModes.indexOf(state.settings.legend_mode || 'both'))} min={0} max={3} step={1} notchCount={4} notchTicksVisible showValue={false} onChange={value => void change({ legend_mode: legendModes[Math.round(value)] })} /></Setting>
      <div className="fe-settings-actions">
      <Setting name="Reset appearance" help="Restore the default accent color, opacity, interface scale and text size. Folder, network and transfer settings stay unchanged."><DialogButton onClick={() => void change(defaultAppearance)}>Reset appearance</DialogButton></Setting>
      <Setting name="Empty Trash" help="Empty the shared SteamOS Trash, including files trashed in Desktop Mode. A confirmation appears before anything is deleted."><DialogButton disabled={state.job?.status === 'running'} onClick={() => openDialog(<EmptyTrashDialog submit={async () => { await api('start', { action: 'empty_trash', sources: [] }); await refresh(); }} />)}>Empty Trash…</DialogButton></Setting>
      </div>
      {state.job?.action === 'empty_trash' && <PanelSectionRow><div role="status" style={{ fontSize: 13 }}>{state.job.status === 'running' ? 'Emptying Trash…' : state.job.status === 'done' ? 'Trash emptied.' : state.job.error}</div></PanelSectionRow>}
      {state.connections.length > 0 && <div className="fe-settings-connections"><Setting name="Saved connections" help="Stored SMB profiles and login details. Select a connection to forget it; confirmation is required."><div className="fe-saved-profiles"><strong>Saved connections</strong><div className="fe-panel-stack">{state.connections.map(c => <PanelSectionRow key={c.id}><DialogButton onClick={() => openDialog(<ConfirmDialog title="Forget connection?" description={`${c.label}\nStored login details will be removed.`} action="Forget" submit={async () => { await api('forget', { key: c.id }); await refresh(); }} />)}>{c.label} • Forget</DialogButton></PanelSectionRow>)}</div></div></Setting></div>}
    </>}
  </div></PanelSection>;
}

function AboutPanel({ back }: { back: () => void }) {
  return <PanelSection title="About"><div className="fe-panel-stack"><PanelSectionRow><DialogButton onClick={back}>‹ Back</DialogButton></PanelSectionRow>
    <PanelSectionRow><div style={{ textAlign: 'center', padding: '12px 0', color: '#65d8e2' }}><Icon size={48} /><h3 style={{ color: 'white', margin: '10px 0 4px' }}>FileExplorer</h3><div style={{ color: '#a5b5c5', fontSize: 13 }}>Version {version}</div><div style={{ color: '#a5b5c5', fontSize: 13, marginTop: 14 }}>by</div><img src={authorLogo} alt="60plus" style={{ display: 'block', width: 144, height: 144, objectFit: 'contain', margin: '6px auto 0' }} /></div></PanelSectionRow>
    <PanelSectionRow><div style={{ fontSize: 13, lineHeight: 1.6 }}>Two panels. One controller.<br />Copy files, unpack archives and browse your network shares.</div></PanelSectionRow>
    <PanelSectionRow><DialogButton onClick={() => Navigation.NavigateToExternalWeb('https://github.com/60plus/Decky-FileExplorer')}>Source code on GitHub</DialogButton></PanelSectionRow>
  </div></PanelSection>;
}

type SidebarPage = 'home' | 'settings' | 'about' | 'update';
// Decky can remount the sidebar while a modal is open. Keep navigation outside
// the mounted component so the modal's Settings button targets the live sidebar.
let sidebar = { page: 'home' as SidebarPage, focusExtraction: false, homeFocus: 'launch' };
const sidebarListeners = new Set<() => void>();
const subscribeSidebar = (listener: () => void) => { sidebarListeners.add(listener); return () => { sidebarListeners.delete(listener); }; };
function navigateSidebar(page: SidebarPage, focusExtraction = false, homeFocus = sidebar.homeFocus) {
  sidebar = { page, focusExtraction, homeFocus };
  for (const listener of sidebarListeners) listener();
}

function launchExplorer() {
  navigateSidebar('home', false, 'launch'); Navigation.CloseSideMenus();
  openDialog(<Explorer openSettings={() => { navigateSidebar('settings', true); Navigation.OpenQuickAccessMenu(QuickAccessTab.Decky); }} />);
}

function Content() {
  const { page, focusExtraction, homeFocus } = useSyncExternalStore(subscribeSidebar, () => sidebar);
  const home = useRef<HTMLDivElement>(null);
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
  return <Focusable noFocusRing onCancelActionDescription={page === 'home' ? undefined : 'Back'}
    onCancelButton={page === 'home' ? undefined : e => { e.preventDefault(); e.stopPropagation(); back(); }}>
    <style>{css}</style>{page === 'update' ? <UpdatePanel back={back} /> : page === 'settings' ? <SettingsPanel back={back} focusExtraction={focusExtraction} /> : page === 'about' ? <AboutPanel back={back} /> :
    <PanelSection><div ref={home} className="fe-panel-stack">
      <PanelSectionRow><DialogButton data-page="launch" onClick={launchExplorer}>Launch FileExplorer</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton data-page="settings" onClick={() => navigateSidebar('settings')}>Settings</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton data-page="update" onClick={() => navigateSidebar('update')}>Update</DialogButton></PanelSectionRow>
      <PanelSectionRow><DialogButton data-page="about" onClick={() => navigateSidebar('about')}>About</DialogButton></PanelSectionRow>
    </div></PanelSection>}</Focusable>;
}

export default definePlugin(() => {
  const stopNotifications = startNotifications(launchExplorer);
  return { name: 'FileExplorer', titleView: <div className={staticClasses.Title}>FileExplorer</div>, content: <Content />, icon: <Icon />, onDismount: () => { stopNotifications(); closeAllDialogs(); } };
});
