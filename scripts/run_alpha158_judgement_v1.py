from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha158_judgement import (  # noqa: E402
    Alpha158JudgementConfig,
    JudgementRules,
    run_alpha158_judgement,
)


DEFAULT_CONFIG = Path("configs/factor_judgement_alpha158_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> Alpha158JudgementConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    rules_payload = payload.get("rules", {}) or {}
    rules = JudgementRules(**rules_payload)
    return Alpha158JudgementConfig(
        screening_input=resolve_path(payload["screening_input"]),
        context_group_ic=resolve_path(payload["context_group_ic"]),
        correlation_summary=resolve_path(payload["correlation_summary"]),
        correlation_pairs=resolve_path(payload["correlation_pairs"]),
        output_dir=resolve_path(payload["output_dir"]),
        rules=rules,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Alpha158 judgement labels and redundancy clusters.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(build_parser().parse_args().config)
    outputs = run_alpha158_judgement(config)
    board = outputs["board"]
    clusters = outputs["clusters"]
    print(f"Alpha158 judgement outputs written to {config.output_dir}", flush=True)
    print(f"Judgement board rows: {len(board)}", flush=True)
    print(f"Redundancy clusters: {len(clusters)}", flush=True)


if __name__ == "__main__":
    main()
