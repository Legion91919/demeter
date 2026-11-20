import type { JobRun, Lineage, Portfolio, Problem } from './types';

export class ApiError extends Error {
  constructor(public readonly problem: Problem) {
    super(problem.detail || problem.title);
  }
}

async function json<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const problem: Problem = body && typeof body === 'object' && 'detail' in body
      ? (body as Problem)
      : { title: 'Request failed', status: response.status, detail: `HTTP ${response.status}` };
    throw new ApiError(problem);
  }
  return body as T;
}

export const getPortfolio = (): Promise<Portfolio> => fetch('/api/portfolio').then((r) => json<Portfolio>(r));
export const getJobRuns = (): Promise<JobRun[]> => fetch('/api/job-runs?limit=25').then((r) => json<JobRun[]>(r));
export const getLineage = (borrowerId: string, propertyCode: string): Promise<Lineage> =>
  fetch(`/api/properties/${encodeURIComponent(borrowerId)}/${encodeURIComponent(propertyCode)}/lineage`).then((r) =>
    json<Lineage>(r),
  );

export function uploadRentRoll(file: File): Promise<JobRun> {
  const form = new FormData();
  form.append('file', file);
  return fetch('/api/loads', { method: 'POST', body: form }).then((r) => json<JobRun>(r));
}
