import type { JobRun } from './types';

/** "384282.42" -> "384,282.42". Works on the decimal string, so cents are never rounded by floats. */
export function money(value: string): string {
  const negative = value.startsWith('-');
  const [whole = '0', cents = '00'] = value.replace('-', '').split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${negative ? '-' : ''}${grouped}.${cents.padEnd(2, '0').slice(0, 2)}`;
}

export function percent(value: string | null): string {
  return value === null ? '–' : `${Number(value).toFixed(1)}%`;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-10-31" -> "31 Oct 2026" (no time-zone shifts: it's a calendar date). */
export function calendarDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${MONTHS[(m ?? 1) - 1]} ${y}`;
}

/** Human freshness, e.g. "12 min ago", relative to `now`. */
export function ago(iso: string, now: Date = new Date()): string {
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export interface Chip {
  icon: string;
  label: string;
  tone: 'ok' | 'warn' | 'bad' | 'muted';
}

/** Status is always icon + word, never colour alone. */
export function statusChip(run: Pick<JobRun, 'status' | 'rows_rejected'>): Chip {
  switch (run.status) {
    case 'succeeded':
      return run.rows_rejected > 0
        ? { icon: '⚠', label: 'loaded, rejects', tone: 'warn' }
        : { icon: '✓', label: 'loaded', tone: 'ok' };
    case 'quarantined':
      return { icon: '✕', label: 'quarantined', tone: 'bad' };
    case 'failed':
      return { icon: '✕', label: 'failed', tone: 'bad' };
    default:
      return { icon: '…', label: 'running', tone: 'muted' };
  }
}

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}
