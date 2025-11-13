# Phase 3 Performance Analysis Guide

This document explains how to use the Phase 3 performance analysis script to monitor and improve the performance of payment-info windows and circulation dialogs.

## Overview

Phase 3 of the performance logging plan focuses on:
- **Payment Info Windows**: `ensure_payment_info_window()`
- **Circulation Dialogs**: Reception confirmation, circulation completion, approval flows

The `phase3_analysis.py` script extracts performance metrics from log files, calculates statistics, stores baselines, and generates reports.

## Prerequisites

All Phase 3 operations are already instrumented with `@log_execution_time` decorator:
- `src/services/window_manager.py:128` - `ensure_payment_info_window()`
- `src/services/dialog_handler.py:363` - `handle_reception_confirmation()`
- `src/services/dialog_handler.py:402` - `handle_circulation_completion()`
- `src/services/dialog_handler.py:467` - `handle_approval_confirmation()`
- `src/services/dialog_handler.py:529` - `handle_approval_result()`
- `src/services/dialog_handler.py:436` - `handle_reception_result()`

## Usage

### 1. Analyze a Single Log File

```bash
python -m src.utils.phase3_analysis --log-file logs/app_20251113_143000.log
```

This will:
- Parse the specified log file
- Extract Phase 3 performance metrics
- Display a performance report in the terminal

### 2. Analyze All Log Files

```bash
python -m src.utils.phase3_analysis --analyze-all
```

This aggregates metrics from all `app_*.log` files in the `logs/` directory.

### 3. Save a Performance Report

```bash
python -m src.utils.phase3_analysis --analyze-all --report reports/phase3_report.md
```

This generates a Markdown report with:
- Total operation counts
- Success rates
- Average/min/max execution times
- Standard deviation

### 4. Create a Performance Baseline

```bash
python -m src.utils.phase3_analysis --analyze-all --save-baseline data/phase3_baseline.json
```

Use this to establish a baseline for future comparisons. Save baselines after major optimizations or deployments.

### 5. Compare Two Baselines

```bash
python -m src.utils.phase3_analysis --compare data/phase3_baseline_old.json data/phase3_baseline_new.json
```

This shows:
- Performance changes (seconds and percentage)
- Improvements (✅) or regressions (⚠️)
- Per-operation comparison

## Example Workflow

### Initial Baseline Creation

After deploying Phase 3 instrumentation:

```bash
# Run your application normally to generate logs
python -m src.main

# Create initial baseline
python -m src.utils.phase3_analysis --analyze-all --save-baseline data/phase3_baseline_initial.json

# Generate initial report
python -m src.utils.phase3_analysis --analyze-all --report reports/phase3_initial_report.md
```

### After Optimization

After making performance improvements:

```bash
# Run application to generate new logs
python -m src.main

# Create new baseline
python -m src.utils.phase3_analysis --analyze-all --save-baseline data/phase3_baseline_optimized.json

# Compare with initial baseline
python -m src.utils.phase3_analysis --compare data/phase3_baseline_initial.json data/phase3_baseline_optimized.json
```

## Report Format

The generated report includes:

```markdown
# Phase 3 Performance Report

**Generated:** 2025-11-13 15:30:00

## Summary

- **Total Phase 3 Operations:** 150
- **Operation Types Tracked:** 6

## Detailed Metrics

### Payment Info Window (`ensure_payment_info_window`)

- **Execution Count:** 25
- **Success Rate:** 100.0%
- **Average Duration:** 0.523s
- **Min/Max Duration:** 0.350s / 0.780s
- **Std Deviation:** 0.089s
```

## Baseline Comparison Output

```
# Baseline Comparison

Baseline 1: 2025-11-13T14:00:00
Baseline 2: 2025-11-13T16:00:00

## Payment Info Window
  Old: 0.523s
  New: 0.412s
  Change: -0.111s (-21.2%)
  ✅ IMPROVEMENT

## Circulation Completion Dialog
  Old: 1.234s
  New: 1.450s
  Change: +0.216s (+17.5%)
  ⚠️  REGRESSION
```

## Tracked Operations

| Operation | Description | File Location |
|-----------|-------------|---------------|
| `ensure_payment_info_window` | Opens payment info window | `window_manager.py:128` |
| `handle_reception_confirmation` | Handles reception confirmation dialog | `dialog_handler.py:363` |
| `handle_circulation_completion` | Handles circulation completion dialog | `dialog_handler.py:402` |
| `handle_approval_confirmation` | Handles approval confirmation dialog | `dialog_handler.py:467` |
| `handle_approval_result` | Handles approval result dialog | `dialog_handler.py:529` |
| `handle_reception_result` | Handles reception result dialog | `dialog_handler.py:436` |

## Performance Targets

Based on `.governance/patterns.md`:
- Store per-phase baselines (Phase 1-7) to compare improvements and regressions
- Target: 40-50% throughput improvement over non-instrumented baseline
- Monitor for performance degradation after changes

## Troubleshooting

### No metrics found

**Problem:** Script reports "No data collected for this operation"

**Solutions:**
1. Ensure the operation was actually executed during the log collection period
2. Verify that `@log_execution_time` decorator is applied to the function
3. Check log file format matches expected pattern: `⏱️ operation_name 완료 (소요시간: X.XXX초)`

### Missing log files

**Problem:** `logs/` directory is empty

**Solutions:**
1. Run the application at least once to generate logs
2. Check that `initialize_execution_logger()` is called in `main.py`
3. Verify write permissions for the `logs/` directory

## Integration with CI/CD

To track performance regressions in CI/CD:

```bash
# In your CI pipeline
python -m src.utils.phase3_analysis --analyze-all --save-baseline artifacts/phase3_${CI_COMMIT_SHA}.json

# Compare with previous baseline
python -m src.utils.phase3_analysis --compare artifacts/phase3_baseline.json artifacts/phase3_${CI_COMMIT_SHA}.json > comparison.txt

# Fail if major regression detected (custom logic needed)
```

## Related Documentation

- `.governance/patterns.md` - Performance instrumentation patterns
- `.spec/performance-observability/spec.yaml` - Phase 3 specification
- `src/utils/performance_logger.py` - Performance logging utilities
- `docs/RUNBOOK.md` - Production monitoring and operations

## Next Steps

After Phase 3 completion:
- Consider adding Phase 4-7 instrumentation for remaining operations
- Set up automated baseline comparison in CI/CD
- Create performance dashboards using aggregated metrics
- Implement alerting for performance regressions
