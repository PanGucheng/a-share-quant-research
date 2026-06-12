from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

import qlib
from qlib.config import C
from qlib.data import D

from data_quality.checker import read_instrument_ranges
from data_quality.rules import normalize_feature_frame
from tradability.report import write_outputs


OUTPUT_COLUMNS = [
    "datetime",
    "instrument",
    "is_suspended",
    "suspension_status",
    "is_limit_up",
    "is_limit_down",
    "is_one_price_limit_up",
    "is_one_price_limit_down",
    "limit_status",
    "liquidity_source",
    "liquidity_value",
    "liquidity_bucket",
    "is_low_liquidity",
    "listed_days",
    "is_new_listing",
    "has_price_anomaly",
    "has_volume_anomaly",
    "has_core_missing",
    "data_quality_status",
    "can_buy",
    "can_sell",
    "tradability_score",
    "disabled_reason",
]

CORE_DQ_FILES = ["row_issues.csv", "instrument_availability.csv", "date_coverage.csv"]
OPTIONAL_DQ_FILES = ["price_anomalies.csv", "volume_amount_anomalies.csv", "expected_missing_spans.csv"]
CORE_PRICE_FIELDS = ["open", "high", "low", "close", "volume"]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid config file: {path}")
    return config


def apply_overrides(config: dict[str, Any], args) -> dict[str, Any]:
    tradability = config.setdefault("tradability", {})
    qlib_conf = config.setdefault("qlib", {})
    for key in ["market", "start_time", "end_time", "output_dir", "data_quality_dir"]:
        value = getattr(args, key, None)
        if value is not None:
            tradability[key] = value
    if getattr(args, "provider_uri", None) is not None:
        qlib_conf["provider_uri"] = args.provider_uri
    return config


def output_dir(config: dict[str, Any]) -> Path:
    scope = config["tradability"]
    run_name = f"{scope['market']}_{scope['start_time']}_{scope['end_time']}".replace(":", "").replace("/", "-")
    return Path(scope["output_dir"]) / run_name


def init_qlib(config: dict[str, Any]) -> None:
    qlib_conf = config["qlib"]
    qlib.init(provider_uri=qlib_conf["provider_uri"], region=qlib_conf.get("region", "cn"))
    C.kernels = 1
    C.joblib_backend = "sequential"


def choose_liquidity_source(frame: pd.DataFrame, warnings: list[str]) -> tuple[pd.DataFrame, str]:
    result = frame.copy()
    if "amount" in result.columns and result["amount"].notna().any():
        result["liquidity_value"] = result["amount"]
        return result, "amount"
    if {"close", "volume"}.issubset(result.columns) and result[["close", "volume"]].notna().all(axis=1).any():
        result["liquidity_value"] = result["close"] * result["volume"]
        return result, "close_volume"
    result["liquidity_value"] = np.nan
    warnings.append("No usable amount or close*volume liquidity source.")
    return result, "unavailable"


def load_features(config: dict[str, Any]) -> tuple[pd.DataFrame, str, list[str]]:
    scope = config["tradability"]
    freq = config.get("qlib", {}).get("freq", "day")
    fields = ["$open", "$high", "$low", "$close", "$volume"]
    warnings: list[str] = []
    raw = D.features(D.instruments(scope["market"]), fields, start_time=scope["start_time"], end_time=scope["end_time"], freq=freq)
    frame = normalize_feature_frame(raw)

    try:
        amount = D.features(
            D.instruments(scope["market"]),
            ["$amount"],
            start_time=scope["start_time"],
            end_time=scope["end_time"],
            freq=freq,
        )
        amount = normalize_feature_frame(amount)[["instrument", "datetime", "amount"]]
        frame = frame.merge(amount, on=["instrument", "datetime"], how="left")
    except Exception as exc:
        warnings.append(f"amount field unavailable; fallback to close*volume. detail={exc}")
        frame["amount"] = np.nan

    if frame.empty:
        raise ValueError("Qlib returned no feature rows for the requested provider/market/date range.")

    frame, liquidity_source = choose_liquidity_source(frame, warnings)
    return frame.sort_values(["datetime", "instrument"]).reset_index(drop=True), liquidity_source, warnings


def read_required_csv(path: Path, name: str) -> pd.DataFrame:
    file_path = path / name
    if not file_path.exists():
        raise FileNotFoundError(f"Required data quality file is missing: {file_path}")
    return pd.read_csv(file_path)


def load_data_quality(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[str]]:
    dq_dir = Path(config["tradability"]["data_quality_dir"])
    if not dq_dir.exists():
        raise FileNotFoundError(f"Data quality directory does not exist: {dq_dir}")
    tables = {name: read_required_csv(dq_dir, name) for name in CORE_DQ_FILES}
    warnings = []
    for name in OPTIONAL_DQ_FILES:
        file_path = dq_dir / name
        if file_path.exists():
            tables[name] = pd.read_csv(file_path)
        else:
            tables[name] = pd.DataFrame()
            warnings.append(f"Optional data quality file missing: {file_path}")
    return tables, warnings


def normalize_issue_dates(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result["datetime"] = pd.to_datetime(result["datetime"])
    return result


def build_quality_flags(labels: pd.DataFrame, dq: dict[str, pd.DataFrame], warnings: list[str]) -> pd.DataFrame:
    result = labels.copy()
    for column in ["has_price_anomaly", "has_volume_anomaly"]:
        result[column] = False
    result["data_quality_status"] = "ok"

    price = normalize_issue_dates(dq.get("price_anomalies.csv", pd.DataFrame()))
    volume = normalize_issue_dates(dq.get("volume_amount_anomalies.csv", pd.DataFrame()))
    if not price.empty:
        keys = price[["instrument", "datetime"]].drop_duplicates()
        result = result.merge(keys.assign(has_price_anomaly=True), on=["instrument", "datetime"], how="left", suffixes=("", "_dq"))
        result["has_price_anomaly"] = result["has_price_anomaly_dq"].fillna(False).astype(bool)
        result = result.drop(columns=["has_price_anomaly_dq"])
    else:
        warnings.append("price_anomalies unavailable or empty; price anomaly flags may be incomplete.")
    if not volume.empty:
        keys = volume[["instrument", "datetime"]].drop_duplicates()
        result = result.merge(keys.assign(has_volume_anomaly=True), on=["instrument", "datetime"], how="left", suffixes=("", "_dq"))
        result["has_volume_anomaly"] = result["has_volume_anomaly_dq"].fillna(False).astype(bool)
        result = result.drop(columns=["has_volume_anomaly_dq"])
    else:
        warnings.append("volume_amount_anomalies unavailable or empty; volume anomaly flags may be incomplete.")

    if warnings:
        result.loc[:, "data_quality_status"] = np.where(
            result["has_price_anomaly"] | result["has_volume_anomaly"], "issue", "ok"
        )
    return result


def listing_start_map(provider_uri: Path) -> dict[str, pd.Timestamp]:
    all_ranges = read_instrument_ranges(provider_uri / "instruments" / "all.txt")
    if all_ranges.empty:
        return {}
    return all_ranges.groupby("instrument")["start_time"].min().to_dict()


def board_limit_pct(instrument: str, rules: dict[str, Any]) -> float | None:
    code = str(instrument).upper()
    if code.startswith("BJ"):
        return float(rules["bse_limit_pct"])
    if code.startswith("SH688") or code.startswith("SZ300"):
        return float(rules["growth_board_limit_pct"])
    if code.startswith("SH") or code.startswith("SZ"):
        return float(rules["main_board_limit_pct"])
    return None


def add_limit_flags(frame: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    result = frame.sort_values(["instrument", "datetime"]).copy()
    result["prev_close"] = result.groupby("instrument")["close"].shift(1)
    result["limit_pct"] = result["instrument"].map(lambda inst: board_limit_pct(inst, rules))
    tolerance = float(rules["price_tolerance"])
    one_price_tolerance = float(rules["one_price_tolerance"])
    up_threshold = result["prev_close"] * (1 + result["limit_pct"] - tolerance)
    down_threshold = result["prev_close"] * (1 - result["limit_pct"] + tolerance)
    comparable = result[["prev_close", "limit_pct", "close", "high", "low", "open"]].notna().all(axis=1)
    result["is_limit_up"] = comparable & result["close"].ge(up_threshold) & result["high"].ge(up_threshold)
    result["is_limit_down"] = comparable & result["close"].le(down_threshold) & result["low"].le(down_threshold)
    one_price = (
        (result["open"] - result["high"]).abs().le(one_price_tolerance)
        & (result["high"] - result["low"]).abs().le(one_price_tolerance)
        & (result["low"] - result["close"]).abs().le(one_price_tolerance)
    )
    result["is_one_price_limit_up"] = result["is_limit_up"] & one_price
    result["is_one_price_limit_down"] = result["is_limit_down"] & one_price
    unknown = ~comparable
    result["limit_status"] = "normal"
    result.loc[result["is_limit_up"], "limit_status"] = "limit_up"
    result.loc[result["is_limit_down"], "limit_status"] = "limit_down"
    result.loc[unknown, "limit_status"] = "unknown"
    return result


def assign_liquidity_buckets(frame: pd.DataFrame, rules: dict[str, Any], liquidity_source: str) -> pd.DataFrame:
    result = frame.copy()
    if liquidity_source == "unavailable":
        result["liquidity_source"] = "unavailable"
        result["liquidity_bucket"] = pd.NA
        result["is_low_liquidity"] = False
        return result
    bucket_count = int(rules["liquidity_buckets"])
    result["liquidity_bucket"] = result.groupby("datetime")["liquidity_value"].transform(
        lambda values: pd.qcut(values, bucket_count, labels=False, duplicates="drop") + 1
        if values.notna().sum() >= bucket_count
        else pd.Series(pd.NA, index=values.index)
    )
    result["liquidity_source"] = liquidity_source
    result["is_low_liquidity"] = result["liquidity_bucket"].le(int(rules["low_liquidity_bucket_max"])).fillna(False)
    return result


def build_reasons(row: pd.Series) -> str:
    reasons = []
    for reason, flag in [
        ("suspended", row["is_suspended"]),
        ("limit_up", row["is_limit_up"]),
        ("limit_down", row["is_limit_down"]),
        ("one_price_limit_up", row["is_one_price_limit_up"]),
        ("one_price_limit_down", row["is_one_price_limit_down"]),
        ("low_liquidity", row["is_low_liquidity"]),
        ("new_listing", row["is_new_listing"]),
        ("price_anomaly", row["has_price_anomaly"]),
        ("volume_anomaly", row["has_volume_anomaly"]),
        ("core_missing", row["has_core_missing"]),
    ]:
        if bool(flag):
            reasons.append(reason)
    if row["limit_status"] == "unknown":
        reasons.append("unknown_limit")
    if row["liquidity_source"] == "unavailable" or pd.isna(row["liquidity_bucket"]):
        reasons.append("unknown_liquidity")
    if row["data_quality_status"] == "quality_unavailable":
        reasons.append("quality_unavailable")
    return "|".join(dict.fromkeys(reasons))


def add_final_flags(frame: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    penalties = rules["score_penalties"]
    result["disabled_reason"] = result.apply(build_reasons, axis=1)
    result["can_buy"] = ~(
        result["is_suspended"]
        | result["is_limit_up"]
        | result["is_one_price_limit_up"]
        | result["is_low_liquidity"]
        | result["is_new_listing"]
        | result["has_price_anomaly"]
        | result["has_volume_anomaly"]
        | result["has_core_missing"]
        | result["limit_status"].eq("unknown")
        | result["liquidity_source"].eq("unavailable")
        | result["liquidity_bucket"].isna()
    )
    result["can_sell"] = ~(
        result["is_suspended"]
        | result["is_limit_down"]
        | result["is_one_price_limit_down"]
        | result["has_price_anomaly"]
        | result["has_volume_anomaly"]
        | result["has_core_missing"]
        | result["limit_status"].eq("unknown")
        | result["liquidity_source"].eq("unavailable")
        | result["liquidity_bucket"].isna()
    )

    score = pd.Series(100.0, index=result.index)
    score -= result["is_suspended"].astype(float) * float(penalties["suspended"])
    score -= (result["is_limit_up"] | result["is_limit_down"]).astype(float) * float(penalties["limit"])
    score -= (result["is_one_price_limit_up"] | result["is_one_price_limit_down"]).astype(float) * float(
        penalties["one_price_limit"]
    )
    score -= result["is_low_liquidity"].astype(float) * float(penalties["low_liquidity"])
    score -= result["is_new_listing"].astype(float) * float(penalties["new_listing"])
    score -= result["has_price_anomaly"].astype(float) * float(penalties["price_anomaly"])
    score -= result["has_volume_anomaly"].astype(float) * float(penalties["volume_anomaly"])
    score -= result["has_core_missing"].astype(float) * float(penalties["core_missing"])
    unknown = result["limit_status"].eq("unknown") | result["liquidity_source"].eq("unavailable") | result[
        "liquidity_bucket"
    ].isna()
    score -= unknown.astype(float) * float(penalties["unknown"])
    result["tradability_score"] = score.clip(lower=0, upper=100).round(2)
    return result


def build_labels(config: dict[str, Any], logger: logging.Logger) -> tuple[pd.DataFrame, str, list[str]]:
    init_qlib(config)
    dq, dq_warnings = load_data_quality(config)
    frame, liquidity_source, warnings = load_features(config)
    warnings.extend(dq_warnings)
    rules = config["rules"]

    frame = add_limit_flags(frame, rules)
    frame = assign_liquidity_buckets(frame, rules, liquidity_source)
    frame["has_core_missing"] = frame[CORE_PRICE_FIELDS].isna().any(axis=1)
    frame["is_suspended"] = frame["has_core_missing"] | frame["volume"].fillna(0).eq(0)
    frame["suspension_status"] = np.where(frame["is_suspended"], "suspected_suspended", "active")

    starts = listing_start_map(Path(config["qlib"]["provider_uri"]))
    first_valid = frame.loc[~frame["has_core_missing"]].groupby("instrument")["datetime"].min().to_dict()
    listed_start = frame["instrument"].map(lambda inst: starts.get(str(inst).upper(), first_valid.get(inst, pd.NaT)))
    frame["listed_days"] = (frame["datetime"] - pd.to_datetime(listed_start)).dt.days
    frame["is_new_listing"] = frame["listed_days"].lt(int(rules["min_listed_days"])).fillna(True)

    frame = build_quality_flags(frame, dq, warnings)
    if any("unavailable" in warning or "missing" in warning for warning in warnings):
        frame.loc[frame["data_quality_status"].eq("ok"), "data_quality_status"] = "ok"

    labels = add_final_flags(frame, rules)
    labels = labels[OUTPUT_COLUMNS].sort_values(["datetime", "instrument"]).reset_index(drop=True)
    if labels.empty:
        raise ValueError("Tradability label result is empty; check provider, market, and date range.")
    logger.info("Built tradability labels: rows=%s liquidity_source=%s", len(labels), liquidity_source)
    return labels, liquidity_source, warnings


def run(config: dict[str, Any], logger: logging.Logger) -> Path:
    out = output_dir(config)
    labels, liquidity_source, warnings = build_labels(config, logger)
    write_outputs(out, labels, config, liquidity_source, warnings)
    with (out / "resolved_config.yaml").open("w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)
    return out
