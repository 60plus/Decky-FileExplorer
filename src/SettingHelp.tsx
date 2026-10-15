import { Focusable, GamepadButton } from '@decky/ui';
import { ReactNode, useEffect, useRef, useState } from 'react';
import { Glyph } from './Glyph';

export const settingHelp: Record<string, ReactNode> = {
  'Show hidden files': 'Include names starting with a dot and SMB files marked as hidden.',
  'Folders first': 'Group folders before files in both panels.',
  'Remember folders': "Restore each panel's last folder when FileExplorer opens. When disabled, both panels start at Home.",
  'Startup update check': 'Check GitHub and notify once per OS boot if a newer release is available. Manual checks in Update stay available when this is off.',
  'Sort by': 'Sort names alphabetically, sizes from largest to smallest, or modification dates from newest to oldest.',
  'Accent color': 'Choose the highlight color for panels, selections and the editor.',
  'Panel opacity': 'Change the background opacity. Text and icons stay fully visible. Reopen FileExplorer to apply.',
  'Interface scale': 'Smaller controls fit more content in the same window. Applies to the file manager, editor and viewers after reopening.',
  'Text size': 'Change the size of file names and editor text separately from the overall interface scale.',
  'Controller legend': "Show matching controller hints on the FileExplorer panel, on Steam's bottom bar, on both, or hide both. Reopen FileExplorer to apply.",
  'Hide toolbar': <>Open FileExplorer with the button bar hidden to give the file panels more room. <Glyph button={GamepadButton.LSTICK_CLICK} label="Left stick click" /> shows or hides the toolbar at any time.</>,
  'Splash screen': 'Show the startup image for three seconds when opening FileExplorer. Off by default. The very first launch shows it once even when this is off.',
};

export function SettingHelp({ name, help = settingHelp[name], children }: { name: string; help?: ReactNode; children: ReactNode }) {
  const [expanded, setExpanded] = useState(false);
  const description = useRef<HTMLDivElement>(null);
  useEffect(() => { if (expanded) description.current?.scrollIntoView({ block: 'nearest' }); }, [expanded]);
  return <div className="fe-setting" data-setting={name}>
    <Focusable className="fe-setting-row" noFocusRing onSecondaryActionDescription={expanded ? 'Hide help' : 'Help'}
      onButtonDown={e => { if (e.detail.button === GamepadButton.DIR_UP || e.detail.button === GamepadButton.DIR_DOWN) setExpanded(false); }}
      onKeyDown={e => { if (e.key === 'ArrowUp' || e.key === 'ArrowDown') setExpanded(false); }}
      onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setExpanded(false); }}
      onSecondaryButton={e => { e.preventDefault(); e.stopPropagation(); setExpanded(value => !value); }}>
      <div className="fe-setting-control">{children}</div>
    </Focusable>
    {expanded && <div ref={description} className="fe-setting-help" role="note">{help}</div>}
  </div>;
}
