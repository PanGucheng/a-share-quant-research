from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha158_portfolio_diagnostics import (  # noqa: E402
    Alpha158PortfolioDiagnosticsConfig,
    run_alpha158_portfolio_diagnostics,
)
from scripts.run_alpha158_candidate_portfolio_smoke_v1 import load_config as load_base_config  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha158_portfolio_diagnostics_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> Alpha158PortfolioDiagnosticsConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    base = load_base_config(resolve_path(payload["base_config"]))
    return Alpha158PortfolioDiagnosticsConfig(
        base=base,
        output_dir=resolve_path(payload["output_dir"]),
        topk_values=[int(value) for value in payload.get("topk_values", [50, 100, 200])],
        cost_bps_values=[float(value) for value in payload.get("cost_bps_values", [5.0, 10.0, 20.0])],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Alpha158 portfolio diagnostics V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(build_parser().parse_args().config)
    outputs = run_alpha158_portfolio_diagnostics(config)
    single = outputs["single_factor"]
    top_single = single.sort_values("net_excess_ir", ascending=False).iloc[0]
    print(f"Alpha158 portfolio diagnostics written to {config.output_dir}", flush=True)
    print(f"Single factor rows: {len(single)}", flush=True)
    print(f"Best single factor: {top_single['factor']} net_excess_ir={top_single['net_excess_ir']}", flush=True)


if __name__ == "__main__":
    main()
