import { toaster } from '@decky/api';
import { DialogButton, Focusable, ModalRoot, ToggleField, TextField } from '@decky/ui';
import { useEffect, useState } from 'react';
import { api, Entry, message } from './api';
import { ErrorText } from './dialogs';
import { Icon } from './Icon';
import { css } from './style';

type Shortcut = { location: string; name: string; executable: string; directory: string; arguments: string; windows: boolean; batch: boolean; needs_execute: boolean };
export function canAddToSteam(entry: Entry) {
  return !entry.directory && !entry.path.startsWith('archive://') && (entry.executable || /\.(exe|com|bat|cmd|sh|bash|zsh|fish|py|pl|rb|appimage|run|bin)$/i.test(entry.name));
}

export async function appDetails(appid: number): Promise<any> {
  const current = (window as any).appDetailsStore?.GetAppDetails?.(appid);
  if (current) return current;
  return new Promise((resolve, reject) => {
    let listener: { unregister: () => void } | undefined;
    let finished = false;
    const timer = window.setTimeout(() => { finished = true; listener?.unregister(); reject(new Error('Steam did not return the game details. Try again.')); }, 8000);
    listener = SteamClient.Apps.RegisterForAppDetails(appid, data => {
      if (finished) return;
      finished = true; window.clearTimeout(timer); resolve(data);
      window.setTimeout(() => listener?.unregister(), 0);
    });
  });
}

export async function folderForApp(appid: number): Promise<string> {
  const details = await appDetails(appid);
  const result = await api<{ path: string }>('game_folder', { executable: details.strShortcutExe || '', start_dir: details.strShortcutStartDir || '', install_dir: details.strInstallFolder || '' });
  return result.path;
}

export function AddToSteamDialog({ location, closeModal }: { location: string; closeModal?: () => void }) {
  const [info, setInfo] = useState<Shortcut | null>(null), [name, setName] = useState('');
  const [execute, setExecute] = useState(false), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  useEffect(() => {
    let alive = true;
    void api<Shortcut>('shortcut_info', { location }).then(value => { if (alive) { setInfo(value); setName(value.name); } }).catch(e => { if (alive) setError(message(e)); });
    return () => { alive = false; };
  }, [location]);
  async function add() {
    if (!info || busy) return;
    setBusy(true); setError('');
    try {
      const title = name.trim();
      if (!title || title.length > 128) throw new Error('Enter a name of 1–128 characters');
      const fields = await api<Shortcut>('shortcut_info', { location, make_executable: execute });
      if (fields.needs_execute) throw new Error('Allow execution before adding this application');
      const matching = ((window as any).appStore?.allApps || []).filter((app: any) => app.display_name === title && app.local_per_client_data?.installed);
      for (const app of matching) {
        const details = await appDetails(app.appid);
        if (details.strShortcutExe === fields.executable && details.strShortcutLaunchOptions === fields.arguments) {
          throw new Error('This shortcut is already in your Steam library');
        }
      }
      const id = (await SteamClient.Apps.AddShortcut(title, fields.executable, fields.directory, fields.arguments)) >>> 0;
      if (!id) throw new Error('Steam could not create the shortcut');
      // Explicit setters keep fields correct across Steam's AddShortcut variants.
      SteamClient.Apps.SetShortcutName(id, title);
      SteamClient.Apps.SetShortcutExe(id, fields.executable);
      SteamClient.Apps.SetShortcutStartDir(id, fields.directory);
      SteamClient.Apps.SetShortcutLaunchOptions(id, fields.arguments);
      toaster.toast({ title: 'Added to Steam', body: title, icon: <Icon />, duration: 5000, playSound: false });
      closeModal?.();
    } catch (e) { setError(message(e)); setBusy(false); }
  }
  return <ModalRoot className="fe-operation-modal" onCancel={closeModal} closeModal={closeModal}><style>{css}</style>
    <Focusable className="fe-dialog fe-shortcut-dialog" flow-children="column"><h2>Add to Steam</h2>
      {info && <Focusable className="fe-stack fe-pack-fields" flow-children="column">
        <TextField label="Library name" value={name} disabled={busy} onChange={e => setName(e.target.value)} />
        <div className="fe-description">Create a non-Steam library shortcut. The file will not be run now.</div>
        <div className="fe-archive-output">{info.location}</div>
        {info.windows && <div className="fe-description">Choose a Proton compatibility tool in Steam's shortcut properties if needed.{info.batch && ' BAT/CMD files may additionally need Windows cmd.exe /c in their launch configuration.'}</div>}
        {info.needs_execute && <ToggleField label="Allow this file to run" description="Adds execute permission for your Steam user." checked={execute} onChange={setExecute} disabled={busy} />}
      </Focusable>}
      <ErrorText text={error} />
      <Focusable className="fe-actions" flow-children="row"><DialogButton disabled={!info || busy || !name.trim() || info.needs_execute && !execute} onClick={() => void add()}>{busy ? 'Adding…' : 'Add to Steam'}</DialogButton><DialogButton onClick={closeModal}>Cancel</DialogButton></Focusable>
    </Focusable>
  </ModalRoot>;
}
