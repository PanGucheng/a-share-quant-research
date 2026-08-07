from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.forward_pipeline import (  # noqa: E402
    finalize_prediction_commit,
    record_forward_failure,
    run_single_day_prediction,
)
from daily_update.forward_adapter import prepare_forward_inputs  # noqa: E402


DEFAULT_FREEZE = (
    PROJECT_ROOT
    / "outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/forward"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one frozen forward prediction")
    parser.add_argument("--date", required=True)
    parser.add_argument("--calendar-file", required=True)
    parser.add_argument("--raw-file")
    parser.add_argument("--feature-file")
    parser.add_argument("--first-seen-at")
    parser.add_argument("--feature-created-at")
    parser.add_argument("--daily-update-dir")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-dev", action="store_true")
    parser.add_argument("--finalize-commit")
    parser.add_argument("--freeze", default=str(DEFAULT_FREEZE))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    state_path = output_root / "status.json"
    if args.finalize_commit:
        result = finalize_prediction_commit(
            decision_date=args.date,
            prediction_commit_sha=args.finalize_commit,
            trading_calendar_path=args.calendar_file,
            freeze_path=args.freeze,
            repository_root=PROJECT_ROOT,
            output_root=output_root,
            state_path=state_path,
        )
    else:
        if args.daily_update_dir:
            if any((args.raw_file, args.feature_file, args.first_seen_at, args.feature_created_at)):
                raise SystemExit(
                    "--daily-update-dir cannot be combined with explicit daily input arguments"
                )
            adapted = prepare_forward_inputs(
                args.daily_update_dir,
                decision_date=args.date,
            )
            args.raw_file = adapted["raw_path"]
            args.feature_file = adapted["feature_path"]
            args.first_seen_at = adapted["raw_snapshot_first_seen_at"]
            args.feature_created_at = adapted["feature_snapshot_created_at"]
        missing = [
            name
            for name, value in (
                ("--raw-file", args.raw_file),
                ("--feature-file", args.feature_file),
                ("--first-seen-at", args.first_seen_at),
            )
            if not value
        ]
        if missing:
            raise SystemExit("missing prediction arguments: " + ", ".join(missing))
        try:
            result = run_single_day_prediction(
                decision_date=args.date,
                raw_path=args.raw_file,
                feature_path=args.feature_file,
                raw_snapshot_first_seen_at=args.first_seen_at,
                feature_snapshot_created_at=args.feature_created_at,
                trading_calendar_path=args.calendar_file,
                freeze_path=args.freeze,
                repository_root=PROJECT_ROOT,
                output_root=output_root,
                state_path=state_path,
                dry_run=bool(args.dry_run),
                force_dev=bool(args.force_dev),
            )
        except Exception as exc:
            record_forward_failure(
                decision_date=args.date,
                error=exc,
                dry_run=bool(args.dry_run),
                freeze_path=args.freeze,
                state_path=state_path,
            )
            raise
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
