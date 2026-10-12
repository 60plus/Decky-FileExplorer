// Steam's keyboard resizes inactive navigation trees too. Their resize observers
// scroll the last focused game tile into view, leaving Home halfway scrolled when
// our modal closes. Preserve background scroll positions while editing; the
// editor, other FileExplorer dialogs and the keyboard keep their own scrolling.
export function preserveBackgroundScroll(root: HTMLElement): () => void {
  const doc = root.ownerDocument;
  const positions = new Map<Element, { left: number; top: number }>();
  for (const element of Array.from(doc.querySelectorAll<HTMLElement>('body *'))) {
    if (element.contains(root) || element.closest('.fe-modal,.fe-dialog,[id="virtual keyboard"]')) continue;
    if (element.clientHeight > 0 && element.clientWidth > 0 &&
        (element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth)) {
      positions.set(element, { left: element.scrollLeft, top: element.scrollTop });
    }
  }
  const restore = (event: Event) => {
    const element = event.target as Element;
    const saved = positions.get(element);
    if (!saved) return;
    if (element.scrollLeft !== saved.left) element.scrollLeft = saved.left;
    if (element.scrollTop !== saved.top) element.scrollTop = saved.top;
  };
  doc.addEventListener('scroll', restore, true);
  return () => doc.removeEventListener('scroll', restore, true);
}
