from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from daily_update.pipeline import DailyUpdateConfig, NotReady, run
from qlib_baseline.settings import load_settings


DEFAULT_UNIVERSE_NAME = "all_stock_shsz_liquid2000.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Community-first Daily Data Update V1")
    parser.add_argument("--project-config", type=Path)
    parser.add_argument("--target-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--universe-file", type=Path)
    parser.add_argument("--qlib-source", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(
        args.project_config,
        cli_overrides={
            "daily_update_cache": args.cache_dir,
            "qlib_source": args.qlib_source,
        },
    )
    cache_dir = settings.daily_update_cache
    if cache_dir is None:
        parser.error("daily_update_cache is not configured; run qlib-doctor")
    universe_file = args.universe_file
    if universe_file is None and settings.qlib_provider is None:
        parser.error("qlib_provider is not configured; run qlib-doctor")
    if universe_file is None:
        assert settings.qlib_provider is not None
        universe_file = (
            settings.qlib_provider / "instruments" / DEFAULT_UNIVERSE_NAME
        )
    if settings.qlib_source is None:
        parser.error("qlib_source is not configured; run qlib-doctor")

    config = DailyUpdateConfig(
        target_date=args.target_date,
        cache_dir=cache_dir,
        output_dir=args.output_dir or settings.outputs_dir / "daily_data_update_v1",
        universe_file=universe_file,
        qlib_source=settings.qlib_source,
    )
    try:
        result = run(config)
    except NotReady as error:
        print(
            json.dumps(
                {
                    "status": "not_ready",
                    "target_date": args.target_date.isoformat(),
                    "reason": str(error),
                },
                ensure_ascii=False,
            )
        )
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
