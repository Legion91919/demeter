// Pure render functions: data in, HTML string out (escaped). Easy to test without a DOM.
import { ago, calendarDate, escapeHtml as e, money, percent, statusChip } from './format';
import type { Freshness, JobRun, Lineage, Portfolio, PropertyFigure } from './types';

export const propertyKey = (p: Pick<PropertyFigure, 'borrower_id' | 'property_code'>): string =>
  `${p.borrower_id}/${p.property_code}`;

export const skeleton = (rows = 4): string =>
  `<div aria-busy="true">${'<div class="skel"></div>'.repeat(rows)}</div>`;

export const errorNote = (message: string): string =>
  `<div class="note" role="alert">${e(message)} <button class="primary" data-action="retry" type="button">Retry</button></div>`;

export function freshness(f: Freshness | null, now: Date = new Date()): string {
  if (!f) return 'Freshness unknown';
  if (!f.latest_as_of_date || !f.last_successful_load_at) return 'No data loaded yet';
  return `Data as of ${calendarDate(f.latest_as_of_date)} · last load ${ago(f.last_successful_load_at, now)}`;
}

export function kpis(p: Portfolio | null): string {
  const tile = (label: string, value: string, cls = '') =>
    `<div class="kpi"><span>${e(label)}</span><strong class="${cls}">${value}</strong></div>`;
  if (!p || p.properties.length === 0) {
    return ['Portfolio occupancy', 'Contracted rent / month', 'Properties · units', 'Files in quarantine']
      .map((label) => tile(label, '–'))
      .join('');
  }
  const q = p.freshness.files_in_quarantine;
  return [
    tile('Portfolio occupancy', percent(p.totals.occupancy_pct)),
    tile('Contracted rent / month', `R ${money(p.totals.monthly_rent)}`),
    tile('Properties · units', `${p.totals.properties} · ${p.totals.units}`),
    tile('Files in quarantine', q > 0 ? `✕ ${q}` : '✓ 0', q > 0 ? 'bad' : 'ok'),
  ].join('');
}

export function propertyTable(properties: PropertyFigure[], selected: string | null): string {
  if (properties.length === 0) {
    return '<p class="muted">No rent rolls loaded. Load a borrower\'s file in the panel on the right.</p>';
  }
  const rows = properties
    .map((p) => {
      const key = propertyKey(p);
      const isSel = key === selected;
      return `<tr tabindex="0" data-key="${e(key)}" class="${isSel ? 'sel' : ''}" aria-selected="${isSel}">
        <td>${e(p.property_name)}</td><td>${e(p.borrower_name)}</td>
        <td class="num">${p.units}</td><td class="num">${p.occupied_units}</td>
        <td><span class="meter" title="${p.occupied_units} of ${p.units} units let"><i style="width:${Number(p.occupancy_pct)}%"></i></span>${percent(p.occupancy_pct)}</td>
        <td class="num">${money(p.monthly_rent)}</td>
        <td class="muted small">${e(calendarDate(p.as_of_date))}</td></tr>`;
    })
    .join('');
  return `<div class="scroll"><table><thead><tr><th>Property</th><th>Borrower</th><th class="num">Units</th>
    <th class="num">Let</th><th>Occupancy</th><th class="num">Rent / month</th><th>As of</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

export function lineagePanel(l: Lineage): string {
  if (l.rows.length === 0) return `<p class="muted">No rows for ${e(l.property_name)}.</p>`;
  const total = l.rows.reduce((sum, r) => sum + Math.round(Number(r.monthly_rent) * 100), 0);
  const rows = l.rows
    .map(
      (r) => `<tr><td>${e(r.unit_ref)}</td><td class="num">${money(r.monthly_rent)}</td>
      <td>${e(r.source_file_name)} · line ${r.source_row}
      <div class="raw">${e(r.raw_line ?? '(raw line unavailable)')}</div>
      <div class="muted small">job run ${e(r.job_run_id.slice(0, 8))}</div></td></tr>`,
    )
    .join('');
  return `<p><b>${e(l.property_name)}</b> <span class="muted">· ${e(l.borrower_name)}</span></p>
    <table><thead><tr><th>Unit</th><th class="num">Rent</th><th>Source file · line</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="muted small">Sum of units: ${money((total / 100).toFixed(2))} (equals the dashboard figure)</p>`;
}

export function jobRunTable(runs: JobRun[]): string {
  if (runs.length === 0) return '<p class="muted">No job runs yet.</p>';
  const rows = runs
    .map((r) => {
      const chip = statusChip(r);
      return `<tr><td class="small">${e(r.started_at.slice(0, 16).replace('T', ' '))}</td><td>${e(r.original_name)}</td>
        <td><span class="chip ${chip.tone}">${chip.icon} ${chip.label}</span></td>
        <td class="num">${r.rows_read}</td><td class="num">${r.rows_written}</td><td class="num">${r.rows_rejected}</td>
        <td class="num">${r.duration_ms ?? '–'}</td><td>${e(r.message ?? '')}</td></tr>`;
    })
    .join('');
  return `<div class="scroll"><table><thead><tr><th>Started (UTC)</th><th>File</th><th>Status</th><th class="num">Read</th>
    <th class="num">Written</th><th class="num">Rejected</th><th class="num">ms</th><th>Message</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

export function uploadResult(run: JobRun): string {
  const chip = statusChip(run);
  return `<div class="note ${chip.tone}-edge"><b class="${chip.tone}">${chip.icon} ${e(run.original_name)}</b>:
    ${run.rows_read} read · ${run.rows_written} written · ${run.rows_rejected} rejected. ${e(run.message ?? '')}</div>`;
}

export function uploadProblem(title: string, detail: string): string {
  return `<div class="note" role="alert"><b class="bad">✕ ${e(title)}:</b> ${e(detail)}</div>`;
}
