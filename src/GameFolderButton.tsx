import { beforePatch, findModuleExport, MenuItem } from '@decky/ui';
import { cloneElement, isValidElement, ReactElement, ReactNode } from 'react';
import { folderForApp } from './SteamIntegration';
import { message } from './api';
import { openDialog, PreviewDialog } from './dialogs';

type Element = ReactElement<any>;

/** Keep Steam's native menu items and focus tree, including controller navigation. */
export function installGameFolderButton(launch: (path: string) => void) {
  let enabled = true, pending = false;
  const cache = new WeakMap<Function, Function[]>();
  async function open(appid: number) {
    if (pending || !enabled) return;
    pending = true;
    try { const path = await folderForApp(appid); if (enabled) launch(path); }
    catch (e) { if (enabled) openDialog(<PreviewDialog name="Game folder unavailable" text={message(e)} />); }
    finally { pending = false; }
  }
  function mapTree(node: ReactNode, transform: (node: Element) => Element): ReactNode {
    if (Array.isArray(node)) return node.map(item => mapTree(item, transform));
    if (!isValidElement(node)) return node;
    const element = node as Element;
    const next = transform(element);
    if (next !== element) return next;
    return element.props.children === undefined ? element : cloneElement(element, {}, mapTree(element.props.children, transform));
  }
  function wrapped(type: Function, stage: number): any {
    let types = cache.get(type);
    if (!types) { types = []; cache.set(type, types); }
    if (!types[stage]) types[stage] = function FileExplorerMenu(props: any) {
      const result = type(props);
      if (!enabled) return result;
      if (stage === 0) return mapTree(result, node => node.props.app && typeof node.type === 'function'
        ? { ...node, type: wrapped(node.type, 1) } : node);
      if (stage === 1) return mapTree(result, node => node.props.app && 'navRef' in node.props && typeof node.type === 'function'
        ? { ...node, type: wrapped(node.type, 2) } : node);
      return mapTree(result, node => {
        const children = node.props.children;
        if (!Array.isArray(children)) return node;
        // Steam groups its mapped items as the first array inside NavigationBox.
        function insert(items: any[]): any[] {
          if (items.some(item => isValidElement(item) && item.key === 'fileexplorer-folder')) return items;
          const index = items.findIndex(item => isValidElement(item) && item.key === 'details' && typeof (item.props as any).onActivate === 'function');
          if (index < 0) {
            const next = items.map(item => Array.isArray(item) ? insert(item) : item);
            return next.some((item, index) => item !== items[index]) ? next : items;
          }
          const button = cloneElement(items[index], { key: 'fileexplorer-folder', text: 'Open in FileExplorer', active: false, disabled: false,
            onActivate: (event: Event) => { event?.preventDefault?.(); event?.stopPropagation?.(); void open(props.app.appid); } });
          return [...items.slice(0, index + 1), button, ...items.slice(index + 1)];
        }
        const next = insert(children);
        return next === children ? node : cloneElement(node, {}, next);
      });
    };
    return types[stage];
  }
  // Steam's library menu accepts additional actions after its Play/Resume item.
  // Use the selected overview, independently of whichever game is running.
  const contextManager = findModuleExport(value => typeof value?.prototype?.CreateContextMenuInstance === 'function');
  const appMenu = findModuleExport(value => typeof value === 'function' && String(value).includes('navigator:') && String(value).includes('instance:'));
  const libraryPatch = contextManager && appMenu ? beforePatch(contextManager.prototype, 'CreateContextMenuInstance', args => {
    if (!enabled) return;
    args[0] = mapTree(args[0], node => {
      const { overview, bInGamepadUI, includeMultiSelect, additionalActions } = node.props;
      if (node.type !== appMenu || !bInGamepadUI || includeMultiSelect || !overview?.installed || !Number.isInteger(overview.appid) || overview.appid <= 0) return node;
      const extras = Array.isArray(additionalActions) ? additionalActions : [additionalActions];
      if (extras.some(item => isValidElement(item) && item.key === 'fileexplorer-library-folder')) return node;
      return cloneElement(node, { additionalActions: [...extras,
        <MenuItem key="fileexplorer-library-folder" onSelected={() => { void open(overview.appid); }}>Open in FileExplorer</MenuItem>] });
    });
  }) : undefined;
  if (!libraryPatch) console.warn('[FileExplorer] Steam library menu integration is unavailable');
  const root = findModuleExport(value => typeof value?.render === 'function' && String(value.render).includes('navID:') && String(value.render).includes('excludeFromScrollRegionSearch:'));
  if (!root) console.warn('[FileExplorer] Steam main menu integration is unavailable');
  const patch = root ? beforePatch(root, 'render', args => {
    if (!enabled || args[0]?.navID !== 'MainNavMenuContainer') return;
    const props = args[0];
    args[0] = { ...props, children: mapTree(props.children, node => node.props.app && 'ownerWindow' in node.props && 'visible' in node.props && typeof node.type === 'function'
      ? { ...node, type: wrapped(node.type, 0) } : node) };
  }) : undefined;
  return () => { enabled = false; patch?.unpatch(); libraryPatch?.unpatch(); };
}
