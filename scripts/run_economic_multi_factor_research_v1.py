from __future__ import annotations

import argparse
import json

from factor_research.economic_sleeves import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Economic Multi-Factor Research V1")
    parser.add_argument(
        "--config",
        default="configs/economic_multi_factor_research_v1.yaml",
        help="Frozen research design YAML",
    )
    parser.add_argument(
        "--canary",
        action="store_true",
        help="Run split_001, 20 test dates and three representative P01 executions",
    )
    parser.add_argument(
        "--skip-execution",
        action="store_true",
        help="Build predictive diagnostics without Qlib P01 execution",
    )
    parser.add_argument(
        "--reuse-execution",
        action="store_true",
        help="Rebuild predictive diagnostics/report while retaining the validated prior P01 summary",
    )
    args = parser.parse_args()
    if args.skip_execution and args.reuse_execution:
        parser.error("--skip-execution and --reuse-execution are mutually exclusive")
    result = run_research(
        args.config,
        canary=args.canary,
        run_execution=not args.skip_execution and not args.reuse_execution,
        reuse_execution=args.reuse_execution,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
