from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.paper_portfolio import (  # noqa: E402
    create_paper_decision,
    load_paper_config,
    refresh_paper_execution,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Strategy V1 paper portfolio")
    parser.add_argument("--date")
    parser.add_argument("--calendar-file")
    parser.add_argument("--refresh-only", action="store_true")
    parser.add_argument(
        "--config",
        default="configs/strategy_v1_paper_portfolio_v1.yaml",
    )
    args = parser.parse_args()
    config = load_paper_config(args.config)
    if args.refresh_only:
        decision = None
    else:
        if not args.date or not args.calendar_file:
            parser.error("--date and --calendar-file are required unless --refresh-only is used")
        decision = create_paper_decision(
            config,
            decision_date=args.date,
            calendar_path=args.calendar_file,
        )
    execution = refresh_paper_execution(config)
    print(json.dumps({"decision": decision, "execution": execution}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
