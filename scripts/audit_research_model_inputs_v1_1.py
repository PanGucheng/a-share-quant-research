from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.inputs import load_split_feature_order  # noqa: E402
from model_research.lineage import (  # noqa: E402
    resolve_authoritative_parents,
    resolve_matrix_runtime_authority,
)
from model_research.protocol import parent_paths, resolve  # noqa: E402
from model_research.protocol_v1_1 import build_protocol_binding  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit V1.1 model inputs through authoritative runtime lineage."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/research_model_protocol_v1_1.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    resolution = resolve_authoritative_parents(parent_paths(config))
    factors: list[str] = []
    splits: list[dict[str, object]] = []
    for split_id in config["development_dry_run"]["split_ids"]:
        ordered, receipt = load_split_feature_order(
            resolve(config["selection"]["factor_weights"]),
            resolve(config["selection"]["allowlist_manifest"]),
            outer_split_id=str(split_id),
        )
        current = ordered["factor"].astype(str).tolist()
        factors.extend(current)
        splits.append(
            {
                "outer_split_id": split_id,
                "factor_count": len(current),
                "allowlist_sha256": receipt["allowlist_sha256"],
                "feature_order_sha256": receipt["feature_order_sha256"],
            }
        )
    matrix = resolve_matrix_runtime_authority(
        project_root=PROJECT_ROOT,
        matrix_manifest_path=parent_paths(config).matrix_manifest,
        selected_factors=sorted(set(factors)),
        verify_selected_partition_hashes=False,
    )
    binding = build_protocol_binding(config, resolution)
    print(
        json.dumps(
            {
                "status": "pass",
                "binding_sha256": binding["binding_sha256"],
                "matrix_runtime_dir": matrix.runtime_dir.as_posix(),
                "matrix_partition_status": matrix.partition_status_path.as_posix(),
                "splits": splits,
                "test_payload_reads": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
