from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.new_source_probe_review import (  # noqa: E402
    ProbeReviewConfig,
    ProbeReviewRules,
    run_probe_review,
)


DEFAULT_CONFIG = Path("configs/new_source_probe_review_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_config(path: Path) -> ProbeReviewConfig:
    payload = load_yaml(resolve_path(path))
    rules = payload.get("rules", {})
    return ProbeReviewConfig(
        diagnostic_board=resolve_path(payload["diagnostic_board"]),
        correlation_pairs=resolve_path(payload["correlation_pairs"]),
        tradability_exposure=resolve_path(payload["tradability_exposure"]),
        output_dir=resolve_path(payload.get("output_dir", "outputs/new_source_probe_review_v1/current")),
        rules=ProbeReviewRules(
            high_abs_corr=float(rules.get("high_abs_corr", 0.95)),
            high_abs_tradability_exposure=float(rules.get("high_abs_tradability_exposure", 0.30)),
            min_probe_rows=int(rules.get("min_probe_rows", 328)),
            min_redundancy_pairs=int(rules.get("min_redundancy_pairs", 1)),
            min_oos_candidates=int(rules.get("min_oos_candidates", 10)),
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run new-source probe review V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    config = load_config(build_parser().parse_args().config)
    outputs = run_probe_review(config)
    contract = outputs["contract_status"]
    blocked = contract[contract["status"].eq("blocked")]
    print(f"New-source probe review written to {config.output_dir}", flush=True)
    print(f"Review rows: {len(outputs['review_board'])}", flush=True)
    print(f"Redundancy groups: {len(outputs['redundancy_groups'])}", flush=True)
    print(f"OOS extension candidates: {len(outputs['oos_extension_candidates'])}", flush=True)
    if not blocked.empty:
        raise SystemExit(f"Probe review contract blocked: {blocked.to_dict(orient='records')}")


if __name__ == "__main__":
    main()
