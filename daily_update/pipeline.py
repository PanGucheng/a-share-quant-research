from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from data_source_audit.normalizers import normalize_baostock
from data_source_audit.sources.baostock import collect_daily_adjust_factor, collect_daily_all
from factor_research.alpha101_source import Alpha101SourceConfig, compute_alpha101_features
from factor_research.factor_library import BASE_FIELDS, add_basic_factors
from factor_research.ta_source import TaSourceConfig, compute_ta_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QLIB_SOURCE = Path("E:/qlib_prj/qlib_clone")
if QLIB_SOURCE.is_dir() and str(QLIB_SOURCE) not in sys.path:
    sys.path.insert(0, str(QLIB_SOURCE))
COMMUNITY_REPOSITORY = "https://github.com/chenditc/investment_data"
DEFAULT_CACHE = Path("E:/qlib_prj/qlib_data/daily_update_v1")
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/daily_data_update_v1"
DEFAULT_UNIVERSE = Path(
    "E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/"
    "instruments/all_stock_shsz_liquid2000.txt"
)
PREPROCESSING = (
    PROJECT_ROOT
    / "outputs/prospective_forward_candidate_v1/runtime/current/model/"
    "forward_candidate_preprocessing.json"
)
ALPHA158_TABLE = (
    PROJECT_ROOT
    / "outputs/alpha158_expression_frame_v1/full158_main_research/expression_table.csv"
)
ALPHA360_TABLE = (
    PROJECT_ROOT
    / "outputs/alpha360_expression_frame_v1/batch358/expression_table.csv"
)


@dataclass(frozen=True)
class CommunityRelease:
    tag: str
    target_trade_date: date
    manifest_url: str
    archive_url: str
    archive_size: int
    archive_sha256: str


@dataclass(frozen=True)
class DailyUpdateConfig:
    target_date: date
    cache_dir: Path = DEFAULT_CACHE
    output_dir: Path = DEFAULT_OUTPUT
    universe_file: Path = DEFAULT_UNIVERSE
    min_coverage: float = 0.95
    warmup_calendar_days: int = 450


class NotReady(RuntimeError):
    """The upstream daily payload is not published yet; retry is safe."""


def baostock_release_window_open(target: date, now: datetime | None = None) -> bool:
    """Wait for the documented K-line and adjustment-factor publication window."""

    shanghai = ZoneInfo("Asia/Shanghai")
    current = now.astimezone(shanghai) if now is not None else datetime.now(shanghai)
    return target < current.date() or (
        target == current.date() and current.time() >= time(18, 0)
    )


def _request(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "qlib-baseline-daily-update-v1"})
    return urllib.request.urlopen(request, timeout=60)


def latest_community_release() -> CommunityRelease:
    # The redirect is not rate limited like GitHub's anonymous API.
    with _request(f"{COMMUNITY_REPOSITORY}/releases/latest") as response:
        tag = response.geturl().rstrip("/").rsplit("/", 1)[-1]
    manifest_url = f"{COMMUNITY_REPOSITORY}/releases/download/{tag}/qlib_bin.manifest.json"
    with _request(manifest_url) as response:
        payload = json.load(response)
    digest = str(payload["archive_sha256"]).removeprefix("sha256:")
    return CommunityRelease(
        tag=str(payload["release_tag"]),
        target_trade_date=date.fromisoformat(str(payload["target_trade_date"])),
        manifest_url=manifest_url,
        archive_url=f"{COMMUNITY_REPOSITORY}/releases/download/{tag}/qlib_bin.tar.gz",
        archive_size=int(payload["archive_size_bytes"]),
        archive_sha256=digest,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_community_provider(release: CommunityRelease, cache_dir: Path) -> Path:
    root = cache_dir / "community" / release.tag
    ready = root / ".ready"
    if ready.is_file():
        provider = Path(ready.read_text(encoding="utf-8").strip())
        if (provider / "calendars/day.txt").is_file():
            return provider
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "qlib_bin.tar.gz"
    if not archive.is_file() or archive.stat().st_size != release.archive_size:
        partial = archive.with_suffix(".partial")
        with _request(release.archive_url) as response, partial.open("wb") as stream:
            shutil.copyfileobj(response, stream, length=1024 * 1024)
        partial.replace(archive)
    if _sha256(archive) != release.archive_sha256:
        raise ValueError("Community archive sha256 mismatch")
    extract_root = root / "extracted"
    if not extract_root.is_dir():
        stage = root / "extracting"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir()
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(stage, filter="data")
        stage.replace(extract_root)
    candidates = [extract_root, *[p for p in extract_root.rglob("calendars") if p.is_dir()]]
    provider = next(
        (p if p.name != "calendars" else p.parent for p in candidates if (p / "day.txt").is_file() or (p / "calendars/day.txt").is_file()),
        None,
    )
    if provider is None:
        raise ValueError("Community archive does not contain a Qlib provider")
    ready.write_text(str(provider.resolve()) + "\n", encoding="utf-8")
    return provider


def load_frozen_universe(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Frozen Strategy V1 universe is missing: {path}")
    instruments = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        symbol = line.split("\t", 1)[0].strip().upper()
        if symbol.startswith(("SH6", "SZ0", "SZ3")):
            instruments.append(symbol)
    if not instruments:
        raise ValueError("Frozen Strategy V1 universe is empty")
    return sorted(set(instruments))


def collect_baostock_range(start: date, end: date) -> tuple[pd.DataFrame, list[str]]:
    """Use one official batch request per calendar date, not one request per stock."""

    import baostock as bs

    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"BaoStock login failed: {login.error_code}:{login.error_msg}")
    frames: list[pd.DataFrame] = []
    failures: list[str] = []
    try:
        for current in pd.date_range(start, end, freq="D"):
            frame, status = collect_daily_all(current.date().isoformat())
            if status != "success":
                failures.append(f"{current.date().isoformat()}:{status}")
            elif not frame.empty:
                frames.append(frame)
    finally:
        bs.logout()
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), failures


def collect_baostock_factor_once(
    target: date, attempts: int = 2, retry_delay_seconds: int = 10
) -> tuple[pd.DataFrame, str]:
    """Low-frequency factor probe; tolerate one transient BaoStock socket error."""

    import baostock as bs

    last_status = "unavailable"
    for attempt in range(max(1, attempts)):
        login = bs.login()
        if login.error_code != "0":
            last_status = f"{login.error_code}:{login.error_msg}"
        else:
            try:
                frame, status = collect_daily_adjust_factor(target.isoformat())
                if status == "success":
                    return frame, status
                last_status = status
            finally:
                bs.logout()
        if attempt + 1 < attempts:
            time.sleep(retry_delay_seconds)
    return pd.DataFrame(), last_status


def validate_baostock_target(
    raw: pd.DataFrame,
    target: date,
    expected: list[str],
    min_coverage: float,
) -> dict[str, object]:
    if raw.empty:
        raise NotReady(f"BaoStock has not published {target.isoformat()} daily bars")
    normalized = normalize_baostock(raw)
    day = normalized.loc[normalized["date"].eq(pd.Timestamp(target))].copy()
    required = [
        "price_raw_open", "price_raw_high", "price_raw_low", "price_raw_close",
        "volume_shares", "amount_cny",
    ]
    complete = day[required].notna().all(axis=1) & day["is_trading"].astype(bool)
    covered = set(day.loc[complete, "instrument"])
    trading = set(day.loc[day["is_trading"].astype(bool), "instrument"])
    required_set = set(expected)
    missing_fields_while_trading = set(
        day.loc[day["is_trading"].astype(bool) & ~day[required].notna().all(axis=1), "instrument"]
    ).intersection(required_set)
    coverage = len(covered.intersection(expected)) / len(expected) if expected else 0.0
    if coverage < min_coverage:
        raise NotReady(
            f"BaoStock {target.isoformat()} coverage {coverage:.2%} is below {min_coverage:.2%}"
        )
    return {
        "expected_instruments": len(expected),
        "complete_instruments": len(covered.intersection(expected)),
        "normal_trading_instruments": len(trading.intersection(required_set)),
        "suspended_or_nontrading_instruments": len(required_set - trading),
        "missing_ohlcva_while_trading": len(missing_fields_while_trading),
        "coverage": coverage,
        "ohlcva_complete": not missing_fields_while_trading,
    }


def _community_anchor(provider: Path, instruments: list[str], anchor: date) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(
        instruments, ["$close", "$factor"], start_time=(anchor - timedelta(days=60)).isoformat(),
        end_time=anchor.isoformat(), freq="day",
    ).reset_index()
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["raw_close"] = pd.to_numeric(frame["$close"], errors="coerce") / pd.to_numeric(frame["$factor"], errors="coerce")
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
        prior_close = float(anchor.loc[instrument, "raw_close"]) if instrument in anchor.index else np.nan
        prior_factor = float(anchor.loc[instrument, "$factor"]) if instrument in anchor.index else np.nan
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
        dump_columns = ["date", "symbol", "open", "high", "low", "close", "volume", "amount", "factor", "vwap"]
        for symbol, frame in bridged.groupby("symbol"):
            frame[dump_columns].to_csv(csv_dir / f"{symbol.lower()}.csv", index=False)
        command = [
            sys.executable, str(Path("E:/qlib_prj/qlib_clone/scripts/dump_bin.py")), "dump_update",
            "--data_path", str(csv_dir), "--qlib_dir", str(stage), "--freq", "day",
            "--max_workers", "4", "--include_fields", "open,high,low,close,volume,amount,factor,vwap",
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(QLIB_SOURCE), environment.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        subprocess.run(command, check=True, cwd=PROJECT_ROOT, env=environment)
    stage.replace(final)
    return final


def _load_raw(provider: Path, instruments: list[str], start: date, end: date) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(
        instruments, BASE_FIELDS, start_time=start.isoformat(), end_time=end.isoformat(), freq="day"
    ).reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def _expression_features(provider: Path, instruments: list[str], target: date, names: list[str]) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    tables = pd.concat([pd.read_csv(ALPHA158_TABLE), pd.read_csv(ALPHA360_TABLE)], ignore_index=True)
    selected = tables.set_index("catalog_name").loc[names]
    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    data = D.features(
        instruments, selected["expression"].tolist(), start_time=target.isoformat(),
        end_time=target.isoformat(), freq="day",
    ).rename(columns=dict(zip(selected["expression"], names))).reset_index()
    data["instrument"] = data["instrument"].astype(str).str.upper()
    return data[["datetime", "instrument", *names]]


def compute_frozen_snapshot(
    provider: Path,
    target: date,
    instruments: list[str],
    warmup_calendar_days: int = 450,
) -> pd.DataFrame:
    feature_names = list(json.loads(PREPROCESSING.read_text(encoding="utf-8"))["feature_names"])
    expression_names = [name for name in feature_names if name.startswith(("alpha158_", "alpha360_"))]
    alpha_names = [name for name in feature_names if name.startswith("kunquant_alpha101_")]
    ta_names = [name for name in feature_names if name.startswith("ta_")]
    start = target - timedelta(days=warmup_calendar_days)
    raw = _load_raw(provider, instruments, start, target)
    target_key = pd.Timestamp(target)

    expression = _expression_features(provider, instruments, target, expression_names)
    basics = add_basic_factors(raw.copy())
    basics = basics.loc[basics["datetime"].eq(target_key), ["datetime", "instrument", "amount_cv_20", "amount_mean_20", "corr_ret_amount_20"]]

    alpha_config = Alpha101SourceConfig(
        provider_uri=str(provider), market="frozen_strategy_v1", start=start.isoformat(),
        end=target.isoformat(), max_instruments=None,
        source_local_path=PROJECT_ROOT / "tmp/reference_repos/KunQuant",
        source_commit="d4b9e61f729df347730aa921b539b9df3c3fe36d",
        source_file="tests/KunTestUtil/ref_alpha101.py",
        source_module="KunTestUtil.ref_alpha101.Alphas", license="Apache-2.0",
        selected_smoke_factors=tuple(alpha_names),
        metadata_catalog=PROJECT_ROOT / "outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml",
        catalog_stage="frozen_strategy_v1", catalog_enabled=True, catalog_runnable=True,
        labels=(), output_dir=PROJECT_ROOT / "outputs/daily_data_update_v1/runtime",
    )
    alpha = compute_alpha101_features(alpha_config, raw)
    alpha = alpha.loc[alpha["datetime"].eq(target_key), ["datetime", "instrument", *alpha_names]]

    ta_config = TaSourceConfig(
        provider_uri=str(provider), market="frozen_strategy_v1", start=start.isoformat(),
        end=target.isoformat(), max_instruments=None,
        source_local_path=PROJECT_ROOT / "tmp/reference_repos/ta",
        source_commit="a890410710a6e483c9ba08da7f3dd5089e4b9dff",
        source_file="ta/wrapper.py", source_function="add_all_ta_features", license="MIT",
        colprefix="ta_", fillna=False, vectorized=False,
        exclude_prefixes=("ta_trend_visual_ichimoku", "ta_others_", "ta_volume_vpt", "ta_volume_nvi"),
        selected_smoke_factors=tuple(ta_names), catalog_stage="frozen_strategy_v1",
        catalog_enabled=True, catalog_runnable=True, labels=(),
        output_dir=PROJECT_ROOT / "outputs/daily_data_update_v1/runtime",
    )
    ohlcv = raw.rename(columns={"$open": "open", "$high": "high", "$low": "low", "$close": "close", "$volume": "volume"})
    ta = compute_ta_features(ta_config, ohlcv)
    ta = ta.loc[ta["datetime"].eq(target_key), ["datetime", "instrument", *ta_names]]

    snapshot = expression.merge(basics, on=["datetime", "instrument"], how="outer", validate="one_to_one")
    snapshot = snapshot.merge(alpha, on=["datetime", "instrument"], how="outer", validate="one_to_one")
    snapshot = snapshot.merge(ta, on=["datetime", "instrument"], how="outer", validate="one_to_one")
    snapshot = snapshot[["datetime", "instrument", *feature_names]].sort_values("instrument").reset_index(drop=True)
    if list(snapshot.columns) != ["datetime", "instrument", *feature_names]:
        raise ValueError("Frozen Strategy V1 feature order changed")
    if snapshot.empty or snapshot[feature_names].notna().sum(axis=1).eq(0).any():
        raise ValueError("Frozen Strategy V1 snapshot contains an all-NaN row")
    return snapshot


def community_daily(provider: Path, target: date, instruments: list[str]) -> pd.DataFrame:
    fields = ["$open", "$high", "$low", "$close", "$volume", "$amount", "$factor"]
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(instruments, fields, start_time=target.isoformat(), end_time=target.isoformat(), freq="day").reset_index()
    factor = pd.to_numeric(frame["$factor"], errors="coerce")
    result = pd.DataFrame({"date": frame["datetime"], "symbol": frame["instrument"].astype(str).str.upper()})
    for name in ("open", "high", "low", "close"):
        result[f"raw_{name}"] = pd.to_numeric(frame[f"${name}"], errors="coerce") / factor
    result["raw_volume"] = pd.to_numeric(frame["$volume"], errors="coerce") * factor * 100.0
    result["raw_amount"] = pd.to_numeric(frame["$amount"], errors="coerce") * 1000.0
    result["factor"] = factor
    return result.dropna(subset=["raw_open", "raw_high", "raw_low", "raw_close", "raw_volume", "raw_amount"])


def compatibility_smoke(
    fallback_daily: pd.DataFrame,
    community: pd.DataFrame,
    fallback_features: pd.DataFrame,
    community_features: pd.DataFrame,
) -> dict[str, object]:
    raw_columns = ["raw_open", "raw_high", "raw_low", "raw_close", "raw_volume", "raw_amount", "factor"]
    raw = fallback_daily[["symbol", *raw_columns]].merge(
        community[["symbol", *raw_columns]], on="symbol", suffixes=("_bao", "_community"), validate="one_to_one"
    )
    raw_failures = {}
    for column in raw_columns:
        left = pd.to_numeric(raw[f"{column}_bao"], errors="coerce").to_numpy(float)
        right = pd.to_numeric(raw[f"{column}_community"], errors="coerce").to_numpy(float)
        atol = 0.02 if column.startswith("raw_") and column not in {"raw_volume", "raw_amount"} else 1e-6
        ok = np.isclose(left, right, rtol=1e-5, atol=atol, equal_nan=True)
        raw_failures[column] = int((~ok).sum())
    feature_names = [c for c in fallback_features if c not in {"datetime", "instrument"}]
    feature = fallback_features.merge(community_features, on=["datetime", "instrument"], suffixes=("_bao", "_community"), validate="one_to_one")
    factor_failure_count = 0
    for name in feature_names:
        left = pd.to_numeric(feature[f"{name}_bao"], errors="coerce").to_numpy(float)
        right = pd.to_numeric(feature[f"{name}_community"], errors="coerce").to_numpy(float)
        factor_failure_count += int((~np.isclose(left, right, rtol=1e-5, atol=1e-6, equal_nan=True)).sum())
    passed = not any(raw_failures.values()) and factor_failure_count == 0
    return {
        "status": "pass" if passed else "blocked_material_difference",
        "common_raw_instruments": len(raw),
        "raw_failure_counts": raw_failures,
        "common_feature_rows": len(feature),
        "feature_value_failure_count": factor_failure_count,
    }


def run(config: DailyUpdateConfig) -> dict[str, object]:
    release = latest_community_release()
    universe = load_frozen_universe(config.universe_file)
    target_dir = config.output_dir / config.target_date.isoformat()
    source = "community" if release.target_trade_date >= config.target_date else "baostock"
    readiness: dict[str, object] = {}

    if source == "baostock":
        if not baostock_release_window_open(config.target_date):
            raise NotReady(
                "BaoStock publication window is not complete; retry after 18:00 Asia/Shanghai"
            )
        raw, failures = collect_baostock_range(
            release.target_trade_date + timedelta(days=1), config.target_date
        )
        factor_frame, factor_status = collect_baostock_factor_once(config.target_date)
        if factor_status != "success":
            raise NotReady(f"BaoStock adjustment factor is not ready: {factor_status}")
        target_codes = (
            raw.loc[raw["date"].astype(str).eq(config.target_date.isoformat()), "code"]
            .astype(str).str.replace(".", "", regex=False).str.upper().unique()
        )
        expected = sorted(set(universe).intersection(target_codes))
        if not expected:
            raise NotReady("BaoStock target daily batch does not overlap the frozen Strategy V1 universe")
        readiness = validate_baostock_target(raw, config.target_date, expected, config.min_coverage)
        readiness["published_sh_sz_market_instruments"] = len(set(target_codes))
        readiness["adjustment_factor_event_rows"] = len(factor_frame)
        readiness["request_failures"] = len(failures)
        if failures:
            raise NotReady(f"BaoStock returned {len(failures)} request failures")
        provider = ensure_community_provider(release, config.cache_dir)
        anchor = _community_anchor(provider, expected, release.target_trade_date)
        bridged = bridge_baostock_to_community(raw, anchor)
        provider = build_fallback_provider(provider, bridged, config.target_date, release, config.cache_dir)
        daily = bridged.loc[bridged["date"].eq(pd.Timestamp(config.target_date))].copy()
        snapshot = compute_frozen_snapshot(provider, config.target_date, expected, config.warmup_calendar_days)
    else:
        provider = ensure_community_provider(release, config.cache_dir)
        daily = community_daily(provider, config.target_date, universe)
        expected = sorted(daily["symbol"].unique())
        snapshot = compute_frozen_snapshot(provider, config.target_date, expected, config.warmup_calendar_days)
        readiness = {
            "expected_instruments": len(expected), "complete_instruments": len(expected),
            "normal_trading_instruments": len(expected),
            "suspended_or_nontrading_instruments": 0,
            "missing_ohlcva_while_trading": 0,
            "coverage": 1.0, "ohlcva_complete": True,
        }

    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = "baostock" if source == "baostock" else "community"
    daily.to_csv(target_dir / f"{suffix}_qlib_daily.csv", index=False, encoding="utf-8-sig")
    snapshot.to_csv(target_dir / f"feature_snapshot_{suffix}.csv", index=False, encoding="utf-8-sig")

    comparison = None
    fallback_daily_path = target_dir / "baostock_qlib_daily.csv"
    fallback_feature_path = target_dir / "feature_snapshot_baostock.csv"
    if source == "community" and fallback_daily_path.is_file() and fallback_feature_path.is_file():
        comparison = compatibility_smoke(
            pd.read_csv(fallback_daily_path), daily,
            pd.read_csv(fallback_feature_path, parse_dates=["datetime"]), snapshot,
        )
        (target_dir / "factor_bridge_compatibility_smoke.json").write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if comparison["status"] != "pass":
            (target_dir / "feature_snapshot.csv").unlink(missing_ok=True)
            blocked = {
                "status": "blocked_material_difference",
                "target_date": config.target_date.isoformat(),
                "source": source,
                "compatibility_smoke": comparison,
            }
            (target_dir / "summary.json").write_text(
                json.dumps(blocked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raise RuntimeError("Factor bridge compatibility smoke found a material difference")

    snapshot.to_csv(target_dir / "feature_snapshot.csv", index=False, encoding="utf-8-sig")
    result = {
        "status": "ready", "target_date": config.target_date.isoformat(), "source": source,
        "community_release": release.tag, "community_trade_date": release.target_trade_date.isoformat(),
        "provider_uri": str(provider), "feature_snapshot": str(target_dir / "feature_snapshot.csv"),
        "feature_rows": len(snapshot), "factor_count": len(snapshot.columns) - 2,
        "coverage": readiness, "compatibility_smoke": comparison,
    }
    (target_dir / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
