from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.protocol import resolve  # noqa: E402
from model_research.protocol_v1_1 import run_canary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the PR #5A.1 zero-test-read closure canary."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/research_model_protocol_canary_v1_1.yaml"),
    )
    args = parser.parse_args()
    canary = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    config = yaml.safe_load(
        resolve(canary["base_protocol"]).read_text(encoding="utf-8")
    ) or {}
    manifest = run_canary(config, canary)
    print(
        json.dumps(
            {
                "artifact_id": manifest["artifact_id"],
                "artifact_status": manifest["artifact_status"],
                "output_dir": canary["output_dir"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["artifact_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
