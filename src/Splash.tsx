import { Focusable, ModalRoot } from '@decky/ui';
import { useEffect, useRef, useState } from 'react';
import splash from '../images/splash.png';

const splashCss = `
.fe-splash-modal { position:fixed!important; left:50%!important; top:50%!important; transform:translate(-50%,-50%)!important; width:min(84vw,calc(200vh - 200px),960px)!important; max-width:84vw!important; height:auto!important; padding:0!important; margin:0!important; background:#001321!important; border:0!important; border-radius:12px!important; overflow:hidden!important; box-sizing:border-box; }
.fe-splash-modal .DialogContent_InnerWidth,.fe-splash-modal form { width:100%!important; max-width:none!important; }
.fe-splash { width:100%; display:flex; align-items:center; justify-content:center; outline:none!important; }
.fe-splash img { width:100%; height:auto; object-fit:contain; display:block; }
`;

export function SplashDialog({ closeModal, completed }: { closeModal?: () => void; completed: () => void }) {
  const [ready, setReady] = useState(false);
  const finished = useRef(false), finish = useRef(() => {});
  finish.current = () => {
    if (finished.current) return;
    finished.current = true; closeModal?.(); completed();
  };
  useEffect(() => {
    // Start the three seconds only after the image is decoded. A broken image
    // must never trap the user at launch. Unmount cancels either timer.
    const timer = window.setTimeout(() => finish.current(), ready ? 3000 : 6000);
    return () => window.clearTimeout(timer);
  }, [ready]);
  return <ModalRoot className="fe-splash-modal" bAllowFullSize bHideCloseIcon onCancel={() => {}}><style>{splashCss}</style>
    <Focusable className="fe-splash" preferredFocus noFocusRing onButtonDown={e => { e.preventDefault(); e.stopPropagation(); }}>
      <img src={splash} alt="FileExplorer. Two panels. One controller." onLoad={() => setReady(true)} onError={() => finish.current()} />
    </Focusable>
  </ModalRoot>;
}
