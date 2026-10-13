import { isArchive, isImage, isText, mediaType } from './fileTypes';

export function Icon({ size = 24 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-label="FileExplorer">
    <path d="M6 17a5 5 0 0 1 5-5h15l6 7h21a5 5 0 0 1 5 5v26a5 5 0 0 1-5 5H11a5 5 0 0 1-5-5Z" fill="currentColor" opacity=".2" />
    <rect x="7" y="22" width="22" height="32" rx="4" stroke="currentColor" strokeWidth="3" />
    <rect x="35" y="22" width="22" height="32" rx="4" stroke="currentColor" strokeWidth="3" />
    <path d="M13 31h10m-10 7h7m21-7h10m-10 7h7M23 46h18m-5-5 5 5-5 5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
}
export function FileIcon({ folder = false, archive = false, name = '' }: { folder?: boolean; archive?: boolean; name?: string }) {
  const kind = folder ? 'Folder' : archive || isArchive(name) ? 'Archive' : isImage(name) ? 'Image' : mediaType(name)?.startsWith('audio/') ? 'Audio' : mediaType(name) ? 'Video' :
    /\.(cfg|conf|config|ini|toml|ya?ml|vdf|acf|properties|env|service|desktop)$/i.test(name) || /^\.env\b/.test(name) ? 'Configuration' :
    /\.(json[c5l]?|xml|html?|css|scss|js|jsx|ts|tsx|py|sh|ps1|c|cpp|h|hpp|cs|go|rs|lua|gd|java|kt|php|rb|sql|svg)$/i.test(name) ? 'Code' : isText(name) ? 'Text' : 'File';
  const colors = { Folder: '#ecc46c', Archive: '#bb9eed', Image: '#8ee3ad', Audio: '#ffa2bb', Video: '#c0a4ff', Configuration: '#f6bc72', Code: '#69dce3', Text: '#a5c8ed', File: '#92a5b6' };
  return <svg width="19" height="19" viewBox="0 0 24 24" fill="none" role="img" aria-label={kind} style={{ flexShrink: 0, color: colors[kind] }}>
    <title>{kind}{name.includes('.') ? ` • ${name.split('.').pop()?.toUpperCase()}` : ''}</title>
    {kind === 'Folder' ? <path d="M3 6h6l2 3h10v11H3Z" fill="currentColor" /> : kind === 'Audio' ? <><path d="M10 17V5l10-2v12M10 8l10-2" stroke="currentColor" strokeWidth="2" /><ellipse cx="7" cy="18" rx="4" ry="3" fill="currentColor" /><ellipse cx="17" cy="16" rx="4" ry="3" fill="currentColor" /></> : kind === 'Video' ? <><rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="1.8" /><path d="m10 7 7 5-7 5Z" fill="currentColor" /></> : kind === 'Image' ? <><rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="1.8" /><circle cx="15.5" cy="8" r="2" fill="currentColor" /><path d="m4 18 6-7 5 6 3-3 3 4" stroke="currentColor" strokeWidth="1.7" /></> : kind === 'Configuration' ? <><path d="M9 3h6l1 4 4 1 1 6-4 2-1 4H9l-1-4-4-2 1-6 4-1Z" stroke="currentColor" strokeWidth="1.5" /><circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" /></> : kind === 'Code' ? <path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-15-2 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /> : <><path d="M6 3h8l5 5v13H6Z" stroke="currentColor" strokeWidth="1.7" /><path d={kind === 'Archive' ? 'M12 4v16M10 8h4m-4 4h4m-4 4h4' : kind === 'Text' ? 'M9 10h4m-4 4h7m-7 4h7' : 'M14 3v5h5'} stroke="currentColor" strokeWidth="1.5" /></>}
  </svg>;
}
