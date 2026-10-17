export const css = `
.fe-modal { width:min(1120px,94vw)!important; max-width:94vw!important; height:min(724px,calc(100vh - 108px))!important; max-height:100%!important; padding:0!important; background:#101c2c!important; border-radius:14px!important; overflow:hidden!important; }
.fe-modal .DialogContent_InnerWidth { width:100%!important; max-width:none!important; }
.fe-modal .DialogContent_InnerWidth,.fe-modal form { height:100%!important; min-height:0!important; }
/* Steam positions its controller focus ring outside this subtree using DOM
   bounds. Its CEF reports incorrect bounds for CSS zoom, while transforms keep
   the ring aligned. Expand the layout before scaling so the window stays full. */
.fe-app { transform:scale(var(--fe-scale,1)); transform-origin:top left; width:calc(100% / var(--fe-scale,1)); height:calc(100% / var(--fe-scale,1)); min-height:0; flex-shrink:0; display:flex; flex-direction:column; color:#edf4fc; font-family:inherit; }
.fe-header { display:flex; align-items:center; gap:12px; padding:15px 20px 12px; flex-shrink:0; border-bottom:1px solid #2b3d51; }
.fe-brand { display:flex; align-items:center; gap:10px; font-size:24px; font-weight:700; flex:1; }
.fe-subtitle { font-size:12px; color:#90a7bd; font-weight:400; margin-top:3px; }
.fe-toolbar { display:flex; gap:8px; padding:10px 18px; flex-shrink:0; }
.fe-toolbar .fe-btn { min-width:0!important; padding:7px 12px!important; font-size:13px!important; flex:1; }
.fe-btn { background:#25364b!important; border-radius:6px!important; color:#e7f0fa!important; box-shadow:none!important; }
.fe-btn:focus,.fe-btn.gpfocus { background:#3c627e!important; color:white!important; outline:2px solid #69dce3!important; }
.fe-panes { display:flex; flex:1; min-height:0; gap:12px; padding:0 18px; }
.fe-pane { display:flex; flex-direction:column; flex:1; min-width:0; border:1px solid #324457; border-radius:9px; overflow:hidden; background:#152236; }
.fe-pane.active { border-color:#5dd6df; box-shadow:0 0 0 1px #5dd6df; }
.fe-path { padding:10px 12px; background:#1b2c41; flex-shrink:0; }
.fe-path-title { font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:#8fa6bd; margin-bottom:5px; }
.active .fe-path-title { color:#70e0e5; }
.fe-path-value { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; text-align:left; direction:ltr; }
.fe-columns { display:flex; align-items:center; gap:9px; flex-shrink:0; color:#8097ae; font-size:11px; padding:5px 22px 5px 14px; border-bottom:1px solid #2b3d51; }
.fe-column-name { flex:1; min-width:0; }
.fe-list { overflow-y:auto; overflow-x:hidden; flex:1; min-height:0; padding:5px; scrollbar-gutter:stable; scrollbar-width:auto; scrollbar-color:auto; color-scheme:dark; }
/* Use Steam's Chromium scrollbar parts so the file lists never inherit the
   light desktop scrollbar. Standard non-auto scrollbar values override these. */
.fe-list::-webkit-scrollbar { display:block!important; width:8px; height:8px; }
.fe-list::-webkit-scrollbar-track { display:block!important; background:var(--fe-code-background,#0d1723); border-radius:8px; }
.fe-list::-webkit-scrollbar-thumb { display:block!important; background:#496278; border:2px solid transparent; background-clip:padding-box; border-radius:8px; min-height:28px; }
.fe-list::-webkit-scrollbar-thumb:hover,.fe-list::-webkit-scrollbar-thumb:active { background-color:var(--fe-accent,#69dce3); }
.fe-list::-webkit-scrollbar-button { display:none; }
.fe-list::-webkit-scrollbar-corner { background:transparent; }
.fe-row { display:flex; align-items:center; gap:9px; border-radius:5px; min-height:35px; padding:3px 8px; box-sizing:border-box; font-size:14px; color:#dfebf8; cursor:pointer; border:1px solid transparent; }
.fe-row:hover { background:#21394e; }
.fe-row.focused,.fe-row:focus { background:#31536c; border-color:#77e4e7; outline:none; }
.fe-row.selected { color:#ffe49c; }
.fe-name { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.fe-size { color:#91a8bf; font-size:11px; flex:0 0 64px; text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
.fe-modified { color:#91a8bf; font-size:11px; flex:0 0 78px; text-align:right; white-space:nowrap; line-height:13px; font-variant-numeric:tabular-nums; }
.fe-modified>span { display:block; }
.fe-modified-time { font-size:10px; color:#8097ae; }
.fe-parent-label { color:#91a8bf; font-size:11px; flex-shrink:0; }
.fe-check { width:13px; height:13px; border:1px solid #587087; border-radius:3px; color:#102235; font-size:12px; line-height:13px; text-align:center; flex-shrink:0; }
.selected .fe-check { background:#f6ce72; border-color:#f6ce72; }
.fe-pane-status { padding:7px 12px; color:#8ea7bc; font-size:11px; border-top:1px solid #2b3d51; flex-shrink:0; display:flex; justify-content:space-between; }
.fe-status { display:flex; align-items:center; justify-content:center; text-align:center; gap:12px; padding:10px 18px; font-size:12px; min-height:22px; color:#a4bdd0; }
.fe-status .fe-btn { min-width:75px!important; width:auto!important; font-size:12px!important; padding:4px 10px!important; }
.fe-status-text { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.fe-status-error { color:#ffb29f; white-space:normal; overflow:visible; overflow-wrap:anywhere; line-height:1.45; }
.fe-error { color:#ffb29f; white-space:normal; font-size:13px; padding:12px; text-align:center; text-wrap:balance; overflow-wrap:anywhere; }
.fe-muted { color:#8fa6bd; padding:16px 10px; font-size:13px; }
.fe-legend { display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:8px 16px; padding:9px 14px 11px; background:#0c1725; border-top:1px solid #293b4e; font-size:11px; color:#a7bdce; }
.fe-legend span { display:inline-flex; align-items:center; gap:5px; }
.fe-legend img { width:20px; height:20px; object-fit:contain; }
.fe-mirrored-legend:empty { display:none; }
.fe-legend-glyph img,.fe-legend-glyph svg { width:auto!important; min-width:16px; max-width:42px; height:20px!important; margin:0!important; }
html[data-fe-legend="steam"] .fe-legend,html[data-fe-legend="none"] .fe-legend { display:none; }
html[data-fe-legend="panel"] #Footer,html[data-fe-legend="none"] #Footer { visibility:hidden!important; }
/* Some Steam themes reserve less height than the glyphs need. Keep every row
   inside the viewport, then reserve that measured height in the handheld frame. */
html[data-fe-legend] #Footer { height:auto!important; }
.fe-dialog { min-width:360px; max-width:620px; }
.fe-dialog h2 { margin:0 0 14px; font-size:22px; }
.fe-dialog .fe-stack { display:flex; flex-direction:column; gap:8px; }
.fe-dialog > .fe-stack { max-height:65vh; overflow:auto; }
.fe-dialog .fe-actions { display:flex; gap:10px; margin-top:16px; }
.fe-dialog .fe-actions>* { flex:1; min-width:0!important; }
.fe-recovery-actions { display:flex; flex-direction:column; gap:10px; margin-top:16px; }
.fe-draft-status { flex-shrink:0; padding:2px 14px; color:var(--fe-muted, #a5b5c5); font-size:11px; line-height:14px; }
.fe-transfer-grid { display:grid; gap:5px; padding:0 18px 8px; flex-shrink:0; }
.fe-transfer-card { position:relative; min-width:0!important; padding:6px 7px 9px!important; width:100%!important; overflow:hidden!important; text-align:left!important; line-height:1.4!important; }
.fe-task-title { display:block; font-size:12px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.fe-task-info { display:block; font-size:11px; font-weight:400; white-space:nowrap; }
.fe-transfer-fill { position:absolute; left:0; bottom:0; height:3px; background:var(--fe-accent,#69dce3); }
.fe-queue-items button { min-width:0!important; padding:8px 12px!important; }
.fe-copy-actions { flex-shrink:0; padding-top:12px; max-height:none!important; overflow:visible!important; }
.fe-dialog .fe-recovery-actions .fe-actions { margin-top:0; }
.fe-recovery-actions button { white-space:normal!important; overflow-wrap:anywhere; text-overflow:clip!important; height:auto!important; min-height:44px; line-height:20px!important; padding:10px 12px!important; }
.fe-dialog .fe-description { color:#a9bccd; font-size:14px; white-space:pre-wrap; overflow-wrap:anywhere; margin:8px 0 16px; text-align:center; text-wrap:balance; line-height:1.5; }
.fe-dialog > h2 { text-align:center; }
.fe-message { text-align:center; text-wrap:balance; overflow-wrap:anywhere; }
.fe-dialog pre { white-space:pre-wrap; overflow-wrap:anywhere; max-height:45vh; overflow:auto; background:#0d1723; padding:12px; font-size:13px; }
.fe-places { max-height:46vh; overflow:auto; }
.fe-dialog > .fe-connection-form { max-height:40vh; overflow:auto; }
.fe-panel-stack { display:flex; flex-direction:column; gap:10px; }
.fe-settings { display:flex; flex-direction:column; gap:8px; }
.fe-setting-row { display:flex; align-items:center; }
.fe-setting-control { flex:1; min-width:0; }
.fe-setting-control [role="slider"] { width:100%!important; min-width:0!important; box-sizing:border-box; }
.fe-setting-control :has([role="slider"]) { min-width:0!important; }
.fe-setting-help { padding:8px 0 12px; font-size:12px; line-height:1.5; color:#b6c7d7; overflow-wrap:anywhere; text-align:center; text-wrap:balance; }
.fe-inline-glyph { display:inline-flex; align-items:center; justify-content:center; vertical-align:-.25em; height:1.25em; min-width:1.25em; margin:0 .1em; }
.fe-inline-glyph img,.fe-inline-glyph svg { display:block; height:1.25em!important; width:auto!important; margin:0!important; }
.fe-slider-label { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
.fe-slider-label b { font-size:12px; font-weight:400; white-space:nowrap; color:#c7d9ea; }
.fe-settings-actions { display:flex; flex-direction:column; gap:14px; margin:8px 0; }
.fe-settings-connections { display:flex; flex-direction:column; gap:12px; margin-top:8px; padding-top:16px; border-top:1px solid #3b4957; }
.fe-saved-profiles { display:flex; flex-direction:column; gap:12px; }
.fe-danger { display:flex; align-items:center; justify-content:center; text-align:center; text-wrap:balance; gap:12px; border:1px solid #ee6666; border-radius:8px; background:#541c25; padding:14px; color:#ffd3d3; }
.fe-danger>span { display:flex; align-items:center; justify-content:center; border-radius:50%; background:#d83246; color:white; width:32px; height:32px; flex-shrink:0; font-size:25px; font-weight:bold; }
.fe-progress { position:relative; background:#20384a; margin:0 18px 9px; min-height:20px; border-radius:4px; overflow:hidden; flex-shrink:0; }
.fe-progress>div { position:absolute; inset:0 auto 0 0; background:#256875; transition:width .3s; }
.fe-progress>span { position:relative; display:block; padding:3px 8px; font-size:11px; text-align:center; }
.fe-code { flex:1; overflow:auto; margin:0 18px; border:1px solid #324457; min-height:0; background:#0d1723; }
.fe-code-line { display:flex; min-height:28px; line-height:28px; white-space:pre; font:14px/28px monospace; border:1px solid transparent; }
.fe-code-line.active,.fe-code-line.gpfocus { background:#29475b; border-color:#69dce3; outline:none; }
.fe-line-number { position:sticky; left:0; background:#132437; color:#8aa6bb; width:56px; text-align:right; padding:0 12px 0 4px; box-sizing:border-box; flex-shrink:0; }
.fe-code-line code { padding:0 10px; tab-size:4; }
.fe-encoding { padding:8px 18px; }
.fe-modal { background:var(--fe-background,#101c2c)!important; }
.fe-pane { background:var(--fe-pane-background,#152236); }
.fe-pane.active { border-color:var(--fe-accent,#69dce3); box-shadow:0 0 0 1px var(--fe-accent,#69dce3); }
.active .fe-path-title { color:var(--fe-accent,#69dce3); }
.fe-row { font-size:var(--fe-text-size,14px); min-height:calc(var(--fe-text-size,14px) + 21px); }
.fe-row.focused,.fe-row:focus,.fe-code-line.active,.fe-code-line.gpfocus { border-color:var(--fe-accent,#69dce3); background:var(--fe-highlight,#29475b); }
.fe-btn:focus,.fe-btn.gpfocus { outline-color:var(--fe-accent,#69dce3)!important; }
.fe-code { background:var(--fe-code-background,#0d1723); }
.fe-code-line { font-size:var(--fe-text-size,14px); line-height:var(--fe-line-height,28px); min-height:var(--fe-line-height,28px); box-sizing:border-box; }
.fe-code-line code { display:block; min-width:1ch; }
.fe-caret { display:inline; border-left:2px solid var(--fe-accent,#69dce3); margin-left:-2px; }
.fe-selection { color:#fff; background:#356f95; }
.fe-text-input { display:flex; flex:1; min-height:0; margin:0 18px; border:1px solid var(--fe-accent,#69dce3); background:var(--fe-code-background,#0d1723); overflow:hidden; }
.fe-editor-gutter { width:56px; flex-shrink:0; overflow:hidden; background:#132437; color:#8aa6bb; font:var(--fe-text-size,14px)/var(--fe-line-height,28px) monospace; text-align:right; }
.fe-editor-gutter>div { padding-top:8px; }
.fe-editor-gutter>div>div { padding-right:12px; }
.fe-editor-gutter .active { color:var(--fe-accent,#69dce3); background:var(--fe-highlight,#29475b); }
.fe-editor-textarea { flex:1; min-width:0; width:100%!important; height:100%!important; max-height:none!important; min-height:0!important; resize:none!important; overflow:auto!important; background:transparent!important; color:#edf4fc!important; border:0!important; outline:none!important; box-shadow:none!important; margin:0!important; padding:8px 10px!important; box-sizing:border-box; font:var(--fe-text-size,14px)/var(--fe-line-height,28px) monospace!important; tab-size:4; white-space:pre!important; caret-color:var(--fe-accent,#69dce3); }
.fe-editor .fe-status,.fe-editor .fe-legend { flex-shrink:0; }
.fe-editor .fe-error { max-height:50px; overflow:auto; flex-shrink:0; }
.fe-editor .fe-toolbar { gap:6px; }
.fe-editor .fe-toolbar .fe-btn { padding:7px 4px!important; font-size:12px!important; }
.fe-editor-title { flex:1; min-width:0; }
.fe-toolbar-toggle { width:auto!important; min-width:0!important; min-height:28px!important; padding:4px 8px!important; font-size:12px!important; line-height:20px!important; flex-shrink:0; }
.fe-editor-modal.fe-keyboard-visible { position:fixed!important; left:50%!important; top:var(--fe-editor-top)!important; transform:translateX(-50%)!important; margin:0!important; height:var(--fe-editor-height)!important; max-height:var(--fe-editor-height)!important; }
.fe-keyboard-visible .fe-editor { height:calc(100% / var(--fe-scale,1))!important; min-height:0!important; }
.fe-keyboard-visible .DialogContent_InnerWidth,.fe-keyboard-visible form { height:100%!important; min-height:0!important; }
.fe-keyboard-visible .fe-header { padding:8px 18px; }
.fe-keyboard-visible .fe-toolbar { padding:6px 18px; }
.fe-keyboard-visible .fe-status { padding:5px 18px; min-height:18px; font-size:11px; }
.fe-keyboard-visible .fe-legend { padding:5px 14px; font-size:10px; }
.fe-appearance-preview { padding:12px; border:1px solid var(--fe-accent); border-radius:8px; background:var(--fe-background); color:#edf4fc; }
.fe-preview-row { color:var(--fe-accent); padding:10px 0; font-size:var(--fe-text-size); }
.fe-swatches { display:flex; gap:8px; }
.fe-swatches span { width:18px; height:18px; border-radius:50%; }
.fe-image-title { min-width:0; }
.fe-image-title>strong { display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.fe-image-folder { color:#8ba7bc; font-size:12px; margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.fe-image-stage { flex:1; min-height:0; margin:12px 18px 0; display:flex; align-items:center; justify-content:center; overflow:hidden; border:1px solid #324457; border-radius:6px; background:repeating-conic-gradient(#162334 0% 25%,#1d2d40 0% 50%) 0 0 / 24px 24px; }
.fe-image-stage img { width:100%; height:100%; object-fit:contain; min-height:0; }
.fe-image-stage.gpfocus { outline:2px solid var(--fe-accent,#69dce3); }
.fe-media-stage { flex:1; min-height:0; position:relative; margin:8px 18px 0; display:flex; align-items:center; justify-content:center; overflow:hidden; background:#080e17; border:1px solid #324457; border-radius:6px; }
.fe-media-stage.gpfocus { border-color:var(--fe-accent); }
.fe-media-stage video { width:100%; height:100%; min-height:0; object-fit:contain; }
.fe-audio-art { height:85%; width:85%; min-height:0; display:flex; align-items:center; justify-content:center; }
.fe-audio-art img { max-width:100%; max-height:100%; object-fit:contain; border-radius:8px; }
.fe-speaker { height:70%; max-width:260px; color:var(--fe-accent); }
.fe-media-overlay { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; text-align:center; padding:24px; background:#080e17cc; }
.fe-media-timeline { display:flex; align-items:center; flex-shrink:0; gap:12px; padding:8px 18px 0; color:#a4bdd0; font-size:12px; font-variant-numeric:tabular-nums; }
.fe-media-track { flex:1; height:10px; border-radius:5px; background:#25364b; overflow:hidden; cursor:pointer; }
.fe-media-track>div { height:100%; background:var(--fe-accent); }
.fe-modal.fe-media-fullscreen { position:fixed!important; inset:0!important; width:100vw!important; max-width:100vw!important; height:100vh!important; max-height:100vh!important; margin:0!important; border-radius:0!important; z-index:10; box-sizing:border-box; padding-bottom:var(--fe-steam-footer-height,0px)!important; }
.fe-media-expanded .fe-header { display:none; }
.fe-media-expanded .fe-media-stage { margin:0; border:0; border-radius:0; }
.fe-media-player .fe-toolbar { gap:4px; }
.fe-media-player .fe-toolbar .fe-btn { padding:6px 3px!important; font-size:12px!important; }
/* Fill Steam's safe modal frame on handhelds and short/scaled displays. The
   native frame already reserves the system header and controller footer. */
@media (max-width:1300px), (max-height:650px) {
  :has(> .fe-modal) { padding:4px!important; }
  html[data-fe-legend] :has(> .fe-modal) { bottom:var(--fe-steam-footer-height,40px)!important; }
  .fe-modal:not(.fe-keyboard-visible) { width:100%!important; max-width:100%!important; min-width:0!important; height:100%!important; max-height:100%!important; margin:0!important; box-sizing:border-box; border-radius:8px!important; }
  /* The keyboard uses a fixed-position modal, so its width is viewport-relative.
     Keep the same 4px side margins as the normal handheld modal frame. */
  .fe-modal.fe-keyboard-visible { width:calc(100vw - 8px)!important; max-width:calc(100vw - 8px)!important; min-width:0!important; box-sizing:border-box; border-radius:8px!important; }
  .fe-header { padding:5px 10px; min-height:26px; gap:8px; }
  .fe-brand { font-size:18px; line-height:24px; gap:7px; }
  .fe-brand svg { width:24px; height:24px; display:block; }
  .fe-subtitle { display:none; }
  .fe-editor .fe-subtitle,.fe-image-viewer .fe-subtitle { display:block; font-size:10px; line-height:14px; margin-top:1px; }
  .fe-toolbar { padding:5px 8px; gap:5px; }
  .fe-toolbar .fe-btn,.fe-editor .fe-toolbar .fe-btn { padding:4px!important; min-height:28px!important; line-height:20px!important; font-size:12px!important; }
  .fe-panes { padding:0 8px; gap:8px; }
  .fe-path { display:flex; align-items:center; gap:8px; padding:5px 7px; }
  .fe-path-title { font-size:9px; letter-spacing:.5px; margin:0; flex-shrink:0; }
  .fe-path-value { flex:1; min-width:0; font-size:12px; }
  .fe-columns { padding:3px 17px 3px 9px; gap:6px; font-size:10px; }
  .fe-list { padding:3px; }
  .fe-row { min-height:calc(var(--fe-text-size,14px) + 14px); padding:2px 5px; gap:6px; }
  .fe-pane-status { padding:4px 7px; gap:6px; font-size:10px; line-height:14px; }
  .fe-pane-status>span { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .fe-status,.fe-keyboard-visible .fe-status { flex-shrink:0; padding:4px 8px; min-height:16px; gap:6px; line-height:16px; font-size:11px; }
  .fe-progress { margin:0 8px 4px; }
  .fe-legend,.fe-keyboard-visible .fe-legend { flex-shrink:0; padding:5px 8px; gap:4px 10px; font-size:10px; line-height:16px; }
  .fe-legend img { width:16px; height:16px; }
  .fe-legend span { gap:4px; }
  .fe-code,.fe-text-input { margin:0 8px; }
  .fe-line-number,.fe-editor-gutter { width:42px; }
  .fe-editor .fe-header>div { min-width:0; }
  .fe-editor .fe-header strong { display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .fe-editor .fe-status { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .fe-keyboard-visible .fe-header { padding:4px 8px; }
  .fe-keyboard-visible .fe-toolbar { padding:4px 8px; }
  .fe-image-stage { margin:4px 8px 0; }
  .fe-image-folder { margin-top:2px; font-size:11px; }
}
.fe-pack-dialog,.fe-shortcut-dialog { width:550px; min-width:0; max-width:calc(100vw - 60px); margin-left:auto; margin-right:auto; }
.fe-info-heading { display:flex; align-items:center; justify-content:center; gap:10px; text-align:center; min-width:0; }
.fe-info-heading>span:last-child { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.fe-info-icon { border:1px solid #69dce3; border-radius:50%; width:25px; height:25px; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; color:#69dce3; font-size:18px; font-family:serif; }
.fe-destination { border:1px solid #354a5e; border-radius:8px; padding:10px 12px; margin:8px 0 12px; text-align:center; background:#152332; }
.fe-destination>span { display:block; color:#91b0c8; font-size:12px; margin-bottom:5px; }
.fe-destination strong { display:block; color:#e3edf6; overflow-wrap:anywhere; font-size:14px; font-weight:500; }
.fe-confirm-dialog { width:550px; min-width:0; max-width:calc(100vw - 80px); margin-left:auto; margin-right:auto; }
.fe-conflict-actions { flex-shrink:0; }
.fe-dialog .fe-conflict-actions .fe-actions { margin-top:8px; }
.fe-destructive.DialogButton { background:#842b38!important; color:#fff1f2!important; border:1px solid #ef6e7f!important; }
.fe-destructive.DialogButton.gpfocus,.fe-destructive.DialogButton:hover { background:#b13246!important; color:white!important; }
.fe-transfer-conflict { outline:1px solid #e8b965; }
.fe-options-modal { width:min(820px,calc(100vw - 48px))!important; max-width:calc(100vw - 48px)!important; min-width:0!important; height:min(544px,calc(100vh - 80px))!important; max-height:calc(100vh - 80px)!important; padding:20px!important; box-sizing:border-box; overflow:hidden!important; }
.fe-options-modal .DialogContent_InnerWidth { width:100%!important; max-width:none!important; }
.fe-options-modal .DialogContent_InnerWidth,.fe-options-modal form { height:100%!important; min-height:0!important; }
.fe-menu-dialog { width:100%; min-width:0; max-width:none; height:100%; display:flex; flex-direction:column; }
.fe-menu-columns { display:flex; flex:1; gap:16px; min-height:0; }
.fe-menu-section { flex:1; min-width:0; display:flex; flex-direction:column; border:1px solid #354a5e; border-radius:8px; background:#12202e; padding:10px; }
.fe-menu-section h3 { margin:0 0 10px; font-size:14px; color:#8ecedc; text-align:center; }
.fe-menu-items { display:flex; flex-direction:column; gap:8px; flex:1; min-height:0; overflow:auto; padding:4px; }
.fe-menu-items .DialogButton { flex-shrink:0; width:100%; min-width:0!important; white-space:normal; line-height:1.25!important; padding:8px 12px!important; min-height:36px!important; font-size:14px!important; box-sizing:border-box; }
@media(max-height:700px) { :has(> .fe-options-modal) { padding:6px 24px!important; } .fe-options-modal { padding:16px!important; } .fe-menu-columns { gap:10px; } .fe-menu-section { padding:6px; } .fe-menu-items { gap:6px; } .fe-menu-items .DialogButton { min-height:28px!important; padding:4px 10px!important; } .fe-menu-dialog h2 { font-size:18px; margin-bottom:8px; } .fe-menu-section h3 { margin-bottom:6px; font-size:12px; } .fe-destination { padding:7px 10px; margin:4px 0 8px; } }
.fe-pack-dialog .fe-pack-fields,.fe-shortcut-dialog .fe-pack-fields { max-height:48vh; overflow:auto; }
.fe-archive-output { color:#79dde3; overflow-wrap:anywhere; font-size:13px; padding:6px 0; }
@media (max-height:700px) {
  .fe-operation-modal { padding:16px 24px!important; height:calc(100vh - 116px)!important; max-height:calc(100vh - 116px)!important; overflow:hidden!important; box-sizing:border-box; }
  .fe-operation-modal .DialogContent_InnerWidth,.fe-operation-modal form { height:100%!important; min-height:0!important; }
  .fe-pack-dialog,.fe-shortcut-dialog { display:flex; flex-direction:column; height:100%; min-height:0; }
  .fe-pack-dialog h2,.fe-shortcut-dialog h2 { font-size:18px; margin-bottom:6px; flex-shrink:0; }
  .fe-pack-dialog .fe-pack-fields,.fe-shortcut-dialog .fe-pack-fields { flex:1; min-height:0; max-height:none; gap:6px; }
  .fe-pack-fields>* { flex-shrink:0; }
  .fe-pack-fields>.DialogInputLabelGroup { margin:0!important; }
  .fe-pack-fields .DialogInput_Wrapper { margin-bottom:0!important; }
  .fe-pack-dialog .fe-pack-fields>.Panel { padding:5px 10px!important; min-height:0!important; }
  .fe-pack-dialog .fe-description,.fe-shortcut-dialog .fe-description { font-size:12px; margin:4px 0 6px; }
  .fe-pack-dialog .fe-actions,.fe-shortcut-dialog .fe-actions { flex-shrink:0; margin-top:8px; }
  .fe-pack-dialog .fe-actions button,.fe-shortcut-dialog .fe-actions button { min-height:30px!important; padding:5px 10px!important; line-height:20px!important; }
}
`;
