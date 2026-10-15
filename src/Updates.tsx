import { DialogButton, Navigation, PanelSection, PanelSectionRow } from '@decky/ui';
import { useRef, useState } from 'react';
import { api, bytes, message } from './api';
import { ErrorText } from './dialogs';
import { version } from '../package.json';

export type UpdateCandidate = { version: string; notes: string; size: number; release_url: string };
type Result = { installed: string; latest: string | null; candidate: UpdateCandidate | null; message: string };
type Prepared = { artifact: string; version: string; sha256: string };
type Installer = { call: (method: string, ...args: unknown[]) => Promise<unknown> };

export function UpdatePanel({ back }: { back: () => void }) {
  const [result, setResult] = useState<Result | null>(null), [busy, setBusy] = useState(''), [error, setError] = useState(''), [note, setNote] = useState('');
  const running = useRef(false);
  async function run(install: boolean) {
    if (running.current) return;
    running.current = true;
    setBusy(install ? 'Downloading and verifying…' : 'Checking GitHub…'); setError(''); setNote('');
    try {
      if (!install) setResult(await api<Result>('check_updates'));
      else {
        const installer = (globalThis as unknown as { DeckyBackend?: Installer }).DeckyBackend;
        if (!installer?.call) throw new Error('This Decky version cannot open the installer. Install the ZIP from GitHub Releases.');
        const prepared = await api<Prepared>('prepare_update', { version: result?.candidate?.version });
        await installer.call('utilities/install_plugin', prepared.artifact, 'FileExplorer', prepared.version, prepared.sha256);
        setNote('Download verified. Confirm Install in the Decky prompt.');
      }
    } catch (e) { setError(message(e)); }
    finally { running.current = false; setBusy(''); }
  }
  return <PanelSection title="Update"><div className="fe-panel-stack">
    <PanelSectionRow><DialogButton disabled={!!busy} onClick={back}>‹ Back</DialogButton></PanelSectionRow>
    <PanelSectionRow><div className="fe-message" style={{ fontSize: 14, lineHeight: 1.6 }}>Installed: {version}<br />{result?.latest && <>Latest: {result.latest}<br /></>}{result?.message || 'Check the latest stable release on GitHub.'}</div></PanelSectionRow>
    <ErrorText text={error} />
    {(busy || note) && <PanelSectionRow><div className="fe-message" role="status" style={{ fontSize: 13 }}>{busy || note}</div></PanelSectionRow>}
    <PanelSectionRow><DialogButton disabled={!!busy} onClick={() => void run(false)}>Check for updates</DialogButton></PanelSectionRow>
    {result?.candidate && <>
      <PanelSectionRow><DialogButton disabled={!!busy} onClick={() => void run(true)}>Download and install {result.candidate.version}</DialogButton></PanelSectionRow>
      <PanelSectionRow><div className="fe-message" style={{ fontSize: 13 }}>{bytes(result.candidate.size)} • SHA-256 verified before installation.<br />Settings and saved connections are kept. Background transfers continue.</div></PanelSectionRow>
      <PanelSectionRow><div style={{ fontSize: 12, lineHeight: 1.5, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}><strong>Release notes</strong><br />{result.candidate.notes || 'No release notes provided.'}</div></PanelSectionRow>
    </>}
    <PanelSectionRow><DialogButton onClick={() => Navigation.NavigateToExternalWeb('https://github.com/60plus/Decky-FileExplorer/releases/latest')}>Open GitHub release</DialogButton></PanelSectionRow>
  </div></PanelSection>;
}
