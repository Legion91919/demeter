# Decision: portfolio dashboard (slice 1)

Reviewed at 1440px and 390px widths. Scores 1-5.

| Variant | Main job speed | Clarity of numbers | Accessibility | Fits tone | Total |
|---|---|---|---|---|---|
| A: dense table | 5 | 5 | 4 (keyboard rows, but colour-only meters need %) | 5 | 19 |
| B: summary cards | 3 | 3 (amounts in prose, no column to scan) | 4 | 4 | 14 |
| C: load inbox | 3 | 4 | 4 | 4 | 15 |

**Pick: A, with B's KPI strip on top and C's drop zone and status chips for job runs.**

- Analysts compare six-to-forty properties side by side; only a table with right-aligned tabular numbers lets them scan rent and occupancy in one pass (A).
- Credit committee members want four numbers at a glance; B's KPI strip gives them that without a second screen.
- C's insight that quarantined files must be impossible to miss survives as the always-visible "files in quarantine" KPI and the job-run table with icon + word status chips (never colour alone).
- New in the final: a lineage drill-down panel. Selecting a property lists its units with source file, line number, job run id and the exact raw line from the unchanged file (AC3).
- Mobile (390px): KPI strip wraps to 2x2, the property table scrolls horizontally inside its card, the lineage panel stacks below.
