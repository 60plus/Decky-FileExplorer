export function Icon({ size = 24 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-label="FileExplorer">
    <path d="M6 17a5 5 0 0 1 5-5h15l6 7h21a5 5 0 0 1 5 5v26a5 5 0 0 1-5 5H11a5 5 0 0 1-5-5Z" fill="currentColor" opacity=".2" />
    <rect x="7" y="22" width="22" height="32" rx="4" stroke="currentColor" strokeWidth="3" />
    <rect x="35" y="22" width="22" height="32" rx="4" stroke="currentColor" strokeWidth="3" />
    <path d="M13 31h10m-10 7h7m21-7h10m-10 7h7M23 46h18m-5-5 5 5-5 5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
}
export function FileIcon({ folder = false, archive = false }: { folder?: boolean; archive?: boolean }) {
  return <svg width="19" height="19" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, color: folder ? '#ecc46c' : archive ? '#bb9eed' : '#85b9d6' }}>
    {folder ? <path d="M3 6h6l2 3h10v11H3Z" fill="currentColor" /> : <><path d="M6 3h8l5 5v13H6Z" stroke="currentColor" strokeWidth="1.7" /><path d={archive ? 'M12 4v16M10 8h4m-4 4h4m-4 4h4' : 'M9 12h7m-7 4h7'} stroke="currentColor" strokeWidth="1.5" /></>}
  </svg>;
}
