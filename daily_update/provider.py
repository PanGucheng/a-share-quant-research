from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from daily_update.sources.community import CommunityRelease
from data_source_audit.normalizers import normalize_baostock
from factor_research.factor_library import BASE_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _community_anchor(
    provider: Path,
    instruments: list[str],
    anchor: date,
) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(
        instruments,
        ["$close", "$factor"],
        start_time=(anchor - timedelta(days=60)).isoformat(),
        end_time=anchor.isoformat(),
        freq="day",
    ).reset_index()
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["raw_close"] = pd.to_numeric(
        frame["$close"],
        errors="coerce",
    ) / pd.to_numeric(frame["$factor"], errors="coerce")
    return (
        frame[["datetime", "instrument", "raw_close", "$factor"]]
        .dropna()
        .sort_values(["instrument", "datetime"])
        .groupby("instrument", as_index=False)
        .tail(1)
        .set_index("instrument")
    )


def bridge_baostock_to_community(
    raw: pd.DataFrame,
    anchor: pd.DataFrame,
) -> pd.DataFrame:
    normalized = normalize_baostock(raw)
    rows: list[dict[str, object]] = []
    for instrument, group in normalized.groupby("instrument", sort=True):
        prior_close = (
            float(anchor.loc[instrument, "raw_close"])
            if instrument in anchor.index
            else np.nan
        )
        prior_factor = (
            float(anchor.loc[instrument, "$factor"])
            if instrument in anchor.index
            else np.nan
        )
        for item in group.sort_values("date").itertuples(index=False):
            raw_close = float(item.price_raw_close)
            preclose = float(item.price_raw_preclose)
            if np.isfinite(prior_close) and np.isfinite(prior_factor) and preclose > 0:
                factor = prior_factor * prior_close / preclose
                bridge_mode = "community_anchor_preclose_bridge"
            elif raw_close > 0:
                factor = 1.0 / raw_close
                bridge_mode = "new_listing_first_close_base"
            else:
                continue
            volume = float(item.volume_shares)
            amount = float(item.amount_cny)
            row = {
                "date": pd.Timestamp(item.date),
                "symbol": instrument,
                "open": float(item.price_raw_open) * factor,
                "high": float(item.price_raw_high) * factor,
                "low": float(item.price_raw_low) * factor,
                "close": raw_close * factor,
                "volume": volume / (factor * 100.0),
                "amount": amount / 1000.0,
                "factor": factor,
                "vwap": (amount / volume * factor) if volume > 0 else np.nan,
                "raw_open": float(item.price_raw_open),
                "raw_high": float(item.price_raw_high),
                "raw_low": float(item.price_raw_low),
                "raw_close": raw_close,
                "raw_volume": volume,
                "raw_amount": amount,
                "bridge_mode": bridge_mode,
            }
            rows.append(row)
            prior_close, prior_factor = raw_close, factor
    return pd.DataFrame(rows).sort_values(["symbol", "date"]).reset_index(drop=True)


def build_fallback_provider(
    community_provider: Path,
    bridged: pd.DataFrame,
    target: date,
    release: CommunityRelease,
    cache_dir: Path,
    qlib_source: Path,
) -> Path:
    final = cache_dir / "providers" / f"{target.isoformat()}_baostock_from_{release.tag}"
    if (final / "calendars/day.txt").is_file():
        last = (final / "calendars/day.txt").read_text(encoding="utf-8").splitlines()[-1]
        if last == target.isoformat():
            return final
    final.parent.mkdir(parents=True, exist_ok=True)
    stage = final.parent / f".{final.name}.building"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(community_provider, stage)
    with tempfile.TemporaryDirectory(prefix="daily_update_csv_", dir=str(cache_dir)) as tmp:
        csv_dir = Path(tmp)
        dump_columns = [
            "date",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "factor",
            "vwap",
        ]
        for symbol, frame in bridged.groupby("symbol"):
            frame[dump_columns].to_csv(csv_dir / f"{symbol.lower()}.csv", index=False)
        command = [
            sys.executable,
            str(qlib_source / "scripts/dump_bin.py"),
            "dump_update",
            "--data_path",
            str(csv_dir),
            "--qlib_dir",
            str(stage),
            "--freq",
            "day",
            "--max_workers",
            "4",
            "--include_fields",
            "open,high,low,close,volume,amount,factor,vwap",
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(qlib_source), environment.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        subprocess.run(command, check=True, cwd=PROJECT_ROOT, env=environment)
    stage.replace(final)
    return final


def _load_raw(
    provider: Path,
    instruments: list[str],
    start: date,
    end: date,
) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(
        instruments,
        BASE_FIELDS,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        freq="day",
    ).reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame.sort_values(["instrument", "datetime"]).reset_index(drop=True)
