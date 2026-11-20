# User flows

## 1. Load a rent roll and see the reconciled portfolio (slice 1)
1. Analyst opens the dashboard (`screens/portfolio.html`, web `/`); the app calls `GET /api/portfolio` and `GET /api/job-runs`.
2. Analyst drops a borrower's CSV in the upload panel; the app calls `POST /api/loads` (multipart `file`, optional `layout`).
3. The API lands the file unchanged (checksum), detects the layout, reconciles rows against the file's total and loads it.
   - Success (`201`): the job-run table shows read / written / rejected; portfolio and freshness refresh.
   - Mismatch (`422` problem+json): the upload panel shows the reason; the job-run table shows "✕ quarantined"; the portfolio is unchanged.
4. Analyst selects a property row; the lineage panel calls `GET /api/properties/{borrower_id}/{property_code}/lineage` and lists each unit with source file, line and job run id, plus the raw line.

## 2. Re-run a load (operations)
1. Engineer runs `python -m demeter.cli load <file>` (or re-uploads). The same bytes produce no duplicates; a new job run is recorded.
2. A corrected file for the same borrower and month replaces the earlier rows completely.

## 3. Review quarantine
1. `GET /api/quarantine` lists quarantined files (with reason) and quarantined rows (file, line, reason). The KPI strip shows the count.
