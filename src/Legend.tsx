import { findModuleExport, getFocusNavController } from '@decky/ui';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';

type Description = { label?: { props?: Record<string, unknown> }; props?: Record<string, unknown> };
type Actions = Record<number, Description>;
type ActionStore = { SetActionsFromMap: (map: Actions) => void };
const useActionStore = (findModuleExport(value => typeof value === 'function' && value.toString().length < 180 && value.toString().includes('?.ActionDescriptionStore')) || (() => undefined)) as () => ActionStore | undefined;
const nativeButtons = findModuleExport(value => value && typeof value === 'object' && 'LeftStickClick' in value && 'RightStickClick' in value);
const patched = new WeakMap<ActionStore, { users: number; restore: () => void }>();

// Steam's converter currently maps stick clicks to A. Mark only our labels,
// then supply those actions in Steam's native enum without changing other apps.
export const stickHint = (label: string) => <span data-fe-stick-hint>{label}</span>;
function useStickHints() {
  const contextStore = useActionStore();
  // Decky portals inherit the SharedJSContext provider. The visible Steam
  // window owns a different action store, which drives its actual footer.
  const steam = (window as unknown as { SteamUIStore?: { GetFocusedWindowInstance: () => { ActionDescriptionStore?: ActionStore } } }).SteamUIStore;
  const store = steam?.GetFocusedWindowInstance()?.ActionDescriptionStore || contextStore;
  useLayoutEffect(() => {
    if (!store || !nativeButtons) return;
    let patch = patched.get(store);
    if (!patch) {
      const original = store.SetActionsFromMap;
      const wrapper = (map: Actions) => {
        const marked = (value: Description) => (value?.label?.props || value?.props)?.['data-fe-stick-hint'] !== undefined;
        if (!marked(map[nativeButtons.A])) { original.call(store, map); return; }
        // The converter already merged both stick clicks into A. Recover the
        // original descriptions from the active navigation node before storing.
        const controller = getFocusNavController() as unknown as { GetActiveNavTree: () => { GetLastFocusedNode: () => { GetActiveActionDescriptions: () => Actions } } };
        const active = controller.GetActiveNavTree()?.GetLastFocusedNode()?.GetActiveActionDescriptions();
        if (!active) { original.call(store, map); return; }
        const fixed = { ...map, [nativeButtons.A]: active[1] };
        for (const [button, native] of [[15, nativeButtons.LeftStickClick], [16, nativeButtons.RightStickClick]])
          if (marked(active[button])) fixed[native] = active[button];
        original.call(store, fixed);
      };
      const descriptor = Object.getOwnPropertyDescriptor(store, 'SetActionsFromMap');
      // Preserve Steam's descriptor and leave a future locked store untouched.
      if (descriptor && !descriptor.configurable) return;
      Object.defineProperty(store, 'SetActionsFromMap', { configurable: true, value: wrapper });
      patch = { users: 0, restore: () => {
        if (store.SetActionsFromMap !== wrapper) return;
        if (descriptor) Object.defineProperty(store, 'SetActionsFromMap', descriptor);
        else delete (store as Partial<ActionStore>).SetActionsFromMap;
      } };
      patched.set(store, patch);
    }
    patch.users++;
    return () => { if (--patch!.users === 0) { patch!.restore(); patched.delete(store); } };
  }, [store]);
}

// Mirror Steam's actual active hints. This keeps ordering, labels, glyphs and
// context-sensitive toolbar actions identical on both surfaces.
export function Legend() {
  useStickHints();
  const root = useRef<HTMLDivElement>(null);
  const [items, setItems] = useState<{ glyph: string; label: string }[]>([]);
  useEffect(() => {
    const doc = root.current?.ownerDocument;
    if (!doc) return;
    let previous = '';
    const update = () => {
      const footer = doc.getElementById('Footer');
      if (!footer) return;
      const height = doc.defaultView?.getComputedStyle(footer).visibility === 'hidden' ? 0 : Math.ceil(footer.getBoundingClientRect().height);
      doc.documentElement.style.setProperty('--fe-steam-footer-height', height + 'px');
      const next = Array.from(footer.querySelectorAll('img,svg')).flatMap(glyph => {
        const row = glyph.parentElement?.parentElement;
        const label = row?.textContent?.trim();
        return label ? [{ glyph: glyph.outerHTML, label }] : [];
      });
      const signature = JSON.stringify(next);
      if (signature !== previous) { previous = signature; setItems(next); }
    };
    update();
    const observer = new MutationObserver(records => {
      if (records.some(record => record.target === doc.documentElement || (record.target instanceof Element ? record.target : record.target.parentElement)?.closest('#Footer') || Array.from(record.addedNodes).some(node => node instanceof Element && (node.id === 'Footer' || node.querySelector('#Footer'))))) update();
    });
    observer.observe(doc.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['src', 'aria-label'] });
    observer.observe(doc.documentElement, { attributes: true, attributeFilter: ['data-fe-legend'] });
    const resize = new ResizeObserver(update), footer = doc.getElementById('Footer');
    if (footer) resize.observe(footer);
    return () => { observer.disconnect(); resize.disconnect(); };
  }, []);
  return <div ref={root} className="fe-legend fe-mirrored-legend" aria-label="Controller controls">{items.map((item, index) => <span key={index}><span className="fe-legend-glyph" dangerouslySetInnerHTML={{ __html: item.glyph }} />{item.label}</span>)}</div>;
}
