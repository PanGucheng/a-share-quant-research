from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.inputs import (  # noqa: E402
    load_split_feature_order,
    partition_factor_index,
    validate_factor_availability,
)
from model_research.protocol import parent_paths, resolve  # noqa: E402
from model_research.lineage import resolve_authoritative_parents  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit PR #5A authoritative model inputs without reading test payloads."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/research_model_protocol_v1.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    resolution = resolve_authoritative_parents(parent_paths(config))
    factor_index = partition_factor_index(
        resolve("outputs/full_research_feature_matrix_v4/current/partition_status.csv")
    )
    summaries = []
    for split_id in ("split_001", "split_002", "split_003"):
        ordered, receipt = load_split_feature_order(
            resolve(config["selection"]["factor_weights"]),
            resolve(config["selection"]["allowlist_manifest"]),
            outer_split_id=split_id,
        )
        factors = ordered["factor"].astype(str).tolist()
        validate_factor_availability(factors, factor_index)
        summaries.append(
            {
                "outer_split_id": split_id,
                "factor_count": len(factors),
                "allowlist_sha256": receipt["allowlist_sha256"],
                "feature_order_sha256": receipt["feature_order_sha256"],
            }
        )
    print(
        json.dumps(
            {
                "status": "pass",
                "date_assignment_sha256": resolution.date_assignment_sha256,
                "direct_parent_stages": [
                    item["stage_id"] for item in resolution.receipts
                ],
                "splits": summaries,
                "test_payload_reads": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
