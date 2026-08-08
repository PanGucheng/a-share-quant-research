from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

from research_validation.external_style import audit_external_style_capability
from research_validation.lineage import (
    capture_code_state,
    config_sha256,
    load_artifact_manifest,
    sha256_file,
    sha256_text,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher


OUTPUTS = (
    "artifact_manifest.json",
    "conditional_factor_ic.csv",
    "contract_status.csv",
    "external_style_capability.csv",
    "factor_structure.csv",
    "feature_importance.csv",
    "model_diagnostic_report.md",
    "model_proxy_exposure.csv",
    "p01_attribution.csv",
    "prediction_equivalence.csv",
    "ranking_concentration.csv",
    "ranking_stability.csv",
    "resolved_config.json",
    "runtime_provenance.json",
    "qlib_capability_audit.csv",
    "signal_decay.csv",
    "v2_hypotheses.md",
)


def _json_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _safe_corr(left: pd.Series, right: pd.Series, method: str = "spearman") -> float:
    valid = left.notna() & right.notna()
    if int(valid.sum()) < 2 or left[valid].nunique() < 2 or right[valid].nunique() < 2:
        return float("nan")
    return float(left[valid].corr(right[valid], method=method))


def forward_returns_t1(
    prices: pd.DataFrame, horizons: Iterable[int], *, price_column: str = "$close"
) -> pd.DataFrame:
    """Return close[t+h+1] / close[t+1] - 1 for each instrument."""
    required = {"datetime", "instrument", price_column}
    if missing := required - set(prices):
        raise ValueError(f"price frame missing columns: {sorted(missing)}")
    frame = prices.loc[:, ["datetime", "instrument", price_column]].copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame = frame.sort_values(["instrument", "datetime"], kind="mergesort")
    grouped = frame.groupby("instrument", sort=False)[price_column]
    entry = grouped.shift(-1)
    for horizon in horizons:
        if int(horizon) <= 0:
            raise ValueError("forward-return horizons must be positive")
        frame[f"return_{int(horizon)}d_t1"] = grouped.shift(-(int(horizon) + 1)) / entry - 1.0
    return frame.drop(columns=price_column)


def assign_rank_buckets(ranks: pd.Series, buckets: list[dict[str, Any]]) -> pd.Series:
    result = pd.Series(pd.NA, index=ranks.index, dtype="string")
    numeric = pd.to_numeric(ranks, errors="coerce")
    for bucket in buckets:
        end = bucket.get("end")
        mask = numeric.ge(int(bucket["start"]))
        if end is not None:
            mask &= numeric.le(int(end))
        result.loc[mask] = str(bucket["name"])
    return result


def prediction_equivalence(
    official: np.ndarray, recomputed: np.ndarray, *, atol: float, rtol: float
) -> dict[str, Any]:
    left = np.asarray(official, dtype=float)
    right = np.asarray(recomputed, dtype=float)
    if left.shape != right.shape:
        return {
            "status": "fail",
            "row_count": int(left.size),
            "mismatch_count": int(max(left.size, right.size)),
            "max_abs_diff": float("nan"),
            "max_rel_diff": float("nan"),
            "exact_match": False,
        }
    finite = np.isfinite(left) & np.isfinite(right)
    close = np.isclose(left, right, atol=atol, rtol=rtol, equal_nan=True)
    absolute = np.abs(left[finite] - right[finite])
    scale = np.maximum(np.maximum(np.abs(left[finite]), np.abs(right[finite])), atol)
    relative = absolute / scale
    return {
        "status": "pass" if bool(close.all()) else "fail",
        "row_count": int(left.size),
        "mismatch_count": int((~close).sum()),
        "max_abs_diff": float(absolute.max()) if absolute.size else 0.0,
        "max_rel_diff": float(relative.max()) if relative.size else 0.0,
        "exact_match": bool(np.array_equal(left, right, equal_nan=True)),
    }


def ranking_stability(
    frame: pd.DataFrame,
    *,
    lags: Iterable[int],
    topks: Iterable[int],
    edge_topk: int,
    edge_start: int,
    edge_end: int,
) -> pd.DataFrame:
    source = frame.loc[:, ["datetime", "instrument", "prediction"]].copy()
    source["datetime"] = pd.to_datetime(source["datetime"])
    source["rank"] = source.groupby("datetime")["prediction"].rank(
        ascending=False, method="first"
    )
    by_date = {date: group.set_index("instrument") for date, group in source.groupby("datetime", sort=True)}
    dates = sorted(by_date)
    rows: list[dict[str, Any]] = []
    for lag in lags:
        for index in range(int(lag), len(dates)):
            previous, current = by_date[dates[index - int(lag)]], by_date[dates[index]]
            joined = previous[["prediction", "rank"]].join(
                current[["prediction", "rank"]], how="inner", lsuffix="_previous", rsuffix="_current"
            )
            base = {
                "datetime": dates[index],
                "lag": int(lag),
                "score_autocorrelation": _safe_corr(
                    joined["prediction_previous"], joined["prediction_current"], "pearson"
                ),
                "rank_autocorrelation": _safe_corr(
                    joined["rank_previous"], joined["rank_current"], "spearman"
                ),
            }
            for topk in topks:
                old = set(previous.index[previous["rank"].le(int(topk))])
                new = set(current.index[current["rank"].le(int(topk))])
                rows.append(
                    {
                        **base,
                        "metric": "retention",
                        "topk": int(topk),
                        "value": len(old & new) / int(topk),
                    }
                )
            old_top = set(previous.index[previous["rank"].le(edge_topk)])
            new_top = set(current.index[current["rank"].le(edge_topk)])
            changed = old_top ^ new_top
            edge = set(previous.index[previous["rank"].between(edge_start, edge_end)]) | set(
                current.index[current["rank"].between(edge_start, edge_end)]
            )
            rows.append(
                {
                    **base,
                    "metric": "edge_churn_share",
                    "topk": edge_topk,
                    "value": len(changed & edge) / len(changed) if changed else 0.0,
                }
            )
    return pd.DataFrame(rows)


def _daily_ic(frame: pd.DataFrame, score: str, target: str, minimum_pairs: int) -> pd.Series:
    def calculate(group: pd.DataFrame) -> float:
        valid = group[[score, target]].dropna()
        return _safe_corr(valid[score], valid[target]) if len(valid) >= minimum_pairs else float("nan")

    return frame.groupby("datetime", sort=True).apply(calculate, include_groups=False).dropna()


def _ic_summary(values: pd.Series, ddof: int) -> dict[str, Any]:
    standard = float(values.std(ddof=ddof)) if len(values) > ddof else float("nan")
    mean = float(values.mean()) if len(values) else float("nan")
    return {
        "mean_rank_ic": mean,
        "rank_icir": mean / standard if np.isfinite(standard) and standard > 0 else float("nan"),
        "positive_ic_ratio": float(values.gt(0).mean()) if len(values) else float("nan"),
        "valid_days": int(len(values)),
    }


def _quantile_bucket(values: pd.Series, count: int) -> pd.Series:
    ranks = values.rank(method="first", pct=True)
    bucket = np.minimum(np.floor(ranks * count).astype("Int64"), count - 1)
    return bucket.map({index: f"q{index + 1}" for index in range(count)}).astype("string")


def _feature_paths(config: dict[str, Any], root: Path) -> list[Path]:
    status = pd.read_csv(_resolve(root, config["parents"]["matrix_partitions"]))
    passed = status.loc[status["status"].astype(str).eq("pass"), "output_path"]
    return [Path(value) for value in passed]


def _load_feature_slice(paths: list[Path], columns: set[str], dates: set[pd.Timestamp]) -> pd.DataFrame:
    import pyarrow.parquet as pq

    result: pd.DataFrame | None = None
    for path in paths:
        available = set(pq.read_schema(path).names)
        selected = sorted(columns & available)
        if not selected:
            continue
        part = pd.read_parquet(path, columns=["datetime", "instrument", *selected])
        part["datetime"] = pd.to_datetime(part["datetime"])
        part = part.loc[part["datetime"].isin(dates)]
        result = part if result is None else result.merge(part, on=["datetime", "instrument"], how="outer", validate="one_to_one")
    if result is None:
        raise ValueError("none of the diagnostic features exist in matrix partitions")
    return result


def _parent_fingerprint(config: dict[str, Any], root: Path, names: Iterable[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in names:
        path = _resolve(root, config["parents"][name])
        if not path.is_file():
            raise FileNotFoundError(f"required parent missing: {name}={path}")
        values[name] = sha256_file(path)
    return values


@dataclass(frozen=True)
class DiagnosticContext:
    root: Path
    config: dict[str, Any]
    config_path: Path
    smoke: bool = False

    @property
    def split_ids(self) -> list[str]:
        return list(self.config["split_ids"][:1] if self.smoke else self.config["split_ids"])


def _build_base(ctx: DiagnosticContext) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    config, root = ctx.config, ctx.root
    receipts = pd.read_csv(_resolve(root, config["parents"]["prediction_receipt"]))
    allowlists = pd.read_csv(_resolve(root, config["parents"]["factor_weights"]))
    allowlists = allowlists.loc[allowlists["method"].astype(str).eq("equal_weight")].copy()
    factor_sets = {
        split: allowlists.loc[allowlists["outer_split_id"].eq(split)].sort_values("feature_order")["factor_column"].astype(str).tolist()
        for split in ctx.split_ids
    }
    expected = config["expected_factor_counts"]
    for split, factors in factor_sets.items():
        if len(factors) != int(expected[split]) or len(factors) != len(set(factors)):
            raise ValueError(f"frozen factor count/order mismatch: {split}")
    if not ctx.smoke:
        union = set().union(*map(set, factor_sets.values()))
        intersection = set.intersection(*map(set, factor_sets.values()))
        if len(union) != int(config["expected_factor_union"]) or len(intersection) != int(config["expected_factor_intersection"]):
            raise ValueError("frozen factor union/intersection mismatch")

    base_inputs = _parent_fingerprint(
        config,
        root,
        ["prediction_receipt", "factor_weights", "matrix_partitions", "labels_runtime", "raw_market_cache"],
    )
    key = _json_hash(
        {
            "inputs": base_inputs,
            "splits": ctx.split_ids,
            "factors": factor_sets,
            "forward_returns": config["forward_returns"],
            "style_proxies": config["style_proxies"],
            "smoke": ctx.smoke,
        }
    )
    cache_dir = _resolve(root, config["cache"]["base_dir"]) / key
    cached = {split: cache_dir / f"{split}.parquet" for split in ctx.split_ids}
    if all(path.is_file() for path in cached.values()):
        return {split: pd.read_parquet(path) for split, path in cached.items()}, {"base_cache_key": key, "base_cache_hit": True, "factor_sets": factor_sets}

    all_predictions: dict[str, pd.DataFrame] = {}
    all_dates: set[pd.Timestamp] = set()
    for split in ctx.split_ids:
        row = receipts.loc[receipts["outer_split_id"].eq(split)]
        if len(row) != 1:
            raise ValueError(f"prediction receipt cardinality mismatch: {split}")
        path = Path(row.iloc[0]["runtime_path"])
        if sha256_file(path) != str(row.iloc[0]["prediction_sha256"]):
            raise ValueError(f"frozen prediction hash mismatch: {split}")
        prediction = pd.read_parquet(path).sort_values(["datetime", "instrument"], kind="mergesort")
        prediction["datetime"] = pd.to_datetime(prediction["datetime"])
        if ctx.smoke:
            keep = sorted(prediction["datetime"].unique())[:8]
            prediction = prediction.loc[prediction["datetime"].isin(keep)]
        if prediction.duplicated(["datetime", "instrument"]).any():
            raise ValueError(f"duplicate prediction keys: {split}")
        all_predictions[split] = prediction
        all_dates.update(prediction["datetime"].unique())

    price = pd.read_parquet(_resolve(root, config["parents"]["raw_market_cache"]), columns=["datetime", "instrument", config["forward_returns"]["price_column"]])
    returns = forward_returns_t1(price, config["forward_returns"]["horizons"], price_column=config["forward_returns"]["price_column"])
    del price
    returns = returns.loc[returns["datetime"].isin(all_dates)]
    labels = pd.read_parquet(_resolve(root, config["parents"]["labels_runtime"]), columns=["datetime", "instrument", config["forward_returns"]["frozen_label"]])
    labels["datetime"] = pd.to_datetime(labels["datetime"])
    labels = labels.loc[labels["datetime"].isin(all_dates)]
    style_columns = {
        config["style_proxies"]["liquidity_proxy"],
        config["style_proxies"]["volatility_proxy"],
        config["style_proxies"]["momentum_source"],
    }
    paths = _feature_paths(config, root)
    result: dict[str, pd.DataFrame] = {}
    cache_dir.mkdir(parents=True, exist_ok=True)
    for split, prediction in all_predictions.items():
        dates = set(prediction["datetime"].unique())
        features = _load_feature_slice(paths, set(factor_sets[split]) | style_columns, dates)
        base = prediction.merge(returns, on=["datetime", "instrument"], how="left", validate="one_to_one")
        base = base.merge(labels, on=["datetime", "instrument"], how="left", validate="one_to_one")
        base = base.merge(features, on=["datetime", "instrument"], how="left", validate="one_to_one")
        source = config["style_proxies"]["momentum_source"]
        base["momentum_proxy"] = 1.0 / base[source].replace(0, np.nan) - 1.0
        base.to_parquet(cached[split], index=False)
        result[split] = base
    (cache_dir / "cache_receipt.json").write_text(json.dumps({"cache_key": key, "inputs": base_inputs}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result, {"base_cache_key": key, "base_cache_hit": False, "factor_sets": factor_sets}


def _label_equivalence(base: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    label = config["forward_returns"]["frozen_label"]
    computed = base["return_20d_t1"]
    frozen = base[label]
    valid = computed.notna() & frozen.notna()
    check = prediction_equivalence(
        frozen[valid].to_numpy(),
        computed[valid].to_numpy(),
        atol=float(config["forward_returns"]["label_atol"]),
        rtol=float(config["forward_returns"]["label_rtol"]),
    )
    check["coverage"] = float(valid.mean())
    return check


def _model_paths(root: Path, config: dict[str, Any], split: str) -> tuple[Path, Path, dict[str, Any]]:
    receipts = pd.read_csv(_resolve(root, config["parents"]["model_receipt"]))
    row = receipts.loc[receipts["outer_split_id"].eq(split)]
    if len(row) != 1:
        raise ValueError(f"model receipt cardinality mismatch: {split}")
    model = Path(row.iloc[0]["runtime_path"])
    preprocessing = model.with_name(model.stem + "_preprocessing.json")
    preprocessing_receipts = pd.read_csv(_resolve(root, config["parents"]["preprocessing_receipt"]))
    preprocessing_row = preprocessing_receipts.loc[preprocessing_receipts["outer_split_id"].eq(split)]
    if len(preprocessing_row) != 1:
        raise ValueError(f"preprocessing receipt cardinality mismatch: {split}")
    receipt = row.iloc[0].to_dict()
    receipt["preprocessing_sha256"] = preprocessing_row.iloc[0]["preprocessing_sha256"]
    return model, preprocessing, receipt


def _transformed_features(base: pd.DataFrame, preprocessing_path: Path) -> tuple[np.ndarray, list[str], np.ndarray]:
    payload = json.loads(preprocessing_path.read_text(encoding="utf-8"))
    factors = list(payload["feature_names"])
    values = base[factors].to_numpy(dtype=float)
    values[~np.isfinite(values)] = np.nan
    eligible = ~np.isnan(values).all(axis=1)
    values = values[eligible]
    medians = np.asarray(payload["medians"], dtype=float)
    missing = np.isnan(values)
    values[missing] = np.take(medians, np.where(missing)[1])
    values = (values - np.asarray(payload["means"], dtype=float)) / np.sqrt(np.asarray(payload["variances"], dtype=float))
    return values, factors, eligible


def _model_equivalence(ctx: DiagnosticContext, split: str, base: pd.DataFrame) -> tuple[dict[str, Any], Any, np.ndarray, list[str], np.ndarray]:
    import lightgbm as lgb

    model_path, preprocessing_path, receipt = _model_paths(ctx.root, ctx.config, split)
    freeze = json.loads((_resolve(ctx.root, ctx.config["parents"]["release_freeze_dir"]) / f"{split}_lightgbm.json").read_text(encoding="utf-8"))
    if sha256_file(model_path) != str(receipt["model_binary_sha256"]) or receipt["model_binary_sha256"] != freeze["model_binary_sha256"]:
        raise ValueError(f"model hash mismatch: {split}")
    if sha256_file(preprocessing_path) != str(receipt["preprocessing_sha256"]):
        raise ValueError(f"preprocessing hash mismatch: {split}")
    values, factors, eligible = _transformed_features(base, preprocessing_path)
    sample_count = min(int(ctx.config["prediction_equivalence"]["sample_rows_per_split"]), len(values))
    indices = np.linspace(0, len(values) - 1, sample_count, dtype=int)
    booster = lgb.Booster(model_file=str(model_path))
    recomputed = booster.predict(values[indices], num_threads=int(ctx.config["resources"]["threads"]))
    official = base.loc[eligible, "prediction"].to_numpy(dtype=float)[indices]
    result = prediction_equivalence(
        official,
        recomputed,
        atol=float(ctx.config["prediction_equivalence"]["atol"]),
        rtol=float(ctx.config["prediction_equivalence"]["rtol"]),
    )
    result.update(
        {
            "outer_split_id": split,
            "model_sha256": sha256_file(model_path),
            "preprocessing_sha256": sha256_file(preprocessing_path),
            "feature_order_sha256": str(freeze["feature_order_sha256"]),
            "prediction_sha256": sha256_file(Path(pd.read_csv(_resolve(ctx.root, ctx.config["parents"]["prediction_receipt"])).loc[lambda x: x["outer_split_id"].eq(split), "runtime_path"].iloc[0])),
        }
    )
    return result, booster, values, factors, eligible


def _factor_structure(ctx: DiagnosticContext, factor_sets: dict[str, list[str]]) -> pd.DataFrame:
    taxonomy = yaml.safe_load(_resolve(ctx.root, ctx.config["taxonomy_config"]).read_text(encoding="utf-8"))
    inventory = pd.read_csv(_resolve(ctx.root, ctx.config["parents"]["factor_inventory"]))
    inventory = inventory.drop_duplicates("name").set_index("name")
    rows = []
    for split, factors in factor_sets.items():
        for order, factor in enumerate(factors):
            group = taxonomy["overrides"].get(factor, taxonomy["default_group"])
            if factor not in taxonomy["overrides"]:
                for rule in taxonomy["rules"]:
                    if re.search(rule["pattern"], factor, flags=re.IGNORECASE):
                        group = rule["group"]
                        break
            metadata = inventory.loc[factor] if factor in inventory.index else {}
            rows.append(
                {
                    "outer_split_id": split,
                    "feature_order": order,
                    "factor": factor,
                    "economic_group": group,
                    "source": metadata.get("source", "unknown"),
                    "source_category": metadata.get("category", "unknown"),
                    "definition": metadata.get("notes", ""),
                }
            )
    return pd.DataFrame(rows)


def _signal_and_concentration(ctx: DiagnosticContext, split: str, base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = ctx.config
    minimum = min(int(config["metrics"]["minimum_daily_pairs"]), 10 if ctx.smoke else 10**9)
    ddof = int(config["metrics"]["icir_ddof"])
    decay_rows = []
    for horizon in config["forward_returns"]["horizons"]:
        target = f"return_{int(horizon)}d_t1"
        summary = _ic_summary(_daily_ic(base, "prediction", target, minimum), ddof)
        ranked = base.assign(_rank=base.groupby("datetime")["prediction"].rank(ascending=False, method="first"))
        top = ranked.loc[ranked["_rank"].le(10)].groupby("datetime")[target].mean()
        universe = ranked.groupby("datetime")[target].mean()
        decay_rows.append({"outer_split_id": split, "horizon": int(horizon), **summary, "top10_mean_return": float(top.mean()), "top10_excess_return": float((top - universe).mean())})
    ranked = base.copy()
    ranked["rank"] = ranked.groupby("datetime")["prediction"].rank(ascending=False, method="first")
    ranked["rank_bucket"] = assign_rank_buckets(ranked["rank"], config["ranking"]["buckets"])
    target = "return_20d_t1"
    universe = ranked.groupby("datetime")[target].mean()
    concentration_rows = []
    for bucket, group in ranked.dropna(subset=["rank_bucket"]).groupby("rank_bucket", observed=True):
        daily = group.groupby("datetime")[target].mean()
        concentration_rows.append({"outer_split_id": split, "rank_bucket": bucket, "mean_forward_return_20d": float(daily.mean()), "mean_excess_return_20d": float((daily - universe).mean()), "valid_days": int(daily.notna().sum()), "mean_names": float(group.groupby("datetime").size().mean())})
    return pd.DataFrame(decay_rows), pd.DataFrame(concentration_rows)


def _conditional_ic(ctx: DiagnosticContext, split: str, base: pd.DataFrame, factors: list[str]) -> pd.DataFrame:
    config = ctx.config
    proxy_map = {
        "liquidity_proxy": config["style_proxies"]["liquidity_proxy"],
        "volatility_proxy": config["style_proxies"]["volatility_proxy"],
        "momentum_proxy": "momentum_proxy",
    }
    count = int(config["style_proxies"]["bucket_count"])
    minimum = 10 if ctx.smoke else int(config["metrics"]["minimum_daily_pairs"])
    rows = []
    work_columns = list(
        dict.fromkeys(["datetime", "return_20d_t1", *factors, *proxy_map.values()])
    )
    work = base[work_columns].copy()
    for proxy_name, column in proxy_map.items():
        work["_bucket"] = work.groupby("datetime")[column].transform(lambda values: _quantile_bucket(values, count))
        for factor in factors:
            for bucket, group in work.groupby("_bucket", observed=True):
                values = _daily_ic(group, factor, "return_20d_t1", minimum)
                rows.append({"outer_split_id": split, "factor": factor, "condition": proxy_name, "bucket": bucket, **_ic_summary(values, int(config["metrics"]["icir_ddof"]))})
    return pd.DataFrame(rows)


class _BoosterEstimator:
    def __init__(self, booster: Any, dates: np.ndarray):
        self.booster = booster
        self.dates = dates

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_BoosterEstimator":
        raise RuntimeError("Model Diagnostic V1 forbids model fitting")

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self.booster.predict(X, num_threads=1), dtype=float)


def _importance(ctx: DiagnosticContext, split: str, base: pd.DataFrame, booster: Any, values: np.ndarray, factors: list[str], eligible: np.ndarray) -> pd.DataFrame:
    builtin = pd.read_csv(_resolve(ctx.root, ctx.config["parents"]["builtin_feature_importance"]))
    builtin = builtin.loc[builtin["outer_split_id"].eq(split)].copy()
    rows = builtin[["outer_split_id", "factor", "importance_type", "importance"]].to_dict("records")
    if not ctx.config["permutation"]["enabled"]:
        return pd.DataFrame(rows)
    from sklearn.inspection import permutation_importance

    eligible_base = base.loc[eligible].reset_index(drop=True)
    dates = sorted(eligible_base["datetime"].unique())
    limit = min(int(ctx.config["permutation"]["sampled_dates_per_split"]), len(dates))
    chosen = set(np.asarray(dates)[np.linspace(0, len(dates) - 1, limit, dtype=int)])
    mask = eligible_base["datetime"].isin(chosen).to_numpy()
    X = values[mask]
    y = eligible_base.loc[mask, "return_20d_t1"].to_numpy(dtype=float)
    date_values = eligible_base.loc[mask, "datetime"].to_numpy()
    finite = np.isfinite(y)
    X, y, date_values = X[finite], y[finite], date_values[finite]
    estimator = _BoosterEstimator(booster, date_values)

    def scorer(model: _BoosterEstimator, features: np.ndarray, target: np.ndarray) -> float:
        pred = model.predict(features)
        scoring = pd.DataFrame({"datetime": date_values, "prediction": pred, "target": target})
        return float(_daily_ic(scoring, "prediction", "target", 10).mean())

    result = permutation_importance(
        estimator,
        X,
        y,
        scoring=scorer,
        n_repeats=int(ctx.config["permutation"]["repeats"]),
        random_state=int(ctx.config["permutation"]["random_seed"]),
        n_jobs=1,
    )
    for factor, mean, standard in zip(factors, result.importances_mean, result.importances_std):
        rows.append({"outer_split_id": split, "factor": factor, "importance_type": "daily_rank_ic_permutation", "importance": float(mean), "importance_std": float(standard)})
    return pd.DataFrame(rows)


def _shap_importance(ctx: DiagnosticContext, split: str, base: pd.DataFrame, booster: Any, values: np.ndarray, factors: list[str], eligible: np.ndarray) -> pd.DataFrame:
    if not ctx.config["shap"]["enabled"]:
        return pd.DataFrame()
    try:
        import shap
    except ImportError:
        return pd.DataFrame()
    limit = min(int(ctx.config["shap"]["maximum_rows_per_split"]), len(values))
    indices = np.linspace(0, len(values) - 1, limit, dtype=int)
    contributions = np.asarray(shap.TreeExplainer(booster).shap_values(values[indices]))
    if contributions.ndim == 3:
        contributions = contributions[0]
    rows = []
    for factor, importance in zip(factors, np.abs(contributions).mean(axis=0)):
        rows.append({"outer_split_id": split, "factor": factor, "importance_type": "mean_abs_shap", "importance": float(importance)})
    eligible_base = base.loc[eligible].reset_index(drop=True).iloc[indices]
    proxy_map = {"liquidity_proxy": ctx.config["style_proxies"]["liquidity_proxy"], "volatility_proxy": ctx.config["style_proxies"]["volatility_proxy"], "momentum_proxy": "momentum_proxy"}
    for proxy_name, column in proxy_map.items():
        buckets = _quantile_bucket(eligible_base[column], int(ctx.config["style_proxies"]["bucket_count"]))
        for bucket in buckets.dropna().unique():
            mask = buckets.eq(bucket).fillna(False).to_numpy(dtype=bool)
            for factor, importance in zip(factors, np.abs(contributions[mask]).mean(axis=0)):
                rows.append({"outer_split_id": split, "factor": factor, "importance_type": f"conditional_shap:{proxy_name}:{bucket}", "importance": float(importance)})
    return pd.DataFrame(rows)


def _p01_attribution(ctx: DiagnosticContext, decay: pd.DataFrame, concentration: pd.DataFrame) -> pd.DataFrame:
    directory = _resolve(ctx.root, ctx.config["parents"]["portfolio_output_dir"])
    performance = pd.read_csv(directory / "performance_summary.csv")
    performance = performance.loc[performance["portfolio_id"].eq("P01") & performance["outer_split_id"].isin(ctx.split_ids)].copy()
    rank20 = decay.loc[decay["horizon"].eq(20), ["outer_split_id", "mean_rank_ic", "rank_icir"]]
    top = concentration.loc[concentration["rank_bucket"].eq("rank_001_010"), ["outer_split_id", "mean_excess_return_20d"]]
    columns = ["outer_split_id", "total_return", "gross_return_approx", "benchmark_total_return", "annualized_excess_return", "average_daily_turnover", "cost_drag"]
    return performance[columns].merge(rank20, on="outer_split_id", how="left").merge(top, on="outer_split_id", how="left")


def _model_proxy_exposure(ctx: DiagnosticContext, bases: dict[str, pd.DataFrame]) -> pd.DataFrame:
    proxy_map = {
        "liquidity_proxy": ctx.config["style_proxies"]["liquidity_proxy"],
        "volatility_proxy": ctx.config["style_proxies"]["volatility_proxy"],
        "momentum_proxy": "momentum_proxy",
    }
    rows: list[dict[str, Any]] = []
    for split, base in bases.items():
        work = base[["datetime", "prediction", *proxy_map.values()]].copy()
        work["model_rank"] = work.groupby("datetime")["prediction"].rank(
            ascending=False, method="first"
        )
        for proxy_name, column in proxy_map.items():
            work["proxy_percentile"] = work.groupby("datetime")[column].rank(pct=True)
            for cohort, topk in [("Top10", 10), ("Top20", 20), ("Top50", 50), ("Top100", 100), ("Universe", None)]:
                selected = work if topk is None else work.loc[work["model_rank"].le(topk)]
                daily_percentile = selected.groupby("datetime")["proxy_percentile"].mean()
                daily_raw_median = selected.groupby("datetime")[column].median()
                rows.append(
                    {
                        "outer_split_id": split,
                        "cohort": cohort,
                        "topk": topk,
                        "proxy": proxy_name,
                        "proxy_source_column": column,
                        "mean_cross_sectional_percentile": float(daily_percentile.mean()),
                        "mean_daily_raw_median": float(daily_raw_median.mean()),
                        "valid_days": int(daily_percentile.notna().sum()),
                    }
                )
    return pd.DataFrame(rows)


def _qlib_capability_audit(ctx: DiagnosticContext) -> pd.DataFrame:
    repository = _resolve(ctx.root, ctx.config["qlib_repository"])
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, capture_output=True, text=True, check=False
    )
    observed_commit = result.stdout.strip()
    checks = [
        ("SignalRecord", "qlib/workflow/record_temp.py", "class SignalRecord"),
        ("SigAnaRecord", "qlib/workflow/record_temp.py", "class SigAnaRecord"),
        ("analysis_model", "qlib/contrib/report/analysis_model/__init__.py", "model_performance_graph"),
        ("TopkDropoutStrategy", "qlib/contrib/strategy/signal_strategy.py", "class TopkDropoutStrategy"),
        ("hold_thresh", "qlib/contrib/strategy/signal_strategy.py", "hold_thresh"),
        ("EnhancedIndexingStrategy", "qlib/contrib/strategy/signal_strategy.py", "class EnhancedIndexingStrategy"),
        ("StructuredCovEstimator", "qlib/model/riskmodel/structured.py", "class StructuredCovEstimator"),
        ("DoubleEnsemble", "qlib/contrib/model/double_ensemble.py", "class DoubleEnsemble"),
        ("Rolling components", "qlib/contrib/rolling/base.py", "class Rolling"),
        ("Online components", "qlib/workflow/online/manager.py", "class OnlineManager"),
    ]
    rows = []
    for component, relative, needle in checks:
        path = repository / relative
        available = path.is_file() and needle in path.read_text(encoding="utf-8", errors="replace")
        rows.append(
            {
                "component": component,
                "status": "available_in_pinned_qlib" if available else "not_available",
                "evidence_path": relative,
                "pinned_commit_expected": ctx.config["qlib_commit_sha"],
                "pinned_commit_observed": observed_commit,
                "commit_match": observed_commit == ctx.config["qlib_commit_sha"],
                "requires_qlib_upgrade": not available,
            }
        )
    return pd.DataFrame(rows)


def _runtime_provenance(base_meta: dict[str, Any]) -> dict[str, Any]:
    import lightgbm
    import sklearn

    try:
        import shap
        shap_version = shap.__version__
    except ImportError:
        shap_version = None
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scikit_learn_version": sklearn.__version__,
        "lightgbm_version": lightgbm.__version__,
        "shap_version": shap_version,
        **base_meta,
    }


def _hypotheses(decay: pd.DataFrame, concentration: pd.DataFrame, stability: pd.DataFrame, attribution: pd.DataFrame) -> str:
    lines = ["# Evidence-Based V2 Hypotheses", "", "> Historical diagnosis is not unbiased future evidence. split_003 has already been observed.", ""]
    if not concentration.empty:
        pivot = concentration.pivot(index="outer_split_id", columns="rank_bucket", values="mean_excess_return_20d")
        if {"rank_001_010", "rank_031_050"}.issubset(pivot.columns):
            delta = float((pivot["rank_001_010"] - pivot["rank_031_050"]).mean())
            if delta > 0:
                statement = f"Top 1-10 exceeded ranks 31-50 by an equal-split mean `{delta:.6f}` over the 20-day diagnostic return. A future Portfolio V2 protocol may preregister a concentrated-portfolio test; P01 remains unchanged."
            else:
                statement = f"Top 1-10 trailed ranks 31-50 by an equal-split mean `{abs(delta):.6f}` over the 20-day diagnostic return. Current evidence does not support a concentrated Top10 hypothesis; a future study should test ranking-shape stability before considering concentration."
            lines += ["## H1: Ranking concentration", "", statement, ""]
    if not stability.empty:
        five = stability.loc[
            stability["lag"].eq(5)
            & stability["metric"].eq("retention")
            & stability["topk"].eq(50),
            "value",
        ]
        if len(five):
            lines += ["## H2: Ranking persistence", "", f"Mean five-day Top50 retention was `{five.mean():.3f}`. A future protocol should test dropout/hold rules against P01 without treating this observed result as selection evidence.", ""]
    if not decay.empty:
        mean = decay.groupby("horizon")["mean_rank_ic"].mean()
        best = int(mean.idxmax()) if mean.notna().any() else 20
        lines += ["## H3: Signal horizon", "", f"The strongest observed equal-split mean Rank IC was at `{best}D`. A future protocol should test horizon/implementation alignment using new data, without changing the current five-day P01 rule here.", ""]
    if len(attribution) >= 3:
        holdout = attribution.loc[attribution["outer_split_id"].eq("split_003")]
        development = attribution.loc[attribution["outer_split_id"].isin(["split_001", "split_002"])]
        if not holdout.empty and not development.empty:
            delta = float(holdout["mean_rank_ic"].iloc[0] - development["mean_rank_ic"].mean())
            lines += ["## H4: Development-to-holdout attribution", "", f"split_003 20-day Rank IC differed from the development-split mean by `{delta:.6f}`. Model V2 work should preregister whether conditional or incremental feature contribution explains this change.", ""]
    return "\n".join(lines).rstrip() + "\n"


def run_model_diagnostics(ctx: DiagnosticContext) -> dict[str, Any]:
    config, root = ctx.config, ctx.root
    bases, base_meta = _build_base(ctx)
    structure = _factor_structure(ctx, base_meta["factor_sets"])
    core_key_inputs: dict[str, str] = {}
    for split in ctx.split_ids:
        model_path, preprocessing_path, _ = _model_paths(root, config, split)
        core_key_inputs[f"{split}:model"] = sha256_file(model_path)
        core_key_inputs[f"{split}:preprocessing"] = sha256_file(preprocessing_path)
    core_key = _json_hash(
        {
            "base_cache_key": base_meta["base_cache_key"],
            "model_inputs": core_key_inputs,
            "core_config": {
                name: config[name]
                for name in [
                    "metrics",
                    "ranking",
                    "permutation",
                    "prediction_equivalence",
                    "shap",
                    "style_proxies",
                ]
            },
            "diagnostic_runtime": {
                "lightgbm": _package_version("lightgbm"),
                "numpy": _package_version("numpy"),
                "scikit_learn": _package_version("scikit-learn"),
                "shap": _package_version("shap"),
            },
            "smoke": ctx.smoke,
        }
    )
    core_cache = _resolve(root, config["cache"]["core_dir"]) / core_key
    cache_names = ["equivalence", "decay", "concentration", "stability", "conditional", "importance"]
    core_cache_hit = all(
        (core_cache / f"{split}_{name}.parquet").is_file()
        for split in ctx.split_ids
        for name in cache_names
    )
    base_meta.update({"core_cache_key": core_key, "core_cache_hit": core_cache_hit})
    equivalence_rows, decay_parts, concentration_parts = [], [], []
    stability_parts, conditional_parts, importance_parts = [], [], []
    for split, base in bases.items():
        split_cache_hit = all(
            (core_cache / f"{split}_{name}.parquet").is_file()
            for name in cache_names
        )
        if split_cache_hit:
            cached = {
                name: pd.read_parquet(core_cache / f"{split}_{name}.parquet")
                for name in cache_names
            }
            equivalence_rows.extend(cached["equivalence"].to_dict("records"))
            decay_parts.append(cached["decay"])
            concentration_parts.append(cached["concentration"])
            stability_parts.append(cached["stability"])
            conditional_parts.append(cached["conditional"])
            importance_parts.append(cached["importance"])
            continue
        label_check = _label_equivalence(base, config)
        model_check, booster, values, factors, eligible = _model_equivalence(ctx, split, base)
        model_check.update({f"label_{key}": value for key, value in label_check.items()})
        split_equivalence = pd.DataFrame([model_check])
        equivalence_rows.append(model_check)
        decay, concentration = _signal_and_concentration(ctx, split, base)
        decay_parts.append(decay)
        concentration_parts.append(concentration)
        stability = ranking_stability(base, lags=config["ranking"]["stability_lags"], topks=config["ranking"]["retention_topk"], edge_topk=int(config["ranking"]["edge_topk"]), edge_start=int(config["ranking"]["edge_band_start"]), edge_end=int(config["ranking"]["edge_band_end"]))
        stability.insert(0, "outer_split_id", split)
        stability_parts.append(stability)
        split_conditional = _conditional_ic(ctx, split, base, factors)
        conditional_parts.append(split_conditional)
        split_importance = _importance(ctx, split, base, booster, values, factors, eligible)
        shap_frame = _shap_importance(ctx, split, base, booster, values, factors, eligible)
        if not shap_frame.empty:
            split_importance = pd.concat([split_importance, shap_frame], ignore_index=True)
        importance_parts.append(split_importance)
        core_cache.mkdir(parents=True, exist_ok=True)
        for name, frame in {
            "equivalence": split_equivalence,
            "decay": decay,
            "concentration": concentration,
            "stability": stability,
            "conditional": split_conditional,
            "importance": split_importance,
        }.items():
            frame.to_parquet(core_cache / f"{split}_{name}.parquet", index=False)
    if not core_cache_hit:
        (core_cache / "cache_receipt.json").write_text(
            json.dumps(
                {"cache_key": core_key, "base_cache_key": base_meta["base_cache_key"], "model_inputs": core_key_inputs},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    equivalence = pd.DataFrame(equivalence_rows)
    decay = pd.concat(decay_parts, ignore_index=True)
    concentration = pd.concat(concentration_parts, ignore_index=True)
    stability = pd.concat(stability_parts, ignore_index=True)
    conditional = pd.concat(conditional_parts, ignore_index=True)
    importance = pd.concat(importance_parts, ignore_index=True)
    attribution = _p01_attribution(ctx, decay, concentration)
    proxy_exposure = _model_proxy_exposure(ctx, bases)
    qlib_audit = _qlib_capability_audit(ctx)
    external = audit_external_style_capability(config["external_style"], project_root=root)
    provenance = _runtime_provenance(base_meta)
    shap_ready = provenance["shap_version"] == str(config["shap"]["required_version"])
    contracts = pd.DataFrame(
        [
            {"check_name": "stage_identity", "status": "pass" if config["stage_id"] == "post_model_diagnostics_v1" else "fail", "severity": "critical", "observed_value": config["stage_id"], "required_value": "post_model_diagnostics_v1"},
            {"check_name": "governance_no_mutation", "status": "pass" if not any(config["governance"][key] for key in ["model_retrained", "predictions_regenerated", "features_reselected", "portfolio_rule_changed"]) else "fail", "severity": "critical", "observed_value": "frozen_read_only", "required_value": "frozen_read_only"},
            {"check_name": "prediction_equivalence", "status": "pass" if equivalence["status"].eq("pass").all() else "fail", "severity": "critical", "observed_value": int(equivalence["mismatch_count"].sum()), "required_value": 0},
            {"check_name": "label_20d_equivalence", "status": "pass" if equivalence["label_status"].eq("pass").all() else "fail", "severity": "critical", "observed_value": int(equivalence["label_mismatch_count"].sum()), "required_value": 0},
            {"check_name": "shap_runtime", "status": "pass" if shap_ready else "warning", "severity": "optional", "observed_value": provenance["shap_version"], "required_value": config["shap"]["required_version"]},
            {"check_name": "external_pit_style", "status": "pass" if external.iloc[0]["external_style_extension_status"] == "available" else "warning", "severity": "optional", "observed_value": external.iloc[0]["external_style_extension_status"], "required_value": "available_or_optional"},
            {"check_name": "historical_evidence_boundary", "status": "pass", "severity": "critical", "observed_value": "historical_diagnosis", "required_value": "not_unbiased_future_evidence"},
        ]
    )
    hypotheses = _hypotheses(decay, concentration, stability, attribution)
    report_lines = [
            "# Model Diagnostic V1",
            "",
            "## Status",
            "",
            f"- Core diagnostic: `{'complete' if contracts.loc[contracts['severity'].eq('critical'), 'status'].eq('pass').all() else 'failed'}`",
            f"- Style attribution: `partial / waiting external PIT data` (`{external.iloc[0]['external_style_extension_status']}`)",
            f"- SHAP runtime: `{'ready' if shap_ready else 'not available in this runtime'}`",
            f"- Frozen base cache: `{base_meta['base_cache_key']}` (hit={base_meta['base_cache_hit']})",
            "- Historical diagnosis != unbiased future evidence; split_003 has already been observed.",
            "",
            "## Deliverables",
            "",
            "Factor structure, existing-PIT conditional IC, fixed ranking concentration, fixed signal decay, ranking stability/retention/edge churn, frozen LightGBM importance, permutation importance, optional SHAP summaries, and P01 prediction/portfolio/cost attribution are published as machine-readable tables.",
            "",
            "Liquidity, volatility, and momentum fields are explicitly proxies. They are not historical market capitalization, Size, or industry data.",
            "",
            "## Split Evidence",
            "",
            "| Split | 20D Rank IC | 20D ICIR | Top10 excess | P01 total | Benchmark total | Cost drag | Avg daily turnover |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    evidence = attribution.merge(
        decay.loc[decay["horizon"].eq(20), ["outer_split_id", "mean_rank_ic", "rank_icir"]],
        on="outer_split_id",
        how="left",
        suffixes=("", "_decay"),
    )
    for row in evidence.itertuples(index=False):
        rank_ic = getattr(row, "mean_rank_ic_decay", getattr(row, "mean_rank_ic", float("nan")))
        rank_icir = getattr(row, "rank_icir_decay", getattr(row, "rank_icir", float("nan")))
        report_lines.append(
            f"| {row.outer_split_id} | {rank_ic:.6f} | {rank_icir:.3f} | {row.mean_excess_return_20d:.6f} | {row.total_return:.4f} | {row.benchmark_total_return:.4f} | {row.cost_drag:.4f} | {row.average_daily_turnover:.4f} |"
        )
    report_lines += [
        "",
        "## Interpretation Boundary",
        "",
        "The tables diagnose the already-observed historical splits. They do not authorize factor deletion, model retraining, TopK/rebalance selection, or any change to P01. The hypotheses document contains only candidates for a separately preregistered V2 study.",
    ]
    report = "\n".join(report_lines) + "\n"
    output_dir = _resolve(root, config["smoke_output_dir"] if ctx.smoke else config["output_dir"])
    parent_manifest_paths = [_resolve(root, config["parents"][name]) for name in ["selection_manifest", "matrix_manifest", "labels_manifest", "lightgbm_release_manifest", "portfolio_manifest"]]
    with StageOutputPublisher(output_dir, OUTPUTS) as publisher:
        frames = {
            "conditional_factor_ic.csv": conditional,
            "contract_status.csv": contracts,
            "external_style_capability.csv": external,
            "factor_structure.csv": structure,
            "feature_importance.csv": importance,
            "model_proxy_exposure.csv": proxy_exposure,
            "p01_attribution.csv": attribution,
            "prediction_equivalence.csv": equivalence,
            "ranking_concentration.csv": concentration,
            "ranking_stability.csv": stability,
            "qlib_capability_audit.csv": qlib_audit,
            "signal_decay.csv": decay,
        }
        for name, frame in frames.items():
            frame.to_csv(publisher.path(name), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("runtime_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("model_diagnostic_report.md").write_text(report, encoding="utf-8")
        publisher.path("v2_hypotheses.md").write_text(hypotheses, encoding="utf-8")
        output_files = [publisher.path(name) for name in OUTPUTS if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(project_root=root, stage_id=config["stage_id"], config=config, output_dir=publisher.staging_dir, output_files=output_files, code_state=capture_code_state(root), input_manifest_paths=parent_manifest_paths, start_date=min(frame["datetime"].min() for frame in bases.values()), end_date=max(frame["datetime"].max() for frame in bases.values()), contract_paths=[publisher.path("contract_status.csv")], require_complete_parents=True)
        publisher.publish()
    return {"output_dir": output_dir, "contracts": contracts, "provenance": provenance}
