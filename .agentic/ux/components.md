# Components (portfolio dashboard)

Every data component designs four states: **loading** (skeleton rows, `aria-busy`), **empty** (what to do next), **error** (problem detail + retry), **success**.

| Component | Props | Loading | Empty | Error | Success |
|---|---|---|---|---|---|
| `AppHeader` | `freshness: {latest_as_of_date, last_successful_load_at}` | "Checking data..." | "No data loaded yet" | "Freshness unknown" | "Data as of 31 Oct 2026 · last load 06:02" |
| `KpiStrip` | `totals: {occupancy_pct, monthly_rent, properties, units}`, `filesInQuarantine` | 4 grey tiles | dashes | hidden (the page error shows) | 4 tiles; quarantine tile uses icon + count |
| `UploadPanel` | `onUpload(file, layout?)`, `layouts[]`, `busy` | button disabled, "Loading file..." | idle drop zone | problem `detail` (e.g. reconciliation reason) in a danger note | "Loaded: 8 read · 8 written · 0 rejected" |
| `PropertyTable` | `properties[]`, `selectedKey`, `onSelect(key)` | 5 skeleton rows | "No rent rolls loaded. Drop a file above." | message + Retry | rows: property, borrower, units, occupied, occupancy meter + %, rent / month, source file |
| `OccupancyMeter` | `pct` | n/a | n/a | n/a | 8px bar (data-bar on data-track) with the % always printed beside it |
| `LineagePanel` | `borrowerId`, `propertyCode` | skeleton | "Select a property to trace its figures" | message + Retry | units with rent, file name, line, job run id (short), raw line in mono |
| `JobRunTable` | `runs[]` | skeleton rows | "No job runs yet" | message + Retry | file, status chip (icon + word), read, written, rejected, duration, message |
| `StatusChip` | `status: succeeded | quarantined | failed | running`, `rejected` | n/a | n/a | n/a | ✓ loaded / ⚠ loaded with rejects / ✕ quarantined / ✕ failed |
