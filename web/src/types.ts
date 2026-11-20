// Shapes returned by the rent-roll API. Money arrives as strings so no float ever touches it.
export interface Freshness {
  last_successful_load_at: string | null;
  latest_as_of_date: string | null;
  files_in_quarantine: number;
}
export interface PropertyFigure {
  borrower_id: string;
  borrower_name: string;
  property_code: string;
  property_name: string;
  as_of_date: string;
  units: number;
  occupied_units: number;
  occupancy_pct: string;
  monthly_rent: string;
  loaded_at: string;
  source_file_id: string;
  source_file_name: string;
  job_run_id: string;
}
export interface Portfolio {
  freshness: Freshness;
  totals: { properties: number; units: number; occupied_units: number; occupancy_pct: string | null; monthly_rent: string };
  properties: PropertyFigure[];
}
export type RunStatus = 'running' | 'succeeded' | 'quarantined' | 'failed';
export interface JobRun {
  job_run_id: string;
  file_id: string;
  original_name: string;
  layout_id: string | null;
  borrower_id: string | null;
  as_of_date: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  status: RunStatus;
  rows_read: number;
  rows_written: number;
  rows_rejected: number;
  message: string | null;
}
export interface LineageRow {
  unit_ref: string;
  occupied: boolean;
  monthly_rent: string;
  source_file_id: string;
  source_file_name: string;
  source_row: number;
  job_run_id: string;
  raw_line: string | null;
}
export interface Lineage {
  borrower_id: string;
  borrower_name: string;
  property_code: string;
  property_name: string;
  rows: LineageRow[];
}
export interface Problem {
  title: string;
  status: number;
  detail: string;
  job_run?: JobRun;
}
