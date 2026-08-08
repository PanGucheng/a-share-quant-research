from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.style_attribution import run_style_attribution  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the independent Model Diagnostic style attribution extension.")
    parser.add_argument("--config", type=Path, default=Path("configs/model_diagnostic_style_attribution_v1.yaml"))
    args = parser.parse_args()
    path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    contracts = run_style_attribution(PROJECT_ROOT, config)
    print(contracts.to_string(index=False))
    return 0 if contracts.loc[contracts["severity"].eq("critical"), "status"].eq("pass").all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
