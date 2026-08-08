from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.external_style_data import run_external_style_data  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build External PIT Style Data V1 with the Tushare SDK.")
    parser.add_argument("--config", type=Path, default=Path("configs/external_pit_style_data_v1.yaml"))
    parser.add_argument("--canary", action="store_true")
    args = parser.parse_args()
    path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    variable = config["source"]["token_environment_variable"]
    if not os.environ.get(variable):
        raise SystemExit(f"Required environment variable {variable} is missing; no request was sent.")
    result = run_external_style_data(PROJECT_ROOT, config, canary=args.canary)
    print(result.to_string(index=False))
    return 0 if result.loc[result["severity"].eq("critical"), "status"].eq("pass").all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
