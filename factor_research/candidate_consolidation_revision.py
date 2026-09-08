"""V0.5.1 proposals from sealed feature evidence; no outcome or Core selection."""
from __future__ import annotations

import ast
import json
import re

import numpy as np
import pandas as pd

from factor_research.candidate_consolidation_proposals import semantic_review


POLICY = {
    "version": "v0_5_1",
    "levels": [0.995, 0.95, 0.85, 0.70],
    "priority": ["resolved_semantics_units_horizon", "same_mechanism_horizon_units",
                 "worst_era_coverage_desc", "full_coverage_desc", "infinite_fraction_asc",
                 "medoid_distance_asc", "factor_id_asc"],
    "pair_requirement": "Full_and_A_B_C_D_comparable_median_and_q10_ge_level_sign_consistency_ge_0.95_same_sign",
    "formula_complexity": "removed_unreliable_metadata_proxy",
    "unknown_semantics": "deferred_never_equal_by_unknown_string",
    "price_level": "deferred_pending_provider_scale_provenance",
    "low_coverage": "annotation_no_new_numeric_cut_three_reviewed_recursive_indicators_deferred",
    "exact_alias": "register_sealed_development_equality_keep_all_identities",
    "authority": "proposal_only_user_decision_pending_no_core",
}
LOW_COVERAGE_REVIEW = {"ta_volatility_atr", "ta_trend_adx_pos", "ta_trend_adx_neg"}
UNKNOWN = {"", "nan", "unknown", "unresolved", "unspecified"}


def ta_definitions(source):
    """Read the pinned wrapper's explicit calls plus constructor defaults, without importing it.

    This is a bounded extractor for ta/wrapper.py assignments, not a formula-equivalence engine.
    Method identities deliberately preserve different outputs of the same indicator.
    """
    wrapper = source / "ta/wrapper.py"
    tree = ast.parse(wrapper.read_text(encoding="utf-8"))
    classes = {}
    for path in sorted((source / "ta").glob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.ClassDef):
                continue
            init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
            if init is not None:
                defaults = {}
                for arg, value in zip(init.args.args[-len(init.args.defaults):], init.args.defaults):
                    defaults[arg.arg] = ast.literal_eval(value)
                classes[node.name] = (defaults, path, node)
    result = {}
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef) or not function.name.startswith("add_"):
            continue
        variables = {}
        for node in sorted(ast.walk(function), key=lambda n: getattr(n, "lineno", 0)):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target, call = node.targets[0], node.value
            if isinstance(target, ast.Name) and isinstance(call, ast.Call):
                variables[target.id] = call
                continue
            if not isinstance(target, ast.Subscript) or not isinstance(call, ast.Call):
                continue
            if not isinstance(target.slice, ast.JoinedStr) or not isinstance(call.func, ast.Attribute):
                continue
            suffix = "".join(n.value for n in target.slice.values if isinstance(n, ast.Constant))
            constructor = call.func.value
            if isinstance(constructor, ast.Name):
                constructor = variables.get(constructor.id)
            if not isinstance(constructor, ast.Call) or not isinstance(constructor.func, ast.Name):
                continue
            cls = constructor.func.id
            if cls not in classes:
                continue
            defaults, path, cls_node = classes[cls]
            params = dict(defaults)
            for keyword in constructor.keywords:
                if isinstance(keyword.value, ast.Constant):
                    params[keyword.arg] = keyword.value.value
            params["fillna"] = False  # ta_batch explicitly passes False
            method = call.func.attr
            method_node = next(n for n in cls_node.body if isinstance(n, ast.FunctionDef) and n.name == method)
            horizon_params = {k: v for k, v in params.items() if k != "fillna"}
            horizon = json.dumps(horizon_params, sort_keys=True)
            units = "dimensionless"
            if cls in {"EMAIndicator", "SMAIndicator", "IchimokuIndicator", "KAMAIndicator",
                       "VolumeWeightedAveragePrice", "DPOIndicator", "MACD", "AwesomeOscillatorIndicator"}:
                units = "provider_price"
            if cls in {"BollingerBands", "KeltnerChannel", "DonchianChannel"}:
                units = "provider_price" if method.endswith(("hband", "lband", "mband", "mavg")) else "dimensionless"
            if cls == "AverageTrueRange":
                units = "provider_price"
            if cls == "PSARIndicator":
                units = "binary" if method.endswith("indicator") else "provider_price"
            if method.endswith("indicator") and cls in {"BollingerBands", "KeltnerChannel"}:
                units = "binary"
            if cls in {"AccDistIndexIndicator", "OnBalanceVolumeIndicator"}:
                units = "provider_volume"
            if cls == "ForceIndexIndicator":
                units = "provider_price_times_volume"
            if cls == "EaseOfMovementIndicator":
                units = "provider_price_squared_per_volume_scaled"
            if not horizon_params:
                horizon = "cumulative_source_state" if cls in {"AccDistIndexIndicator", "OnBalanceVolumeIndicator"} else "same_day"
            result["ta_" + suffix] = {
                "definition": f"{cls}({json.dumps(params, sort_keys=True)}).{method}()",
                "mechanism": f"{cls}.{method}", "horizon": horizon, "formula_units": units,
                "source_reference": f"{path.as_posix()}:{method_node.lineno}; {wrapper.as_posix()}:{node.lineno}",
                "review_status": "source_call_and_parameters_reconciled",
                "reason": "Pinned upstream method and ta_batch fillna=False; distinct outputs retain distinct mechanisms.",
            }
    return result


def revised_semantics(inventory, ta):
    result = semantic_review(inventory).drop(columns="formula_token_count")
    result["source_reference"] = "inventory_definition_not_fully_reconciled"
    for index, row in result.iterrows():
        f = row.factor
        if row.source == "ta" and f in ta:
            for key, value in ta[f].items():
                result.at[index, key] = value
            if ta[f]["formula_units"] == "provider_price":
                result.at[index, "proposed_family"] = "PriceLevelOrPriceDifference"
        elif row.source in {"alpha158", "alpha360"}:
            result.at[index, "source_reference"] = "Qlib expression inventory; lag/operator identity retained"
        elif row.source == "project_basic":
            n = re.search(r"\d+", f)
            result.at[index, "horizon"] = "window_" + n.group() if n else "unspecified"
            result.at[index, "mechanism"] = f.removesuffix("_" + n.group()) if n else f
            result.at[index, "formula_units"] = "provider_amount" if f in {"amount_mean_20", "amount_std_20"} else "dimensionless"
            result.at[index, "source_reference"] = "factor_research/factor_library.py::add_basic_factors"
            definitions = {
                "amount_mean_20": "rolling_mean(amount,20,min_periods=20)",
                "amount_std_20": "rolling_std(amount,20,min_periods=20,ddof=1)",
                "amount_cv_20": "rolling_std(amount,20)/rolling_mean(amount,20)",
                "amplitude_20": "rolling_mean((high-low)/close,20)",
                "std_20": "rolling_std(close/lag(close,1)-1,20,ddof=1)",
                "rev_5": "-(close/lag(close,5)-1)",
                "rev_20_exclude_5": "-(lag(close,5)/lag(close,20)-1)",
                "corr_ret_amount_20": "rolling_corr(close/lag(close,1)-1,amount,20)",
                "corr_ret_volume_20": "rolling_corr(close/lag(close,1)-1,volume,20)",
            }
            if f in {"ret_5", "ret_10", "ret_20"}:
                definitions[f] = f"close/lag(close,{n.group()})-1"
            if f in definitions:
                result.at[index, "definition"] = definitions[f]
                result.at[index, "review_status"] = "source_formula_reconciled"
            if f == "rev_20_exclude_5":
                result.at[index, "horizon"] = "lags_5_to_20"
        elif row.source == "mature_public" and row.active:
            # Preserve distinct accounting inputs and estimator identities, even at equal rho.
            result.at[index, "mechanism"] = re.sub(r"_\d+$", "", f)
            result.at[index, "formula_units"] = "dimensionless"
            n = re.search(r"_(\d+)$", f)
            result.at[index, "horizon"] = "window_" + n.group(1) if n else "asof_daily_basic"
            if f.endswith("_ttm"):
                result.at[index, "horizon"] = "vendor_TTM_asof_daily_basic"
            if f.endswith("_pit"):
                result.at[index, "horizon"] = "latest_available_consolidated_statement_period_not_TTM_rebuilt"
                result.at[index, "reason"] = "CNY numerator/market cap; information_available_date <= decision_date. No trailing-four-quarter conversion in compute_fundamental_factors."
            if f == "mature_reversal_1m":
                result.at[index, "horizon"] = "lag_21"
            if f == "mature_log_total_market_cap":
                result.at[index, "formula_units"] = "log_total_mv_vendor_unit"
            if f == "mature_amihud_illiquidity_20":
                result.at[index, "formula_units"] = "inverse_CNY"
            minimums = {
                "mature_turnover_mean_20": 10, "mature_turnover_volatility_20": 10,
                "mature_realized_volatility_60": 30, "mature_downside_volatility_60": 15,
                "mature_return_skewness_60": 30, "mature_max_daily_return_21": 11,
                "mature_parkinson_volatility_20": 10, "mature_amihud_illiquidity_20": 10,
                "mature_intraday_return_20": 10, "mature_vwap_deviation_20": 10,
            }
            if f in minimums:
                result.at[index, "horizon"] += f"_min_observations_{minimums[f]}"
            if f == "mature_downside_volatility_60":
                result.at[index, "definition"] = "std(close.pct_change(fill_method=None).where(return<0),window=60,min_periods=15,ddof=1)"
            if f == "mature_idiosyncratic_volatility_60":
                result.at[index, "horizon"] = "beta_window_60_min40_then_residual_std_window_60_min40"
                result.at[index, "definition"] = "beta_t=cov_60_min40(stock_return,market_return)/var_60_min40(market_return); std_60_min40(stock_return_t-beta_t*market_return_t,ddof=1)"
            result.at[index, "source_reference"] = "factor_universe_v2/mature_factors.py; factor_universe_v2/historical_data.py::statement_event_timeline"
            result.at[index, "review_status"] = "source_formula_reconciled_distinct_input_identity"
    kama = result.factor.eq("ta_momentum_kama")
    result.loc[kama, ["definition", "mechanism", "horizon", "source_reference", "reason"]] = [
        "causal_kama(close,window=10,fast_period=2,slow_period=30)", "canonical_causal_kama",
        "window_10_fast_2_slow_30_state_anchor_2000-01-04",
        "research_validation/overlap_lineage.py::causal_kama; canonical factor_lineage.csv",
        "Canonical override: causal diff, skip missing output while preserving state; not upstream np.roll.",
    ]
    result["semantic_resolved"] = (
        ~result.horizon.astype(str).isin(UNKNOWN)
        & ~result.formula_units.astype(str).isin(UNKNOWN)
        & ~result.mechanism.astype(str).isin(UNKNOWN)
        & ~result.definition.astype(str).str.contains("wrapper smoke", regex=False)
        & result.review_status.isin(["formula_reconciled", "source_call_and_parameters_reconciled",
                                     "source_formula_reconciled", "source_formula_reconciled_distinct_input_identity"])
    )
    result["replacement_hold_reason"] = ""
    result.loc[~result.semantic_resolved, "replacement_hold_reason"] = "unresolved_semantics"
    result.loc[result.formula_units.str.startswith("provider_price"), "replacement_hold_reason"] = "provider_price_scale_unverified"
    result.loc[result.factor.str.contains("psar") | result.formula_units.eq("binary"), "replacement_hold_reason"] = "state_or_event_mask_review"
    result.loc[result.factor.isin(LOW_COVERAGE_REVIEW), "replacement_hold_reason"] = "recursive_missingness_quality_review"
    result["representative_eligible"] = result.semantic_resolved & result.replacement_hold_reason.eq("")
    return result.sort_values("factor").reset_index(drop=True)


def propose_revision(membership, semantics, quality, distance, pair_evidence):
    """Require exact semantic strata and a strict stable edge to the proposed leader.

    Failure retains the member; no transitive chaining, unknown-string grouping or
    new outcome/coverage threshold. The caller supplies Full+A/B/C/D pair evidence.
    """
    data = membership.merge(semantics, on="factor", validate="one_to_one").merge(quality, on="factor", validate="one_to_one")
    evidence = pair_evidence.set_index(["factor_a", "factor_b"])
    resolved = data.semantic_resolved & ~data.horizon.isin(UNKNOWN) & ~data.formula_units.isin(UNKNOWN) & ~data.mechanism.isin(UNKNOWN)
    data["eligible"] = data.representative_eligible & resolved
    known = pair_evidence.loc[pair_evidence.all_views_comparable]
    peer_counts = pd.concat([known.factor_a, known.factor_b]).value_counts()
    rows = []
    for cluster, group in data.groupby("cluster_id", sort=True):
        for _, stratum in group.groupby(["mechanism", "horizon", "formula_units"], dropna=False, sort=True):
            eligible = stratum.loc[stratum.eligible].copy()
            leader = None
            if not eligible.empty:
                eligible["medoid_distance"] = distance.loc[eligible.factor, eligible.factor].mean(axis=1).to_numpy()
                eligible = eligible.sort_values(["worst_era_coverage", "full_coverage", "infinite_fraction", "medoid_distance", "factor"], ascending=[False, False, True, True, True])
                leader = eligible.factor.iloc[0]
            for row in stratum.to_dict("records"):
                f = row["factor"]
                peers = int(peer_counts.get(f, 0))
                unknown = len(data) - 1 - peers
                role, rep, reason, sign = "deferred", None, row["replacement_hold_reason"] or "unresolved_semantics", np.nan
                pair = {}
                if row["eligible"] and leader is not None:
                    rep, sign = f, 1.0
                    role = "retain_semantic_or_horizon_variant"
                    reason = "Distinct resolved mechanism/window/units; identity retained"
                    if len(group) == 1:
                        role = "retain_unmerged_with_unknown_pairs" if unknown else "retain_unmerged_all_pairs_comparable"
                        reason = "Singleton is not evidence of independence"
                    if f != leader:
                        key = tuple(sorted([f, leader]))
                        if key not in evidence.index:
                            raise ValueError("missing member-representative evidence")
                        pair = evidence.loc[key].to_dict()
                        if pair["relation"] == "stable_redundancy" and bool(pair["strict_stable"]):
                            role, rep, sign = "conditional_alias_proposal", leader, float(pair["Full_dominant_sign"])
                            reason = "Same resolved mechanism/window/units and strict Full/Era stable pair"
                        else:
                            role, reason = "retain_pair_not_stable", pair["relation"]
                rows.append({"factor": f, "cluster_id": cluster, "proposal_role": role,
                             "proposed_representative": rep, "considered_representative": leader,
                             "representation_sign": sign, "reason": reason,
                             "semantic_resolved": bool(resolved.loc[data.factor.eq(f)].iloc[0]),
                             "all_views_comparable_peers": peers, "unknown_pair_count": unknown,
                             "full_coverage": row["full_coverage"], "worst_era_coverage": row["worst_era_coverage"],
                             "user_decision": "pending", **{"pair_" + k: v for k, v in pair.items()}})
    result = pd.DataFrame(rows)
    used = set(result.loc[result.proposal_role.eq("conditional_alias_proposal"), "proposed_representative"])
    result.loc[result.factor.isin(used), "proposal_role"] = "proposed_representative"
    return result.sort_values("factor").reset_index(drop=True)
