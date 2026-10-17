import { DialogButton, DropdownItem, Focusable, ModalRoot, SliderField } from '@decky/ui';
import { useEffect, useState } from 'react';
import { api, bytes, Job, message } from './api';
import { DestinationInfo, DialogHeading, ErrorText, openDialog } from './dialogs';
import { css } from './style';
import { showConflict } from './ConflictDialog';

export const pendingJob = (job: Job) => ['running', 'queued', 'paused'].includes(job.status);
export const parallelJob = (job: Job) => ['copy', 'move', 'pack', 'extract', 'trash', 'delete', 'empty_trash'].includes(job.action);

export function useTransferJobs(initial: Job[]) {
  const [jobs, setJobs] = useState(initial);
  useEffect(() => {
    let alive = true, pending = false;
    const update = async () => {
      if (pending) return;
      pending = true;
      try { const result = await api<Job[]>('jobs'); if (alive) setJobs(result); }
      catch { /* Keep the last known queue; submission still validates it. */ }
      finally { pending = false; }
    };
    void update();
    const timer = window.setInterval(() => void update(), 750);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);
  return jobs;
}

export function CopyDialog({ count, destination, existing, action = 'copy', submit, closeModal }: {
  count: number; destination: string; existing: Job[];
  action?: 'copy' | 'move' | 'extract';
  submit: (mode: string, parallel: number) => Promise<void>; closeModal?: () => void;
}) {
  const [parallel, setParallel] = useState(false), [limit, setLimit] = useState(Math.min(2, count));
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const liveJobs = useTransferJobs(existing);
  const occupied = liveJobs.some(pendingJob), canParallel = !liveJobs.some(j => pendingJob(j) && !parallelJob(j));
  const verb = action === 'move' ? 'Move' : action === 'extract' ? 'Extract' : 'Copy';
  async function start(mode: string) {
    setBusy(true); setError('');
    try { await submit(mode, parallel ? limit : 1); closeModal?.(); }
    catch (e) { setError(message(e)); setBusy(false); }
  }
  return <ModalRoot className="fe-operation-modal" onCancel={busy ? undefined : closeModal} closeModal={busy ? undefined : closeModal}><style>{css}</style>
    <Focusable className="fe-dialog fe-pack-dialog fe-copy-dialog" flow-children="column">
      <DialogHeading>{verb} {count} item{count === 1 ? '' : 's'}?</DialogHeading>
      <Focusable className="fe-stack fe-pack-fields" flow-children="column">
        <DestinationInfo path={destination} />
        {action === 'move' && <p className="fe-description">Source items are removed only after a successful move. Transfers between disks or shares are verified first.</p>}
        <p className="fe-description">{action === 'extract' ? 'Extract into the other panel. Whole archives create a new folder.' : 'If a name already exists, choose change name, overwrite, backup or cancel.'}</p>
        {count > 1 && <>
          <DropdownItem label="Selected items" selectedOption={parallel} disabled={busy} rgOptions={[{ data: false, label: 'One at a time' }, { data: true, label: 'In parallel' }]} onChange={o => setParallel(o.data)} />
          {parallel && count > 2 && <SliderField label="Simultaneous transfers" layout="below" min={2} max={Math.min(5, count)} step={1} value={limit} showValue disabled={busy} onChange={setLimit} />}
          <p className="fe-description">{parallel ? `Up to ${limit} selected items at once.` : 'Each selected file or folder waits for the previous one.'} Folders include all their contents.</p>
        </>}
        {occupied && <p className="fe-description">Another transfer is active or waiting. Run alongside it, or add this selection after the existing queue.</p>}
        <p className="fe-description">At most 5 transfers run at once. Items using the same files wait until those files are available. You can keep browsing, editing or playing media.</p>
      </Focusable>
      <ErrorText text={error} />
      <Focusable className="fe-stack fe-copy-actions" flow-children="column">
        {occupied ? <>
          <DialogButton preferredFocus disabled={busy || !canParallel} onClick={() => void start('parallel')}>{verb} in parallel</DialogButton>
          <DialogButton disabled={busy} onClick={() => void start('queue')}>Add to queue</DialogButton>
        </> : <DialogButton preferredFocus disabled={busy} onClick={() => void start('now')}>{verb}</DialogButton>}
        <DialogButton disabled={busy} onClick={closeModal}>Cancel</DialogButton>
      </Focusable>
    </Focusable>
  </ModalRoot>;
}

function TransferDetails({ initial, cancel, closeModal }: { initial: Job; cancel: (job: Job) => void; closeModal?: () => void }) {
  const [job, setJob] = useState(initial), [error, setError] = useState('');
  useEffect(() => {
    let alive = true, pending = false;
    const timer = window.setInterval(async () => {
      if (pending) return; pending = true;
      try { const next = await api<Job>('job', { job_id: initial.id }); if (alive && next) setJob(next); }
      catch (e) { if (alive) setError(message(e)); } finally { pending = false; }
    }, 500);
    return () => { alive = false; window.clearInterval(timer); };
  }, [initial.id]);
  return <ModalRoot onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog" flow-children="column">
    <h2>Transfer details</h2><p className="fe-description">{job.label}<br />{job.phase} • {job.status}<br />{job.percent}% • {bytes(job.bytes)} / {bytes(job.total_bytes)} • {bytes(job.speed || 0)}/s<br />{job.current}</p>
    <ErrorText text={error || job.error} />
    <Focusable className="fe-stack" flow-children="column">
      {pendingJob(job) && <DialogButton onClick={() => cancel(job)}>{job.status === 'running' ? 'Cancel transfer…' : 'Remove from queue…'}</DialogButton>}
      <DialogButton onClick={closeModal}>Close</DialogButton>
    </Focusable>
  </Focusable></ModalRoot>;
}

export const showTransfer = (job: Job, cancel: (job: Job) => void) => job.conflict ? showConflict(job) : openDialog(<TransferDetails initial={job} cancel={cancel} />);

export function TransfersDialog({ cancel, closeModal }: { cancel: (job: Job) => void; closeModal?: () => void }) {
  const [jobs, setJobs] = useState<Job[]>([]), [error, setError] = useState('');
  useEffect(() => {
    let alive = true, pending = false;
    const update = async () => {
      if (pending) return; pending = true;
      try { const result = await api<Job[]>('jobs'); if (alive) setJobs(result.filter(pendingJob)); }
      catch (e) { if (alive) setError(message(e)); } finally { pending = false; }
    };
    void update(); const timer = window.setInterval(() => void update(), 1000);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);
  return <ModalRoot className="fe-operation-modal" onCancel={closeModal} closeModal={closeModal}><style>{css}</style><Focusable className="fe-dialog fe-pack-dialog" flow-children="column">
    <h2>Transfers</h2><p className="fe-description">{jobs.filter(j => j.status === 'running').length} running • {jobs.filter(j => j.status === 'queued').length} waiting • {jobs.filter(j => j.status === 'paused').length} paused</p>
    <ErrorText text={error} /><Focusable className="fe-stack fe-pack-fields fe-queue-items" flow-children="column">
      {jobs.map((job, index) => <DialogButton key={job.id} preferredFocus={index === 0} onClick={() => showTransfer(job, cancel)}><span className="fe-task-title">{job.label}</span><span className="fe-task-info">{job.conflict ? 'Name conflict • Choose an action' : job.status === 'running' ? `${job.percent}% • ${bytes(job.speed || 0)}/s` : job.status === 'paused' ? 'Paused after shutdown' : 'Waiting in queue'}</span></DialogButton>)}
      {!jobs.length && <p className="fe-description">No active or queued transfers.</p>}
    </Focusable><Focusable className="fe-actions" flow-children="row">
      {jobs.some(j => j.status === 'paused') && <DialogButton onClick={async () => { try { setJobs((await api<Job[]>('resume_queue')).filter(pendingJob)); } catch (e) { setError(message(e)); } }}>Resume queue</DialogButton>}
      <DialogButton onClick={closeModal}>Close</DialogButton>
    </Focusable>
  </Focusable></ModalRoot>;
}
