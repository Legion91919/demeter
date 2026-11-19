# 0001. Architecture style

- Status: Accepted
- Date: 2026-11-19

## Context

Borrowers send Harbourline rent rolls in a dozen layouts, so the portfolio view is rebuilt by hand every month and rarely reconciles first time. Traits: BatchDataFeeds, ReadHeavy, ExternalPartnerIntegrations, RegulatoryAudit, SmallTeam.

## Decision

Build one re-runnable import job per layout into a single warehouse, with a plain read-only dashboard on top.

## Alternatives considered

- Spreadsheet macros: what exists today; no lineage or reconciliation.
- A streaming platform: monthly files don't need it.

## Consequences

- Clear boundaries that tests can enforce.
- Room to extract a part later if its load demands it.
