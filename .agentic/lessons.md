# Lessons

Generic, reusable lessons only. No client names, data or secrets.

- Reconcile against every row the source sent (valid or not), in the source's own unit, before validation; then validate rows separately. Mixing the two hides which problem happened.
- Use the content checksum as the raw file's name and the business natural key as the upsert key: re-runs become safe without client idempotency keys.
- Keep lineage at physical line granularity and read the raw line back from the immutable file; auditors trust the exact text more than a re-rendered row.
- Recent ruff versions also pick up Markdown files; set `include = ["*.py", "pyproject.toml"]` so lint never touches docs.
- Render functions that return escaped HTML strings make a framework-free TypeScript UI easy to unit-test without a DOM.
