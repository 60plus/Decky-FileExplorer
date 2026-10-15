type Intent = 'rename' | 'overwrite';
const intents = new Map<string, Intent>();
export function rememberConflictIntent(job: string, intent: Intent) {
  if (intents.size >= 20) intents.delete(intents.keys().next().value!);
  intents.set(job, intent);
}
export function takeConflictIntent(job: string) {
  const value = intents.get(job); intents.delete(job); return value;
}
