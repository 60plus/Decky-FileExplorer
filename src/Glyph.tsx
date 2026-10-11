import { findModuleExport, GamepadButton } from '@decky/ui';
import { ComponentType } from 'react';

// Steam's own glyph renderer uses NavigationSourceGlyphInfo, so the images
// follow the active controller (Xbox, PlayStation, Steam Deck, etc.).
const NativeGlyph = findModuleExport(value => typeof value === 'function' &&
  value.toString().includes('actionButton:') && value.toString().includes('NavigationSourceGlyphInfo')) as ComponentType<{ actionButton: number }> | undefined;
const nativeButtons = findModuleExport(value => value && typeof value === 'object' &&
  'A' in value && 'B' in value && 'LeftBumper' in value && 'RightBumper' in value);
const names: Record<number, string> = { 1: 'A', 2: 'B', 3: 'X', 4: 'Y', 5: 'LeftBumper', 6: 'RightBumper', 7: 'LeftTrigger', 8: 'RightTrigger', 13: 'Select', 14: 'Start', 16: 'RightStick' };
const labels: Record<number, string> = { 1: 'A', 2: 'B', 3: 'X', 4: 'Y', 5: 'L1', 6: 'R1', 7: 'L2', 8: 'R2', 13: 'View', 14: 'Start', 16: 'R3' };
export function Glyph({ button, label }: { button: GamepadButton; label: string }) {
  const nativeButton = nativeButtons?.[names[button]];
  return <span>{NativeGlyph && nativeButton !== undefined ? <NativeGlyph actionButton={nativeButton} /> : <b>{labels[button]}</b>}{label}</span>;
}
