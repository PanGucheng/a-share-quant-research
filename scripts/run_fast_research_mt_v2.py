from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from model_research.fast_research import (
    load_fast_research_config,
    run_fast_research_pair,
)
from model_research.full_execution import qualified_fast_execution_summary
from model_research.protocol import PROJECT_ROOT
from research_validation.feature_matrix import canonical_hash, file_sha256


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _needs_confirmation(
    deltas: pd.DataFrame, receipt: dict[str, object], profile: dict[str, object]
) -> tuple[bool, str]:
    fallback = profile["single_thread_fallback"]
    if (
        receipt["promotion_status"] == "inconclusive"
        and fallback["confirm_inconclusive"]
    ):
        return True, "mt_result_inconclusive"
    mean_delta = float(deltas["mean_daily_rank_ic_delta"].mean())
    gate = profile["promotion_gate"]
    margin = float(fallback["threshold_margin"])
    distances = {
        "promotion": abs(
            mean_delta - float(gate["promote_minimum_mean_rank_ic_delta"])
        ),
        "rejection": abs(
            mean_delta - float(gate["reject_maximum_mean_rank_ic_delta"])
        ),
        "zero": abs(mean_delta),
    }
    nearest = min(distances, key=distances.get)
    return (
        distances[nearest] <= margin,
        f"mt_delta_within_margin_of_{nearest}",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Fast Research MT with automatic Fast V1 confirmation"
    )
    parser.add_argument("--config", default="configs/fast_research_mt_v2.yaml")
    parser.add_argument("--qualification-summary")
    parser.add_argument("--baseline", default="strict_current_baseline")
    parser.add_argument("--proposal", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--feature-manifest")
    parser.add_argument("--policy-manifest")
    parser.add_argument("--changed-dimension", default="feature_pool_policy")
    parser.add_argument(
        "--cache-root", default="tmp/research_productivity_v1/projection_spool_cache"
    )
    parser.add_argument(
        "--runtime-root", default="outputs/research_productivity_v1/runtime/fast_mt_v2"
    )
    args = parser.parse_args()
    config_path = _resolve(args.config)
    profile = load_fast_research_config(config_path)
    qualification_path = _resolve(
        args.qualification_summary or profile["qualification_summary"]
    )
    qualification = qualified_fast_execution_summary(
        qualification_summary_path=qualification_path,
        num_threads=int(profile["num_threads"]),
    )
    if qualification["summary_sha256"] != profile["qualification_summary_sha256"]:
        raise ValueError("Fast MT profile qualification hash changed")
    output_dir = _resolve(args.output_dir)
    if output_dir.exists():
        raise FileExistsError("Fast MT coordinated output is immutable")
    common = {
        "baseline_id": args.baseline,
        "proposal_id": args.proposal,
        "cache_root": _resolve(args.cache_root),
        "runtime_root": _resolve(args.runtime_root),
        "feature_manifest_path": _resolve(args.feature_manifest) if args.feature_manifest else None,
        "policy_manifest_path": _resolve(args.policy_manifest) if args.policy_manifest else None,
        "changed_dimension": args.changed_dimension,
    }
    mt_output = output_dir / "mt"
    mt_receipt = run_fast_research_pair(
        config_path=config_path,
        output_dir=mt_output,
        **common,
    )
    deltas = pd.read_csv(mt_output / "paired_deltas.csv")
    confirm, reason = _needs_confirmation(deltas, mt_receipt, profile)
    confirmation_receipt = None
    if confirm:
        confirmation_output = output_dir / "confirmation_1t"
        confirmation_receipt = run_fast_research_pair(
            config_path=_resolve(profile["parent_profile_config"]),
            output_dir=confirmation_output,
            **common,
        )
    final_receipt = confirmation_receipt or mt_receipt
    receipt = {
        "schema_version": 1,
        "execution_profile": profile["profile_id"],
        "authoritative_execution": False,
        "promotion_is_scientific_winner": False,
        "mt_thread_count": int(profile["num_threads"]),
        "single_thread_confirmation_run": bool(confirm),
        "single_thread_confirmation_reason": reason if confirm else "not_required",
        "final_resource_gate_source": "confirmation_1t" if confirm else "mt",
        "final_promotion_status": final_receipt["promotion_status"],
        "final_promotion_reason": final_receipt["promotion_reason"],
        "mt_receipt_sha256": mt_receipt["receipt_sha256"],
        "confirmation_receipt_sha256": (
            confirmation_receipt["receipt_sha256"] if confirmation_receipt else None
        ),
        "profile_config_sha256": file_sha256(config_path),
        "qualification_summary_sha256": qualification["summary_sha256"],
    }
    receipt["receipt_sha256"] = canonical_hash(receipt)
    (output_dir / "fast_mt_coordinator_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
