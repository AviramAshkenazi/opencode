# Decision Log — FastCI cache improvements

Date: 2026-04-25

Summary:
- Identified cache key granularity and missing Bun cache as likely contributors to low cache hit rates.
- Modified `.github/workflows/test.yml` to: (1) use lockfile-based hash keys instead of commit-specific key; (2) add a `Cache Bun` step before `Setup Bun`; (3) widen Playwright restore-keys.

Reasoning:
- Per diagnostics (`python3 -m tools.fastci_cli diagnose data/trace.jsonl`) the FinOps report showed total cache duration ~4000ms but retries were high for steps like `-o` and `actions/cache@v4` repeated attempts.
- Lockfile-based hashing increases chance cache hits across commits with identical dependencies.
- Adding a Bun cache avoids repeated Bun downloads/install overhead.

Next steps:
- Open PR on ephemeral branch `fastci-agent/ci-cache-improve`.
- After PR run completes, fetch latest trace and run `python3 -m tools.fastci_cli diff data/trace.jsonl data/latest_trace.jsonl --pr > pr_body.md` to generate the PR body with diff.
