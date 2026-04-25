🤖 FastCI Optimization — Cache improvements

Summary
- Use lockfile-based cache keys for Turbo to improve cache hit rates across commits.
- Add a `Cache Bun` step to preserve Bun install cache between runs.
- Broaden Playwright cache restore-keys to increase reuse across runner versions.

Files changed
- .github/workflows/test.yml — change cache keys and add Bun cache.

Why
- Diagnostics showed cache inefficiencies and repeated cache steps. These changes are conservative, scoped to CI only, and adhere to the repo's lockfile-based cache policy.

What remains
- After this PR is run, fetch the produced trace artifact and run the CLI diff to compute real impact. We'll update this PR body with the `compare_reports` output and FinOps delta.

Checklist
- [ ] Confirm PR run completed and artifacts are available
- [ ] Update this body with `python3 -m tools.fastci_cli diff data/trace.jsonl data/latest_trace.jsonl --pr > pr_body.md`
- [ ] Address any regressions
