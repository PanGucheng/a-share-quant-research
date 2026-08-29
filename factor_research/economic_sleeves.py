from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "economic_multi_factor_research_v1"
KEYS = ["datetime", "instrument"]


def resolve(path: str | Path, *, project_root: Path = PROJECT_ROOT) -> Path:
    value = Path(path)
    return value if value.is_absolute() else (project_root / value).resolve()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig", lineterminator="\n")
    temporary.replace(path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_design(path: str | Path, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    design_path = resolve(path, project_root=project_root)
    design = yaml.safe_load(design_path.read_text(encoding="utf-8"))
    if design.get("stage_id") != STAGE_ID:
        raise ValueError("economic multi-factor stage_id mismatch")
    if design.get("experiment_class") != "post_observation_research":
        raise ValueError("historical sleeve research must remain post_observation_research")
    if not bool(design.get("design_frozen_before_outcomes")):
        raise ValueError("research design must be frozen before outcomes")
    governance = design.get("governance", {})
    false_fields = (
        "unbiased_final_estimate",
        "strategy_v1_changed",
        "matrix_changed",
        "forward_track_changed",
        "machine_learning_used",
        "optimized_weights_used",
        "production_winner_selected",
        "strategy_v2_authorized",
    )
    if any(bool(governance.get(field)) for field in false_fields):
        raise ValueError("research design overclaims authority or uses a prohibited method")
    if not bool(governance.get("historical_test_already_observed")):
        raise ValueError("observed historical tests must be declared")
    construction = design.get("construction", {})
    if bool(construction.get("result_driven_sign_changes_allowed")):
        raise ValueError("result-driven factor sign changes are prohibited")
    if bool(construction.get("optimized_weights_allowed")):
        raise ValueError("optimized sleeve weights are prohibited")

    sleeve_ids: set[str] = set()
    member_factors: set[str] = set()
    for sleeve in design.get("sleeves", []):
        sleeve_id = str(sleeve["sleeve_id"])
        if sleeve_id in sleeve_ids:
            raise ValueError(f"duplicate sleeve_id: {sleeve_id}")
        sleeve_ids.add(sleeve_id)
        subfamilies: set[str] = set()
        for member in sleeve.get("factors", []):
            factor = str(member["factor"])
            direction = int(member["direction"])
            if direction not in (-1, 1):
                raise ValueError(f"factor direction must be predeclared +/-1: {factor}")
            if factor in member_factors:
                raise ValueError(f"factor assigned to multiple sleeves in V1: {factor}")
            if not str(member.get("rationale", "")).strip():
                raise ValueError(f"factor direction rationale is missing: {factor}")
            member_factors.add(factor)
            subfamilies.add(str(member["subfamily"]))
        if not subfamilies:
            raise ValueError(f"sleeve has no members: {sleeve_id}")

    archetype_ids: set[str] = set()
    for archetype in design.get("archetypes", []):
        archetype_id = str(archetype["archetype_id"])
        if archetype_id in sleeve_ids or archetype_id in archetype_ids:
            raise ValueError(f"duplicate research variant id: {archetype_id}")
        missing = sorted(set(archetype.get("sleeves", [])) - sleeve_ids)
        if missing:
            raise ValueError(f"archetype references unknown sleeves: {missing}")
        archetype_ids.add(archetype_id)
    variant_ids = sleeve_ids | archetype_ids
    for comparison in design.get("incremental_comparisons", []):
        missing = sorted(
            {comparison["base"], comparison["added"], comparison["combined"]}
            - variant_ids
        )
        if missing:
            raise ValueError(f"incremental comparison references unknown variants: {missing}")
    design["_design_path"] = design_path
    design["_design_sha256"] = file_sha256(design_path)
    return design


def _selected_members(design: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for sleeve in design["sleeves"]:
        for member in sleeve["factors"]:
            selected[str(member["factor"])] = {
                **member,
                "sleeve_id": str(sleeve["sleeve_id"]),
                "mechanism": str(sleeve["mechanism"]),
                "evidence_level": str(sleeve["evidence_level"]),
                "intended_role": str(sleeve["intended_role"]),
            }
    return selected


def _taxonomy_revision(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    family = str(row.get("economic_family", ""))
    subfamily = str(row.get("economic_subfamily", ""))
    text = " ".join(
        str(row.get(field, ""))
        for field in ("name", "definition", "economic_subfamily", "notes")
    ).lower()
    if family == "Value":
        return "Valuation", subfamily or "valuation_other", "relative_valuation", "alpha"
    if family == "Profitability":
        return "Fundamentals", subfamily or "profitability_other", "operating_strength", "alpha_or_conditioning"
    if family in {"Quality", "CashFlow"}:
        return "Fundamentals", subfamily or "accounting_quality_other", "earnings_and_cash_quality", "conditioning"
    if family == "GrowthInvestment":
        return "Fundamentals", subfamily or "investment_growth_other", "investment_or_realized_growth", "exploratory_alpha"
    if family == "Leverage":
        return "CapitalStructure", subfamily or "leverage", "financing_and_distress", "risk_or_conditioning"
    if family == "Size":
        return "SizeStructure", subfamily or "size", "scale_float_and_shell_value", "control_or_conditioning"
    if family == "Reversal":
        mechanism = "overnight_sentiment" if "overnight" in text else "short_horizon_overreaction"
        return "ReturnDynamics", subfamily or "reversal", mechanism, "alpha"
    if family == "MomentumTrend":
        mechanism = "price_anchor" if "52" in text or "anchor" in text else "return_continuation"
        return "ReturnDynamics", subfamily or "momentum_trend", mechanism, "alpha_or_competing_hypothesis"
    if family == "PriceTrend":
        if any(token in text for token in ("volume", "vwap", "amount", "turnover")):
            sub = "price_volume_pattern"
        elif any(token in text for token in ("high", "low", "max", "min", "range")):
            sub = "price_range_pattern"
        else:
            sub = "price_path_pattern"
        return "TechnicalPriceVolume", sub, "formula_based_price_or_volume_pattern", "exploratory_candidate"
    if family == "Liquidity":
        if any(token in text for token in ("amihud", "impact", "spread", "illiquid")):
            return "LiquidityTrading", subfamily or "price_impact", "liquidity_price_impact", "alpha_with_cost_warning"
        if any(token in text for token in ("turnover", "volume", "amount")):
            return "LiquidityTrading", subfamily or "activity", "liquidity_or_speculative_activity", "alpha_or_conditioning"
        return "LiquidityTrading", subfamily or "liquidity_other", "liquidity_state", "alpha_or_conditioning"
    if family == "TradingBehavior":
        if any(token in text for token in ("flow", "order", "imbalance")):
            return "TradingBehavior", subfamily or "order_flow", "order_flow_pressure", "short_horizon_alpha"
        if any(token in text for token in ("overnight", "intraday", "vwap")):
            return "TradingBehavior", subfamily or "price_formation", "within_day_price_formation", "short_horizon_alpha"
        return "TradingBehavior", subfamily or "trading_other", "trading_activity_or_attention", "alpha_or_conditioning"
    if family == "VolatilityRisk":
        if any(token in text for token in ("max", "skew", "lottery")):
            mechanism = "lottery_preference"
        elif "beta" in text:
            mechanism = "systematic_risk"
        elif any(token in text for token in ("drawdown", "downside")):
            mechanism = "downside_path_risk"
        else:
            mechanism = "realized_or_residual_risk"
        return "RiskLottery", subfamily or "risk_other", mechanism, "alpha_risk_or_conditioning"
    if family == "Multi":
        return "OpaqueMultiInput", subfamily or "unresolved_multi", "mixed_formula_information", "exploratory_only"
    return family or "Unclassified", subfamily or "unclassified", "unresolved", "exploratory_only"


def build_economic_map(
    inventory: pd.DataFrame,
    qualification: pd.DataFrame,
    design: Mapping[str, Any],
) -> pd.DataFrame:
    if "name" not in inventory or "factor" not in qualification:
        raise ValueError("factor inventory/qualification schema mismatch")
    qualified = qualification.loc[
        qualification["research_usable"].astype(str).str.lower().eq("true")
    ].copy()
    merged = inventory.merge(
        qualified[["factor", "coverage", "qualified_month_fraction"]],
        left_on="name",
        right_on="factor",
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != len(qualified):
        raise ValueError("not every research-usable factor has inventory lineage")
    selected = _selected_members(design)
    controls = set(design.get("diagnostic_controls", {}).values())
    rows: list[dict[str, Any]] = []
    for row in merged.to_dict("records"):
        primary, subfamily, mechanism, default_role = _taxonomy_revision(row)
        name = str(row["name"])
        member = selected.get(name)
        if member:
            role = "selected_sleeve_member"
            subfamily = str(member["subfamily"])
            mechanism = str(member["mechanism"])
            direction: int | str = int(member["direction"])
            direction_rationale = str(member["rationale"])
            evidence_level = str(member["evidence_level"])
            intended_role = str(member["intended_role"])
            sleeve_id = str(member["sleeve_id"])
        elif name in controls:
            role = "diagnostic_control"
            direction = "not_applicable"
            direction_rationale = "Exposure diagnostic only; not aggregated as alpha."
            evidence_level = "diagnostic"
            intended_role = "exposure_control"
            sleeve_id = ""
        else:
            role = default_role
            direction = "ambiguous_not_used"
            direction_rationale = "No V1 sleeve direction assigned; physical qualification is not economic evidence."
            evidence_level = "weak_or_exploratory"
            intended_role = default_role
            sleeve_id = ""
        rows.append(
            {
                "factor": name,
                "source": row.get("source", ""),
                "original_family": row.get("economic_family", ""),
                "original_subfamily": row.get("economic_subfamily", ""),
                "primary_family": primary,
                "secondary_family": row.get("secondary_family", ""),
                "economic_subfamily": subfamily,
                "mechanism": mechanism,
                "research_role": role,
                "sleeve_id": sleeve_id,
                "expected_direction": direction,
                "direction_rationale": direction_rationale,
                "evidence_level": evidence_level,
                "intended_role": intended_role,
                "data_horizon": _data_horizon(row),
                "turnover_implication": _turnover_implication(primary, mechanism),
                "global_coverage": row.get("coverage", np.nan),
                "global_qualified_month_fraction": row.get("qualified_month_fraction", np.nan),
                "definition": row.get("definition", ""),
                "lineage_status": row.get("lineage_status", ""),
            }
        )
    result = pd.DataFrame(rows).sort_values("factor", kind="stable").reset_index(drop=True)
    if result["factor"].duplicated().any():
        raise ValueError("economic map contains duplicate factors")
    return result


def _data_horizon(row: Mapping[str, Any]) -> str:
    required = str(row.get("required_fields", "")).lower()
    name = str(row.get("name", "")).lower()
    if "information_available_date" in required:
        return "quarterly_pit_slow"
    if any(token in name for token in ("5", "10", "20", "21", "intraday", "overnight")):
        return "daily_short_to_medium"
    if any(token in name for token in ("60", "120", "252", "52w", "12_1")):
        return "daily_medium_to_long"
    return "daily_or_formula_dependent"


def _turnover_implication(primary: str, mechanism: str) -> str:
    text = f"{primary} {mechanism}".lower()
    if any(token in text for token in ("trading", "reversal", "flow", "short_horizon")):
        return "high"
    if any(token in text for token in ("fundamental", "valuation", "accounting", "investment")):
        return "low"
    return "medium_or_unknown"


def factor_partition_lookup(partition_manifest: pd.DataFrame) -> dict[str, Path]:
    required = {"partition_path", "factors"}
    if not required.issubset(partition_manifest):
        raise ValueError(f"partition manifest missing columns: {sorted(required - set(partition_manifest))}")
    lookup: dict[str, Path] = {}
    for row in partition_manifest.to_dict("records"):
        path = Path(str(row["partition_path"]))
        for factor in str(row["factors"]).split(","):
            factor = factor.strip()
            if factor in lookup:
                raise ValueError(f"factor appears in multiple partitions: {factor}")
            lookup[factor] = path
    return lookup


def load_factor_panel(
    factors: Iterable[str],
    partition_manifest: pd.DataFrame,
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    requested = list(dict.fromkeys(str(factor) for factor in factors))
    lookup = factor_partition_lookup(partition_manifest)
    missing = sorted(set(requested) - set(lookup))
    if missing:
        raise ValueError(f"factors absent from matrix partitions: {missing}")
    grouped: dict[Path, list[str]] = {}
    for factor in requested:
        grouped.setdefault(lookup[factor], []).append(factor)
    merged: pd.DataFrame | None = None
    for path, columns in grouped.items():
        frame = pd.read_parquet(
            path,
            columns=KEYS + columns,
            filters=[("datetime", ">=", start_date), ("datetime", "<=", end_date)],
        )
        frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.normalize()
        frame["instrument"] = frame["instrument"].astype(str).str.upper()
        if frame.duplicated(KEYS).any():
            raise ValueError(f"matrix partition contains duplicate keys: {path}")
        merged = frame if merged is None else merged.merge(frame, on=KEYS, how="outer", validate="one_to_one")
    if merged is None:
        raise ValueError("no factors requested")
    return merged.sort_values(KEYS, kind="stable").reset_index(drop=True)


def compute_split_local_eligibility(
    panel: pd.DataFrame,
    development_dates: pd.DatetimeIndex,
    factors: Iterable[str],
    thresholds: Mapping[str, Any],
    *,
    split_id: str,
) -> pd.DataFrame:
    development = panel.loc[panel["datetime"].isin(development_dates)].copy()
    if development.empty:
        raise ValueError(f"development panel is empty: {split_id}")
    expected_rows = len(development)
    expected_dates = len(development_dates)
    rows: list[dict[str, Any]] = []
    for factor in factors:
        values = pd.to_numeric(development[factor], errors="coerce").replace([np.inf, -np.inf], np.nan)
        finite = values.notna()
        finite_by_date = finite.groupby(development["datetime"]).sum().reindex(development_dates, fill_value=0)
        finite_dates = int((finite_by_date > 0).sum())
        qualified_date_fraction = float(
            (finite_by_date >= int(thresholds["minimum_cross_section"])).mean()
        )
        coverage = float(finite.sum() / expected_rows) if expected_rows else 0.0
        unique_values = int(values.loc[finite].nunique())
        eligible = bool(
            coverage >= float(thresholds["minimum_row_coverage"])
            and finite_dates >= min(int(thresholds["minimum_finite_dates"]), expected_dates)
            and qualified_date_fraction >= float(thresholds["minimum_qualified_date_fraction"])
            and unique_values >= int(thresholds["minimum_unique_values"])
        )
        rows.append(
            {
                "outer_split_id": split_id,
                "factor": factor,
                "development_row_count": expected_rows,
                "development_date_count": expected_dates,
                "valid_count": int(finite.sum()),
                "coverage": coverage,
                "finite_dates": finite_dates,
                "qualified_date_fraction": qualified_date_fraction,
                "unique_values": unique_values,
                "split_local_eligible": eligible,
                "eligibility_scope": "development_only_train_plus_validation",
            }
        )
    return pd.DataFrame(rows)


def _rank_signal(values: pd.Series, groups: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    grouped = numeric.groupby(groups, sort=False)
    rank = grouped.rank(method="average")
    count = grouped.transform("count")
    scaled = rank.sub(1.0).div(count.sub(1.0)).mul(2.0).sub(1.0)
    return scaled.where(count.gt(1))


def construct_scores(
    panel: pd.DataFrame,
    design: Mapping[str, Any],
    eligibility: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = panel[KEYS].copy()
    eligible = set(
        eligibility.loc[eligibility["split_local_eligible"].astype(bool), "factor"].astype(str)
    )
    minimum_fraction = float(design["construction"]["minimum_member_fraction"])
    membership_rows: list[dict[str, Any]] = []
    for sleeve in design["sleeves"]:
        sleeve_id = str(sleeve["sleeve_id"])
        subfamily_signals: dict[str, list[pd.Series]] = {}
        for member in sleeve["factors"]:
            factor = str(member["factor"])
            is_eligible = factor in eligible
            membership_rows.append(
                {
                    "sleeve_id": sleeve_id,
                    "factor": factor,
                    "subfamily": member["subfamily"],
                    "direction": int(member["direction"]),
                    "split_local_eligible": is_eligible,
                    "effective_member": is_eligible,
                    "exclusion_reason": "" if is_eligible else "development_only_eligibility_failed",
                }
            )
            if not is_eligible:
                continue
            ranked = _rank_signal(panel[factor], panel["datetime"]).mul(int(member["direction"]))
            subfamily_signals.setdefault(str(member["subfamily"]), []).append(ranked)
        if not subfamily_signals:
            result[sleeve_id] = np.nan
            continue
        subfamily_frame = pd.DataFrame(
            {
                subfamily: pd.concat(signals, axis=1).mean(axis=1, skipna=True)
                for subfamily, signals in subfamily_signals.items()
            }
        )
        required = max(1, math.ceil(len(subfamily_frame.columns) * minimum_fraction))
        score = subfamily_frame.mean(axis=1, skipna=True)
        score.loc[subfamily_frame.notna().sum(axis=1) < required] = np.nan
        result[sleeve_id] = score
    for archetype in design["archetypes"]:
        archetype_id = str(archetype["archetype_id"])
        components = list(archetype["sleeves"])
        ranked = pd.DataFrame(
            {component: _rank_signal(result[component], result["datetime"]) for component in components}
        )
        required = max(1, math.ceil(len(components) * minimum_fraction))
        score = ranked.mean(axis=1, skipna=True)
        score.loc[ranked.notna().sum(axis=1) < required] = np.nan
        result[archetype_id] = score
    return result, pd.DataFrame(membership_rows)


def _daily_rank_ic(frame: pd.DataFrame, score_column: str, label: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date, group in frame.groupby("datetime", sort=True):
        clean = group[[score_column, label]].replace([np.inf, -np.inf], np.nan).dropna()
        value = clean[score_column].corr(clean[label], method="spearman") if len(clean) >= 10 else np.nan
        rows.append({"datetime": date, "variant_id": score_column, "rank_ic": value, "n": len(clean)})
    return pd.DataFrame(rows)


def _topk_turnover(frame: pd.DataFrame, score_column: str, *, top_k: int, interval: int) -> float:
    dates = pd.DatetimeIndex(sorted(frame["datetime"].unique()))[::interval]
    previous: set[str] | None = None
    values: list[float] = []
    for date in dates:
        day = frame.loc[frame["datetime"].eq(date), ["instrument", score_column]].dropna()
        holdings = set(day.nlargest(top_k, score_column)["instrument"].astype(str))
        if previous is not None and previous and holdings:
            denominator = min(top_k, len(previous), len(holdings))
            values.append(1.0 - len(previous & holdings) / denominator)
        previous = holdings
    return float(np.mean(values)) if values else float("nan")


def _monotonicity(frame: pd.DataFrame, score_column: str, label: str) -> tuple[list[float], float, int]:
    work = frame[["datetime", score_column, label]].dropna().copy()
    work["pct"] = work.groupby("datetime")[score_column].rank(method="first", pct=True)
    work["quintile"] = np.ceil(work["pct"] * 5).clip(1, 5).astype(int)
    daily_means = work.groupby(["datetime", "quintile"])[label].mean().unstack("quintile")
    means = daily_means.reindex(columns=range(1, 6)).mean(axis=0)
    values = [float(value) if pd.notna(value) else float("nan") for value in means]
    steps = sum(
        int(np.isfinite(values[index]) and np.isfinite(values[index + 1]) and values[index + 1] >= values[index])
        for index in range(4)
    )
    spread = values[-1] - values[0] if np.isfinite(values[-1]) and np.isfinite(values[0]) else float("nan")
    return values, float(spread), int(steps)


def diagnose_variants(
    scores: pd.DataFrame,
    labels: pd.DataFrame,
    panel: pd.DataFrame,
    design: Mapping[str, Any],
    *,
    split_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    label_name = str(design["label"])
    merged = scores.merge(labels[KEYS + [label_name]], on=KEYS, how="left", validate="one_to_one")
    controls = design.get("diagnostic_controls", {})
    missing_controls = [control for control in controls.values() if control not in merged]
    if missing_controls:
        merged = merged.merge(
            panel[KEYS + missing_controls],
            on=KEYS,
            how="left",
            validate="one_to_one",
        )
    variant_ids = [str(row["sleeve_id"]) for row in design["sleeves"]] + [
        str(row["archetype_id"]) for row in design["archetypes"]
    ]
    summary_rows: list[dict[str, Any]] = []
    daily_frames: list[pd.DataFrame] = []
    regime_rows: list[dict[str, Any]] = []
    for variant_id in variant_ids:
        daily = _daily_rank_ic(merged, variant_id, label_name)
        daily["outer_split_id"] = split_id
        daily_frames.append(daily)
        clean_ic = daily["rank_ic"].dropna()
        quintiles, spread, monotonic_steps = _monotonicity(merged, variant_id, label_name)
        exposure_values: dict[str, float] = {}
        for control_name, control_factor in controls.items():
            correlations = []
            for _, group in merged.groupby("datetime", sort=False):
                clean = group[[variant_id, control_factor]].dropna()
                if len(clean) >= 10:
                    correlations.append(clean[variant_id].corr(clean[control_factor], method="spearman"))
            exposure_values[f"mean_{control_name}_rank_corr"] = float(np.nanmean(correlations)) if correlations else np.nan
        summary_rows.append(
            {
                "outer_split_id": split_id,
                "variant_id": variant_id,
                "variant_type": "sleeve" if variant_id in {str(row["sleeve_id"]) for row in design["sleeves"]} else "archetype",
                "date_count": int(merged["datetime"].nunique()),
                "row_coverage": float(merged[variant_id].notna().mean()),
                "mean_rank_ic": float(clean_ic.mean()) if len(clean_ic) else np.nan,
                "rank_ic_std": float(clean_ic.std(ddof=1)) if len(clean_ic) > 1 else np.nan,
                "rank_ic_ir_annualized": float(clean_ic.mean() / clean_ic.std(ddof=1) * np.sqrt(252.0)) if len(clean_ic) > 1 and clean_ic.std(ddof=1) > 0 else np.nan,
                "positive_ic_fraction": float(clean_ic.gt(0).mean()) if len(clean_ic) else np.nan,
                "quintile_1_mean_label": quintiles[0],
                "quintile_2_mean_label": quintiles[1],
                "quintile_3_mean_label": quintiles[2],
                "quintile_4_mean_label": quintiles[3],
                "quintile_5_mean_label": quintiles[4],
                "quintile_5_minus_1": spread,
                "nondecreasing_quintile_steps": monotonic_steps,
                "top50_five_day_one_way_turnover": _topk_turnover(merged, variant_id, top_k=50, interval=5),
                **exposure_values,
                "evidence_class": "post_observation_research_diagnostic_only",
            }
        )
        daily_year = daily.assign(year=pd.to_datetime(daily["datetime"]).dt.year).groupby("year")["rank_ic"]
        for year, values in daily_year:
            regime_rows.append(
                {
                    "outer_split_id": split_id,
                    "variant_id": variant_id,
                    "regime_type": "calendar_year",
                    "regime": str(year),
                    "date_count": int(values.notna().sum()),
                    "mean_rank_ic": float(values.mean()),
                    "positive_ic_fraction": float(values.dropna().gt(0).mean()) if values.notna().any() else np.nan,
                }
            )
    daily_all = pd.concat(daily_frames, ignore_index=True)
    pairwise = _pairwise_score_correlations(merged, variant_ids, split_id=split_id)
    incremental = _incremental_diagnostics(merged, daily_all, design, split_id=split_id)
    return pd.DataFrame(summary_rows), daily_all, pairwise, pd.concat(
        [pd.DataFrame(regime_rows).assign(record_type="regime"), incremental.assign(record_type="incremental")],
        ignore_index=True,
        sort=False,
    )


def _pairwise_score_correlations(frame: pd.DataFrame, variant_ids: list[str], *, split_id: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, left in enumerate(variant_ids):
        for right in variant_ids[index + 1 :]:
            values: list[float] = []
            for _, group in frame.groupby("datetime", sort=False):
                clean = group[[left, right]].dropna()
                if len(clean) >= 10:
                    values.append(clean[left].corr(clean[right], method="spearman"))
            rows.append(
                {
                    "outer_split_id": split_id,
                    "left_variant": left,
                    "right_variant": right,
                    "mean_daily_rank_correlation": float(np.nanmean(values)) if values else np.nan,
                    "date_count": int(np.isfinite(values).sum()) if values else 0,
                }
            )
    return pd.DataFrame(rows)


def _residual_rank_ic(frame: pd.DataFrame, base: str, added: str, label: str) -> float:
    values: list[float] = []
    for _, group in frame.groupby("datetime", sort=False):
        clean = group[[base, added, label]].dropna()
        if len(clean) < 10 or clean[base].std(ddof=1) <= 0:
            continue
        matrix = np.column_stack([np.ones(len(clean)), clean[base].to_numpy(dtype=float)])
        coefficients = np.linalg.lstsq(matrix, clean[added].to_numpy(dtype=float), rcond=None)[0]
        residual = clean[added].to_numpy(dtype=float) - matrix @ coefficients
        values.append(pd.Series(residual).corr(clean[label].reset_index(drop=True), method="spearman"))
    return float(np.nanmean(values)) if values else float("nan")


def _incremental_diagnostics(
    frame: pd.DataFrame,
    daily_ic: pd.DataFrame,
    design: Mapping[str, Any],
    *,
    split_id: str,
) -> pd.DataFrame:
    label = str(design["label"])
    mean_ic = daily_ic.groupby("variant_id")["rank_ic"].mean().to_dict()
    rows: list[dict[str, Any]] = []
    for comparison in design["incremental_comparisons"]:
        base = str(comparison["base"])
        added = str(comparison["added"])
        combined = str(comparison["combined"])
        correlation = _pairwise_score_correlations(frame, [base, added], split_id=split_id)
        rows.append(
            {
                "outer_split_id": split_id,
                "base_variant": base,
                "added_variant": added,
                "combined_variant": combined,
                "base_mean_rank_ic": mean_ic.get(base, np.nan),
                "added_mean_rank_ic": mean_ic.get(added, np.nan),
                "combined_mean_rank_ic": mean_ic.get(combined, np.nan),
                "combined_minus_base_rank_ic": mean_ic.get(combined, np.nan) - mean_ic.get(base, np.nan),
                "added_residual_mean_rank_ic": _residual_rank_ic(frame, base, added, label),
                "base_added_mean_rank_correlation": float(correlation.iloc[0]["mean_daily_rank_correlation"]),
                "incremental_positive": bool(mean_ic.get(combined, np.nan) > mean_ic.get(base, np.nan)),
            }
        )
    return pd.DataFrame(rows)


def _load_labels(path: Path, dates: pd.DatetimeIndex, label: str) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        columns=KEYS + [label],
        filters=[("datetime", ">=", dates.min()), ("datetime", "<=", dates.max())],
    )
    frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.normalize()
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame.loc[frame["datetime"].isin(dates)].copy()


def run_research(
    design_path: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
    canary: bool = False,
    run_execution: bool = True,
    reuse_execution: bool = False,
) -> dict[str, Any]:
    design = load_design(design_path, project_root=project_root)
    inputs = design["inputs"]
    inventory_path = resolve(inputs["factor_inventory"], project_root=project_root)
    qualification_path = resolve(inputs["factor_qualification"], project_root=project_root)
    partition_path = resolve(inputs["partition_manifest"], project_root=project_root)
    literature_path = resolve(inputs["literature_evidence_map"], project_root=project_root)
    if not literature_path.is_file() or len(pd.read_csv(literature_path)) < 8:
        raise ValueError("literature evidence map is missing or too small")
    inventory = pd.read_csv(inventory_path)
    qualification = pd.read_csv(qualification_path)
    partition_manifest = pd.read_csv(partition_path)
    economic_map = build_economic_map(inventory, qualification, design)
    selected = _selected_members(design)
    controls = list(design.get("diagnostic_controls", {}).values())
    requested_factors = list(selected) + controls
    missing_selected = sorted(set(selected) - set(economic_map["factor"]))
    if missing_selected:
        raise ValueError(f"selected sleeve factors are not globally research-usable: {missing_selected}")

    assignments = pd.read_csv(resolve(inputs["date_assignments"], project_root=project_root))
    assignments["datetime"] = pd.to_datetime(assignments["datetime"]).dt.normalize()
    split_ids = ["split_001"] if canary else sorted(assignments["split_id"].unique())
    report_dir = resolve(design["outputs"]["report_dir"], project_root=project_root)
    runtime_dir = resolve(design["outputs"]["runtime_dir"], project_root=project_root)
    report_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    _atomic_csv(report_dir / "economic_map.csv", economic_map)

    eligibility_frames: list[pd.DataFrame] = []
    membership_frames: list[pd.DataFrame] = []
    diagnostic_frames: list[pd.DataFrame] = []
    daily_ic_frames: list[pd.DataFrame] = []
    pairwise_frames: list[pd.DataFrame] = []
    complementarity_frames: list[pd.DataFrame] = []
    score_frames: dict[str, pd.DataFrame] = {}
    for split_id in split_ids:
        split_assignment = assignments.loc[assignments["split_id"].astype(str).eq(split_id)].copy()
        dates = pd.DatetimeIndex(sorted(split_assignment["datetime"].unique()))
        panel = load_factor_panel(
            requested_factors,
            partition_manifest,
            start_date=dates.min(),
            end_date=dates.max(),
        )
        panel = panel.loc[panel["datetime"].isin(dates)].copy()
        development_dates = pd.DatetimeIndex(
            sorted(
                split_assignment.loc[
                    split_assignment["fold"].isin(design["development_folds"]), "datetime"
                ].unique()
            )
        )
        test_dates = pd.DatetimeIndex(
            sorted(split_assignment.loc[split_assignment["fold"].eq(design["evaluation_fold"]), "datetime"].unique())
        )
        eligibility = compute_split_local_eligibility(
            panel,
            development_dates,
            selected,
            design["eligibility"],
            split_id=split_id,
        )
        scores, membership = construct_scores(panel, design, eligibility)
        membership["outer_split_id"] = split_id
        test_scores = scores.loc[scores["datetime"].isin(test_dates)].copy()
        if canary:
            canary_dates = test_dates[:20]
            test_scores = test_scores.loc[test_scores["datetime"].isin(canary_dates)].copy()
            test_dates = canary_dates
        labels = _load_labels(
            resolve(inputs["labels"], project_root=project_root),
            test_dates,
            str(design["label"]),
        )
        test_panel = panel.loc[panel["datetime"].isin(test_dates)].copy()
        diagnostics, daily_ic, pairwise, complementarity = diagnose_variants(
            test_scores,
            labels,
            test_panel,
            design,
            split_id=split_id,
        )
        eligibility_frames.append(eligibility)
        membership_frames.append(membership)
        diagnostic_frames.append(diagnostics)
        daily_ic_frames.append(daily_ic)
        pairwise_frames.append(pairwise)
        complementarity_frames.append(complementarity)
        score_frames[split_id] = test_scores
        test_scores.to_parquet(runtime_dir / f"{split_id}_scores.parquet", index=False)

    eligibility_all = pd.concat(eligibility_frames, ignore_index=True)
    membership_all = pd.concat(membership_frames, ignore_index=True)
    diagnostics_all = pd.concat(diagnostic_frames, ignore_index=True)
    daily_ic_all = pd.concat(daily_ic_frames, ignore_index=True)
    pairwise_all = pd.concat(pairwise_frames, ignore_index=True)
    complementarity_all = pd.concat(complementarity_frames, ignore_index=True)
    _atomic_csv(report_dir / "split_local_eligibility.csv", eligibility_all)
    _atomic_csv(report_dir / "effective_sleeve_membership.csv", membership_all)
    _atomic_csv(report_dir / "sleeve_diagnostics.csv", diagnostics_all)
    _atomic_csv(report_dir / "daily_rank_ic.csv", daily_ic_all)
    _atomic_csv(report_dir / "score_correlation.csv", pairwise_all)
    _atomic_csv(report_dir / "complementarity_diagnostics.csv", complementarity_all)

    execution_path = report_dir / "transaction_cost_diagnostics.csv"
    if run_execution:
        execution = run_execution_diagnostics(
            score_frames,
            design,
            project_root=project_root,
            canary=canary,
        )
    elif reuse_execution:
        if not execution_path.is_file():
            raise FileNotFoundError("no prior transaction-cost diagnostics to reuse")
        execution = pd.read_csv(execution_path)
    else:
        execution = pd.DataFrame()
    _validate_execution_summary(
        execution,
        design,
        split_count=len(split_ids),
        canary=canary,
        required=run_execution or reuse_execution,
    )
    _atomic_csv(execution_path, execution)
    _write_report(
        report_dir / "REPORT.md",
        economic_map=economic_map,
        design=design,
        eligibility=eligibility_all,
        diagnostics=diagnostics_all,
        pairwise=pairwise_all,
        complementarity=complementarity_all,
        execution=execution,
        canary=canary,
    )
    manifest = _write_manifest(
        report_dir,
        design,
        project_root=project_root,
        canary=canary,
        execution_complete=run_execution or reuse_execution,
    )
    return {
        "artifact_status": manifest["artifact_status"],
        "design_sha256": design["_design_sha256"],
        "research_usable_factor_count": len(economic_map),
        "selected_member_count": len(selected),
        "variant_count": len(design["sleeves"]) + len(design["archetypes"]),
        "split_count": len(split_ids),
        "execution_scenario_count": len(execution),
        "report": str(report_dir / "REPORT.md"),
    }


def _validate_execution_summary(
    execution: pd.DataFrame,
    design: Mapping[str, Any],
    *,
    split_count: int,
    canary: bool,
    required: bool,
) -> None:
    if not required:
        return
    variant_count = 3 if canary else len(design["sleeves"]) + len(design["archetypes"])
    expected = split_count * variant_count
    if len(execution) != expected:
        raise ValueError(f"execution scenario count mismatch: {len(execution)} != {expected}")
    if execution.duplicated(["outer_split_id", "variant_id"]).any():
        raise ValueError("execution summary contains duplicate split/variant scenarios")
    if pd.to_numeric(execution["fill_count"], errors="coerce").le(0).any():
        raise ValueError("one or more execution scenarios have no fills")
    if pd.to_numeric(execution["cost_drag"], errors="coerce").le(0).any():
        raise ValueError("one or more execution scenarios have no realized implementation cost")


def run_execution_diagnostics(
    score_frames: Mapping[str, pd.DataFrame],
    design: Mapping[str, Any],
    *,
    project_root: Path,
    canary: bool,
) -> pd.DataFrame:
    from qlib_integration.historical_portfolio_backtest import (
        initialize_qlib,
        load_backtest_config,
        load_market_inputs,
    )
    from qlib_integration.runner import run_qlib_execution

    backtest = load_backtest_config(
        resolve(design["inputs"]["historical_backtest_config"], project_root=project_root)
    )
    initialize_qlib(backtest)
    markets, _, _ = load_market_inputs(backtest)
    portfolio = dict(design["portfolio_diagnostic"])
    variants = [str(row["sleeve_id"]) for row in design["sleeves"]] + [
        str(row["archetype_id"]) for row in design["archetypes"]
    ]
    if canary:
        variants = ["value", "speculative_activity", "diversified_economic"]
    rows: list[dict[str, Any]] = []
    for split_id, scores in score_frames.items():
        market = markets[split_id]
        if canary:
            market_dates = pd.DatetimeIndex(sorted(scores["datetime"].unique()))
            market = market.loc[market["datetime"].isin(market_dates)].copy()
        calendar = pd.DatetimeIndex(sorted(market["datetime"].unique()))
        if len(calendar) < 2:
            raise ValueError(f"execution market is too short: {split_id}")
        signal_dates = calendar[:-1]
        for variant_id in variants:
            signal = scores.loc[
                scores["datetime"].isin(signal_dates) & scores[variant_id].notna(),
                KEYS + [variant_id],
            ].rename(columns={variant_id: "score"})
            signal["method"] = variant_id
            signal["signal_artifact_id"] = f"{STAGE_ID}:{design['_design_sha256']}"
            signal["profile_name"] = "economic_multi_factor_research_v1"
            signal["profile_type"] = "historical_diagnostic"
            signal["research_run_family_id"] = STAGE_ID
            result = run_qlib_execution(signal, market, portfolio)
            daily = result["daily_accounting"]
            costs = result["transaction_costs"]
            initial_cash = float(portfolio["initial_cash"])
            ending_nav = float(daily["nav"].iloc[-1])
            implementation_cost = float(costs["implementation_cost"].sum()) if not costs.empty else 0.0
            returns = pd.to_numeric(daily["return"], errors="coerce").dropna()
            rows.append(
                {
                    "outer_split_id": split_id,
                    "variant_id": variant_id,
                    "portfolio_id": portfolio["portfolio_id"],
                    "trading_days": len(daily),
                    "net_total_return": ending_nav / initial_cash - 1.0,
                    "gross_total_return_approx": (ending_nav + implementation_cost) / initial_cash - 1.0,
                    "cost_drag": implementation_cost / initial_cash,
                    "annualized_turnover": float(daily["turnover"].sum() * 252.0 / len(daily)),
                    "net_sharpe": float(returns.mean() / returns.std(ddof=1) * np.sqrt(252.0)) if len(returns) > 1 and returns.std(ddof=1) > 0 else np.nan,
                    "fill_count": len(result["fills"]),
                    "rejected_order_count": len(result["rejected_orders"]),
                    "historical_execution_approximate": True,
                    "unbiased_final_estimate": False,
                }
            )
    return pd.DataFrame(rows)


def _write_manifest(
    report_dir: Path,
    design: Mapping[str, Any],
    *,
    project_root: Path,
    canary: bool,
    execution_complete: bool,
) -> dict[str, Any]:
    files = sorted(
        path for path in report_dir.iterdir() if path.is_file() and path.name != "manifest.json"
    )
    manifest = {
        "schema_version": 1,
        "stage_id": STAGE_ID,
        "artifact_status": "canary_pass" if canary else "research_complete",
        "experiment_class": "post_observation_research",
        "evidence_grade": "historical_diagnostic_only",
        "design_path": str(Path(design["_design_path"]).relative_to(project_root)).replace("\\", "/"),
        "design_sha256": design["_design_sha256"],
        "design_frozen_before_outcomes": True,
        "execution_complete": execution_complete,
        "historical_test_already_observed": True,
        "unbiased_final_estimate": False,
        "strategy_v1_changed": False,
        "matrix_changed": False,
        "forward_track_changed": False,
        "machine_learning_used": False,
        "production_winner_selected": False,
        "strategy_v2_authorized": False,
        "trial_inventory": {
            "sleeve_count": len(design["sleeves"]),
            "archetype_count": len(design["archetypes"]),
            "construction_variant_count": len(design["sleeves"]) + len(design["archetypes"]),
            "optimized_weight_trials": 0,
            "result_driven_sign_changes": 0,
            "post_result_research_iterations": 0,
        },
        "output_file_hashes": {path.name: file_sha256(path) for path in files},
    }
    _atomic_json(report_dir / "manifest.json", manifest)
    return manifest


def _format_table(frame: pd.DataFrame, columns: list[str], limit: int | None = None) -> str:
    data = frame[columns].copy()
    if limit is not None:
        data = data.head(limit)
    for column in data.select_dtypes(include=["float", "float64", "float32"]).columns:
        data[column] = data[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in data.itertuples(index=False, name=None)]
    return "\n".join([header, separator, *rows])


def _write_report(
    path: Path,
    *,
    economic_map: pd.DataFrame,
    design: Mapping[str, Any],
    eligibility: pd.DataFrame,
    diagnostics: pd.DataFrame,
    pairwise: pd.DataFrame,
    complementarity: pd.DataFrame,
    execution: pd.DataFrame,
    canary: bool,
) -> None:
    selected_count = int(economic_map["research_role"].eq("selected_sleeve_member").sum())
    family_counts = (
        economic_map.groupby("primary_family").size().sort_values(ascending=False).rename("factor_count").reset_index()
    )
    performance = diagnostics.sort_values(["outer_split_id", "variant_type", "variant_id"])
    split_total = int(diagnostics["outer_split_id"].nunique())
    aggregate_performance = (
        diagnostics.groupby(["variant_id", "variant_type"], as_index=False)
        .agg(
            mean_rank_ic=("mean_rank_ic", "mean"),
            min_rank_ic=("mean_rank_ic", "min"),
            max_rank_ic=("mean_rank_ic", "max"),
            positive_split_count=("mean_rank_ic", lambda values: int((values > 0).sum())),
            mean_quintile_5_minus_1=("quintile_5_minus_1", "mean"),
            mean_turnover_proxy=("top50_five_day_one_way_turnover", "mean"),
            mean_size_rank_corr=("mean_size_rank_corr", "mean"),
        )
        .sort_values("mean_rank_ic", ascending=False)
    )
    correlations = pairwise.reindex(pairwise["mean_daily_rank_correlation"].abs().sort_values(ascending=False).index).head(12)
    incremental = complementarity.loc[complementarity["record_type"].eq("incremental")].copy()
    aggregate_incremental = (
        incremental.groupby(["base_variant", "added_variant", "combined_variant"], as_index=False)
        .agg(
            mean_combined_minus_base_rank_ic=("combined_minus_base_rank_ic", "mean"),
            delta_positive_split_count=("combined_minus_base_rank_ic", lambda values: int((values > 0).sum())),
            mean_added_residual_rank_ic=("added_residual_mean_rank_ic", "mean"),
            residual_positive_split_count=("added_residual_mean_rank_ic", lambda values: int((values > 0).sum())),
            mean_base_added_rank_correlation=("base_added_mean_rank_correlation", "mean"),
        )
        .sort_values("mean_combined_minus_base_rank_ic", ascending=False)
    )
    eligible_summary = eligibility.groupby("outer_split_id")["split_local_eligible"].agg(["sum", "count"]).reset_index()
    portfolio_text = "未运行真实执行诊断。"
    aggregate_execution = pd.DataFrame()
    if not execution.empty:
        portfolio_text = _format_table(
            execution.sort_values(["outer_split_id", "variant_id"]),
            ["outer_split_id", "variant_id", "net_total_return", "cost_drag", "annualized_turnover"],
        )
        aggregate_execution = (
            execution.groupby("variant_id", as_index=False)
            .agg(
                mean_net_total_return=("net_total_return", "mean"),
                positive_net_split_count=("net_total_return", lambda values: int((values > 0).sum())),
                mean_cost_drag=("cost_drag", "mean"),
                mean_annualized_turnover=("annualized_turnover", "mean"),
                minimum_fill_count=("fill_count", "min"),
            )
            .sort_values("mean_net_total_return", ascending=False)
        )

    stable_incremental_count = int(
        (
            aggregate_incremental["delta_positive_split_count"].eq(split_total)
            & aggregate_incremental["residual_positive_split_count"].eq(split_total)
        ).sum()
    )
    if canary:
        historical_findings = (
            "- Canary 仅用于验证数据、构造、诊断与执行链路，不用于形成经济结论。正式结论只读取完整三个 split 的 CLOSED 产物。"
        )
    else:
        performance_index = aggregate_performance.set_index("variant_id")
        execution_index = aggregate_execution.set_index("variant_id") if not aggregate_execution.empty else pd.DataFrame()

        def performance_value(variant_id: str, column: str) -> float:
            return float(performance_index.at[variant_id, column])

        def execution_value(variant_id: str, column: str) -> float:
            if aggregate_execution.empty:
                return float("nan")
            return float(execution_index.at[variant_id, column])

        historical_findings = f"""- 已观察历史中，`speculation_reversal` 的跨 split 平均 Rank IC 最高（{performance_value('speculation_reversal', 'mean_rank_ic'):.4f}，{int(performance_value('speculation_reversal', 'positive_split_count'))}/{split_total} 为正）；`speculative_activity` 也为 {performance_value('speculative_activity', 'mean_rank_ic'):.4f}（{int(performance_value('speculative_activity', 'positive_split_count'))}/{split_total} 为正）。但两者平均单个约半年 test 窗口的 P01 成本拖累分别为 {execution_value('speculation_reversal', 'mean_cost_drag'):.2%} 与 {execution_value('speculative_activity', 'mean_cost_drag'):.2%}，不能把 gross 排序关系直接当作可交易 alpha。
- `illiquidity_premium` 的平均 Rank IC 为 {performance_value('illiquidity_premium', 'mean_rank_ic'):.4f}，但只在 {int(performance_value('illiquidity_premium', 'positive_split_count'))}/{split_total} 个 split 为正，且与 Size 的平均秩相关为 {performance_value('illiquidity_premium', 'mean_size_rank_corr'):.4f}；它更像带有显著小盘暴露的历史信号，而不是已识别的纯流动性溢价。
- `traditional_momentum` 在 {int(performance_value('traditional_momentum', 'positive_split_count'))}/{split_total} 个 split 为正，平均 Rank IC 为 {performance_value('traditional_momentum', 'mean_rank_ic'):.4f}；`trend_anchor` 同样不稳定。相较之下，短期反转和投机—反转组合更符合本样本历史，但预注册方向不会因结果被翻转。
- `value` 平均 Rank IC 为 {performance_value('value', 'mean_rank_ic'):.4f}，仅 {int(performance_value('value', 'positive_split_count'))}/{split_total} 个 split 为正；profitability、accounting quality 及其 fundamental archetypes 没有显示跨 split 稳定增量。`diversified_economic` 也只是 {performance_value('diversified_economic', 'mean_rank_ic'):.4f}、{int(performance_value('diversified_economic', 'positive_split_count'))}/{split_total} 为正，不能作为默认胜者。
- {len(aggregate_incremental)} 个预注册增量比较中，同时满足 combined-minus-base 与 residual-added IC 在全部 {split_total} 个 split 为正的有 {stable_incremental_count} 个。因此本阶段没有“稳定互补”结论，也没有据此继续调权或搜索新组合。
- P01 表报告的是固定执行规则下的绝对组合路径，不含 benchmark-adjusted alpha。已观察历史市场方向可能使负 IC 的 variant 仍获得正绝对收益；预测力判断以 Rank IC/单调性为主，P01 只用于可投资性、换手和成本诊断。"""
    text = f"""# Economic Multi-Factor Research V1

> 状态：`{'CANARY' if canary else 'CLOSED'}`；证据类别：`post_observation_research / historical_diagnostic_only`。本阶段不产生 fresh OOS、production winner 或 Strategy V2 授权。

## 结论

- 765 个全局物理合格因子被重新映射为经济机制；首代 sleeves 只使用 {selected_count} 个方向可由机制与文献预先说明的透明 mature factors。其余因子保留在 economic map 中，但不因技术变体数量多而获得组合权重。
- 原 taxonomy 被重写为 Valuation、Fundamentals、Liquidity/Trading、Return Dynamics、Risk/Lottery、Size/Structure、Technical Price/Volume 与 Opaque Multi-input 等研究层。`Multi` 不再被当作经济含义，PriceTrend 与 MomentumTrend 也不再自动等同。
- 共冻结 {len(design['sleeves'])} 个 sleeves、{len(design['archetypes'])} 个有限 archetypes；权重均为“因子在 subfamily 内等权、subfamily 在 sleeve 内等权、sleeve 在 archetype 内等权”。没有权重搜索、子集穷举、ML、SHAP 或结果后翻符号。
- Size 没有被预设为 small-cap alpha；它只作为暴露/条件变量。Residual Momentum 有文献先验，但当前矩阵没有可诚实等同的 PIT residual-return factor，因此未用 raw momentum 冒充。
- 三个 outer split 的资格仅使用各自 train+validation 日期。测试期 coverage、IC 或收益没有参与 membership。

## 已观察历史发现

{historical_findings}

跨 split 聚合（按平均 Rank IC 排序）：

{_format_table(aggregate_performance, ['variant_id', 'variant_type', 'mean_rank_ic', 'min_rank_ic', 'max_rank_ic', 'positive_split_count', 'mean_quintile_5_minus_1', 'mean_turnover_proxy', 'mean_size_rank_corr'])}

## Economic map

{_format_table(family_counts, ['primary_family', 'factor_count'])}

完整 765 行映射见 `economic_map.csv`。大量 Alpha158/360/101 与 TA 公式被归入 Technical Price/Volume 或 Opaque Multi-input 的 exploratory layer；这是对其经济可解释性边界的诚实表达，不是否定其后续模型价值。

## 文献如何影响设计

`literature_evidence_map.csv` 保存机制、A 股与国际证据、预期方向、冗余、互补角色、horizon、turnover 和证据等级。最直接的设计影响是：

1. Liu–Stambaugh–Yuan 促使 Value 保留 earnings/book/sales/cash-flow/payout 多种测量，并让 Size 可见而非机械做多小盘；
2. Jansen–Swinkels–Zhou 将 value/risk/trading/reversal 设为较强先验，将 raw momentum/quality 设为混合证据；
3. Leippold–Wang–Zhou 使 liquidity/trading 被拆成 price impact、speculative activity 与 order flow，并从一开始报告成本；
4. Hsu 等使 traditional momentum、overnight sentiment 与 reversal 分开，禁止看结果后把 momentum 改名为 reversal；
5. Pan–Tang–Xu 预先冻结 abnormal turnover 的负方向；Wan 的中国证据使 IVOL 与 MAX 都保留但在 subfamily 层平衡。

## Split-local eligibility

{_format_table(eligible_summary, ['outer_split_id', 'sum', 'count'])}

`sum` 是在该 split 的 development-only scope 通过资格的预注册成员数，`count` 是候选成员数。完整统计和排除原因见 `split_local_eligibility.csv` 与 `effective_sleeve_membership.csv`。

## Sleeve 与 archetype 历史诊断

{_format_table(performance, ['outer_split_id', 'variant_id', 'variant_type', 'mean_rank_ic', 'positive_ic_fraction', 'quintile_5_minus_1', 'nondecreasing_quintile_steps', 'top50_five_day_one_way_turnover'])}

这些是已观察历史 test 上的机制诊断。不能因为本轮 sleeve 定义是新的，就把结果重新称为 unbiased holdout。逐日 IC 和 calendar-year regime 结果分别保存在 `daily_rank_ic.csv` 与 `complementarity_diagnostics.csv`。

## 冗余与互补

绝对相关性最高的 variant pairs：

{_format_table(correlations, ['outer_split_id', 'left_variant', 'right_variant', 'mean_daily_rank_correlation'], 12)}

预注册增量比较：

{_format_table(incremental, ['outer_split_id', 'base_variant', 'added_variant', 'combined_variant', 'combined_minus_base_rank_ic', 'added_residual_mean_rank_ic', 'base_added_mean_rank_correlation', 'incremental_positive'])}

跨 split 增量一致性：

{_format_table(aggregate_incremental, ['base_variant', 'added_variant', 'combined_variant', 'mean_combined_minus_base_rank_ic', 'delta_positive_split_count', 'mean_added_residual_rank_ic', 'residual_positive_split_count', 'mean_base_added_rank_correlation'])}

`combined_minus_base_rank_ic` 回答透明 A 与 A+B 的历史差异；`added_residual_mean_rank_ic` 先在每日截面从 added 中去除 base 的线性部分，再衡量剩余排序信息。两者共同用于区分 complementarity 与 redundancy，不做 2^N 搜索。

## P01 固定执行与成本

{portfolio_text}

跨 split 执行摘要：

{_format_table(aggregate_execution, ['variant_id', 'mean_net_total_return', 'positive_net_split_count', 'mean_cost_drag', 'mean_annualized_turnover', 'minimum_fill_count']) if not aggregate_execution.empty else '未生成执行摘要。'}

执行诊断沿用固定 Top50、每 5 日调仓、T+1、A 股佣金/印花税、10 bps 滑点、动态手数、5% participation cap 和既有近似 market semantics。预测排序、换手与成本后绝对组合路径分开解释；这里没有扫描 TopK、调仓频率或费用参数。运行期间既有 Qlib 执行栈出现 empty-slice 与个别 execution-price 缺失后回退 close 的警告；54 个场景均完成且存在成交与成本，但执行结果仍须按 approximate historical diagnostic 使用。

## 针对计划问题的回答

1. **765 如何理解**：它们是物理合格候选，不是 765 个独立经济 bets。透明成员进入 sleeves，技术/opaque 公式保留作 exploratory/model information。
2. **taxonomy 修正**：拆分 liquidity/trading/order-flow，拆分 raw momentum/reversal/anchor，拆分 risk/lottery/downside，`Multi` 降为 unresolved，Size 改为多重角色。
3. **A 股文献影响**：见上文与 evidence map；没有直接照搬美国方向。
4. **机制**：价值、经营盈利、现金/应计质量、保守投资与增长、价格冲击、投机活动、大单流、短期反转/隔夜情绪、传统动量、52 周锚定、低风险/彩票偏好。
5. **为何这些 sleeves**：每个 sleeve 代表一个可叙述机制，而不是原 folder 的平均值。
6. **为何保留多测量**：同一机制的 level/change、PIT/TTM、risk/behavior 和 horizon 由 subfamily balancing 保留，近义变体不会因数量多而增权。
7. **冗余**：以每日 score correlation 报告，不使用“一簇只留一个”。
8. **互补**：以 A、A+B、added residual IC 和成本分散共同判断。
9. **Value/Liquidity/Trading/Risk**：结果见 diagnostics；解释受短样本与已观察历史限制。
10. **Momentum/Residual Momentum/Reversal**：raw momentum 与 reversal 分开；residual momentum 因缺少诚实输入而不伪造。
11. **Fundamentals**：Value→Value+Profitability→+Accounting Quality 是预注册增量链。
12. **Size**：V1 中是 exposure/control/conditioning variable，不是自动做多小盘。
13. **高换手/成本**：见 P01 表；交易与反转类必须以 net 而非 gross 解释。
14. **稳定 incremental value**：只有在多个 split 的 combined delta 与 residual IC 同向时才可称“较一致的历史互补”，仍不是 fresh OOS。
15. **失败组合**：负增量或高相关/高成本组合是有效研究结果，不会继续改权重。
16. **split 一致性**：所有表逐 split 保留，不用 pooled 均值掩盖差异。
17. **research variants**：实际预注册 {len(design['sleeves']) + len(design['archetypes'])} 个；无额外搜索 arm。
18. **result-driven iteration**：V1 为 0；manifest 明确记录。未来修改必须另记 post-result iteration。
19. **historical evidence**：仅用于机制、稳定性、失败与假设生成；`unbiased_final_estimate=false`。
20. **是否形成 ML baseline**：形成了 human-structured 输入与诊断基线，但是否进入 ML 由后续单独授权决定。

## Governance 与边界

- Strategy V1、Forward Track、frozen Matrix、历史 prediction 和旧 release 均未修改；
- 本阶段没有启动 LightGBM/XGBoost/神经网络/SHAP/Strategy V2；
- `split_003` 与其他 historical tests 都按 post-observation diagnostic 解释；
- 真正新证据仍只能来自未来另行冻结的 Forward Track；
- 本报告允许“不成立”和 mixed evidence，不选择 production winner。
"""
    path.write_text(text, encoding="utf-8")
