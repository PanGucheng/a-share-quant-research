from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha158_screening_input import (  # noqa: E402
    Alpha158ScreeningInputConfig,
    run_screening_input,
)


DEFAULT_CONFIG = Path("configs/factor_screening_alpha158_full_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> Alpha158ScreeningInputConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    correlation = payload.get("correlation", {}) or {}
    return Alpha158ScreeningInputConfig(
        first20_output_dir=resolve_path(payload["first20_output_dir"]),
        first20_metric_index=resolve_path(payload["first20_metric_index"]),
        remaining138_batch_root=resolve_path(payload["remaining138_batch_root"]),
        remaining138_metric_index=resolve_path(payload["remaining138_metric_index"]),
        all_catalog=resolve_path(payload["all_catalog"]),
        runnable_catalog=resolve_path(payload["runnable_catalog"]),
        holdout_catalog=resolve_path(payload["holdout_catalog"]),
        promotion_audit=resolve_path(payload["promotion_audit"]),
        expression_summary=resolve_path(payload["expression_summary"]),
        expression_validation_coverage=resolve_path(payload["expression_validation_coverage"]),
        factor_frame=resolve_path(payload["factor_frame"]),
        output_dir=resolve_path(payload["output_dir"]),
        correlation_enabled=bool(correlation.get("enabled", True)),
        correlation_max_dates=correlation.get("max_dates", 120),
        correlation_min_instruments=int(correlation.get("min_instruments", 100)),
        correlation_top_pairs=int(correlation.get("top_pairs", 100)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build full Alpha158 screening input from existing evaluation outputs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(build_parser().parse_args().config)
    outputs = run_screening_input(config)
    board = outputs["board"]
    print(f"Alpha158 screening input written to {config.output_dir}", flush=True)
    print(f"Factor board rows: {len(board)}", flush=True)


if __name__ == "__main__":
    main()
