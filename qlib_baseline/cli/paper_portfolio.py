from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_research.paper_portfolio import (
    create_paper_decision,
    load_paper_config,
    refresh_paper_execution,
)
from qlib_baseline.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Strategy V1 paper portfolio")
    parser.add_argument("--project-config", type=Path)
    parser.add_argument("--date")
    parser.add_argument("--calendar-file")
    parser.add_argument("--refresh-only", action="store_true")
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(args.project_config)
    config_path = args.config or (
        settings.project_root / "configs/strategy_v1_paper_portfolio_v1.yaml"
    )
    config = load_paper_config(config_path)
    if args.refresh_only:
        decision = None
    else:
        if not args.date or not args.calendar_file:
            parser.error("--date and --calendar-file are required unless --refresh-only is used")
        decision = create_paper_decision(
            config,
            decision_date=args.date,
            calendar_path=args.calendar_file,
            repository_root=settings.project_root,
        )
    execution = refresh_paper_execution(config)
    print(json.dumps({"decision": decision, "execution": execution}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
