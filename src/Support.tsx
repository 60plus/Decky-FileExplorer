import { DialogButton, Focusable, ModalRoot, Navigation, PanelSection, PanelSectionRow } from '@decky/ui';
import { useRef, useState } from 'react';
import { ErrorText, openDialog } from './dialogs';
import { message } from './api';
import { css } from './style';
import destinations from './support.json';
import coffeeQr from '../images/support/coffee-qr.png';
import bitcoinQr from '../images/support/bitcoin-qr.png';
import cardanoQr from '../images/support/cardano-qr.png';

type Method = keyof typeof destinations;
const methods = {
  coffee: { name: 'Buy me a beer', detail: 'Buy Me a Coffee', qr: coffeeQr },
  bitcoin: { name: 'Bitcoin', detail: 'BTC · Bitcoin network', qr: bitcoinQr },
  cardano: { name: 'Cardano', detail: 'ADA · Cardano network', qr: cardanoQr },
};

export function HeartIcon() {
  return <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" style={{ color: '#e5484d', flexShrink: 0 }}><path fill="currentColor" d="M12 21 3.4 12.5C-2.1 7.2 5.9-.9 12 5.3 18.1-.9 26.1 7.2 20.6 12.5Z" /></svg>;
}

function MethodIcon({ method }: { method: Method }) {
  if (method === 'coffee') return <svg viewBox="0 0 32 32" aria-hidden="true"><rect x="5" y="9" width="17" height="21" rx="3" fill="#ffd45a" /><path d="M22 13h4a4 4 0 0 1 4 4v4a4 4 0 0 1-4 4h-4" fill="none" stroke="#ffd45a" strokeWidth="3" /><path d="M7 14v12m6-12v12m6-12v12" stroke="#ae7820" strokeWidth="1.5" /><path d="M5 12C0 12 1 4 6 4 6-1 15 0 15 4c5-4 11 2 7 7Z" fill="#fff4d4" /></svg>;
  if (method === 'bitcoin') return <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="15" fill="#f7931a" /><g transform="rotate(14 16 16)" stroke="#fff" strokeWidth="2.6" fill="none"><path d="M10 8h8c7 0 7 8 0 8h-6m-2 0h9c7 0 7 8 0 8h-9m2-16v16m2-20v4m5-4v4m-5 16v4m5-4v4" /></g></svg>;
  return <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="15" fill="#246fc5" /><g fill="#fff">{Array.from({ length: 6 }, (_, i) => {
    const angle = Math.PI * i / 3;
    return <g key={i}><circle cx={16 + 5 * Math.cos(angle)} cy={16 + 5 * Math.sin(angle)} r="1.65" /><circle cx={16 + 10 * Math.cos(angle + Math.PI / 6)} cy={16 + 10 * Math.sin(angle + Math.PI / 6)} r="1.1" /><circle cx={16 + 13 * Math.cos(angle)} cy={16 + 13 * Math.sin(angle)} r=".65" /></g>;
  })}</g></svg>;
}

const supportCss = `
.fe-support-label { display:inline-flex; align-items:center; justify-content:center; gap:9px; }
.fe-support-label svg { width:24px; height:24px; flex-shrink:0; }
.fe-support-intro { text-align:center; color:#b6c8d9; font-size:13px; line-height:1.5; margin:0; }
.fe-support-intro strong { display:block; color:#f2f5fa; font-size:17px; margin:4px 0 8px; }
.fe-support-modal .fe-support { width:560px; min-width:0; max-width:calc(100vw - 80px); }
.fe-support h2 { display:flex; align-items:center; justify-content:center; gap:12px; }
.fe-support h2 svg { width:30px; height:30px; }
.fe-support-content { display:grid; grid-template-columns:auto minmax(0,1fr); gap:22px; align-items:center; }
.fe-support-qr { width:232px; height:232px; display:block; background:#f4f0e4; border-radius:8px; image-rendering:pixelated; }
.fe-support-detail { text-align:center; min-width:0; }
.fe-support-network { display:block; font-size:15px; color:#f2d486; margin-bottom:10px; }
.fe-support-address { display:block; color:#e4edf6; font-family:monospace; font-size:13px; line-height:1.6; overflow-wrap:anywhere; user-select:text; }
.fe-support .fe-description { margin:12px 0 0; }
.fe-support-result { text-align:center; font-size:13px; color:#8cddb9; min-height:18px; margin-top:10px; }
.fe-support .fe-actions { margin-top:10px; }
@media(max-height:650px) {
  .fe-support-modal .fe-support { width:520px; }
  .fe-support-qr { width:196px; height:196px; }
  .fe-support h2 { font-size:20px; margin-bottom:12px; }
  .fe-support-address { font-size:12px; }
}
@media(max-width:560px) {
  .fe-support-content { grid-template-columns:1fr; gap:12px; }
  .fe-support-qr { margin:auto; }
  .fe-support-modal .fe-support { max-width:calc(100vw - 48px); max-height:calc(100vh - 100px); overflow:auto; }
}
`;

export function SupportDialog({ method, closeModal }: { method: Method; closeModal?: () => void }) {
  const root = useRef<HTMLDivElement>(null);
  const [notice, setNotice] = useState(''), [error, setError] = useState('');
  const option = methods[method], value = destinations[method];
  function copy() {
    const doc = root.current?.ownerDocument;
    if (!doc) return;
    const previous = doc.activeElement as HTMLElement | null;
    const field = doc.createElement('textarea');
    field.value = value; field.readOnly = true;
    field.style.cssText = 'position:fixed;left:-10000px;top:0';
    doc.body.appendChild(field); field.select(); setError(''); setNotice('');
    try {
      if (!doc.execCommand('copy')) throw new Error('Copy is unavailable. Scan the QR code instead.');
      setNotice(method === 'coffee' ? 'Link copied.' : 'Address copied.');
    } catch (e) { setError(message(e)); }
    finally { field.remove(); previous?.focus({ preventScroll: true }); }
  }
  return <ModalRoot className="fe-support-modal" onCancel={closeModal} closeModal={closeModal}><style>{css}{supportCss}</style>
    <Focusable className="fe-dialog fe-support" flow-children="column"><div ref={root}>
      <h2><MethodIcon method={method} />{option.name}</h2>
      <div className="fe-support-content">
        <img className="fe-support-qr" src={option.qr} alt={`${option.name} QR code`} />
        <div className="fe-support-detail"><strong className="fe-support-network">{option.detail}</strong><span className="fe-support-address">{value}</span>
          <p className="fe-description">{method === 'coffee' ? 'Scan to open the support page on your phone.' : 'Scan the address with your wallet.'}</p>
        </div>
      </div>
      <div className="fe-support-result" role="status">{notice}</div><ErrorText text={error} />
      <Focusable className="fe-actions" flow-children="row">
        {method === 'coffee' && <DialogButton onClick={() => { closeModal?.(); Navigation.NavigateToExternalWeb(value); }}>Open page</DialogButton>}
        <DialogButton onClick={copy}>{method === 'coffee' ? 'Copy link' : 'Copy address'}</DialogButton>
        <DialogButton onClick={closeModal}>Back</DialogButton>
      </Focusable>
    </div></Focusable>
  </ModalRoot>;
}

export function SupportPanel({ back }: { back: () => void }) {
  return <PanelSection title="Support"><style>{supportCss}</style><div className="fe-panel-stack">
    <PanelSectionRow><DialogButton onClick={back}>‹ Back</DialogButton></PanelSectionRow>
    <PanelSectionRow><div className="fe-support-intro"><HeartIcon /><strong>Support FileExplorer</strong>Enjoy using FileExplorer?<br />You can help support its development.<br />All features stay free.</div></PanelSectionRow>
    {(Object.keys(methods) as Method[]).map(method => <PanelSectionRow key={method}><DialogButton onClick={() => openDialog(<SupportDialog method={method} />)}><span className="fe-support-label"><MethodIcon method={method} />{methods[method].name}</span></DialogButton></PanelSectionRow>)}
    <PanelSectionRow><p className="fe-support-intro">Thank you for your support!</p></PanelSectionRow>
  </div></PanelSection>;
}
