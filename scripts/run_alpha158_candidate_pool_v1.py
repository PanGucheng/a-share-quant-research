from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha158_candidate_pool import (  # noqa: E402
    Alpha158CandidatePoolConfig,
    run_alpha158_candidate_pool,
)


DEFAULT_CONFIG = Path("configs/factor_candidate_pool_alpha158_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> Alpha158CandidatePoolConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    return Alpha158CandidatePoolConfig(
        judgement_board=resolve_path(payload["judgement_board"]),
        redundancy_clusters=resolve_path(payload["redundancy_clusters"]),
        redundancy_cluster_members=resolve_path(payload["redundancy_cluster_members"]),
        output_dir=resolve_path(payload["output_dir"]),
        pool_name=str(payload.get("pool_name", "alpha158_full_v1")),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze Alpha158 judgement output into a candidate pool.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(build_parser().parse_args().config)
    outputs = run_alpha158_candidate_pool(config)
    pool = outputs["pool"]
    print(f"Alpha158 candidate pool outputs written to {config.output_dir}", flush=True)
    print(f"Pool rows: {len(pool)}", flush=True)
    print(f"Alpha candidates: {int(pool['role'].eq('alpha_candidate').sum())}", flush=True)


if __name__ == "__main__":
    main()
