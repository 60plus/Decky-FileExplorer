import { memo } from 'react';
import { fileDate } from './fileDate';

export const ModifiedDate = memo(function ModifiedDate({ seconds }: { seconds: number }) {
  const value = fileDate(seconds);
  return <time className="fe-modified" dateTime={value.iso} title={value.title} aria-label={value.title}>
    <span>{value.date}</span><span className="fe-modified-time">{value.time}</span>
  </time>;
});
