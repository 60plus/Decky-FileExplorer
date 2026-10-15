const pad = (value: number) => String(value).padStart(2, '0');

export function fileDate(seconds: number) {
  const value = new Date(seconds * 1000);
  // Archives can omit timestamps (represented by zero). Do not invent 1970 dates.
  if (!Number.isFinite(seconds) || seconds === 0 || !Number.isFinite(value.getTime())) {
    return { date: '—', time: '', title: 'Modification date unavailable', iso: undefined };
  }
  const date = `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
  const time = `${pad(value.getHours())}:${pad(value.getMinutes())}`;
  return { date, time, title: `Last modified: ${value.toLocaleString()}`, iso: value.toISOString() };
}
