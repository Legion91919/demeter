import './styles.css';
import { ApiError, getJobRuns, getLineage, getPortfolio, uploadRentRoll } from './api';
import * as view from './render';
import type { Portfolio } from './types';

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
let selected: string | null = null;
let portfolio: Portfolio | null = null;

const message = (err: unknown) => (err instanceof Error ? err.message : 'Something went wrong');

async function loadPortfolio(): Promise<void> {
  $('properties').innerHTML = view.skeleton(5);
  try {
    portfolio = await getPortfolio();
    $('freshness').textContent = view.freshness(portfolio.freshness);
    $('kpis').innerHTML = view.kpis(portfolio);
    $('properties').innerHTML = view.propertyTable(portfolio.properties, selected);
  } catch (err) {
    $('freshness').textContent = view.freshness(null);
    $('kpis').innerHTML = view.kpis(null);
    $('properties').innerHTML = view.errorNote(`Could not load the portfolio: ${message(err)}`);
  }
}

async function loadRuns(): Promise<void> {
  $('runs').innerHTML = view.skeleton(3);
  try {
    $('runs').innerHTML = view.jobRunTable(await getJobRuns());
  } catch (err) {
    $('runs').innerHTML = view.errorNote(`Could not load job runs: ${message(err)}`);
  }
}

async function trace(key: string): Promise<void> {
  selected = key;
  if (portfolio) $('properties').innerHTML = view.propertyTable(portfolio.properties, selected);
  const [borrower = '', code = ''] = key.split('/');
  $('lineage').innerHTML = view.skeleton(4);
  try {
    $('lineage').innerHTML = view.lineagePanel(await getLineage(borrower, code));
  } catch (err) {
    $('lineage').innerHTML = view.errorNote(`Could not trace this property: ${message(err)}`);
  }
}

const refresh = () => Promise.all([loadPortfolio(), loadRuns()]);

$('properties').addEventListener('click', (ev) => {
  const row = (ev.target as HTMLElement).closest<HTMLTableRowElement>('tr[data-key]');
  if (row?.dataset.key) void trace(row.dataset.key);
});
$('properties').addEventListener('keydown', (ev) => {
  const row = (ev.target as HTMLElement).closest<HTMLTableRowElement>('tr[data-key]');
  if (!row) return;
  if (ev.key === 'Enter' && row.dataset.key) void trace(row.dataset.key);
  if (ev.key === 'ArrowDown') (row.nextElementSibling as HTMLElement | null)?.focus();
  if (ev.key === 'ArrowUp') (row.previousElementSibling as HTMLElement | null)?.focus();
});
document.body.addEventListener('click', (ev) => {
  if ((ev.target as HTMLElement).dataset.action === 'retry') void refresh();
});

$<HTMLFormElement>('upload').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const input = $<HTMLInputElement>('file');
  const file = input.files?.[0];
  if (!file) return;
  const button = (ev.currentTarget as HTMLFormElement).querySelector('button')!;
  button.disabled = true;
  $('upload-result').textContent = 'Loading file…';
  try {
    $('upload-result').innerHTML = view.uploadResult(await uploadRentRoll(file));
  } catch (err) {
    const p = err instanceof ApiError ? err.problem : { title: 'Upload failed', detail: message(err) };
    $('upload-result').innerHTML = view.uploadProblem(p.title, p.detail);
  } finally {
    button.disabled = false;
    input.value = '';
    await refresh();
  }
});

void refresh();
