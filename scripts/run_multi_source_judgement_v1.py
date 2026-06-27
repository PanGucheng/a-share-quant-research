from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.multi_source_judgement import (  # noqa: E402
    MultiSourceJudgementConfig,
    MultiSourceJudgementRules,
    run_multi_source_judgement,
)


DEFAULT_CONFIG = Path("configs/multi_source_judgement_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> MultiSourceJudgementConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    rules = MultiSourceJudgementRules(**(payload.get("rules", {}) or {}))
    return MultiSourceJudgementConfig(
        screening_input=resolve_path(payload["screening_input"]),
        output_dir=resolve_path(payload["output_dir"]),
        pool_name=str(payload.get("pool_name", "multi_source_judgement_v1")),
        rules=rules,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a generic multi-source research judgement board.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(build_parser().parse_args().config)
    outputs = run_multi_source_judgement(config)
    print(f"Multi-source judgement outputs written to {config.output_dir}", flush=True)
    print(f"Judgement board rows: {len(outputs['board'])}", flush=True)
    print(f"Research candidates: {len(outputs['research_candidates'])}", flush=True)
    print(f"New-source alpha probes: {len(outputs['new_source_alpha_probes'])}", flush=True)


if __name__ == "__main__":
    main()
