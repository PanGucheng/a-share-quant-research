"""Label-free semantic reconciliation and transparent representative proposals."""

from __future__ import annotations
import json
import re

import numpy as np
import pandas as pd


POLICY = {
    "version": "v0_5_label_free_1",
    "levels": [0.995, 0.95, 0.85, 0.70],
    "priority": [
        "unresolved_conflict_deferred",
        "same_mechanism_and_horizon",
        "worst_era_feature_coverage_desc",
        "full_feature_coverage_desc",
        "infinite_fraction_asc",
        "formula_token_count_asc",
        "feature_medoid_distance_asc",
        "factor_id_asc",
    ],
    "no_outcome_inputs": True,
    "horizon_variants": "retain_separate_strata",
    "exposure": "annotation_only",
    "unknown_semantics": "deferred",
    "authority": "proposal_only_all_levels_parallel_no_final_core",
}


def semantic_review(inventory):
    data = inventory.loc[inventory.research_usable].copy().sort_values("factor")
    rows = []
    for row in data.to_dict("records"):
        factor, definition = row["factor"], str(row["definition"])
        mechanism = str(row["mechanism"])
        family = str(row["primary_family"])
        units, horizon, status = "unresolved", "unspecified", "inherited_definition_requires_review"
        note = "Existing definition retained; numeric clustering does not establish economic equivalence."
        match = re.fullmatch(r"alpha360_(CLOSE|OPEN|HIGH|LOW|VWAP|VOLUME)(\d+)", factor)
        if match:
            field, lag = match.groups()
            denominator = "volume" if field == "VOLUME" else "close"
            mechanism = f"historical_{field.lower()}_to_current_{denominator}_ratio"
            family, units, horizon, status = (
                "PriceTrend" if field != "VOLUME" else "Liquidity",
                "ratio",
                f"lag_{lag}",
                "formula_reconciled",
            )
            note = "Historical/current ratio; lag identity retained; sign is not a return-based direction."
        elif factor.startswith("alpha158_"):
            name = factor.removeprefix("alpha158_")
            parts = re.fullmatch(r"([A-Z]+)(\d+)", name)
            if parts:
                op, window = parts.groups()
                horizon = f"window_{window}"
                mechanism = "normalized_price_slope" if op == "BETA" else f"alpha158_{op.lower()}"
                if op == "BETA":
                    family = "PriceTrend"
                    note = "Slope(close,n)/close is price slope, not market beta."
            else:
                mechanism, horizon = "intraday_" + name.lower(), "same_day"
            units, status = "ratio_or_normalized_statistic", "formula_reconciled"
        elif factor in {"ta_volatility_bbhi", "ta_volatility_kchi"}:
            units, mechanism, status = (
                "binary",
                "channel_breakout_event",
                "state_mask_review_required",
            )
            note = "Binary event; tied values preserved; no arbitrary quantile split."
        elif "psar" in factor:
            units, status = "price_or_state_dependent", "state_mask_review_required"
            note = "PSAR direction/state can cause intentional missingness; do not treat ordinary missingness as equivalent."
        elif "canonical_vwap_v2" in factor or row["source"] == "alpha101":
            status = "implementation_semantics_review_required"
            note = "Keep proxy/direct VWAP implementations distinct; no automatic replacement from correlations."
        else:
            numbers = re.findall(r"(?<![A-Za-z])\d+", factor)
            if numbers:
                horizon = "name_window_" + "_".join(numbers)
            if (
                definition
                and definition != "nan"
                and mechanism not in {"nan", "", "ambiguous", "unknown"}
            ):
                status = "documented_semantics_pending_human_review"
        complexity = len(re.findall(r"[A-Za-z_$][\w$]*|\d+|[^\w\s]", definition))
        rows.append(
            {
                "factor": factor,
                "source": row["source"],
                "active": bool(row["active"]),
                "original_family": row["economic_family"],
                "proposed_family": family,
                "mechanism": mechanism,
                "horizon": horizon,
                "formula_units": units,
                "definition": definition,
                "formula_token_count": complexity,
                "review_status": status,
                "reason": note,
                "representative_eligible": status
                in {"formula_reconciled", "documented_semantics_pending_human_review"},
            }
        )
    return pd.DataFrame(rows)


def propose_groups(membership, semantics, quality, distance):
    """Ranks only within predeclared mechanism/horizon strata; unknowns deferred."""
    data = membership.merge(semantics, on="factor", validate="one_to_one").merge(
        quality, on="factor", validate="one_to_one"
    )
    rows = []
    for cluster, group in data.groupby("cluster_id", sort=True):
        for _, stratum in group.groupby(["mechanism", "horizon"], dropna=False, sort=True):
            eligible = stratum.loc[stratum.representative_eligible].copy()
            representative = None
            if not eligible.empty:
                names = sorted(eligible.factor)
                distances = distance.loc[names, names]
                if not np.isfinite(distances.to_numpy()).all():
                    eligible = eligible.iloc[:0]
                else:
                    eligible["medoid_distance"] = eligible.factor.map(distances.mean(axis=1))
                    eligible = eligible.sort_values(
                        [
                            "worst_era_coverage",
                            "full_coverage",
                            "infinite_fraction",
                            "formula_token_count",
                            "medoid_distance",
                            "factor",
                        ],
                        ascending=[False, False, True, True, True, True],
                        kind="stable",
                    )
                    representative = eligible.factor.iloc[0]
            for row in stratum.to_dict("records"):
                deferred = not row["representative_eligible"] or representative is None
                role = (
                    "deferred"
                    if deferred
                    else (
                        "proposed_representative"
                        if row["factor"] == representative
                        else "conditional_alias_proposal"
                    )
                )
                if not deferred and len(stratum) == 1 and len(group) > 1:
                    role = "retain_horizon_or_semantic_variant"
                rows.append(
                    {
                        "factor": row["factor"],
                        "cluster_id": cluster,
                        "proposal_role": role,
                        "proposed_representative": None if deferred else representative,
                        "mechanism": row["mechanism"],
                        "horizon": row["horizon"],
                        "worst_era_coverage": row["worst_era_coverage"],
                        "full_coverage": row["full_coverage"],
                        "infinite_fraction": row["infinite_fraction"],
                        "formula_token_count": row["formula_token_count"],
                        "reason": "Deferred semantic/mask review"
                        if deferred
                        else "Fixed label-free lexicographic policy within mechanism/horizon",
                        "alternatives": "[]",
                        "related_stratum_members": json.dumps(sorted(set(stratum.factor) - {row["factor"]})),
                        "user_decision": "pending",
                    }
                )
    return pd.DataFrame(rows).sort_values("factor").reset_index(drop=True)
