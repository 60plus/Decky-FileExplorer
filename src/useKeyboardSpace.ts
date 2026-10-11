import { CSSProperties, RefObject, useEffect, useState } from 'react';

// The editor lives in a different Steam window from the plugin's JS context.
// Measure its ownerDocument, using Steam's stable keyboard ID rather than CSS hashes.
export function useKeyboardSpace(root: RefObject<HTMLElement>) {
  const [space, setSpace] = useState({ top: 0, height: 0 });
  useEffect(() => {
    const measure = () => {
      const doc = root.current?.ownerDocument, win = doc?.defaultView;
      const keyboard = doc?.getElementById('virtual keyboard');
      const rect = keyboard?.getBoundingClientRect();
      let next = { top: 0, height: 0 };
      if (win && rect && rect.width > 0 && rect.height > 0 && rect.top < win.innerHeight && rect.bottom > 0) {
        const above = Math.max(0, rect.top), below = Math.max(0, win.innerHeight - rect.bottom);
        next = above >= below ? { top: 52, height: Math.max(100, above - 64) } :
          { top: rect.bottom + 12, height: Math.max(100, below - 32) };
      }
      setSpace(old => old.top === next.top && old.height === next.height ? old : next);
    };
    measure();
    const timer = window.setInterval(measure, 150);
    return () => window.clearInterval(timer);
  }, [root]);
  return { visible: space.height > 0, style: space.height ? {
    '--fe-editor-top': `${space.top}px`, '--fe-editor-height': `${space.height}px`,
  } as CSSProperties : {} };
}
