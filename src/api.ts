import { callable } from '@decky/api';

const request = callable<[method: string, args: Record<string, unknown>], { ok: boolean; data?: any; error?: string }>('request');
export async function api<T = any>(method: string, args: Record<string, unknown> = {}): Promise<T> {
  const result = await request(method, args);
  if (!result.ok) throw new Error(result.error || 'Request failed');
  return result.data as T;
}
export type Entry = { name: string; path: string; directory: boolean; link: boolean; size: number; modified: number; hidden: boolean; executable?: boolean };
export type Listing = { path: string; parent: string; entries: Entry[]; free: number | null; archive: boolean; label?: string };
export type Settings = { show_hidden: boolean; folders_first: boolean; sort_by: string; remember_paths: boolean; left: string; right: string; extraction_limit_gib: number; accent: string; opacity: number; text_size: number; ui_scale: number; legend_mode: string; check_updates_on_start: boolean; toolbar_hidden: boolean; splash_enabled: boolean; splash_seen: boolean; setup_completed: boolean; profile: string };
export type Profile = 'handheld' | 'pc';
export type ProfileSettings = Pick<Settings, 'opacity' | 'text_size' | 'show_hidden' | 'folders_first' | 'remember_paths' | 'check_updates_on_start' | 'sort_by' | 'ui_scale' | 'legend_mode' | 'toolbar_hidden' | 'splash_enabled'>;
export type ProfilePresets = Record<Profile, ProfileSettings>;
export type Connection = { id: string; label: string; host: string; share: string; username: string; saved: boolean; password_storage?: 'tpm' | 'system' | 'session' | 'legacy' | 'none' | 'unavailable' };
export type Conflict = { id: string; source: string; target: string; backup: string; directory: boolean; size: number };
export type Job = { id: string; action: string; kind?: string; status: string; bytes: number; current: string; completed: number; total: number; error: string; outputs: string[]; phase: string; total_bytes: number; percent: number; speed: number; background?: boolean; recoverable?: boolean; cleanup_pending?: boolean; label?: string; updated?: number; conflict?: Conflict };
export type TextFile = { text: string; encoding: string; bom: boolean; newline: string; revision: string; name: string; location: string };
export type State = { settings: Settings; connections: Connection[]; credential_error?: string; home: string; version: string; job: Job | null; jobs?: Job[] };
export type Place = { name: string; path: string; connection?: string };
export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ['KiB', 'MiB', 'GiB', 'TiB'];
  let i = -1;
  do { n /= 1024; i++; } while (n >= 1024 && i < units.length - 1);
  return `${n.toFixed(n < 10 ? 1 : 0)} ${units[i]}`;
}
export function message(error: unknown): string { return error instanceof Error ? error.message : String(error); }
