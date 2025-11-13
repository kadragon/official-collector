"""
Phase 3 Performance Log Analysis Script.

Parses performance logs to extract Phase 3 metrics (payment-info windows and
circulation dialogs), calculates statistics, stores baselines, and generates reports.

Usage:
    python -m src.utils.phase3_analysis --log-file logs/app_YYYYMMDD_HHMMSS.log
    python -m src.utils.phase3_analysis --analyze-all  # Analyze all log files
    python -m src.utils.phase3_analysis --compare baseline.json current.json
"""

import re
import json
import argparse
import statistics
from pathlib import Path
from typing import Any
from datetime import datetime
from collections import defaultdict


# Phase 3 specific operations to track
PHASE3_OPERATIONS = {
    "ensure_payment_info_window": "Payment Info Window",
    "handle_circulation_completion": "Circulation Completion Dialog",
    "handle_reception_confirmation": "Reception Confirmation Dialog",
    "handle_approval_confirmation": "Approval Confirmation Dialog",
    "handle_approval_result": "Approval Result Dialog",
    "handle_reception_result": "Reception Result Dialog",
}


class PerformanceMetric:
    """Represents a single performance measurement."""

    def __init__(
        self, operation: str, duration: float, status: str, timestamp: str
    ) -> None:
        self.operation = operation
        self.duration = duration
        self.status = status  # '완료' or '실패'
        self.timestamp = timestamp


class Phase3Analyzer:
    """Analyzes Phase 3 performance logs."""

    def __init__(self) -> None:
        self.metrics: dict[str, list[PerformanceMetric]] = defaultdict(list)

    def parse_log_file(self, log_path: Path) -> None:
        """
        Parse a log file and extract Phase 3 performance metrics.

        Args:
            log_path: Path to the log file to parse
        """
        # Pattern: ⏱️ operation_name 완료 (소요시간: X.XXX초)
        # Pattern: ⏱️ operation_name 실패 (소요시간: X.XXX초) - error
        pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?⏱️\s+(\w+)\s+(완료|실패)\s+\(소요시간:\s+([\d.]+)초\)"
        )

        try:
            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        timestamp, operation, status, duration_str = match.groups()
                        # Only track Phase 3 operations
                        if operation in PHASE3_OPERATIONS:
                            metric = PerformanceMetric(
                                operation=operation,
                                duration=float(duration_str),
                                status=status,
                                timestamp=timestamp,
                            )
                            self.metrics[operation].append(metric)
        except FileNotFoundError:
            print(f"Error: Log file not found: {log_path}")
        except OSError as e:
            print(f"Error reading log file {log_path}: {e}")

    def calculate_statistics(
        self, operation: str
    ) -> dict[str, float | int] | dict[str, str]:
        """
        Calculate statistics for a specific operation.

        Args:
            operation: Name of the operation to analyze

        Returns:
            Dictionary containing statistics (count, avg, min, max, stddev, success_rate)
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return {"error": "No data available"}

        measurements = self.metrics[operation]
        durations = [m.duration for m in measurements]
        success_count = sum(1 for m in measurements if m.status == "완료")

        stats: dict[str, float | int] = {
            "count": len(measurements),
            "success_count": success_count,
            "failure_count": len(measurements) - success_count,
            "success_rate": (success_count / len(measurements)) * 100,
            "avg_duration": statistics.mean(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
        }

        if len(durations) > 1:
            stats["stddev"] = statistics.stdev(durations)
        else:
            stats["stddev"] = 0.0

        return stats

    def get_all_statistics(self) -> dict[str, dict[str, float | int] | dict[str, str]]:
        """
        Get statistics for all Phase 3 operations.

        Returns:
            Dictionary mapping operation names to their statistics
        """
        return {op: self.calculate_statistics(op) for op in PHASE3_OPERATIONS}

    def save_baseline(self, output_path: Path) -> None:
        """
        Save current statistics as a baseline for future comparisons.

        Args:
            output_path: Path to save the baseline JSON file
        """
        baseline = {
            "timestamp": datetime.now().isoformat(),
            "phase": "Phase 3",
            "operations": self.get_all_statistics(),
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, indent=2, ensure_ascii=False)
            print(f"Baseline saved to: {output_path}")
        except OSError as e:
            print(f"Error saving baseline to {output_path}: {e}")

    def generate_report(self, output_file: Path | None = None) -> str:
        """
        Generate a detailed performance report.

        Args:
            output_file: Optional path to save the report as a markdown file

        Returns:
            Markdown-formatted report string
        """
        report_lines = [
            "# Phase 3 Performance Report",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Summary\n",
        ]

        stats = self.get_all_statistics()
        total_operations = sum(
            s["count"] if isinstance(s, dict) and "count" in s else 0
            for s in stats.values()
        )

        report_lines.append(f"- **Total Phase 3 Operations:** {total_operations}")
        report_lines.append(
            f"- **Operation Types Tracked:** {len(PHASE3_OPERATIONS)}\n"
        )

        report_lines.append("## Detailed Metrics\n")

        for op_name, op_display in PHASE3_OPERATIONS.items():
            report_lines.append(f"### {op_display} (`{op_name}`)\n")

            op_stats = stats.get(op_name, {})
            if isinstance(op_stats, dict) and "error" in op_stats:
                report_lines.append("*No data collected for this operation.*\n")
                continue

            if not isinstance(op_stats, dict):
                continue

            count = op_stats.get("count", 0)
            success_rate = op_stats.get("success_rate", 0.0)
            avg_duration = op_stats.get("avg_duration", 0.0)
            min_duration = op_stats.get("min_duration", 0.0)
            max_duration = op_stats.get("max_duration", 0.0)
            stddev = op_stats.get("stddev", 0.0)

            report_lines.extend(
                [
                    f"- **Execution Count:** {count}",
                    f"- **Success Rate:** {success_rate:.1f}%",
                    f"- **Average Duration:** {avg_duration:.3f}s",
                    f"- **Min/Max Duration:** {min_duration:.3f}s / {max_duration:.3f}s",
                    f"- **Std Deviation:** {stddev:.3f}s\n",
                ]
            )

        report_content = "\n".join(report_lines)

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(report_content)
                print(f"Report saved to: {output_file}")
            except OSError as e:
                print(f"Error saving report to {output_file}: {e}")

        return report_content

    @staticmethod
    def compare_baselines(
        baseline1_path: Path, baseline2_path: Path
    ) -> dict[str, Any]:
        """
        Compare two baseline files and show performance differences.

        Args:
            baseline1_path: Path to first baseline (e.g., old baseline)
            baseline2_path: Path to second baseline (e.g., new baseline)

        Returns:
            Dictionary containing comparison results
        """
        try:
            with open(baseline1_path, encoding="utf-8") as f:
                baseline1 = json.load(f)
            with open(baseline2_path, encoding="utf-8") as f:
                baseline2 = json.load(f)
        except FileNotFoundError as e:
            return {"error": f"Baseline file not found: {e}"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in baseline file: {e}"}
        except OSError as e:
            return {"error": f"Error reading baseline file: {e}"}

        comparison: dict[str, Any] = {
            "baseline1_timestamp": baseline1.get("timestamp", "unknown"),
            "baseline2_timestamp": baseline2.get("timestamp", "unknown"),
            "operations": {},
        }

        ops1 = baseline1.get("operations", {})
        ops2 = baseline2.get("operations", {})

        for op_name in PHASE3_OPERATIONS:
            stats1 = ops1.get(op_name, {})
            stats2 = ops2.get(op_name, {})

            if (
                isinstance(stats1, dict)
                and "error" not in stats1
                and isinstance(stats2, dict)
                and "error" not in stats2
            ):
                avg1 = stats1.get("avg_duration", 0.0)
                avg2 = stats2.get("avg_duration", 0.0)

                if avg1 > 0:
                    change_percent = ((avg2 - avg1) / avg1) * 100
                else:
                    change_percent = 0.0

                comparison["operations"][op_name] = {
                    "baseline1_avg": avg1,
                    "baseline2_avg": avg2,
                    "change_seconds": avg2 - avg1,
                    "change_percent": change_percent,
                    "improvement": change_percent < 0,
                }

        return comparison


def main() -> None:
    """Main entry point for the Phase 3 analysis script."""
    parser = argparse.ArgumentParser(
        description="Analyze Phase 3 performance logs and generate reports"
    )
    parser.add_argument(
        "--log-file", type=str, help="Path to a specific log file to analyze"
    )
    parser.add_argument(
        "--analyze-all",
        action="store_true",
        help="Analyze all log files in the logs directory",
    )
    parser.add_argument(
        "--save-baseline", type=str, help="Save statistics as baseline to this file"
    )
    parser.add_argument(
        "--report", type=str, help="Save markdown report to this file"
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASELINE1", "BASELINE2"),
        help="Compare two baseline files",
    )

    args = parser.parse_args()

    # Comparison mode
    if args.compare:
        baseline1_path = Path(args.compare[0])
        baseline2_path = Path(args.compare[1])
        result = Phase3Analyzer.compare_baselines(baseline1_path, baseline2_path)

        if "error" in result:
            print(f"Comparison failed: {result['error']}")
            return

        print("\n# Baseline Comparison\n")
        print(f"Baseline 1: {result['baseline1_timestamp']}")
        print(f"Baseline 2: {result['baseline2_timestamp']}\n")

        for op_name, comparison in result["operations"].items():
            op_display = PHASE3_OPERATIONS.get(op_name, op_name)
            print(f"## {op_display}")
            print(f"  Old: {comparison['baseline1_avg']:.3f}s")
            print(f"  New: {comparison['baseline2_avg']:.3f}s")
            print(
                f"  Change: {comparison['change_seconds']:+.3f}s ({comparison['change_percent']:+.1f}%)"
            )
            if comparison["improvement"]:
                print("  ✅ IMPROVEMENT")
            else:
                print("  ⚠️  REGRESSION")
            print()
        return

    # Analysis mode
    analyzer = Phase3Analyzer()

    if args.analyze_all:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            print(f"Error: Logs directory not found: {logs_dir}")
            return

        log_files = list(logs_dir.glob("app_*.log"))
        if not log_files:
            print(f"No log files found in {logs_dir}")
            return

        print(f"Analyzing {len(log_files)} log files...")
        for log_file in log_files:
            analyzer.parse_log_file(log_file)
    elif args.log_file:
        log_path = Path(args.log_file)
        print(f"Analyzing log file: {log_path}")
        analyzer.parse_log_file(log_path)
    else:
        print("Error: Please specify --log-file or --analyze-all")
        parser.print_help()
        return

    # Generate report
    report = analyzer.generate_report(
        Path(args.report) if args.report else None
    )
    print("\n" + report)

    # Save baseline if requested
    if args.save_baseline:
        analyzer.save_baseline(Path(args.save_baseline))


if __name__ == "__main__":
    main()
