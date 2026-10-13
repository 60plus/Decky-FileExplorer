import { DialogButton, Focusable, GamepadButton, GamepadEvent, ModalRoot, getFocusNavController } from '@decky/ui';
import { useEffect, useRef, useState } from 'react';
import { api, Entry, message } from './api';
import { useAppearance, useModalStyle } from './appearance';
import { mediaType } from './fileTypes';
import { Legend, stickHint } from './Legend';
import { css } from './style';

type Stream = { token: string; url: string; mime: string; size: number; cover: string | null; compatibility: boolean; duration: number | null; has_video: boolean };
const stopEvent = (e: { preventDefault: () => void; stopPropagation: () => void }) => { e.preventDefault(); e.stopPropagation(); };
const clock = (value: number) => {
  const total = Math.max(0, Math.floor(Number.isFinite(value) ? value : 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
};
function Speaker() {
  return <svg className="fe-speaker" viewBox="0 0 120 120" fill="none" aria-label="Audio without embedded cover">
    <circle cx="60" cy="60" r="57" fill="currentColor" opacity=".08" />
    <path d="M25 48h17l20-17v58L42 72H25Z" fill="currentColor" />
    <path d="M75 45a22 22 0 0 1 0 30m11-42a39 39 0 0 1 0 54" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
  </svg>;
}

export function MediaPlayer({ entries, selected, closeModal }: { entries: Entry[]; selected: string; closeModal?: () => void }) {
  const [items] = useState(() => {
    const kind = mediaType(entries.find(e => e.path === selected)?.name || '')?.split('/')[0];
    return entries.filter(e => !e.directory && !e.link && mediaType(e.name)?.split('/')[0] === kind);
  });
  const [index, setIndex] = useState(() => Math.max(0, items.findIndex(e => e.path === selected)));
  const [stream, setStream] = useState<Stream | null>(null), [error, setError] = useState('');
  const [playing, setPlaying] = useState(false), [position, setPosition] = useState(0), [duration, setDuration] = useState(0);
  const [fullscreen, setFullscreen] = useState(false), [waiting, setWaiting] = useState(true);
  const [compatibility, setCompatibility] = useState(false), [offset, setOffset] = useState(0), [seekRevision, setSeekRevision] = useState(0);
  const root = useRef<HTMLDivElement>(null), player = useRef<HTMLVideoElement>(null), stage = useRef<HTMLDivElement>(null);
  const appearance = useAppearance();
  useModalStyle(root, appearance);
  const current = items[index], video = !!mediaType(current?.name || '')?.startsWith('video/');
  const currentStream = useRef<Stream | null>(null);
  const toolbarActive = useRef(false), wantPlay = useRef(true);

  useEffect(() => {
    let live = true, token: string | undefined;
    const element = player.current;
    setStream(null); currentStream.current = null; wantPlay.current = true; setError(''); setPosition(0); setDuration(0); setPlaying(false); setWaiting(true); setCompatibility(false); setOffset(0);
    const mime = mediaType(current?.name || '');
    if (current) {
      void api<Stream>('open_media', { location: current.path }).then(value => {
        token = value.token;
        if (live) {
          currentStream.current = value; setStream(value); if (value.duration) setDuration(value.duration);
          if (element && mime && !element.canPlayType(mime) && value.compatibility) setCompatibility(true);
        }
        else void api('close_media', { token }).catch(() => {});
      }).catch(e => { if (live) { setError(message(e)); setWaiting(false); } });
    }
    return () => {
      live = false;
      if (element) { element.pause(); element.removeAttribute('src'); element.load(); }
      if (token) void api('close_media', { token }).catch(() => {});
    };
  }, [current?.path]);

  useEffect(() => {
    const modal = root.current?.closest<HTMLElement>('.fe-modal');
    modal?.classList.toggle('fe-media-fullscreen', fullscreen);
    return () => modal?.classList.remove('fe-media-fullscreen');
  }, [fullscreen]);

  async function playPause() {
    const element = player.current;
    if (!element || !currentStream.current || error) return;
    if (!element.paused) { wantPlay.current = false; element.pause(); }
    else {
      wantPlay.current = true;
      try { await element.play(); }
      catch (e) {
        if ((e as DOMException).name !== 'AbortError' && (e as DOMException).name !== 'NotAllowedError') setError('Playback failed. The file may be damaged or its codec is unavailable in Steam.');
      }
    }
  }
  function seek(delta: number) {
    const element = player.current;
    if (element) seekTo((compatibility ? offset : 0) + element.currentTime + delta);
  }
  function seekTo(value: number) {
    const element = player.current;
    const target = Math.max(0, duration ? Math.min(duration - .05, value) : value);
    if (!element) return;
    if (compatibility) {
      wantPlay.current = !element.paused; setOffset(target); setSeekRevision(n => n + 1); setPosition(target); setWaiting(true);
    } else if (Number.isFinite(element.duration)) element.currentTime = target;
  }
  function halt() {
    wantPlay.current = false;
    const element = player.current;
    if (element) { element.pause(); if (compatibility) { setOffset(0); setSeekRevision(n => n + 1); setPosition(0); } else if (element.readyState) element.currentTime = 0; }
    setPlaying(false); setWaiting(false);
  }
  function move(delta: number) {
    if (items.length > 1) { halt(); setIndex(old => (old + delta + items.length) % items.length); }
  }
  function back() { if (fullscreen) setFullscreen(false); else closeModal?.(); }
  function focus(element: HTMLElement | null | undefined) {
    const find = (node: any): any => node?.Element === element ? node : node?.GetChildren?.().map(find).find(Boolean);
    const target = find(getFocusNavController()?.GetActiveNavTree?.()?.Root);
    if (target) target.BTakeFocus(); else element?.focus();
  }
  function toolbar() {
    focus(toolbarActive.current ? stage.current : root.current?.querySelector<HTMLElement>('.fe-toolbar button:not(:disabled)'));
  }
  function buttons(e: GamepadEvent) {
    if (e.detail.button === GamepadButton.BUMPER_LEFT) { stopEvent(e); move(-1); }
    else if (e.detail.button === GamepadButton.BUMPER_RIGHT) { stopEvent(e); move(1); }
    else if (e.detail.button === GamepadButton.RSTICK_CLICK) { stopEvent(e); toolbar(); }
  }
  function direction(e: GamepadEvent) {
    if (e.detail.button === GamepadButton.DIR_LEFT || e.detail.button === GamepadButton.DIR_RIGHT) { stopEvent(e); seek(e.detail.button === GamepadButton.DIR_LEFT ? -10 : 10); }
  }
  return <ModalRoot className="fe-modal" style={appearance} bAllowFullSize bHideCloseIcon onCancel={back} closeModal={back}><style>{css}</style>
    <Focusable ref={root} className={`fe-app fe-media-player${fullscreen ? ' fe-media-expanded' : ''}`} flow-children="column" onButtonDown={buttons}
      onCancelButton={e => { stopEvent(e); back(); }} onCancelActionDescription={fullscreen ? 'Back' : 'Close'}
      onSecondaryButton={e => { stopEvent(e); halt(); }} onSecondaryActionDescription="Stop"
      onOptionsButton={e => { stopEvent(e); if (video) setFullscreen(value => !value); }} onOptionsActionDescription={video ? 'Fullscreen' : undefined}
      actionDescriptionMap={{ [GamepadButton.BUMPER_LEFT]: 'Previous', [GamepadButton.BUMPER_RIGHT]: 'Next', [GamepadButton.DIR_LEFT]: '−10 s', [GamepadButton.DIR_RIGHT]: '+10 s', [GamepadButton.RSTICK_CLICK]: stickHint('Toolbar') }}>
      <header className="fe-header"><div className="fe-image-title"><strong>{current?.name || 'Media player'}</strong><div className="fe-subtitle">{index + 1} / {items.length} {video ? 'videos' : 'audio files'} in this folder{compatibility && ' • Compatibility playback'}</div></div></header>
      <Focusable noFocusRing ref={stage} className={`fe-media-stage ${video ? 'fe-video-stage' : 'fe-audio-stage'}`} preferredFocus
        onGamepadFocus={() => { toolbarActive.current = false; }}
        onActivate={e => { stopEvent(e); void playPause(); }} onOKActionDescription={playing ? 'Pause' : 'Play'} onClick={() => void playPause()}
        onGamepadDirection={direction} onKeyDown={e => {
          if (['ArrowLeft', 'ArrowRight', ' '].includes(e.key)) { stopEvent(e); if (e.key === ' ') void playPause(); else seek(e.key === 'ArrowLeft' ? -10 : 10); }
        }} aria-label={video ? 'Video playback' : 'Audio playback'}>
        <video ref={player} src={stream ? compatibility ? `${stream.url}/compat?start=${offset}&revision=${seekRevision}` : stream.url : undefined} preload="metadata" playsInline disablePictureInPicture
          style={video && !error ? undefined : { display: 'none' }}
          onLoadedMetadata={() => {
            const element = player.current, source = currentStream.current;
            // Some Steam builds silently discard Theora video and play only audio.
            if (video && source?.has_video && !element?.videoWidth && !compatibility && source.compatibility) { setCompatibility(true); setWaiting(true); return; }
            const length = element?.duration;
            if (length && Number.isFinite(length) && (!compatibility || !source?.duration)) setDuration(length + offset);
            setWaiting(false); if (wantPlay.current && element?.paused) void playPause();
          }}
          onTimeUpdate={() => setPosition(offset + (player.current?.currentTime || 0))} onDurationChange={() => { const length = player.current?.duration; if (length && Number.isFinite(length) && (!compatibility || !currentStream.current?.duration)) setDuration(length + offset); }}
          onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onPlaying={() => setWaiting(false)} onWaiting={() => setWaiting(true)}
          onSeeked={() => setWaiting(false)} onEnded={() => { setPlaying(false); setWaiting(false); }}
          onError={() => { if (currentStream.current) { if (!compatibility && currentStream.current.compatibility) { setCompatibility(true); setWaiting(true); setError(''); } else { setWaiting(false); setError('Cannot play this file. Its codec may be unsupported, the file may be damaged, or the network connection was interrupted.'); } } }} />
        {!video && !error && <div className="fe-audio-art">{stream?.cover ? <img src={stream.cover} alt="Embedded album cover" onError={e => { e.currentTarget.style.display = 'none'; setStream(s => s ? { ...s, cover: null } : s); }} /> : <Speaker />}</div>}
        {error ? <div className="fe-media-overlay fe-error" role="alert">{error}</div> : waiting && <div className="fe-media-overlay fe-muted" role="status">{stream ? 'Buffering…' : 'Opening media…'}</div>}
      </Focusable>
      <div className="fe-media-timeline"><span>{clock(position)}</span><div role="progressbar" aria-label="Playback position" aria-valuenow={position} aria-valuemax={duration || 0} className="fe-media-track"
        onClick={e => { const box = e.currentTarget.getBoundingClientRect(); if (duration) seekTo(duration * Math.max(0, Math.min(1, (e.clientX - box.left) / box.width))); }}><div style={{ width: `${duration ? position / duration * 100 : 0}%` }} /></div><span>{clock(duration)}</span></div>
      <Focusable className="fe-toolbar" flow-children="row" onGamepadFocus={() => { toolbarActive.current = true; }}>
        <DialogButton className="fe-btn" disabled={items.length < 2} onClick={() => move(-1)}>Previous</DialogButton>
        <DialogButton className="fe-btn" disabled={!duration || !!error} onClick={() => seek(-10)}>−10 s</DialogButton>
        <DialogButton className="fe-btn" disabled={!stream || !!error} onClick={() => void playPause()}>{playing ? 'Pause' : 'Play'}</DialogButton>
        <DialogButton className="fe-btn" disabled={!duration || !!error} onClick={() => seek(10)}>+10 s</DialogButton>
        <DialogButton className="fe-btn" disabled={!stream} onClick={halt}>Stop</DialogButton>
        <DialogButton className="fe-btn" disabled={items.length < 2} onClick={() => move(1)}>Next</DialogButton>
        {video && <DialogButton className="fe-btn" onClick={() => setFullscreen(value => !value)}>{fullscreen ? 'Window' : 'Fullscreen'}</DialogButton>}
        <DialogButton className="fe-btn" onClick={back}>Close</DialogButton>
      </Focusable>
      <Legend />
    </Focusable>
  </ModalRoot>;
}
