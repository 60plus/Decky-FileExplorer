import { DialogButton, DropdownItem, Focusable, ModalRoot, SliderField, TextField } from '@decky/ui';
import { useState } from 'react';
import { Job, message } from './api';
import { parallelJob, pendingJob, useTransferJobs } from './Transfers';
import { ErrorText } from './dialogs';
import { css } from './style';

export type PackOptions = { format: string; level: number; name: string };
const formats = [
  { data: 'zip', label: 'ZIP (.zip)' }, { data: '7z', label: '7z (.7z)' },
  { data: 'tar', label: 'TAR (.tar)' }, { data: 'tar.gz', label: 'TAR + gzip (.tar.gz)' },
  { data: 'tar.bz2', label: 'TAR + bzip2 (.tar.bz2)' }, { data: 'tar.xz', label: 'TAR + xz (.tar.xz)' },
];
export function PackDialog({ count, initialName, folders, existing = [], submit, closeModal }: {
  count: number; initialName: string; folders: { data: string; label: string }[];
  existing?: Job[];
  submit: (destination: string, options: PackOptions, mode: string) => Promise<void>; closeModal?: () => void;
}) {
  const [name, setName] = useState(initialName), [format, setFormat] = useState('zip');
  const [level, setLevel] = useState(5), [destination, setDestination] = useState(folders[0].data);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const liveJobs = useTransferJobs(existing);
  const occupied = liveJobs.some(pendingJob);
  const [mode, setMode] = useState('parallel');
  const canParallel = !liveJobs.some(j => pendingJob(j) && !parallelJob(j));
  const minimum = format.startsWith('tar.') ? 1 : 0;
  const effective = format === 'tar' ? 0 : Math.max(minimum, level);
  const output = name.toLowerCase().endsWith('.' + format) ? name : `${name}.${format}`;
  return <ModalRoot className="fe-operation-modal" onCancel={closeModal} closeModal={closeModal}><style>{css}</style>
    <Focusable className="fe-dialog fe-pack-dialog" flow-children="column">
      <h2>Create archive</h2>
      <div className="fe-description">Pack {count} selected item{count === 1 ? '' : 's'}. Original files are kept.</div>
      <Focusable className="fe-stack fe-pack-fields" flow-children="column">
        <TextField label="Archive name" value={name} disabled={busy} onChange={e => setName(e.target.value)} />
        <DropdownItem label="Format" rgOptions={formats} selectedOption={format} onChange={o => setFormat(o.data)} disabled={busy} />
        <DropdownItem label="Save in" rgOptions={folders} selectedOption={destination} onChange={o => setDestination(o.data)} disabled={busy} />
        <SliderField className="fe-pack-option" label="Compression" layout="below" min={minimum} max={9} step={1} value={effective}
          disabled={busy || format === 'tar'} showValue onChange={setLevel} />
        <div className="fe-description">{effective === 0 ? 'No compression.' : `${effective}/9. Lower is faster; higher can make a smaller archive and use more memory.`}<br />The operation continues in the background.</div>
        <div className="fe-archive-output">{output}</div>
        {occupied && <DropdownItem label="Other transfers" selectedOption={canParallel ? mode : 'queue'} disabled={busy}
          rgOptions={[...(canParallel ? [{ data: 'parallel', label: 'Pack in parallel' }] : []), { data: 'queue', label: 'Add to queue' }]} onChange={o => setMode(o.data)} />}
        {occupied && <div className="fe-description">Up to 5 transfers can run at once. Files used by another transfer wait until available.</div>}
      </Focusable>
      <ErrorText text={error} />
      <Focusable className="fe-actions" flow-children="row">
        <DialogButton disabled={busy || !name.trim()} onClick={async () => {
          setBusy(true); setError('');
          try { await submit(destination, { format, level: effective, name: name.trim() }, occupied ? canParallel ? mode : 'queue' : 'now'); closeModal?.(); }
          catch (e) { setError(message(e)); setBusy(false); }
        }}>{busy ? 'Starting…' : 'Create archive'}</DialogButton>
        <DialogButton onClick={closeModal}>Cancel</DialogButton>
      </Focusable>
    </Focusable>
  </ModalRoot>;
}
