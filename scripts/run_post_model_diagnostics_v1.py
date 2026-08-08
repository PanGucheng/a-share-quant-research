from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.diagnostics import DiagnosticContext, run_model_diagnostics  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Model Diagnostic V1 against frozen Model V1 artifacts.")
    parser.add_argument("--config", type=Path, default=Path("configs/post_model_diagnostics_v1.yaml"))
    parser.add_argument("--smoke", action="store_true", help="Run one split and eight dates into the smoke output directory.")
    args = parser.parse_args()
    path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    result = run_model_diagnostics(DiagnosticContext(PROJECT_ROOT, config, path, smoke=args.smoke))
    print(result["contracts"].to_string(index=False))
    print(f"Published: {result['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
