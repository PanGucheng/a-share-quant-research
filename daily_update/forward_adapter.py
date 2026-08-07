from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from research_validation.feature_matrix import file_sha256


QLIB_COLUMNS = ("open", "high", "low", "close", "volume", "amount")
FORWARD_COLUMNS = (
    "datetime",
    "instrument",
    "$open",
    "$high",
    "$low",
    "$close",
    "$volume",
    "$amount",
)


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _file_created_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_ctime, timezone.utc).isoformat()


def prepare_forward_inputs(
    daily_update_dir: str | Path,
    *,
    decision_date: str,
) -> dict[str, str]:
    """Adapt one ready Daily Data Update output to the existing Forward schema."""

    target = Path(daily_update_dir)
    summary_path = target / "summary.json"
    daily_path = target / "baostock_qlib_daily.csv"
    feature_path = target / "feature_snapshot.csv"
    for path in (summary_path, daily_path, feature_path):
        if not path.is_file():
            raise FileNotFoundError(f"Daily Data Update input is missing: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "ready" or summary.get("target_date") != decision_date:
        raise ValueError("Daily Data Update summary is not ready for the decision date")
    if int(summary.get("factor_count", 0)) != 52:
        raise ValueError("Daily Data Update summary does not contain 52 factors")

    features = pd.read_csv(feature_path, usecols=["datetime", "instrument"])
    features["datetime"] = pd.to_datetime(features["datetime"], errors="raise").dt.date
    features["instrument"] = features["instrument"].astype(str).str.upper()
    decision = date.fromisoformat(decision_date)
    if features.empty or not features["datetime"].eq(decision).all():
        raise ValueError("Feature snapshot does not contain exactly the decision date")
    if features.duplicated(["datetime", "instrument"]).any():
        raise ValueError("Feature snapshot contains duplicate instruments")
    feature_instruments = set(features["instrument"])

    daily = pd.read_csv(daily_path)
    required = {"date", "symbol", *QLIB_COLUMNS}
    missing = sorted(required - set(daily.columns))
    if missing:
        raise ValueError(f"Daily Qlib data is missing columns: {missing}")
    raw = daily[["date", "symbol", *QLIB_COLUMNS]].rename(
        columns={
            "date": "datetime",
            "symbol": "instrument",
            **{name: f"${name}" for name in QLIB_COLUMNS},
        }
    )
    raw["datetime"] = pd.to_datetime(raw["datetime"], errors="raise").dt.date
    raw["instrument"] = raw["instrument"].astype(str).str.upper()
    raw = raw.loc[raw["instrument"].isin(feature_instruments)].copy()
    if raw.empty or not raw["datetime"].eq(decision).all():
        raise ValueError("Daily Qlib data does not contain exactly the decision date")
    if raw.duplicated(["datetime", "instrument"]).any():
        raise ValueError("Daily Qlib data contains duplicate instruments")
    raw[list(FORWARD_COLUMNS[2:])] = raw[list(FORWARD_COLUMNS[2:])].apply(
        pd.to_numeric, errors="coerce"
    )
    suspended = (
        raw[["$volume", "$amount"]].isna().all(axis=1)
        & raw[["$open", "$high", "$low", "$close"]].notna().all(axis=1)
        & raw["$open"].eq(raw["$high"])
        & raw["$open"].eq(raw["$low"])
        & raw["$open"].eq(raw["$close"])
    )
    suspended_instruments = sorted(raw.loc[suspended, "instrument"])
    raw.loc[suspended, ["$volume", "$amount"]] = 0.0
    if raw[list(FORWARD_COLUMNS[2:])].isna().any().any():
        raise ValueError("Daily Qlib data contains incomplete Forward OHLCVA")
    if set(raw["instrument"]) != feature_instruments:
        raise ValueError("Daily Qlib data does not exactly cover feature instruments")
    raw = raw[list(FORWARD_COLUMNS)].sort_values("instrument").reset_index(drop=True)

    first_seen = str(
        summary.get("raw_snapshot_first_seen_at") or _file_created_at(daily_path)
    )
    feature_created = str(
        summary.get("feature_snapshot_created_at") or _file_created_at(feature_path)
    )
    first_seen_time = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
    feature_created_time = datetime.fromisoformat(
        feature_created.replace("Z", "+00:00")
    )
    if first_seen_time.tzinfo is None or feature_created_time.tzinfo is None:
        raise ValueError("Daily input timestamps must be timezone-aware")
    if feature_created_time < first_seen_time:
        raise ValueError("Daily feature snapshot predates the raw snapshot")

    raw_output = target / "forward_raw_snapshot.csv"
    metadata_output = target / "forward_input_metadata.json"
    _atomic_csv(raw_output, raw)
    metadata = {
        "decision_date": decision_date,
        "raw_path": str(raw_output.resolve()),
        "raw_sha256": file_sha256(raw_output),
        "raw_row_count": len(raw),
        "suspended_zero_fill_count": len(suspended_instruments),
        "suspended_zero_fill_instruments": suspended_instruments,
        "raw_snapshot_first_seen_at": first_seen_time.isoformat(),
        "raw_timestamp_source": (
            "daily_summary" if summary.get("raw_snapshot_first_seen_at") else "source_file_creation_time"
        ),
        "feature_path": str(feature_path.resolve()),
        "feature_sha256": file_sha256(feature_path),
        "feature_snapshot_created_at": feature_created_time.isoformat(),
        "factor_count": 52,
        "label_read_count": 0,
    }
    _atomic_json(metadata_output, metadata)
    return {
        "raw_path": str(raw_output.resolve()),
        "feature_path": str(feature_path.resolve()),
        "raw_snapshot_first_seen_at": first_seen_time.isoformat(),
        "feature_snapshot_created_at": feature_created_time.isoformat(),
        "metadata_path": str(metadata_output.resolve()),
    }
