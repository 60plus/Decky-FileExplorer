import { DialogButton, DropdownItem, Focusable, GamepadButton, ModalRoot, SliderField, ToggleField } from '@decky/ui';
import { useEffect, useState } from 'react';
import { api, message, Profile, ProfilePresets, ProfileSettings, State } from './api';
import { accents } from './appearance';
import { DialogHeading, ErrorText } from './dialogs';
import { Glyph } from './Glyph';
import { SettingHelp } from './SettingHelp';
import { setupCss } from './setupStyle';
import { css } from './style';

export const profileLabels: Record<Profile, string> = { handheld: 'Handheld', pc: 'Steam PC' };
export const profiles: Profile[] = ['handheld', 'pc'];
const legendModes = ['panel', 'steam', 'both', 'none'];
const legendLabels = ['Panel only', 'Steam bar only', 'Both', 'Hidden'];
const legendSummary: Record<string, string> = { panel: 'Button hints sit inside the FileExplorer window.', steam: "Button hints appear on Steam's bottom bar.", both: 'Button hints appear both in the window and on the Steam bar.', none: 'No button hints are shown.' };
const textSizes: { data: number; label: string }[] = [{ data: 12, label: 'Small' }, { data: 14, label: 'Default' }, { data: 16, label: 'Large' }, { data: 18, label: 'Extra large' }];
export type SetupValues = ProfileSettings & { accent: string };

// Plain description of how a preset looks, shown on the profile buttons. The
// exact values appear on the next step, so no option names here.
export function profileSummary(values: Partial<ProfileSettings>): string[] {
  const scale = values.ui_scale ?? 100;
  return [
    scale < 100 ? 'Smaller controls leave more room for files on a small screen.' : 'Full-size controls are easy to read from the sofa or at a desk.',
    legendSummary[values.legend_mode || 'both'] || legendSummary.both,
    values.toolbar_hidden ? 'The button bar stays out of the way until you call it up.' : 'The button bar is always visible above the file panels.',
  ];
}

export function SetupDialog({ closeModal, saved, cancelled }: { closeModal?: () => void; saved?: (state: State) => void; cancelled?: () => void }) {
  const [step, setStep] = useState(1);
  const [presets, setPresets] = useState<ProfilePresets | null>(null), [accent, setAccent] = useState('cyan');
  const [profile, setProfile] = useState<Profile | null>(null), [values, setValues] = useState<SetupValues | null>(null);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    Promise.all([api<ProfilePresets>('setup_profiles'), api<State>('state')])
      .then(([loaded, state]) => { if (live) { setPresets(loaded); setAccent(state.settings.accent); } })
      .catch(e => { if (live) setError(message(e)); });
    return () => { live = false; };
  }, []);
  function choose(next: Profile) {
    if (!presets) return;
    // Start from the preset every time the profile is chosen, keeping the current accent.
    setProfile(next); setValues({ ...presets[next], accent }); setError(''); setStep(3);
  }
  const set = (changes: Partial<SetupValues>) => setValues(current => current && { ...current, ...changes });
  function back() {
    if (busy) return;
    if (step > 1) { setError(''); setStep(step - 1); return; }
    cancelled?.(); closeModal?.();
  }
  async function save() {
    if (busy || !profile || !values) return;
    setBusy(true); setError('');
    try { const state = await api<State>('setup', { profile, changes: values }); closeModal?.(); saved?.(state); }
    catch (e) { setError(message(e)); setBusy(false); }
  }
  const legend = Math.max(0, legendModes.indexOf(values?.legend_mode || 'both'));
  return <ModalRoot className="fe-setup-modal" bAllowFullSize onCancel={back} closeModal={back}><style>{css}{setupCss}</style><Focusable className="fe-dialog fe-setup" flow-children="column" data-step={step}>
    <div className="fe-setup-step">Step {step} of 3</div>
    {step === 1 && <>
      <DialogHeading>Welcome to Decky FileExplorer</DialogHeading>
      <div className="fe-setup-intro"><p>Thanks for installing Decky FileExplorer.</p><p>Choose how it should look on this device.</p>
        <ol><li>Pick the Handheld or Steam PC profile.</li><li>Review its settings and change anything you like.</li><li>Save. Every value stays editable later in Settings.</li></ol>
        <p>Profile settings change only when you save.</p><p><Glyph button={GamepadButton.CANCEL} label="Back button" /> goes back one step.</p></div>
      <ErrorText text={error} />
      <Focusable className="fe-actions" flow-children="row">
        <DialogButton preferredFocus disabled={!presets} onClick={() => { setError(''); setStep(2); }}>Continue</DialogButton>
        <DialogButton onClick={back}>Not now</DialogButton>
      </Focusable>
    </>}
    {step === 2 && presets && <>
      <DialogHeading>Choose a profile</DialogHeading>
      <p className="fe-description">Each profile sets the interface scale, controller hints and toolbar for one kind of device. You can adjust every value in the next step.</p>
      <Focusable className="fe-setup-profiles fe-stack" flow-children="column">
        {profiles.map((option, index) => <DialogButton key={option} className="fe-setup-profile" preferredFocus={profile ? option === profile : index === 0} onClick={() => choose(option)}>
          <strong>{profileLabels[option]}</strong>{profileSummary(presets[option]).map(line => <span key={line}>{line}</span>)}
        </DialogButton>)}
      </Focusable>
      <Focusable className="fe-actions" flow-children="row"><DialogButton onClick={back}>‹ Back</DialogButton></Focusable>
    </>}
    {step === 3 && profile && values && <>
      <DialogHeading>{profileLabels[profile]} settings</DialogHeading>
      <p className="fe-setup-summary"><span className="fe-setup-summary-line">Recommended settings for {profileLabels[profile]} have been selected.</span><span className="fe-setup-summary-line">Adjust them below, then Save. <Glyph button={GamepadButton.SECONDARY} label="Help button" /> explains the focused setting.</span></p>
      <Focusable className="fe-stack fe-setup-fields" flow-children="column">
        <SettingHelp name="Interface scale"><SliderField label="Interface scale" layout="below" value={values.ui_scale} min={70} max={100} step={10} notchCount={4} notchTicksVisible showValue valueSuffix="%" onChange={value => set({ ui_scale: Math.round(value) })} /></SettingHelp>
        <SettingHelp name="Controller legend"><SliderField label={<span className="fe-slider-label">Controller legend <b>{legendLabels[legend]}</b></span>} layout="below" value={legend} min={0} max={3} step={1} notchCount={4} notchTicksVisible showValue={false} onChange={value => set({ legend_mode: legendModes[Math.round(value)] })} /></SettingHelp>
        <SettingHelp name="Hide toolbar"><ToggleField label="Hide toolbar" checked={values.toolbar_hidden} onChange={value => set({ toolbar_hidden: value })} /></SettingHelp>
        <SettingHelp name="Splash screen"><ToggleField label="Splash screen" checked={values.splash_enabled} onChange={value => set({ splash_enabled: value })} /></SettingHelp>
        <SettingHelp name="Text size"><DropdownItem label="Text size" rgOptions={textSizes} selectedOption={values.text_size} onChange={option => set({ text_size: option.data })} /></SettingHelp>
        <SettingHelp name="Panel opacity"><SliderField label="Panel opacity" layout="below" value={values.opacity} min={70} max={100} step={15} notchCount={3} notchTicksVisible showValue valueSuffix="%" onChange={value => set({ opacity: Math.round(value) })} /></SettingHelp>
        <SettingHelp name="Accent color"><DropdownItem label="Accent color" rgOptions={Object.keys(accents).map(data => ({ data, label: data[0].toUpperCase() + data.slice(1) }))} selectedOption={values.accent} onChange={option => set({ accent: option.data })} /></SettingHelp>
        <SettingHelp name="Show hidden files"><ToggleField label="Show hidden files" checked={values.show_hidden} onChange={value => set({ show_hidden: value })} /></SettingHelp>
        <SettingHelp name="Folders first"><ToggleField label="Folders first" checked={values.folders_first} onChange={value => set({ folders_first: value })} /></SettingHelp>
        <SettingHelp name="Remember folders"><ToggleField label="Remember folders" checked={values.remember_paths} onChange={value => set({ remember_paths: value })} /></SettingHelp>
        <SettingHelp name="Startup update check"><ToggleField label="Startup update check" checked={values.check_updates_on_start} onChange={value => set({ check_updates_on_start: value })} /></SettingHelp>
        <SettingHelp name="Sort by"><DropdownItem label="Sort by" rgOptions={[{ data: 'name', label: 'Name' }, { data: 'size', label: 'Size' }, { data: 'modified', label: 'Date modified' }]} selectedOption={values.sort_by} onChange={option => set({ sort_by: option.data })} /></SettingHelp>
      </Focusable>
      <ErrorText text={error} />
      <Focusable className="fe-actions" flow-children="row">
        <DialogButton preferredFocus disabled={busy} onClick={() => void save()}>{busy ? 'Saving…' : 'Save'}</DialogButton>
        <DialogButton disabled={busy} onClick={back}>‹ Back</DialogButton>
      </Focusable>
    </>}
  </Focusable></ModalRoot>;
}
