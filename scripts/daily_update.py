from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from daily_update.pipeline import DailyUpdateConfig, NotReady, run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Community-first Daily Data Update V1")
    parser.add_argument("--target-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--cache-dir", type=Path, default=Path("E:/qlib_prj/qlib_data/daily_update_v1"))
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs/daily_data_update_v1")
    parser.add_argument(
        "--universe-file", type=Path,
        default=Path("E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/all_stock_shsz_liquid2000.txt"),
    )
    args = parser.parse_args()
    try:
        result = run(DailyUpdateConfig(
            target_date=args.target_date, cache_dir=args.cache_dir,
            output_dir=args.output_dir, universe_file=args.universe_file,
        ))
    except NotReady as error:
        print(json.dumps({"status": "not_ready", "target_date": args.target_date.isoformat(), "reason": str(error)}, ensure_ascii=False))
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
