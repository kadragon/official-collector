## Security Fixes — official-collector

> Fix all open GitHub security alerts for this repository.

### Dependabot Alerts

- [x] Upgrade PyJWT to >=2.12.0 (HIGH) — PyJWT accepts unknown `crit` header extensions (GHSA-752w-5fwx-jx9f). Transitive dependency — pin or constrain in pyproject.toml
- [x] Upgrade Pygments to >=2.20.0 (LOW) — ReDoS due to inefficient regex for GUID matching (GHSA-5239-wwwm-4pmq). Transitive dependency — pin or constrain in pyproject.toml

### Code Scanning Alerts

- [x] Fix `.bandit` config format — current YAML-style `exclude_dirs` is not parsed by bandit (expects INI format). Convert to proper INI: `[bandit]\nexclude = tests`. This will resolve all 317 B101 (assert used) false positives in test files
- [x] Update `bandit.yml` workflow `excluded_paths` glob — current `tests/**,tests/*` may not match all subdirectories. Verify exclusion works after `.bandit` fix and remove redundant patterns if needed
- [x] Dismiss or resolve 30 remaining B101 (assert_used) alerts — all in test files, false positives. `.bandit` INI config already excludes `./tests`; alerts will auto-close on next workflow run
