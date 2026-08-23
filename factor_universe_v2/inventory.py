from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from factor_research.catalog import FactorCatalogEntry, load_factor_catalog
from factor_universe_v2.local_recovery import LOCAL_RECOVERED_FACTOR_METADATA


AUDIT_COLUMNS = [
    "factor_name",
    "factor_family",
    "original_source",
    "original_formula_or_definition",
    "historical_status",
    "implementation_quality",
    "historical_missing_dependency",
    "historical_reason",
    "current_dependency_available",
    "recoverable_now",
    "recommended_action",
    "notes",
]


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _catalog_map(root: Path, path: str) -> dict[str, FactorCatalogEntry]:
    return {entry.name: entry for entry in load_factor_catalog(_resolve(root, path))}


def _formula(entry: FactorCatalogEntry | None) -> str:
    if entry is None:
        return "source_formula_not_present_in_local_reference"
    marker = "expression:"
    if marker in entry.notes.lower():
        position = entry.notes.lower().index(marker) + len(marker)
        return entry.notes[position:].strip()
    return entry.notes or f"upstream {entry.source_function} definition"


def build_historical_missing_audit(root: Path, config: dict[str, Any]) -> pd.DataFrame:
    v1 = pd.read_csv(_resolve(root, config["v1_inventory"]))
    v1_names = set(v1["name"].astype(str))
    alpha158 = _catalog_map(root, config["alpha158_all"])
    alpha360 = _catalog_map(root, config["alpha360_all"])
    alpha101 = _catalog_map(root, config["alpha101_all"])
    ta_eligible = _catalog_map(root, config["ta_all_eligible"])
    rows: list[dict[str, Any]] = []

    def append(
        name: str,
        family: str,
        entry: FactorCatalogEntry | None,
        status: str,
        quality: str,
        dependency: str,
        reason: str,
        available: bool,
        recoverable: bool,
        action: str,
        notes: str = "",
    ) -> None:
        rows.append(
            dict(
                zip(
                    AUDIT_COLUMNS,
                    [
                        name,
                        family,
                        entry.source_project if entry else family,
                        _formula(entry),
                        status,
                        quality,
                        dependency,
                        reason,
                        available,
                        recoverable,
                        action,
                        notes,
                    ],
                )
            )
        )

    for name, entry in alpha158.items():
        if name not in v1_names:
            append(
                name,
                "Alpha158",
                entry,
                "evaluation_holdout",
                "exact",
                "none_current",
                "old_alphalens_quantile_turnover_partial_pass",
                True,
                True,
                "recover_into_v2_without_alpha_performance_gate",
            )
    for name in ("alpha360_CLOSE0", "alpha360_VOLUME0"):
        append(
            name,
            "Alpha360",
            alpha360.get(name),
            "adapter_holdout",
            "exact_but_non_informative",
            "none",
            "normalization_identity_is_constant_or_near_constant",
            True,
            False,
            "reject_formula_equivalent_constant",
        )
    alpha101_inventory = pd.read_csv(_resolve(root, config["alpha101_inventory"])).set_index("factor")
    alpha101_promotion = pd.read_csv(_resolve(root, config["alpha101_promotion_audit"]))
    promotion_reason = dict(zip(alpha101_promotion["factor"], alpha101_promotion["reason"]))
    for name, entry in alpha101.items():
        if name in v1_names:
            continue
        item = alpha101_inventory.loc[name]
        eligible = bool(item["eligible"])
        append(
            name,
            "Alpha101",
            entry,
            "evaluation_holdout" if eligible else "adapter_holdout",
            "proxy_based" if entry.registry_name in config["alpha101_vwap_registry_names"] else "exact",
            "none_current" if eligible else "valid_formula_output",
            promotion_reason.get(name, str(item["exclusion_reason"])),
            eligible,
            eligible,
            "recover_into_v2_without_alpha_performance_gate" if eligible else "research_pending_formula_debug",
        )
    for number in config["alpha101_missing_formula_numbers"]:
        append(
            f"worldquant_alpha101_alpha{int(number):03d}",
            "Alpha101",
            None,
            "source_implementation_missing",
            "not_implemented",
            "audited_local_formula_source",
            "KunQuant_all_alpha_does_not_contain_formula",
            False,
            False,
            "defer_to_network_mature_factor_expansion",
        )
    ta_inventory = pd.read_csv(_resolve(root, config["ta_inventory"]))
    ta_promotion = pd.read_csv(_resolve(root, config["ta_promotion_audit"]))
    ta_promotion_reason = dict(zip(ta_promotion["factor"], ta_promotion["reason"]))
    for name, entry in ta_eligible.items():
        if name not in v1_names:
            append(
                name,
                "TA",
                entry,
                "evaluation_holdout",
                "exact",
                "none_current",
                ta_promotion_reason.get(name, "not_in_v1"),
                True,
                True,
                "recover_into_v2_without_alpha_performance_gate",
            )
    for item in ta_inventory.loc[~ta_inventory["eligible"].astype(bool)].itertuples(index=False):
        name = str(item.factor)
        reason = str(item.exclusion_reason)
        recoverable = name in {"ta_volume_vpt", "ta_volume_nvi"}
        quality = "degraded" if recoverable else "lookahead" if "forward_shift" in reason else "duplicate"
        append(
            name,
            "TA",
            None,
            "disabled",
            quality,
            "explicit_pct_change_semantics" if recoverable else "none",
            reason,
            recoverable,
            recoverable,
            "add_canonical_v2_version" if recoverable else "reject",
            "V1 remains immutable",
        )
    for registry_name in config["alpha101_vwap_registry_names"]:
        base = f"kunquant_alpha101_{registry_name}"
        if base not in alpha101 or not bool(alpha101_inventory.loc[base, "eligible"]):
            continue
        append(
            base,
            "Alpha101",
            alpha101[base],
            "active_v1_degraded" if base in v1_names else "recoverable_degraded_holdout",
            "proxy_based",
            "direct_provider_vwap",
            "reference_class_derived_vwap_as_amount_div_volume_plus_epsilon",
            True,
            True,
            "retain_proxy_and_add_canonical_vwap_v2",
            "Separate annotation row for degraded implementation; may duplicate a holdout row.",
        )
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS).sort_values(
        ["factor_family", "factor_name", "historical_status"]
    ).reset_index(drop=True)


def _economic_taxonomy(category: str, source: str) -> tuple[str, str]:
    value = category.lower()
    if "volume" in value or "liquid" in value:
        return "Liquidity", "VolumeAmount"
    if "volatility" in value or value in {"risk", "alpha158_rolling_price"}:
        return "VolatilityRisk", "RollingRiskOrPriceState"
    if "momentum" in value or "trend" in value:
        return "MomentumTrend", "TechnicalTrend"
    if "reversal" in value:
        return "Reversal", "ReturnReversal"
    if "price_volume" in value or "kbar" in value:
        return "TradingBehavior", "PriceVolumeOrKbar"
    if source == "alpha101":
        return "Multi", "CrossSectionalTechnicalFormula"
    if source == "alpha360":
        return "PriceTrend", "NormalizedLag"
    return "PriceTrend", "TechnicalTransformation"


def _entry_row(entry: FactorCatalogEntry, source: str) -> dict[str, Any]:
    row = asdict(entry)
    row["source"] = source
    row["required_fields"] = ",".join(entry.required_fields)
    row["labels"] = ",".join(entry.labels)
    return row


def build_local_candidate_catalog(root: Path, config: dict[str, Any]) -> pd.DataFrame:
    v1 = pd.read_csv(_resolve(root, config["v1_inventory"]))
    v1["lineage_status"] = "legacy_v1"
    v1["parent_v1_factor"] = v1["name"]
    v1["canonical_replacement_for"] = ""
    v1["evidence_tier"] = "A_or_B_legacy"
    additions: list[dict[str, Any]] = []
    sources = {
        "alpha158": _catalog_map(root, config["alpha158_all"]),
        "alpha101": _catalog_map(root, config["alpha101_all"]),
        "ta": _catalog_map(root, config["ta_all_eligible"]),
    }
    v1_names = set(v1["name"].astype(str))
    alpha101_inventory = pd.read_csv(_resolve(root, config["alpha101_inventory"])).set_index("factor")
    for source, entries in sources.items():
        for name, entry in entries.items():
            if name in v1_names:
                continue
            recover = False
            if source == "alpha158":
                recover = True
            elif source == "alpha101":
                recover = bool(alpha101_inventory.loc[name, "eligible"])
            elif source == "ta":
                recover = True
            if not recover:
                continue
            row = _entry_row(entry, source)
            row.update(
                lineage_status="recovered",
                parent_v1_factor="",
                canonical_replacement_for="",
                evidence_tier="A" if source in {"alpha158", "alpha101"} else "B",
            )
            additions.append(row)
    for name, metadata in LOCAL_RECOVERED_FACTOR_METADATA.items():
        additions.append(
            {
                "source": "ta",
                "batch_id": "ta_local_recovery_v2",
                "name": name,
                "registry_name": name,
                "category": "ta_volume",
                "source_project": "ta",
                "source_file": "ta/volume.py",
                "source_function": metadata["canonical_replacement_for"],
                "source_commit": "a890410710a6e483c9ba08da7f3dd5089e4b9dff",
                "license": "MIT",
                "expected_direction": "watch",
                "required_fields": ",".join(metadata["required_fields"]),
                "labels": "label_10d_t1,label_20d_t1",
                "stage": "factor_universe_v2_pre_network",
                "enabled": True,
                "runnable": True,
                "compute_adapter": "factor_universe_v2.local_recovery.add_local_recovered_factors",
                "notes": "Canonical repair with explicit pct_change(fill_method=None).",
                "lineage_status": "recovered",
                "parent_v1_factor": "",
                "canonical_replacement_for": metadata["canonical_replacement_for"],
                "evidence_tier": metadata["evidence_tier"],
            }
        )
    eligible_alpha101 = set(alpha101_inventory.loc[alpha101_inventory["eligible"].astype(bool)].index)
    alpha101_entries = sources["alpha101"]
    for registry_name in config["alpha101_vwap_registry_names"]:
        base = f"kunquant_alpha101_{registry_name}"
        if base not in eligible_alpha101:
            continue
        entry = alpha101_entries[base]
        row = _entry_row(entry, "alpha101")
        row.update(
            name=f"{base}_canonical_vwap_v2",
            required_fields=",".join(sorted(set(entry.required_fields) | {"$vwap"})),
            stage="factor_universe_v2_pre_network",
            enabled=True,
            runnable=True,
            compute_adapter="factor_universe_v2.alpha101_canonical.compute_canonical_alpha101_features",
            notes="Canonical replacement uses the provider's direct $vwap field; V1 proxy remains immutable.",
            lineage_status="canonicalized",
            parent_v1_factor=base if base in v1_names else "",
            canonical_replacement_for=base,
            evidence_tier="A",
        )
        additions.append(row)
    combined = pd.concat([v1, pd.DataFrame(additions)], ignore_index=True, sort=False)
    if combined["name"].duplicated().any():
        raise ValueError(f"duplicate local V2 candidates: {combined.loc[combined['name'].duplicated(), 'name'].tolist()}")
    taxonomy = combined.apply(
        lambda row: _economic_taxonomy(str(row["category"]), str(row["source"])), axis=1
    )
    combined[["economic_family", "economic_subfamily"]] = pd.DataFrame(
        taxonomy.tolist(), index=combined.index
    )
    canonical = combined["lineage_status"].eq("canonicalized")
    combined.loc[canonical, "economic_family"] = "TradingBehavior"
    combined.loc[canonical, "economic_subfamily"] = "CanonicalVWAPFormula"
    combined["candidate_status"] = "pre_network_data_correctness_candidate"
    return combined.sort_values(["source", "lineage_status", "name"]).reset_index(drop=True)


def build_data_capability_matrix(config: dict[str, Any], probes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for item in config["community_capabilities"]:
        rows.append(
            {
                **item,
                "history_end": "current_local_snapshot",
                "announcement_timestamp_available": False,
                "revision_semantics": "provider_release_snapshot",
                "permission_required": "none_local",
                "current_account_accessible": True,
                "rate_limit": "local_io",
                "storage_estimate": "existing_provider_no_incremental_v2_cost",
                "probe_status": "verified_local_inventory",
                "official_source": "docs/_archive/02_data_layer_history/PROVIDER_DATA_CAPABILITY_V3_6.md",
            }
        )
    probe_map = probes.set_index("api").to_dict("index") if not probes.empty else {}
    for item in config["tushare_capabilities"]:
        probe = probe_map.get(item["api"], {})
        rows.append(
            {
                "field_or_dataset": item["api"],
                "provider": "tushare",
                **item,
                "history_end": "current",
                "announcement_timestamp_available": item["api"]
                in {"income", "balancesheet", "cashflow", "fina_indicator", "forecast", "express", "dividend"},
                "revision_semantics": "preserve_all_source_revisions_order_by_availability",
                "adjustment_semantics": "dataset_specific_no_silent_adjustment",
                "coverage": "probe_only_not_full_history_coverage_proof",
                "permission_required": "official_documentation_2000_points_minimum_for_core_set",
                "current_account_accessible": str(probe.get("probe_status", "not_probed")).startswith("accessible"),
                "rate_limit": "2000_point_base_limits_bulk_bootstrap_requires_throttled_observation",
                "storage_estimate": "see_resource_estimate.csv",
                "reliability": "usable_with_receipts_and_incremental_cache",
                "probe_status": probe.get("probe_status", "not_probed"),
                "official_source": f"https://tushare.pro/document/2?doc_id={item['doc_id']}",
            }
        )
    return pd.DataFrame(rows)


def build_duplicate_audit(catalog: pd.DataFrame) -> pd.DataFrame:
    rows = []
    canonical = catalog.loc[catalog["canonical_replacement_for"].fillna("").ne("")]
    for item in canonical.itertuples(index=False):
        rows.append(
            {
                "factor_a": item.canonical_replacement_for,
                "factor_b": item.name,
                "relationship": "proxy_to_canonical_replacement",
                "hard_delete": False,
                "recommended_action": "retain_both_annotate_canonical_preference",
            }
        )
    rows.extend(
        [
            {"factor_a": "ret_5", "factor_b": "rev_5", "relationship": "monotonic_inverse", "hard_delete": False, "recommended_action": "annotate_only"},
            {"factor_a": "alpha360_CLOSE0", "factor_b": "constant_1", "relationship": "formula_equivalent_constant", "hard_delete": True, "recommended_action": "excluded_before_candidate_catalog"},
            {"factor_a": "alpha360_VOLUME0", "factor_b": "constant_1", "relationship": "formula_equivalent_constant", "hard_delete": True, "recommended_action": "excluded_before_candidate_catalog"},
        ]
    )
    return pd.DataFrame(rows)


def write_limitations(path: Path) -> None:
    payload = {
        "stage_status": "pre_network_checkpoint_not_frozen",
        "limitations": [
            "Tushare probes prove current token access for small slices, not unrestricted full-market bootstrap throughput.",
            "Fundamental and event factors are not admitted until historical bootstrap coverage and PIT canaries pass.",
            "SW membership intervals prove effective dates, not historical database-vintage availability.",
            "External mature-factor and A-share literature expansion was intentionally not started.",
            "No IC, model, portfolio, Strategy V2, or winner research was performed.",
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
