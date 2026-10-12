import { RefObject, useEffect, useState } from 'react';

// The editor lives in a different Steam window from the plugin's JS context.
// Measure its ownerDocument, using Steam's stable keyboard ID rather than CSS hashes.
export function useKeyboardSpace(root: RefObject<HTMLElement>) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    let ownerWindow: Window | null = null, frame = 0, retry = 0;
    let modal: HTMLElement | null = null, previous = { top: 0, height: 0 };
    const measure = () => {
      const doc = root.current?.ownerDocument, win = doc?.defaultView;
      // Decky's portal can mount after this effect. Once mounted, follow the
      // editor window's frames, not the shared plugin window's timer.
      if (!win) { retry = window.setTimeout(measure, 16); return; }
      ownerWindow = win;
      modal = root.current?.closest<HTMLElement>('.fe-modal') || null;
      const keyboard = doc?.getElementById('virtual keyboard');
      const rect = keyboard?.getBoundingClientRect();
      let next = { top: 0, height: 0 };
      if (win && rect && rect.width > 0 && rect.height > 0 && rect.top < win.innerHeight && rect.bottom > 0) {
        const above = Math.max(0, rect.top), below = Math.max(0, win.innerHeight - rect.bottom);
        next = above >= below ? { top: 52, height: Math.max(100, above - 64) } :
          { top: rect.bottom + 12, height: Math.max(100, below - 32) };
      }
      if (modal && (previous.top !== next.top || previous.height !== next.height)) {
        // Move the surface in the same frame as the keyboard. Routing every
        // animation frame through React in Steam's shared JS window delays the
        // layout and needlessly renders the entire document again.
        modal.style.setProperty('--fe-editor-top', `${next.top}px`);
        modal.style.setProperty('--fe-editor-height', `${next.height}px`);
        modal.classList.toggle('fe-keyboard-visible', next.height > 0);
        if (!!previous.height !== !!next.height) setVisible(next.height > 0);
        previous = next;
      }
      // Steam slides the keyboard using transforms. ResizeObserver alone does
      // not report those positions; a 150ms poll visibly stair-steps the panel.
      frame = win.requestAnimationFrame(measure);
    };
    measure();
    return () => {
      window.clearTimeout(retry); ownerWindow?.cancelAnimationFrame(frame);
      modal?.classList.remove('fe-keyboard-visible');
      modal?.style.removeProperty('--fe-editor-top');
      modal?.style.removeProperty('--fe-editor-height');
    };
  }, [root]);
  return { visible };
}
