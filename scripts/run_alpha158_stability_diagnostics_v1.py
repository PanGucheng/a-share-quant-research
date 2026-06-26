from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha158_stability_diagnostics import (  # noqa: E402
    Alpha158StabilityDiagnosticsConfig,
    run_alpha158_stability_diagnostics,
)


DEFAULT_CONFIG = Path("configs/alpha158_stability_diagnostics_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> Alpha158StabilityDiagnosticsConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    return Alpha158StabilityDiagnosticsConfig(
        main_dir=resolve_path(payload["main_dir"]),
        recent_dir=resolve_path(payload["recent_dir"]),
        output_dir=resolve_path(payload["output_dir"]),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Alpha158 stability diagnostics V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    config = load_config(build_parser().parse_args().config)
    outputs = run_alpha158_stability_diagnostics(config)
    single = outputs["single_factor_stability"]
    label_counts = single["stability_label"].value_counts().to_dict()
    print(f"Alpha158 stability diagnostics written to {config.output_dir}", flush=True)
    print(f"Single factor rows: {len(single)}", flush=True)
    print(f"Stability labels: {label_counts}", flush=True)


if __name__ == "__main__":
    main()
