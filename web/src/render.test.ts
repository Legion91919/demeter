import { describe, expect, it } from 'vitest';
import { freshness, jobRunTable, kpis, lineagePanel, propertyTable } from './render';
import type { JobRun, Lineage, Portfolio } from './types';

const portfolio: Portfolio = {
  freshness: { last_successful_load_at: '2026-11-02T06:02:00Z', latest_as_of_date: '2026-10-31', files_in_quarantine: 1 },
  totals: { properties: 1, units: 4, occupied_units: 3, occupancy_pct: '75.0', monthly_rent: '54725.50' },
  properties: [
    {
      borrower_id: 'keelridge-estates', borrower_name: 'Keelridge Estates', property_code: 'KR-01',
      property_name: 'Keelridge Quay', as_of_date: '2026-10-31', units: 4, occupied_units: 3, occupancy_pct: '75.0',
      monthly_rent: '54725.50', loaded_at: '2026-11-02T06:02:00Z', source_file_id: 'abc',
      source_file_name: 'keelridge-estates_2026-10.csv', job_run_id: 'da327469-0000',
    },
  ],
};

describe('portfolio rendering', () => {
  it('shows freshness, KPIs and quarantine count with an icon', () => {
    expect(freshness(portfolio.freshness, new Date('2026-11-02T06:14:00Z'))).toBe(
      'Data as of 31 Oct 2026 · last load 12 min ago',
    );
    const html = kpis(portfolio);
    expect(html).toContain('75.0%');
    expect(html).toContain('R 54,725.50');
    expect(html).toContain('✕ 1');
  });

  it('renders empty and unknown states', () => {
    expect(freshness(null)).toBe('Freshness unknown');
    expect(freshness({ last_successful_load_at: null, latest_as_of_date: null, files_in_quarantine: 0 })).toBe(
      'No data loaded yet',
    );
    expect(propertyTable([], null)).toContain('No rent rolls loaded');
    expect(jobRunTable([])).toContain('No job runs yet');
  });

  it('marks the selected property row and prints the percentage next to the meter', () => {
    const html = propertyTable(portfolio.properties, 'keelridge-estates/KR-01');
    expect(html).toContain('data-key="keelridge-estates/KR-01"');
    expect(html).toContain('class="sel" aria-selected="true"');
    expect(html).toContain('width:75%');
    expect(html).toContain('54,725.50');
  });
});

describe('job runs and lineage', () => {
  it('shows rejected counts and a worded status for quarantined files', () => {
    const run: JobRun = {
      job_run_id: 'r1', file_id: 'f1', original_name: 'bad.csv', layout_id: 'tidewater', borrower_id: 'tidewater-living',
      as_of_date: '2026-10-31', started_at: '2026-11-02T06:01:00.123Z', finished_at: null, duration_ms: 7,
      status: 'quarantined', rows_read: 6, rows_written: 0, rows_rejected: 6, message: 'rows sum to <x>',
    };
    const html = jobRunTable([run]);
    expect(html).toContain('✕ quarantined');
    expect(html).toContain('<td class="num">6</td>');
    expect(html).toContain('rows sum to &lt;x&gt;');
  });

  it('lists source file, line, job run and raw line, and sums to the figure', () => {
    const lineage: Lineage = {
      borrower_id: 'keelridge-estates', borrower_name: 'Keelridge Estates', property_code: 'KR-01',
      property_name: 'Keelridge Quay',
      rows: [
        { unit_ref: '101', occupied: true, monthly_rent: '18450.00', source_file_id: 'abc', source_file_name: 'k.csv', source_row: 2, job_run_id: 'da327469-1111', raw_line: 'KR-01,Keelridge Quay,101' },
        { unit_ref: '103', occupied: true, monthly_rent: '21075.50', source_file_id: 'abc', source_file_name: 'k.csv', source_row: 4, job_run_id: 'da327469-1111', raw_line: null },
      ],
    };
    const html = lineagePanel(lineage);
    expect(html).toContain('k.csv · line 2');
    expect(html).toContain('job run da327469');
    expect(html).toContain('KR-01,Keelridge Quay,101');
    expect(html).toContain('Sum of units: 39,525.50');
  });
});
