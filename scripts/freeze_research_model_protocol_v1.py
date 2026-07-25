from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.protocol import freeze_protocol, resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze PR #5A compact input and experiment protocol receipts."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/research_model_protocol_v1.yaml"),
    )
    parser.add_argument(
        "--canary-manifest",
        type=Path,
        default=Path(
            "outputs/research_model_protocol_v1/canary/artifact_manifest.json"
        ),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    manifest = freeze_protocol(
        config, canary_manifest_path=resolve(args.canary_manifest)
    )
    print(
        json.dumps(
            {
                "artifact_id": manifest["artifact_id"],
                "artifact_status": manifest["artifact_status"],
                "output_dir": config["output_dir"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["artifact_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
