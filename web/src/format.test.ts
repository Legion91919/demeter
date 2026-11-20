import { describe, expect, it } from 'vitest';
import { ago, calendarDate, escapeHtml, money, percent, statusChip } from './format';

describe('money', () => {
  it('groups thousands on the decimal string without float rounding', () => {
    expect(money('384282.42')).toBe('384,282.42');
    expect(money('0.10')).toBe('0.10');
    expect(money('1234567890123.99')).toBe('1,234,567,890,123.99');
    expect(money('-4000.00')).toBe('-4,000.00');
  });
});

describe('dates and percentages', () => {
  it('formats calendar dates without time-zone shifts', () => {
    expect(calendarDate('2026-10-31')).toBe('31 Oct 2026');
  });
  it('describes freshness relative to now', () => {
    const now = new Date('2026-11-02T06:30:00Z');
    expect(ago('2026-11-02T06:18:00Z', now)).toBe('12 min ago');
    expect(ago('2026-11-01T06:30:00Z', now)).toBe('24 h ago');
  });
  it('prints one decimal and a dash for unknown', () => {
    expect(percent('72.7')).toBe('72.7%');
    expect(percent(null)).toBe('–');
  });
});

describe('statusChip', () => {
  it('never relies on colour alone', () => {
    expect(statusChip({ status: 'succeeded', rows_rejected: 0 })).toEqual({ icon: '✓', label: 'loaded', tone: 'ok' });
    expect(statusChip({ status: 'succeeded', rows_rejected: 1 }).label).toBe('loaded, rejects');
    expect(statusChip({ status: 'quarantined', rows_rejected: 6 })).toMatchObject({ icon: '✕', label: 'quarantined' });
  });
});

it('escapes HTML from file contents', () => {
  expect(escapeHtml('<b>"Tern & Co"</b>')).toBe('&lt;b&gt;&quot;Tern &amp; Co&quot;&lt;/b&gt;');
});
