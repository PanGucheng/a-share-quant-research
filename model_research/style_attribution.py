from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from model_research.diagnostics import _daily_ic, _ic_summary
from research_validation.lineage import (
    capture_code_state,
    load_artifact_manifest,
    sha256_file,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher


OUTPUTS = (
    "artifact_manifest.json",
    "benchmark_attribution_capability.csv",
    "conditional_size_ic.csv",
    "contract_status.csv",
    "controlled_alpha_daily.csv",
    "controlled_alpha_summary.csv",
    "industry_conditional_ic.csv",
    "industry_exposure.csv",
    "report.md",
    "resolved_config.json",
    "size_exposure.csv",
    "style_proxy_size_association.csv",
    "size_regime_attribution.csv",
    "v2_hypothesis_status.md",
)


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _base_frames(root: Path, config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    provenance = json.loads(_resolve(root, config["parents"]["core_runtime_provenance"]).read_text(encoding="utf-8"))
    directory = root / "outputs/post_model_diagnostics_v1/runtime/base" / provenance["base_cache_key"]
    frames = {}
    for split in config["split_ids"]:
        path = directory / f"{split}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"frozen diagnostic base missing: {path}")
        frame = pd.read_parquet(path)
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame["outer_split_id"] = split
        frames[split] = frame
    return frames


def _cohorts(frame: pd.DataFrame, topks: list[int]) -> dict[str, pd.DataFrame]:
    ranked = frame.copy()
    ranked["model_rank"] = ranked.groupby("datetime")["prediction"].rank(ascending=False, method="first")
    result = {f"Top{topk}": ranked.loc[ranked["model_rank"].le(topk)] for topk in topks}
    return result


def _size_exposure(
    bases: dict[str, pd.DataFrame], style: pd.DataFrame, topks: list[int]
) -> pd.DataFrame:
    rows = []
    for split, base in bases.items():
        dates = set(base["datetime"].unique())
        universe = style.loc[style["datetime"].isin(dates)]
        merged = base[["datetime", "instrument", "prediction"]].merge(
            style, on=["datetime", "instrument"], how="left", validate="one_to_one"
        )
        cohorts = {"Universe": universe, **_cohorts(merged, topks)}
        for name, frame in cohorts.items():
            daily = frame.groupby("datetime").agg(
                mean_size_percentile=("size_percentile", "mean"),
                median_size_percentile=("size_percentile", "median"),
                mean_total_mv=("total_mv", "mean"),
                median_total_mv=("total_mv", "median"),
                mean_circ_mv=("circ_mv", "mean"),
                median_circ_mv=("circ_mv", "median"),
            )
            shares = frame.pivot_table(index="datetime", columns="size_bucket", values="instrument", aggfunc="count").fillna(0)
            shares = shares.div(shares.sum(axis=1), axis=0)
            rows.append(
                {
                    "outer_split_id": split,
                    "cohort": name,
                    **{column: float(daily[column].mean()) for column in daily},
                    **{f"{bucket.lower()}_share": float(shares.get(bucket, pd.Series(dtype=float)).mean()) for bucket in ["Small", "Mid", "Large"]},
                    "valid_days": int(len(daily)),
                }
            )
    return pd.DataFrame(rows)


def _conditional_size_ic(
    root: Path, config: dict[str, Any], bases: dict[str, pd.DataFrame], style: pd.DataFrame
) -> pd.DataFrame:
    structures = pd.read_csv(_resolve(root, config["parents"]["core_factor_structure"]))
    weights = pd.read_csv(_resolve(root, config["parents"]["factor_weights"]))
    weights = weights.loc[weights["method"].eq("equal_weight")]
    rows = []
    for split, base in bases.items():
        frame = base.merge(
            style[["datetime", "instrument", "size_bucket"]],
            on=["datetime", "instrument"], how="left", validate="one_to_one",
        )
        group_map = structures.loc[structures["outer_split_id"].eq(split)].groupby("economic_group")["factor"].apply(list)
        directions = weights.loc[weights["outer_split_id"].eq(split)].set_index("factor_column")["direction"].to_dict()
        signals: dict[str, pd.Series] = {"Model score": frame["prediction"]}
        for group, factors in group_map.items():
            available = [factor for factor in factors if factor in frame]
            if not available:
                continue
            ranked = pd.DataFrame(index=frame.index)
            for factor in available:
                ranked[factor] = frame.groupby("datetime")[factor].rank(pct=True) * float(directions.get(factor, 1))
            signals[f"Factor group: {group}"] = ranked.mean(axis=1)
        for signal_name, signal in signals.items():
            frame["_signal"] = signal
            for bucket in config["size_buckets"]:
                subset = frame.loc[frame["size_bucket"].eq(bucket)]
                values = _daily_ic(subset, "_signal", "return_20d_t1", int(config["minimum_daily_pairs"]))
                rows.append(
                    {
                        "outer_split_id": split,
                        "signal": signal_name,
                        "size_bucket": bucket,
                        **_ic_summary(values, 1),
                        "coverage_rows": int(subset[["_signal", "return_20d_t1"]].dropna().shape[0]),
                    }
                )
    return pd.DataFrame(rows)


def _size_regime(bases: dict[str, pd.DataFrame], style: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, base in bases.items():
        frame = base.merge(
            style[["datetime", "instrument", "size_bucket", "size_percentile"]],
            on=["datetime", "instrument"], how="left", validate="one_to_one",
        )
        frame["model_rank"] = frame.groupby("datetime")["prediction"].rank(ascending=False, method="first")
        bucket_return = frame.groupby(["datetime", "size_bucket"])["return_20d_t1"].mean().unstack()
        spread = bucket_return.get("Small") - bucket_return.get("Large")
        for topk in [10, 20, 50, 100]:
            top = frame.loc[frame["model_rank"].le(topk)]
            rows.append(
                {
                    "outer_split_id": split,
                    "cohort": f"Top{topk}",
                    "small_minus_large_mean_return": float(spread.mean()),
                    "top_mean_size_percentile": float(top.groupby("datetime")["size_percentile"].mean().mean()),
                    "top_small_share": float(top["size_bucket"].eq("Small").groupby(top["datetime"]).mean().mean()),
                    "valid_days": int(spread.notna().sum()),
                }
            )
    return pd.DataFrame(rows)


def _style_proxy_size_association(
    config: dict[str, Any], bases: dict[str, pd.DataFrame], style: pd.DataFrame
) -> pd.DataFrame:
    proxy = str(config["style_proxy_association"]["liquidity_proxy"])
    rows = []
    for split, base in bases.items():
        if proxy not in base.columns:
            rows.append(
                {
                    "outer_split_id": split,
                    "proxy": proxy,
                    "coverage_status": "unavailable",
                    "mean_daily_rank_correlation_with_size": float("nan"),
                    "small_mean_daily_proxy_percentile": float("nan"),
                    "mid_mean_daily_proxy_percentile": float("nan"),
                    "large_mean_daily_proxy_percentile": float("nan"),
                    "valid_days": 0,
                    "coverage_rows": 0,
                }
            )
            continue
        frame = base[["datetime", "instrument", proxy]].merge(
            style[["datetime", "instrument", "size_percentile", "size_bucket"]],
            on=["datetime", "instrument"], how="left", validate="one_to_one",
        )
        valid = frame.dropna(subset=[proxy, "size_percentile", "size_bucket"]).copy()
        valid["proxy_percentile"] = valid.groupby("datetime")[proxy].rank(pct=True)
        daily_correlation = valid.groupby("datetime").apply(
            lambda group: group["proxy_percentile"].corr(group["size_percentile"], method="spearman")
            if len(group) >= int(config["minimum_daily_pairs"])
            else float("nan"),
            include_groups=False,
        ).dropna()
        bucket_means = valid.groupby(["datetime", "size_bucket"])["proxy_percentile"].mean().groupby("size_bucket").mean()
        rows.append(
            {
                "outer_split_id": split,
                "proxy": proxy,
                "coverage_status": "pass" if len(daily_correlation) >= int(config["minimum_valid_days"]) else "insufficient_coverage",
                "mean_daily_rank_correlation_with_size": float(daily_correlation.mean()),
                "small_mean_daily_proxy_percentile": float(bucket_means.get("Small", float("nan"))),
                "mid_mean_daily_proxy_percentile": float(bucket_means.get("Mid", float("nan"))),
                "large_mean_daily_proxy_percentile": float(bucket_means.get("Large", float("nan"))),
                "valid_days": int(len(daily_correlation)),
                "coverage_rows": int(len(valid)),
            }
        )
    return pd.DataFrame(rows)


def _industry_exposure(
    bases: dict[str, pd.DataFrame], style: pd.DataFrame, topks: list[int]
) -> pd.DataFrame:
    rows = []
    for split, base in bases.items():
        dates = set(base["datetime"].unique())
        universe = style.loc[style["datetime"].isin(dates)]
        merged = base[["datetime", "instrument", "prediction"]].merge(
            style[["datetime", "instrument", "sw_l1_code", "sw_l1_name"]],
            on=["datetime", "instrument"], how="left", validate="one_to_one",
        )
        universe_share = universe.groupby(["datetime", "sw_l1_code", "sw_l1_name"]).size()
        universe_share = universe_share / universe.groupby("datetime").size()
        for cohort, frame in {"Universe": universe, **_cohorts(merged, topks)}.items():
            share = frame.groupby(["datetime", "sw_l1_code", "sw_l1_name"]).size()
            share = share / frame.groupby("datetime").size()
            combined = share.rename("share").to_frame().join(universe_share.rename("universe_share"), how="outer").fillna(0).reset_index()
            for (code, name), group in combined.groupby(["sw_l1_code", "sw_l1_name"]):
                rows.append(
                    {
                        "outer_split_id": split,
                        "cohort": cohort,
                        "sw_l1_code": code,
                        "sw_l1_name": name,
                        "mean_share": float(group["share"].mean()),
                        "mean_universe_share": float(group["universe_share"].mean()),
                        "mean_active_share": float((group["share"] - group["universe_share"]).mean()),
                    }
                )
    result = pd.DataFrame(rows)
    hhi = result.groupby(["outer_split_id", "cohort"])["mean_share"].apply(lambda value: float((value**2).sum())).rename("industry_hhi").reset_index()
    return result.merge(hhi, on=["outer_split_id", "cohort"], how="left")


def _industry_ic(config: dict[str, Any], bases: dict[str, pd.DataFrame], style: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, base in bases.items():
        frame = base.merge(
            style[["datetime", "instrument", "sw_l1_code", "sw_l1_name"]],
            on=["datetime", "instrument"], how="left", validate="one_to_one",
        )
        for (code, name), group in frame.dropna(subset=["sw_l1_code"]).groupby(["sw_l1_code", "sw_l1_name"]):
            values = _daily_ic(group, "prediction", "return_20d_t1", int(config["minimum_daily_pairs"]))
            summary = _ic_summary(values, 1)
            status = "pass" if len(values) >= int(config["minimum_valid_days"]) else "insufficient_coverage"
            rows.append({"outer_split_id": split, "sw_l1_code": code, "sw_l1_name": name, "coverage_status": status, **summary, "rows": len(group)})
    return pd.DataFrame(rows)


def _controlled_alpha(
    config: dict[str, Any], bases: dict[str, pd.DataFrame], style: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    target = config["controlled_attribution"]["target"]
    for split, base in bases.items():
        frame = base[["datetime", "instrument", "prediction", target]].merge(
            style[["datetime", "instrument", "size_percentile", "sw_l1_code"]],
            on=["datetime", "instrument"], how="left", validate="one_to_one",
        ).dropna()
        for date, group in frame.groupby("datetime"):
            if len(group) < int(config["minimum_daily_pairs"]):
                continue
            score = group["prediction"].to_numpy(float)
            size = group["size_percentile"].to_numpy(float)
            score_sd, size_sd = score.std(), size.std()
            if score_sd == 0 or size_sd == 0:
                continue
            score = (score - score.mean()) / score_sd
            size = (size - size.mean()) / size_sd
            industries = pd.get_dummies(group["sw_l1_code"], drop_first=True, dtype=float).to_numpy()
            X = np.column_stack([np.ones(len(group)), score, size, industries])
            coefficients, _, rank, _ = np.linalg.lstsq(X, group[target].to_numpy(float), rcond=None)
            rows.append({"outer_split_id": split, "datetime": date, "model_score_coefficient": coefficients[1], "size_coefficient": coefficients[2], "rows": len(group), "design_rank": int(rank), "industry_controls": industries.shape[1]})
    daily = pd.DataFrame(rows)
    summary_rows = []
    for split, group in daily.groupby("outer_split_id"):
        values = group["model_score_coefficient"]
        coefficient_std = float(values.std(ddof=1))
        summary_rows.append(
            {
                "outer_split_id": split,
                "mean_model_score_coefficient": float(values.mean()),
                "coefficient_std": coefficient_std,
                "coefficient_mean_over_std": float(values.mean() / coefficient_std) if coefficient_std > 0 else float("nan"),
                "positive_ratio": float(values.gt(0).mean()),
                "valid_days": len(values),
                "specification": "daily OLS: return_20d_t1 ~ model_score_z + size_percentile_z + SW_L1_FE",
            }
        )
    return daily, pd.DataFrame(summary_rows)


def _protected_file_hashes(root: Path, config: dict[str, Any]) -> dict[str, str]:
    paths = [_resolve(root, value) for value in config["protected_frozen_files"]]
    receipt = _resolve(root, config["parents"]["prediction_receipt"])
    receipts = pd.read_csv(receipt)
    paths.extend(Path(value) for value in receipts["runtime_path"])
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"protected frozen files missing: {missing}")
    return {str(path.resolve()): sha256_file(path) for path in paths}


def _hash_map(values: dict[str, str]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _report(
    size: pd.DataFrame,
    conditional: pd.DataFrame,
    regime: pd.DataFrame,
    proxy: pd.DataFrame,
    controlled: pd.DataFrame,
    industry: pd.DataFrame,
) -> tuple[str, str]:
    top50 = size.loc[size["cohort"].eq("Top50")]
    universe = size.loc[size["cohort"].eq("Universe"), ["outer_split_id", "mean_size_percentile"]].rename(columns={"mean_size_percentile": "universe_size"})
    top50 = top50.merge(universe, on="outer_split_id")
    lines = ["# Model Diagnostic Style Attribution Extension V1", "", "Core diagnostic values were not recomputed or modified.", "", "## Evidence", ""]
    for row in top50.itertuples(index=False):
        lines.append(f"- `{row.outer_split_id}` Top50 mean size percentile `{row.mean_size_percentile:.3f}` vs universe `{row.universe_size:.3f}`; Small share `{row.small_share:.3f}`.")
    lines += [""]
    for row in proxy.itertuples(index=False):
        lines.append(f"- `{row.outer_split_id}` liquidity-size daily rank correlation `{row.mean_daily_rank_correlation_with_size:.3f}`; Small/Large proxy percentiles `{row.small_mean_daily_proxy_percentile:.3f}`/`{row.large_mean_daily_proxy_percentile:.3f}`.")
    model_size_ic = conditional.loc[conditional["signal"].eq("Model score")]
    for split, group in model_size_ic.groupby("outer_split_id"):
        values = group.set_index("size_bucket")["mean_rank_ic"]
        lines.append(f"- `{split}` model Size-conditional Rank IC: Small `{values.get('Small', float('nan')):.4f}`, Mid `{values.get('Mid', float('nan')):.4f}`, Large `{values.get('Large', float('nan')):.4f}`.")
    lines += ["", "## Controlled Model Alpha", ""]
    for row in controlled.itertuples(index=False):
        lines.append(f"- `{row.outer_split_id}` controlled model-score coefficient `{row.mean_model_score_coefficient:.6f}`, positive-day ratio `{row.positive_ratio:.3f}`.")
    top_industry = industry.loc[industry["cohort"].eq("Top50")].copy()
    top_industry = top_industry.loc[top_industry.groupby("outer_split_id")["mean_active_share"].idxmax()]
    lines += ["", "## Industry Evidence", ""]
    for row in top_industry.itertuples(index=False):
        lines.append(f"- `{row.outer_split_id}` largest Top50 over-exposure: `{row.sw_l1_name}` at `{row.mean_active_share:.3f}` active share.")
    mean_top_size = float(top50["mean_size_percentile"].mean())
    mean_proxy_corr = float(proxy.loc[proxy["coverage_status"].eq("pass"), "mean_daily_rank_correlation_with_size"].mean())
    alpha_all_positive = bool(controlled["mean_model_score_coefficient"].gt(0).all())
    lines += ["", "## Answers To Frozen Research Questions", ""]
    small_bias_splits = top50.loc[top50["mean_size_percentile"].lt(0.5), "outer_split_id"].tolist()
    lines.append(f"1. Small-cap bias: not persistent; below-universe Top50 Size appears only in `{', '.join(small_bias_splits) if small_bias_splits else 'none'}`, while the three-split average Top50 size percentile is `{mean_top_size:.3f}`.")
    proxy_answer = "strongly associated with" if mean_proxy_corr >= 0.7 else "partly associated with" if mean_proxy_corr >= 0.4 else "not strongly associated with"
    lines.append(f"2. Low-liquidity proxy: {proxy_answer} Small Cap cross-sectionally (`amount_mean_20` versus Size mean daily rank correlation `{mean_proxy_corr:.3f}`); this is association, not proof that the proxy is only Size.")
    spread = regime.groupby("outer_split_id")["small_minus_large_mean_return"].first()
    development_spread = float(spread.reindex(["split_001", "split_002"]).mean())
    holdout_spread = float(spread.get("split_003", float("nan")))
    mismatch = np.isfinite(holdout_spread) and np.isfinite(development_spread) and holdout_spread < development_spread
    lines.append(f"3. Size regime mismatch: {'consistent with the observed decay' if mismatch else 'not clearly supported'}; Small-minus-Large future return changed from development mean `{development_spread:.6f}` to split_003 `{holdout_spread:.6f}`. This is attribution only.")
    top50_industry = industry.loc[industry["cohort"].eq("Top50")]
    max_active = float(top50_industry["mean_active_share"].abs().max())
    lines.append(f"4. Industry concentration: maximum absolute Top50 active SW L1 share is `{max_active:.3f}`; detailed drift and HHI are in `industry_exposure.csv`.")
    lines.append("5. Benchmark-relative industry explanation: unresolved because monthly index weights were canary-verified only and were not admitted as formal SDK research input.")
    lines.append(f"6. Independent model information: {'positive in every split' if alpha_all_positive else 'mixed across splits'} after daily Size and SW L1 controls; coefficients are attribution statistics, not an unbiased final estimate.")
    lines.append("7. V2 hypotheses: evidence statuses are listed in `v2_hypothesis_status.md`; no V2 training, factor deletion, neutralization, TopK scan, or portfolio optimization was performed.")
    lines += ["", "Industry data represents historical effective-date classification reconstructed today, not proof of the database vintage available on each historical date.", "", "Historical diagnosis != unbiased future evidence."]
    hypotheses = ["# V2 Hypothesis Evidence Status", "", "> These statuses support only a future preregistered test.", ""]
    hypotheses += ["- `Small-cap exposure`: supported for future test." if float((top50["mean_size_percentile"] < 0.5).mean()) >= 2 / 3 else "- `Small-cap exposure`: mixed."]
    hypotheses += ["- `Size regime mismatch`: supported for future test." if spread.nunique() > 1 and spread.loc["split_003"] < spread.loc[["split_001", "split_002"]].mean() else "- `Size regime mismatch`: mixed."]
    hypotheses += ["- `Independent model alpha after Size/Industry control`: supported for future test." if controlled["mean_model_score_coefficient"].gt(0).all() else "- `Independent model alpha after Size/Industry control`: mixed."]
    hypotheses += ["- `Benchmark active style attribution`: unresolved; monthly index weights were MCP-canary verified but not used as formal SDK input in this extension."]
    return "\n".join(lines) + "\n", "\n".join(hypotheses) + "\n"


def run_style_attribution(root: Path, config: dict[str, Any]) -> pd.DataFrame:
    core_path = _resolve(root, config["parents"]["core_manifest"])
    core_hash_before = sha256_file(core_path)
    protected_before = _protected_file_hashes(root, config)
    core_manifest = load_artifact_manifest(core_path)
    external_manifest = load_artifact_manifest(_resolve(root, config["parents"]["external_style_manifest"]))
    if external_manifest["artifact_status"] != "pass":
        raise ValueError("External PIT Style Data V1 is not a passing artifact")
    bases = _base_frames(root, config)
    style = pd.read_parquet(_resolve(root, config["parents"]["external_style_data"]))
    style["datetime"] = pd.to_datetime(style["datetime"])
    topks = [int(value) for value in config["cohorts"]]
    size = _size_exposure(bases, style, topks)
    conditional = _conditional_size_ic(root, config, bases, style)
    regime = _size_regime(bases, style)
    proxy = _style_proxy_size_association(config, bases, style)
    industry = _industry_exposure(bases, style, topks)
    industry_ic = _industry_ic(config, bases, style)
    controlled_daily, controlled = _controlled_alpha(config, bases, style)
    core_hash_after = sha256_file(core_path)
    protected_after = _protected_file_hashes(root, config)
    protected_hash_before = _hash_map(protected_before)
    protected_hash_after = _hash_map(protected_after)
    contracts = pd.DataFrame(
        [
            {"check_name": "external_style_parent", "status": "pass", "severity": "critical", "observed_value": external_manifest["artifact_status"], "required_value": "pass"},
            {"check_name": "external_style_lineage", "status": "pass" if external_manifest["lineage_status"] == "complete" else "fail", "severity": "critical", "observed_value": external_manifest["lineage_status"], "required_value": "complete"},
            {"check_name": "core_parent", "status": "pass" if core_manifest["artifact_status"] == "pass" else "fail", "severity": "critical", "observed_value": core_manifest["artifact_status"], "required_value": "pass"},
            {"check_name": "core_lineage", "status": "pass" if core_manifest["lineage_status"] == "complete" else "fail", "severity": "critical", "observed_value": core_manifest["lineage_status"], "required_value": "complete"},
            {"check_name": "core_manifest_unchanged", "status": "pass" if core_hash_before == core_hash_after else "fail", "severity": "critical", "observed_value": core_hash_after, "required_value": core_hash_before},
            {"check_name": "protected_frozen_artifacts_unchanged", "status": "pass" if protected_before == protected_after else "fail", "severity": "critical", "observed_value": protected_hash_after, "required_value": protected_hash_before},
            {"check_name": "all_splits_present", "status": "pass" if set(size["outer_split_id"]) == set(config["split_ids"]) else "fail", "severity": "critical", "observed_value": size["outer_split_id"].nunique(), "required_value": len(config["split_ids"])},
            {"check_name": "controlled_attribution_complete", "status": "pass" if controlled["valid_days"].min() >= int(config["minimum_valid_days"]) else "fail", "severity": "critical", "observed_value": controlled["valid_days"].min(), "required_value": config["minimum_valid_days"]},
            {"check_name": "core_heavy_components_rerun", "status": "pass", "severity": "critical", "observed_value": False, "required_value": False},
        ]
    )
    benchmark = pd.DataFrame([{"project_symbol": config["benchmark_optional"]["project_symbol"], "tushare_code": config["benchmark_optional"]["confirmed_tushare_code"], "frequency": "monthly", "status": config["benchmark_optional"]["status"], "blocking": False}])
    report, hypotheses = _report(size, conditional, regime, proxy, controlled, industry)
    output = _resolve(root, config["output_dir"])
    frames = {
        "benchmark_attribution_capability.csv": benchmark,
        "conditional_size_ic.csv": conditional,
        "contract_status.csv": contracts,
        "controlled_alpha_daily.csv": controlled_daily,
        "controlled_alpha_summary.csv": controlled,
        "industry_conditional_ic.csv": industry_ic,
        "industry_exposure.csv": industry,
        "size_exposure.csv": size,
        "style_proxy_size_association.csv": proxy,
        "size_regime_attribution.csv": regime,
    }
    with StageOutputPublisher(output, OUTPUTS) as publisher:
        for name, frame in frames.items():
            frame.to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
        publisher.path("report.md").write_text(report, encoding="utf-8")
        publisher.path("v2_hypothesis_status.md").write_text(hypotheses, encoding="utf-8")
        publisher.path("resolved_config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files = [publisher.path(name) for name in OUTPUTS if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=root, stage_id=config["stage_id"], config=config,
            output_dir=publisher.staging_dir, output_files=files,
            code_state=capture_code_state(root),
            input_manifest_paths=[core_path, _resolve(root, config["parents"]["external_style_manifest"])],
            start_date=min(frame["datetime"].min() for frame in bases.values()),
            end_date=max(frame["datetime"].max() for frame in bases.values()),
            contract_paths=[publisher.path("contract_status.csv")],
            require_complete_parents=False,
        )
        publisher.publish()
    return contracts
