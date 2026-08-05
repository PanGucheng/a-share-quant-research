from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.forward_pipeline import update_mature_forward_labels  # noqa: E402


DEFAULT_FREEZE = (
    PROJECT_ROOT
    / "outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/forward"


def main() -> None:
    parser = argparse.ArgumentParser(description="Update mature forward labels")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--calendar-file", required=True)
    parser.add_argument("--label-dir", required=True)
    parser.add_argument("--freeze", default=str(DEFAULT_FREEZE))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output_root = Path(args.output_root)
    result = update_mature_forward_labels(
        as_of_date=args.as_of_date,
        label_dir=args.label_dir,
        trading_calendar_path=args.calendar_file,
        freeze_path=args.freeze,
        repository_root=PROJECT_ROOT,
        output_root=output_root,
        state_path=output_root / "status.json",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
