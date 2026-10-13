import { toaster } from '@decky/api';
import { api } from './api';
import { explorerVisible } from './activity';
import { Icon } from './Icon';
import { UpdateCandidate } from './Updates';
import { ConfirmDialog, openDialog, RecoveryDialog } from './dialogs';

type Notice = { id: string; kind: string; label: string; milestone: number | string; error: string; recoverable: boolean };
export function startNotifications(openExplorer: () => void) {
  let stopped = false, pending = false;
  let updatePending = false;
  const checkStartup = async () => {
    if (stopped || updatePending) return;
    updatePending = true;
    try {
      const update = await api<UpdateCandidate | null>('startup_update');
      if (stopped || !update) return;
      toaster.toast({ title: 'FileExplorer update available', body: `Version ${update.version} is available on GitHub. Open FileExplorer → Update to install.`,
        icon: <Icon size={24} />, logo: <Icon size={48} />, duration: 8000, playSound: false });
    } catch { /* Startup may precede backend readiness; retry without a toast. */ }
    finally { updatePending = false; }
  };
  const poll = async () => {
    if (stopped || pending) return;
    pending = true;
    try {
      const events = await api<Notice[]>('notifications', { visible: explorerVisible() });
      if (stopped) return;
      for (const event of events) {
        if (event.recoverable && ['error', 'cancelled'].includes(String(event.milestone)) && !explorerVisible()) {
          openDialog(<RecoveryDialog error={`${event.label}: ${event.error}`} openExplorer={openExplorer}
            resume={async () => { await api('retry', { job_id: event.id, mode: 'resume' }); }}
            restart={() => openDialog(<ConfirmDialog title="Start the copy again?" description="Copy all selected items into a new FileExplorer retry folder in the original destination. Previous completed files and partial copies will be kept." action="Start again" submit={async () => { await api('retry', { job_id: event.id, mode: 'restart' }); }} />)} />);
          continue;
        }
        const verb = event.kind === 'extract' ? 'Extracted' : 'Copied';
        toaster.toast({ title: 'FileExplorer', body: typeof event.milestone === 'number'
          ? `${verb} ${event.milestone}% of ${event.label}${event.milestone === 100 ? ' • Done' : ''}`
          : `${event.milestone === 'error' ? 'Operation failed' : 'Operation cancelled'}: ${event.label}`,
          subtext: typeof event.milestone === 'string' ? event.error : undefined,
          icon: <Icon size={24} />, logo: <Icon size={48} />, duration: 5000, playSound: false });
      }
    } catch { /* Reconnect on the next poll when Decky is reloading. */ }
    finally { pending = false; }
  };
  const timer = window.setInterval(() => void poll(), 1000);
  const updateTimer = window.setInterval(() => void checkStartup(), 60000);
  // Let Decky finish loading before presenting a startup notification.
  const startupTimer = window.setTimeout(() => void checkStartup(), 12000);
  void poll();
  return () => { stopped = true; window.clearInterval(timer); window.clearInterval(updateTimer); window.clearTimeout(startupTimer); };
}
