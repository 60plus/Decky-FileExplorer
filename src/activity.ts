let openExplorers = 0;
export function explorerOpened() { openExplorers++; }
export function explorerClosed() { openExplorers = Math.max(0, openExplorers - 1); }
export function explorerVisible() { return openExplorers > 0; }
