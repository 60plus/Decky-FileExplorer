import { CSSProperties, RefObject, useEffect, useLayoutEffect, useState } from 'react';
import { api, Settings, State } from './api';

export const accents = { cyan: '#69dce3', blue: '#83baff', green: '#8ee3ad', amber: '#f6ce72', violet: '#b9a2ff', rose: '#ffa2bb' };
export const defaultAppearance = { accent: 'cyan', opacity: 100, text_size: 14, ui_scale: 100, legend_mode: 'both' };
const legendOwners = new WeakMap<Document, Map<HTMLElement, string>>();
function updateLegend(doc: Document) {
  const values = [...(legendOwners.get(doc)?.values() || [])];
  if (values.length) doc.documentElement.dataset.feLegend = values[values.length - 1];
  else { delete doc.documentElement.dataset.feLegend; doc.documentElement.style.removeProperty('--fe-steam-footer-height'); }
}

export function appearanceStyle(settings?: Partial<Settings>): CSSProperties {
  const color = accents[settings?.accent as keyof typeof accents] || accents.cyan;
  const opacity = [70, 85, 100].includes(settings?.opacity || 0) ? settings!.opacity! / 100 : 1;
  const size = [12, 14, 16, 18].includes(settings?.text_size || 0) ? settings!.text_size : 14;
  const scale = [70, 80, 90, 100].includes(settings?.ui_scale || 0) ? settings!.ui_scale! / 100 : 1;
  return { '--fe-accent': color, '--fe-highlight': color + '30', '--fe-background': `rgba(16,28,44,${opacity})`,
    '--fe-pane-background': `rgba(21,34,54,${opacity})`, '--fe-code-background': `rgba(13,23,35,${opacity})`,
    '--fe-text-size': size + 'px', '--fe-line-height': (size! * 2) + 'px', '--fe-scale': scale, '--fe-legend-mode': settings?.legend_mode || 'both' } as CSSProperties;
}

export function useAppearance() {
  const [settings, setSettings] = useState<Partial<Settings>>(defaultAppearance);
  useEffect(() => { let live = true; void api<State>('state').then(s => { if (live) setSettings(s.settings); }).catch(() => {}); return () => { live = false; }; }, []);
  return appearanceStyle(settings);
}

// ModalRoot forwards style to its inner form, not its outer surface.
export function useModalStyle(root: RefObject<HTMLElement>, style: CSSProperties) {
  const mode = (style as Record<string, unknown>)['--fe-legend-mode'] as string || 'both';
  useLayoutEffect(() => {
    const element = root.current, doc = element?.ownerDocument;
    if (!element || !doc) return;
    if (!legendOwners.has(doc)) legendOwners.set(doc, new Map());
    legendOwners.get(doc)!.set(element, mode); updateLegend(doc);
    return () => { legendOwners.get(doc)?.delete(element); updateLegend(doc); };
  }, [root]);
  useLayoutEffect(() => {
    const element = root.current, doc = element?.ownerDocument;
    if (element && doc) { legendOwners.get(doc)?.set(element, mode); updateLegend(doc); }
  }, [root, mode]);
  useLayoutEffect(() => {
    const modal = root.current?.closest<HTMLElement>('.fe-modal');
    if (modal) for (const [key, value] of Object.entries(style)) modal.style.setProperty(key, String(value));
  }, [root, style]);
}
