from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha158_portfolio_smoke import (  # noqa: E402
    Alpha158PortfolioSmokeConfig,
    run_alpha158_portfolio_smoke,
)


DEFAULT_CONFIG = Path("configs/alpha158_candidate_portfolio_smoke_v1.yaml")


def resolve_path(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> Alpha158PortfolioSmokeConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    feature_cache = payload.get("feature_cache_dir")
    return Alpha158PortfolioSmokeConfig(
        candidate_pool=resolve_path(payload["candidate_pool"]),
        expression_frame_dir=resolve_path(payload["expression_frame_dir"]),
        tradability_dir=resolve_path(payload["tradability_dir"]),
        provider_uri=str(payload["provider_uri"]),
        market=str(payload["market"]),
        start_time=str(payload["start_time"]),
        end_time=str(payload["end_time"]),
        label=str(payload.get("label", "label_20d_t1")),
        feature_cache_dir=resolve_path(feature_cache) if feature_cache else None,
        output_dir=resolve_path(payload["output_dir"]),
        score_policy=str(payload.get("score_policy", "equal_directional_zscore")),
        score_clip=float(payload.get("score_clip", 3.0)),
        min_score_components=int(payload.get("min_score_components", 1)),
        rebalance_every=int(payload.get("rebalance_every", 20)),
        topk=int(payload.get("topk", 100)),
        cost_bps=float(payload.get("cost_bps", 10.0)),
        min_liquidity_bucket=int(payload.get("min_liquidity_bucket", 3)),
        min_tradability_score=float(payload.get("min_tradability_score", 75.0)),
        min_capacity_multiple=float(payload.get("min_capacity_multiple", 2.0)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Alpha158 candidate portfolio smoke V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(build_parser().parse_args().config)
    outputs = run_alpha158_portfolio_smoke(config)
    summary = outputs["summary"]
    print(f"Alpha158 candidate portfolio smoke outputs written to {config.output_dir}", flush=True)
    print(f"Trading days: {summary.get('trading_days')}", flush=True)
    print(f"Executed rebalances: {summary.get('executed_rebalances')}", flush=True)
    print(f"Net excess IR: {summary.get('net_excess_ir')}", flush=True)


if __name__ == "__main__":
    main()
