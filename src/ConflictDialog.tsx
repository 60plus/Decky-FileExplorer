import { DialogButton, Focusable, GamepadButton, ModalRoot, NavEntryPositionPreferences } from '@decky/ui';
import { useEffect, useState } from 'react';
import { api, Conflict, Job, message } from './api';
import { ChoiceDialog, ConfirmDialog, DestinationInfo, DialogHeading, ErrorText, openDialog, revealExplorer, TextDialog } from './dialogs';
import { css } from './style';
import { takeConflictIntent } from './conflictIntent';
import { Glyph } from './Glyph';

let opened: string | undefined;
const shown = new Set<string>();
export function showConflict(job: Pick<Job, 'id' | 'action' | 'conflict'>, automatic = false, openExplorer?: () => void) {
  if (!job.conflict || opened || automatic && shown.has(job.conflict.id)) return false;
  opened = job.conflict.id; shown.add(opened);
  openDialog(<ConflictDialog jobId={job.id} action={job.action} conflict={job.conflict} openExplorer={openExplorer} initialChoice={takeConflictIntent(job.id)} />);
  return true;
}

function ConflictDialog({ jobId, action, conflict, closeModal, openExplorer, initialChoice }: { jobId: string; action: string; conflict: Conflict; closeModal?: () => void; openExplorer?: () => void; initialChoice?: 'rename' | 'overwrite' }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  useEffect(() => { if (initialChoice === 'rename') rename(); else if (initialChoice === 'overwrite') overwrite(); }, []);
  useEffect(() => {
    const timer = window.setInterval(() => {
      void api<Job>('job', { job_id: jobId }).then(job => {
        if (job.status !== 'running' || job.conflict?.id !== conflict.id) closeModal?.();
      }).catch(() => {});
    }, 700);
    return () => { window.clearInterval(timer); if (opened === conflict.id) opened = undefined; };
  }, []);
  async function choose(choice: string) {
    setBusy(true); setError('');
    try { await api('resolve_conflict', { job_id: jobId, conflict_id: conflict.id, choice }); closeModal?.(); }
    catch (e) { setError(message(e)); setBusy(false); }
  }
  const name = (path: string) => path.startsWith('smb://') ? decodeURIComponent(path.split('/').pop() || path) : path.split('/').pop() || path;
  function rename() {
    openDialog(<TextDialog title="Change incoming name" initial={name(conflict.target)} description="Give the incoming item a different name. The existing destination item stays unchanged." submit={async value => {
      await api('resolve_conflict', { job_id: jobId, conflict_id: conflict.id, choice: 'rename', name: value }); closeModal?.();
    }} />);
  }
  function overwrite() {
    openDialog(<ChoiceDialog title="Replace the existing item?" description={`${conflict.directory ? 'The entire destination folder will be replaced, including old-only files. Folders are not merged.' : 'Replace the existing destination file.'}\n\nBack up & replace keeps it as ${name(conflict.backup)}. Overwrite permanently removes it after the replacement is ready.`} choices={[
      { label: 'Back up & replace', run: async () => { await api('resolve_conflict', { job_id: jobId, conflict_id: conflict.id, choice: 'backup' }); closeModal?.(); } },
      { label: 'Overwrite', danger: true, run: async () => { await api('resolve_conflict', { job_id: jobId, conflict_id: conflict.id, choice: 'overwrite' }); closeModal?.(); } },
      { label: 'Cancel', run: async () => {} },
    ]} />);
  }
  function restart() {
    openDialog(<ConfirmDialog title="Start again?" description="Start the remaining items in a new FileExplorer retry folder. Existing destination items and any partial copy are kept. This avoids the current name conflict." action="Start again" submit={async () => {
      await api('restart_conflict', { job_id: jobId, conflict_id: conflict.id }); closeModal?.();
    }} />);
  }
  return <ModalRoot className="fe-operation-modal" onCancel={busy ? undefined : closeModal} closeModal={busy ? undefined : closeModal}><style>{css}</style>
    <Focusable className="fe-dialog fe-pack-dialog fe-conflict-dialog" flow-children="column">
      <DialogHeading>{action === 'move' ? 'Move' : 'Copy'} interrupted</DialogHeading>
      <Focusable className="fe-pack-fields" flow-children="column">
        <p className="fe-description"><strong>Name conflict • {conflict.directory ? 'Folder' : 'File'} already exists</strong></p>
        <DestinationInfo path={conflict.target} />
        <p className="fe-description">Change name keeps both items. Overwrite offers replacement with or without a backup.</p>
        <p className="fe-description">Resume after removing the conflict, or start again in a new folder.<br /><Glyph button={GamepadButton.CANCEL} label="Back button" /> or Open FileExplorer leaves this transfer waiting.</p>
      </Focusable>
      <ErrorText text={error} />
      <Focusable className="fe-conflict-actions" flow-children="column">
        <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
          <DialogButton disabled={busy} onClick={() => void choose('resume')}>Resume</DialogButton>
          <DialogButton disabled={busy} onClick={restart}>Start again</DialogButton>
        </Focusable>
        <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
          <DialogButton preferredFocus disabled={busy} onClick={rename}>Change name</DialogButton>
          <DialogButton className="fe-destructive" disabled={busy} onClick={overwrite}>Overwrite</DialogButton>
        </Focusable>
        <Focusable className="fe-actions" flow-children="row" navEntryPreferPosition={NavEntryPositionPreferences.MAINTAIN_X}>
          <DialogButton disabled={busy} onClick={() => void choose('cancel')}>Cancel</DialogButton>
          <DialogButton disabled={busy} onClick={() => revealExplorer(openExplorer)}>Open FileExplorer</DialogButton>
        </Focusable>
      </Focusable>
    </Focusable>
  </ModalRoot>;
}
