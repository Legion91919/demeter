# Product brief

> Harbourline Lending is a fictional company. All names, documents and numbers in this repo are invented.

## Problem
Borrowers send Harbourline rent rolls in a dozen layouts, so the portfolio view is rebuilt by hand every month and rarely reconciles first time.

## Users
Portfolio analysts (daily); credit committee (monthly).

## Outcomes
Portfolio view refreshed within an hour of files arriving; totals reconcile automatically.

## Constraints
Files kept unchanged; bad files quarantined, never half-loaded.

## Out of scope
Anything not needed for the outcomes above in the first three slices.

## Traits (for the architecture advisor)
- BatchDataFeeds: "monthly rent rolls and operating statements from ~40 borrowers"
- ReadHeavy: "portfolio dashboard read daily, data changes monthly"
- ExternalPartnerIntegrations: "each borrower's layout is different"
- RegulatoryAudit: "every reported figure must trace to its source file"
- SmallTeam: "one engineer plus an analyst"
