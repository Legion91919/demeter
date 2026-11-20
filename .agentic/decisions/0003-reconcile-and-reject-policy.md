# 0003. Reconcile the whole file; quarantine bad rows, never half a file

- Status: Accepted
- Date: 2026-11-20

## Context

Product constraint: files kept unchanged; bad files quarantined, never half-loaded. Borrower files can also contain a few individually invalid rows (a blank suite reference, a lease that ends before it starts).

## Decision

1. Reconciliation is a file-integrity check: the sum of the amount column over every data row (valid or not) must equal the total row, in the file's own unit (annual for layouts that state annual rent), and the unit count must match when the file states one. Any mismatch, missing total row or unreadable amount fails the job, quarantines the file with the reason, and writes nothing to the model.
2. A file that reconciles is loaded in one transaction. Rows that fail the contract or the shared rules go to `quarantine_rows` with the file, line and reason; the job run records them as rejected and the dashboard shows the count.
3. A later file for the same borrower and as-of date replaces that month completely (upsert, then delete rows not written by this run).

## Alternatives considered

- Fail the whole file on any invalid row: safest, but one blank cell would hold a borrower's whole portfolio back for a month.
- Reconcile only the valid rows: would fail every file with a single bad row and hide which problem actually happened.

## Consequences

- A loaded figure can exclude rows the borrower sent; the job run, quarantine list and dashboard say so explicitly.
- Revisit when the credit committee asks for a threshold (for example, fail when rejected rent exceeds 1% of the file total).
