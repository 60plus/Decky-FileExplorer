import { GamepadButton, GamepadEvent, gamepadDialogClasses } from '@decky/ui';
import { RefObject, useEffect } from 'react';

export function focusControl(element: HTMLElement | null | undefined) {
  const owner = element?.ownerDocument.defaultView;
  if (!element || !owner) return;
  element.dispatchEvent(new owner.CustomEvent('vgp_requestfocus', { bubbles: true, cancelable: true, detail: { button: 1, source: 0 } }));
  element.scrollIntoView({ block: 'nearest', inline: 'nearest' });
}

function available(element: HTMLElement) {
  return !element.matches(':disabled,[aria-disabled="true"]') && !element.closest('[inert]') &&
    element.getClientRects().length > 0 && element.ownerDocument.defaultView?.getComputedStyle(element).visibility !== 'hidden';
}

// Wrap only at a menu's edge. Steam retains its normal spatial navigation inside
// each menu, and text inputs/slider editing retain their directional controls.
function wrapMenu(event: Event, button: number) {
  if (event.defaultPrevented) return;
  const vertical = button === GamepadButton.DIR_UP || button === GamepadButton.DIR_DOWN;
  if (!vertical && button !== GamepadButton.DIR_LEFT && button !== GamepadButton.DIR_RIGHT) return;
  const target = event.target as HTMLElement | null;
  if (!target?.closest || target.closest('input,textarea,select,[contenteditable="true"],[role="slider"]')) return;
  const scope = vertical
    ? target.closest<HTMLElement>('.fe-menu-items,.fe-dialog,.fe-settings') || target.closest<HTMLElement>('.fe-panel-stack')
    : target.closest<HTMLElement>('.fe-menu-columns,.fe-actions,.fe-toolbar,.fe-status,.fe-transfer-grid,.fe-stack,.fe-dialog,.fe-panel-stack');
  if (!scope || target.closest('.fe-editor-code,.fe-list,.fe-app .fe-status,.fe-app .fe-transfer-grid')) return;
  // Decky's header sits outside our sidebar content. Keep vertical navigation
  // native here so Up can reach its back arrow instead of wrapping to the bottom.
  if (vertical && scope.matches('.fe-settings,.fe-panel-stack') && scope.closest('.fe-sidebar')) return;
  const candidates = Array.from(scope.querySelectorAll<HTMLElement>('button,[role="button"],[role="checkbox"],[role="switch"],input,textarea,select')).filter(available);
  const controls = candidates.filter(element => !candidates.some(parent => parent !== element && parent.contains(element)));
  const current = controls.find(element => element === target || element.contains(target)) ||
    (target.classList.contains(gamepadDialogClasses.Field) ? controls.find(element => target.contains(element)) : undefined);
  if (!current || (!vertical && current.querySelector('[role="slider"]'))) return;
  const rect = current.getBoundingClientRect();
  const origin = vertical ? rect.top + rect.height / 2 : rect.left + rect.width / 2;
  const cross = vertical ? rect.left + rect.width / 2 : rect.top + rect.height / 2;
  const forward = button === GamepadButton.DIR_DOWN || button === GamepadButton.DIR_RIGHT;
  const points = controls.map(element => {
    const box = element.getBoundingClientRect();
    return { element, main: vertical ? box.top + box.height / 2 : box.left + box.width / 2,
      cross: vertical ? box.left + box.width / 2 : box.top + box.height / 2 };
  });
  // DOM order stays stable when a form's fields scroll between a fixed header
  // and footer. Off-screen fields must not appear to extend beyond Save/Back.
  let destinations = points;
  if (vertical) {
    const first = [points[0]], last = [points[points.length - 1]];
    for (let i = 1; i < points.length && Math.abs(points[i].main - first[0].main) < 4; i++) first.push(points[i]);
    for (let i = points.length - 2; i >= 0 && Math.abs(points[i].main - last[0].main) < 4; i--) last.push(points[i]);
    if (!(forward ? last : first).some(p => p.element === current)) return;
    destinations = forward ? first : last;
  } else {
    if (points.some(p => forward ? p.main > origin + 4 : p.main < origin - 4)) return;
    const edge = (forward ? Math.min : Math.max)(...points.map(p => p.main));
    destinations = points.filter(p => Math.abs(p.main - edge) < 4);
  }
  const next = destinations.filter(p => p.element !== current)
    .sort((a, b) => Math.abs(a.cross - cross) - Math.abs(b.cross - cross))[0];
  if (!next) return;
  event.preventDefault(); event.stopPropagation();
  focusControl(next.element);
}

const documents = new WeakMap<Document, { users: number; remove: () => void }>();

export function useMenuWrapping(marker: RefObject<HTMLElement>) {
  useEffect(() => {
    const doc = marker.current?.ownerDocument;
    if (!doc) return;
    const release = () => {
      const owner = documents.get(doc);
      if (owner && --owner.users === 0) { owner.remove(); documents.delete(doc); }
    };
    const existing = documents.get(doc);
    if (existing) { existing.users++; return release; }
    const direction = (event: Event) => wrapMenu(event, (event as GamepadEvent).detail?.button);
    const keyboard = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      const button = { ArrowUp: GamepadButton.DIR_UP, ArrowDown: GamepadButton.DIR_DOWN, ArrowLeft: GamepadButton.DIR_LEFT, ArrowRight: GamepadButton.DIR_RIGHT }[event.key];
      if (button) wrapMenu(event, button);
    };
    doc.addEventListener('vgp_ondirection', direction, true);
    doc.addEventListener('keydown', keyboard, true);
    documents.set(doc, { users: 1, remove: () => { doc.removeEventListener('vgp_ondirection', direction, true); doc.removeEventListener('keydown', keyboard, true); } });
    return release;
  }, [marker]);
}
