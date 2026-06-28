from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.new_source_probe_diagnostics import (  # noqa: E402
    NewSourceProbeDiagnosticsConfig,
    ProbeDiagnosticsRules,
    ProbePortfolioConfig,
    ProbeSelectionConfig,
    run_new_source_probe_diagnostics,
)


DEFAULT_CONFIG = Path("configs/new_source_probe_diagnostics_v1.yaml")


def resolve_path(path: str | Path | None) -> Path | None:
    if path in {None, ""}:
        return None
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_config(path: Path) -> NewSourceProbeDiagnosticsConfig:
    payload = load_yaml(resolve_path(path) or path)
    selection = payload.get("selection", {})
    rules = payload.get("rules", {})
    portfolio = payload.get("portfolio", {})
    return NewSourceProbeDiagnosticsConfig(
        probe_input=resolve_path(payload["probe_input"]) or Path(payload["probe_input"]),
        judgement_board=resolve_path(payload["judgement_board"]) or Path(payload["judgement_board"]),
        factor_frames={str(key): resolve_path(value) or Path(value) for key, value in payload.get("factor_frames", {}).items()},
        tradability_dir=resolve_path(payload["tradability_dir"]) or Path(payload["tradability_dir"]),
        output_dir=resolve_path(payload.get("output_dir", "outputs/new_source_probe_diagnostics_v1/current"))
        or Path("outputs/new_source_probe_diagnostics_v1/current"),
        selection=ProbeSelectionConfig(
            max_frame_factors=int(selection.get("max_frame_factors", 120)),
            max_portfolio_factors=int(selection.get("max_portfolio_factors", 50)),
            per_source_caps={str(key): int(value) for key, value in selection.get("per_source_caps", {}).items()},
        ),
        rules=ProbeDiagnosticsRules(
            min_total_probes=int(rules.get("min_total_probes", 300)),
            min_frame_factors=int(rules.get("min_frame_factors", 80)),
            min_portfolio_factors=int(rules.get("min_portfolio_factors", 30)),
            high_abs_corr=float(rules.get("high_abs_corr", 0.85)),
            high_abs_tradability_exposure=float(rules.get("high_abs_tradability_exposure", 0.30)),
            min_horizon_consistency=float(rules.get("min_horizon_consistency", 0.67)),
        ),
        portfolio=ProbePortfolioConfig(
            provider_uri=str(portfolio["provider_uri"]),
            market=str(portfolio["market"]),
            start_time=str(portfolio["start_time"]),
            end_time=str(portfolio["end_time"]),
            label=str(portfolio["label"]),
            feature_cache_dir=resolve_path(portfolio.get("feature_cache_dir")),
            rebalance_every=int(portfolio.get("rebalance_every", 20)),
            topk=int(portfolio.get("topk", 100)),
            cost_bps=float(portfolio.get("cost_bps", 10.0)),
            score_clip=float(portfolio.get("score_clip", 3.0)),
            min_score_components=int(portfolio.get("min_score_components", 10)),
            min_liquidity_bucket=int(portfolio.get("min_liquidity_bucket", 3)),
            min_tradability_score=float(portfolio.get("min_tradability_score", 75.0)),
            min_capacity_multiple=float(portfolio.get("min_capacity_multiple", 2.0)),
        ),
        correlation_max_dates=int(payload.get("correlation_max_dates", 60)),
        exposure_max_dates=int(payload.get("exposure_max_dates", 60)),
        min_instruments=int(payload.get("min_instruments", 100)),
        top_pairs=int(payload.get("top_pairs", 200)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run new-source alpha probe diagnostics V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = build_config(build_parser().parse_args().config)
    outputs = run_new_source_probe_diagnostics(config)
    contract = outputs["contract"]
    blocked = contract[contract["status"].eq("blocked")]
    print(f"New-source probe diagnostics written to {config.output_dir}", flush=True)
    print(f"Probes: {len(outputs['probes'])}", flush=True)
    print(f"Frame diagnostics selected: {len(outputs['frame_selected'])}", flush=True)
    print(f"Portfolio smoke selected: {len(outputs['portfolio_selected'])}", flush=True)
    if not blocked.empty:
        raise SystemExit(f"New-source probe diagnostics contract blocked: {blocked.to_dict(orient='records')}")


if __name__ == "__main__":
    main()
