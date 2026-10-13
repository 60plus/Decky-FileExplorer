import { DialogButton, Focusable, GamepadButton, GamepadEvent, ModalRoot } from '@decky/ui';
import { useEffect, useRef, useState } from 'react';
import { api, bytes, Entry, message } from './api';
import { useAppearance, useModalStyle } from './appearance';
import { Legend } from './Legend';
import { css } from './style';
import { isImage } from './fileTypes';
type ImageData = { data: string; mime: string; size: number; width: number; height: number };
const stop = (event: { preventDefault: () => void; stopPropagation: () => void }) => { event.preventDefault(); event.stopPropagation(); };

export function ImageViewer({ entries, selected, folder, closeModal }: { entries: Entry[]; selected: string; folder: string; closeModal?: () => void }) {
  const [items] = useState(() => entries.filter(e => !e.directory && !e.link && isImage(e.name)));
  const [index, setIndex] = useState(() => Math.max(0, items.findIndex(e => e.path === selected)));
  const [image, setImage] = useState<{ location: string; value: ImageData } | null>(null), [error, setError] = useState('');
  const root = useRef<HTMLDivElement>(null), appearance = useAppearance();
  useModalStyle(root, appearance);
  const current = items[index], shown = image?.location === current?.path ? image.value : null;
  useEffect(() => {
    let active = true;
    setImage(null); setError('');
    if (current) void api<ImageData>('image', { location: current.path }).then(value => { if (active) setImage({ location: current.path, value }); }).catch(e => { if (active) setError(message(e)); });
    return () => { active = false; };
  }, [current?.path]);
  function move(amount: number) { if (items.length > 1) setIndex(old => (old + amount + items.length) % items.length); }
  useEffect(() => {
    const doc = root.current?.ownerDocument;
    const navigate = (event: Event) => {
      const e = event as GamepadEvent;
      if (!root.current?.contains(e.target as Node)) return;
      if (e.detail.button === GamepadButton.DIR_LEFT || e.detail.button === GamepadButton.DIR_RIGHT) {
        stop(e); move(e.detail.button === GamepadButton.DIR_LEFT ? -1 : 1);
      }
    };
    // Handle directions before a focused toolbar button uses Steam's navigation.
    doc?.addEventListener('vgp_ondirection', navigate, true);
    return () => doc?.removeEventListener('vgp_ondirection', navigate, true);
  }, [items.length]);
  function direction(e: GamepadEvent) {
    if (e.detail.button === GamepadButton.DIR_LEFT || e.detail.button === GamepadButton.DIR_RIGHT) {
      stop(e); move(e.detail.button === GamepadButton.DIR_LEFT ? -1 : 1);
    }
  }
  return <ModalRoot className="fe-modal" style={appearance} bAllowFullSize bHideCloseIcon onCancel={closeModal} closeModal={closeModal}><style>{css}</style>
    <Focusable ref={root} className="fe-app fe-image-viewer" flow-children="column" onGamepadDirection={direction}
      onCancelButton={e => { stop(e); closeModal?.(); }} onCancelActionDescription="Close image"
      onButtonDown={e => { if (e.detail.button === GamepadButton.BUMPER_LEFT || e.detail.button === GamepadButton.BUMPER_RIGHT) { stop(e); move(e.detail.button === GamepadButton.BUMPER_LEFT ? -1 : 1); } }}
      onKeyDown={e => { if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { stop(e); move(e.key === 'ArrowLeft' ? -1 : 1); } }}
      actionDescriptionMap={{ [GamepadButton.BUMPER_LEFT]: 'Previous image', [GamepadButton.BUMPER_RIGHT]: 'Next image' }}>
      <header className="fe-header"><div className="fe-image-title"><strong>{current?.name || 'Image preview'}</strong><div className="fe-subtitle">{index + 1} / {items.length} images in this folder{shown && ` • ${shown.width} × ${shown.height} • ${bytes(shown.size)}`}</div><div className="fe-image-folder" title={folder}>{folder}</div></div></header>
      <Focusable noFocusRing className="fe-image-stage" preferredFocus aria-label="Image preview">
        {error ? <div className="fe-error" role="alert">{error}<br />Use left or right to open another image.</div> : shown ? <img key={current.path} src={shown.data} alt={current.name} draggable={false} onError={() => setError('This image could not be decoded. The file may be damaged or use unsupported encoding.')} /> : <div className="fe-muted" role="status">Loading image…</div>}
      </Focusable>
      <Focusable className="fe-toolbar" flow-children="row"><DialogButton className="fe-btn" disabled={items.length < 2} onClick={() => move(-1)}>← Previous</DialogButton><DialogButton className="fe-btn" disabled={items.length < 2} onClick={() => move(1)}>Next →</DialogButton><DialogButton className="fe-btn" onClick={closeModal}>Close</DialogButton></Focusable>
      <Legend />
    </Focusable>
  </ModalRoot>;
}
