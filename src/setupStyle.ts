import { gamepadDialogClasses } from '@decky/ui';

// Steam's own class names are hashed, so compact-field rules use the names
// @decky/ui resolves at runtime. A missing name selects nothing.
const steam = (classes: Record<string, string> | undefined, name: string) => {
  const value = classes?.[name];
  return typeof value === 'string' && /^[\w-]+$/.test(value) ? `.${value}` : '.fe-no-such-class';
};
const field = steam(gamepadDialogClasses, 'Field'), fieldLabel = steam(gamepadDialogClasses, 'FieldLabel');

export const setupCss = `
/* Keep the whole wizard inside the handheld viewport: only the settings list
   scrolls, the heading and the Save/Back row always stay visible. */
.fe-setup-modal { max-height:calc(100vh - 100px)!important; display:flex!important; flex-direction:column!important; overflow:hidden!important; }
.fe-setup-modal .DialogContent_InnerWidth,.fe-setup-modal form { display:flex; flex-direction:column; flex:1; min-height:0; max-height:100%; }
.fe-setup { display:flex; flex-direction:column; flex:1; min-height:0; min-width:460px; max-width:640px; }
.fe-setup .fe-setup-step,.fe-setup .fe-info-heading,.fe-setup .fe-description,.fe-setup .fe-setup-summary,.fe-setup .fe-error,.fe-setup > .fe-actions { flex-shrink:0; }
.fe-setup > .fe-actions { margin-top:10px; }
.fe-setup-step { color:#8fa6bd; font-size:11px; letter-spacing:1.5px; text-transform:uppercase; text-align:center; margin-bottom:4px; }
.fe-setup-intro { color:#c7d6e4; font-size:14px; line-height:1.55; text-align:center; text-wrap:balance; margin:0 0 14px; min-height:0; overflow:auto; }
.fe-setup-intro p { margin:4px 0; }
.fe-setup-intro ol { margin:8px 0; padding:0; list-style-position:inside; }
.fe-setup-intro li { margin:3px 0; }
.fe-setup-profiles { display:flex; flex-direction:column; gap:10px; }
.fe-setup-profile { text-align:center!important; text-wrap:balance; height:auto!important; white-space:normal!important; line-height:1.45!important; padding:12px 14px!important; }
.fe-setup-profile strong { display:block; font-size:16px; margin-bottom:4px; }
.fe-setup-profile span { display:block; font-size:12px; font-weight:400; color:#b6c7d7; }
.fe-setup-profile.gpfocus span,.fe-setup-profile:focus span { color:inherit; opacity:.85; }
.fe-setup-summary { font-size:12px; color:#e8b965; margin:0 0 6px; line-height:1.4; text-align:center; text-wrap:balance; }
.fe-setup-summary-line { display:block; }
.fe-setup > .fe-setup-fields,.fe-setup > .fe-setup-profiles { flex:1; min-height:0; max-height:none; overflow:auto; padding-right:4px; }
/* Step 3 is a long list on a short screen: tighter heading, fields that never
   shrink (the list scrolls instead) and compact padding on non-slider rows.
   Slider rows keep Steam's own padding so their notches stay inside. */
.fe-setup[data-step="3"] .fe-info-heading { margin:0 0 4px; font-size:18px; }
.fe-setup[data-step="3"] .fe-info-icon { width:20px; height:20px; font-size:14px; }
.fe-setup-fields { gap:4px!important; }
.fe-setup-fields > * { flex-shrink:0; }
.fe-setup-fields .fe-setting-help { padding:6px 12px 10px; }
.fe-setup-fields ${field}:not(:has([role="slider"])) { padding:6px 12px!important; }
.fe-setup-fields ${fieldLabel} { font-size:14px!important; }
.fe-setup-fields [role="slider"] { width:100%!important; min-width:0!important; box-sizing:border-box; }
/* Handheld: the wizard fills the space between Steam's header and footer, like
   the file manager window, so more settings fit at once. PC stays centered. */
@media (max-height:600px),(max-width:900px) {
  .fe-setup-modal { width:94vw!important; max-width:94vw!important; height:calc(100vh - 100px)!important; max-height:calc(100vh - 100px)!important; padding:10px 18px 12px!important; box-sizing:border-box; }
  .fe-setup-modal .DialogContent_InnerWidth { width:100%!important; max-width:none!important; }
  .fe-setup { min-width:0; max-width:none; width:100%; }
  .fe-setup-intro { margin-bottom:10px; }
  .fe-setup-profile { padding:9px 12px!important; }
  .fe-setup > .fe-actions { margin-top:8px; }
}
`;
