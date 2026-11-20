# Backlog

Vertical slices, smallest valuable first.

## Now
- [x] Slice 1: An analyst drops one borrower's rent roll and sees occupancy and rent per property, reconciled to the file total
  - [x] Given a valid file, when it is loaded twice, then the warehouse has no duplicates
  - [x] Given a file whose total doesn't match its rows, then the load fails and the file is quarantined with a reason
  - [x] Given a dashboard figure, then its source file and row can be looked up
  - Test notes: one acceptance test per criterion; seeded invented data. Done: `tests/test_pipeline.py`, `tests/test_api.py` (see `docs/DESIGN.md` section 13).

## Next
- [x] Sketch leg: tokens + three variants of the slice-1 screen (`sketch-ui`)
- [ ] CI green with all gates before the first feature commit (workflow written; not yet run on GitHub)
- [ ] Slice 2: month-over-month view per property (occupancy and rent change since last roll), so the committee sees movement, not just a snapshot
- [ ] Slice 3: file inbox (folder/SFTP watcher calling `run_load`) and a re-load button for quarantined files after a contract fix

## Later
- Operating statements (second feed) and covenant checks: a second module (ADR-0001 trigger)
- SSO and roles before any real data
- Postgres warehouse when a second writer process appears (ADR-0002 trigger)
