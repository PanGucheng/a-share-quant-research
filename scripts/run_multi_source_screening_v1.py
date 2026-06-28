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

from factor_research.multi_source_screening import (  # noqa: E402
    MultiSourceScreeningConfig,
    run_multi_source_screening,
)


DEFAULT_CONFIG = Path("configs/multi_source_screening_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_paths(payload: dict[str, Any], key: str) -> tuple[Path, ...]:
    return tuple(resolve_path(item) for item in payload.get(key, []))


def build_config(path: Path) -> MultiSourceScreeningConfig:
    payload = load_yaml(resolve_path(path))
    alpha = payload["alpha158"]
    ta = payload["ta"]
    alpha101 = payload["alpha101"]
    alpha360 = payload["alpha360"]
    contract = payload.get("contract", {})
    return MultiSourceScreeningConfig(
        alpha158_screening_input=resolve_path(alpha["screening_input"]),
        alpha158_candidate_pool=resolve_path(alpha["candidate_pool"]),
        alpha158_catalog=resolve_path(alpha["catalog"]),
        ta_catalog=resolve_path(ta["promoted_catalog"]),
        ta_holdout_catalog=resolve_path(ta["holdout_catalog"]),
        ta_factor_summary=resolve_path(ta["factor_summary"]),
        ta_metric_indexes=list_paths(ta, "metric_indexes"),
        ta_promotion_audits=list_paths(ta, "promotion_audits"),
        ta_evaluator_statuses=list_paths(ta, "evaluator_statuses"),
        alpha101_catalog=resolve_path(alpha101["promoted_catalog"]),
        alpha101_holdout_catalog=resolve_path(alpha101["holdout_catalog"]),
        alpha101_factor_summary=resolve_path(alpha101["factor_summary"]),
        alpha101_metric_indexes=list_paths(alpha101, "metric_indexes"),
        alpha101_promotion_audits=list_paths(alpha101, "promotion_audits"),
        alpha101_evaluator_statuses=list_paths(alpha101, "evaluator_statuses"),
        alpha360_catalog=resolve_path(alpha360["promoted_catalog"]),
        alpha360_holdout_catalog=resolve_path(alpha360["holdout_catalog"]),
        alpha360_factor_summary=resolve_path(alpha360["factor_summary"]),
        alpha360_metric_indexes=list_paths(alpha360, "metric_indexes"),
        alpha360_promotion_audits=list_paths(alpha360, "promotion_audits"),
        alpha360_evaluator_statuses=list_paths(alpha360, "evaluator_statuses"),
        output_dir=resolve_path(payload.get("output_dir", "outputs/multi_source_screening_v1/current")),
        pool_name=str(payload.get("pool_name", "multi_source_v1")),
        min_sources=int(contract.get("min_sources", 2)),
        min_total_rows=int(contract.get("min_total_rows", 200)),
        min_new_source_rows=int(contract.get("min_new_source_rows", 20)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the generic multi-source factor screening contract.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = build_config(build_parser().parse_args().config)
    outputs = run_multi_source_screening(config)
    contract = outputs["contract_status"]
    blocked = contract[contract["status"].eq("blocked")]
    print(f"Multi-source screening outputs written to {config.output_dir}", flush=True)
    print(f"Screening rows: {len(outputs['screening_input'])}", flush=True)
    print(f"Alpha candidates: {len(outputs['alpha_candidates'])}", flush=True)
    if not blocked.empty:
        raise SystemExit(f"Multi-source screening contract blocked: {blocked.to_dict(orient='records')}")


if __name__ == "__main__":
    main()
