# Backlog

Vertical slices, smallest valuable first.

## Now
- [ ] Slice 1: An analyst drops one borrower's rent roll and sees occupancy and rent per property, reconciled to the file total
  - Given a valid file, when it is loaded twice, then the warehouse has no duplicates
  - Given a file whose total doesn't match its rows, then the load fails and the file is quarantined with a reason
  - Given a dashboard figure, then its source file and row can be looked up
  - Test notes: one acceptance test per criterion; seeded invented data.

## Next
- [ ] Sketch leg: tokens + three variants of the slice-1 screen (`sketch-ui`)
- [ ] CI green with all gates before the first feature commit

## Later
