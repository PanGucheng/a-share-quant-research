from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.development_dry_run import (  # noqa: E402
    run_development_dry_run,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the PR #5A.1 development-only preprocessing dry-run."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/research_model_protocol_v1_1.yaml"),
    )
    parser.add_argument(
        "--canary-manifest",
        type=Path,
        default=Path(
            "outputs/research_model_protocol_v1_1/canary/artifact_manifest.json"
        ),
    )
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    scope = config["development_dry_run"]
    if args.smoke:
        split_ids = [str(scope["split_ids"][0])]
        train_limit = 20
        validation_limit = 10
        output_dir = resolve(
            "outputs/research_model_protocol_v1_1/development_smoke"
        )
        runtime_dir = resolve(
            "outputs/research_model_protocol_v1_1/runtime/development_smoke"
        )
        full_scope = False
    else:
        split_ids = [str(item) for item in scope["split_ids"]]
        train_limit = None
        validation_limit = None
        output_dir = resolve(scope["output_dir"])
        runtime_dir = resolve(scope["runtime_dir"])
        full_scope = True
    manifest = run_development_dry_run(
        config,
        canary_manifest_path=resolve(args.canary_manifest),
        output_dir=output_dir,
        runtime_dir=runtime_dir,
        split_ids=split_ids,
        train_date_limit=train_limit,
        validation_date_limit=validation_limit,
        full_scope=full_scope,
    )
    print(
        json.dumps(
            {
                "artifact_id": manifest["artifact_id"],
                "artifact_status": manifest["artifact_status"],
                "output_dir": output_dir.as_posix(),
                "full_scope": full_scope,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["artifact_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
