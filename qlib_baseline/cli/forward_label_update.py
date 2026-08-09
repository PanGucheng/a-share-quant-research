from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_research.forward_pipeline import update_mature_forward_labels
from qlib_baseline.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update mature forward labels")
    parser.add_argument("--project-config", type=Path)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--calendar-file", required=True)
    parser.add_argument("--label-dir", required=True)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--output-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(args.project_config)
    freeze = args.freeze or (
        settings.outputs_dir
        / "prospective_forward_hardening_v1/current/forward_candidate_freeze.json"
    )
    output_root = args.output_root or settings.outputs_dir / "forward"
    result = update_mature_forward_labels(
        as_of_date=args.as_of_date,
        label_dir=args.label_dir,
        trading_calendar_path=args.calendar_file,
        freeze_path=freeze,
        repository_root=settings.project_root,
        output_root=output_root,
        state_path=output_root / "status.json",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
