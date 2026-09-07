"""Development-only inputs for the long-history screening MVP.

This module deliberately has no dependency on legacy selection outcomes. Native
smoke evidence is not candidate evidence; full execution requires later gates.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research_validation.canonical_dataset import (
    canonical_dataset_identity,
    canonical_hash,
    read_effective_partition,
    validate_partition_segments,
    validate_semantic_continuity,
)
from research_validation.labels import build_exact_calendar_label, build_label_date_map
from research_validation.bootstrap import gap_aware_moving_block_mean_test
from research_validation.multiple_testing import apply_fdr

KEYS = ["datetime", "instrument"]
START = pd.Timestamp("2010-01-29")
END = pd.Timestamp("2023-12-29")
LABEL = "label_20d_t1"
DATASET_ID = "canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_hash(frame: pd.DataFrame) -> str:
    """Logical hash includes schema and sorted normalized content, not file bytes."""
    value = frame.sort_values(KEYS, kind="stable").reset_index(drop=True)
    digest = hashlib.sha256(canonical_hash(list(value.columns)).encode())
    digest.update(pd.util.hash_pandas_object(value, index=False).values.tobytes())
    return digest.hexdigest()


def development_range(start: Any, end: Any) -> tuple[pd.Timestamp, pd.Timestamp]:
    left, right = pd.Timestamp(start), pd.Timestamp(end)
    if pd.isna(left) or pd.isna(right) or not START <= left <= right <= END:
        raise ValueError("request outside development range 2010-01-29..2023-12-29")
    return left, right


def normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if result[KEYS].isna().any().any():
        raise ValueError("null date/instrument key")
    result["datetime"] = pd.to_datetime(result["datetime"], errors="raise")
    result["instrument"] = result["instrument"].astype(str).str.upper()
    if result.duplicated(KEYS).any():
        raise ValueError("duplicate normalized date/instrument keys")
    if not result.empty:
        development_range(result.datetime.min(), result.datetime.max())
    return result.sort_values(KEYS, kind="stable").reset_index(drop=True)


def development_calendar(path: Path) -> pd.DatetimeIndex:
    # The calendar is identity metadata; no recent prices/factors are accessed.
    calendar = pd.DatetimeIndex(pd.to_datetime(path.read_text().splitlines()))
    if calendar.has_duplicates or not calendar.is_monotonic_increasing:
        raise ValueError("calendar must be strictly increasing and unique")
    calendar = calendar[(calendar >= START) & (calendar <= END)]
    if calendar.empty or calendar[0] != START or calendar[-1] != END:
        raise ValueError("incomplete development calendar")
    return calendar


def preflight(root: Path, config: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    fixed = {
        "canonical_dataset_id": DATASET_ID,
        "development_start": str(START.date()),
        "development_end": str(END.date()),
        "primary_label": LABEL,
        "entry_lag": 1,
        "holding_days": 20,
        "universe": "canonical_practical_raw",
    }
    for key, expected in fixed.items():
        if config.get(key) != expected:
            raise ValueError(f"unsupported research contract: {key}")
    if config["min_count"] < 5 or config["quantiles"] != 5:
        raise ValueError("invalid sample/quantile contract")
    base = root / config["canonical_root"]
    partitions = pd.read_csv(base / "partition_manifest.csv")
    lineage = pd.read_csv(base / "factor_lineage.csv")
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    identity = canonical_dataset_identity(partitions, lineage)
    if identity != DATASET_ID or manifest.get("canonical_dataset_id") != identity:
        raise ValueError("canonical identity mismatch")
    if len(lineage) != 774 or lineage.factor.nunique() != 774:
        raise ValueError("canonical inventory mismatch")
    if (
        not lineage.research_usable.isin([True, False]).all()
        or lineage.research_usable.sum() != 765
    ):
        raise ValueError("canonical usable inventory mismatch")
    for check in (validate_partition_segments(partitions), validate_semantic_continuity(lineage)):
        if not check.status.eq("pass").all():
            raise ValueError("canonical segment/semantic contract failed")
    missing = [str(p) for p in partitions.partition_path if not Path(p).is_file()]
    if missing:
        raise FileNotFoundError(f"canonical partitions missing: {missing[:3]}")
    # Descriptive identity only; never import historical coverage or direction.
    inventory = lineage[
        [
            "factor",
            "partition_id",
            "source",
            "economic_family",
            "research_usable",
            "block_reason",
            "authoritative_semantics",
        ]
    ].copy()
    inventory["canonical_factor_id"] = inventory.factor.map(lambda f: canonical_hash([identity, f]))
    inventory["lineage_hash"] = [canonical_hash(row) for row in lineage.to_dict("records")]
    requested = config["smoke"]["representative_factors"]
    minimal = config["smoke"]["minimal_factors"]
    allowed = set(inventory.loc[inventory.research_usable, "factor"])
    if len(requested) != 24 or len(set(requested)) != 24 or not set(requested) <= allowed:
        raise ValueError(f"invalid representative inventory: {sorted(set(requested) - allowed)}")
    if len(minimal) != 6 or len(set(minimal)) != 6 or not set(minimal) <= set(requested):
        raise ValueError("invalid minimal smoke inventory")
    identity_record = {
        "canonical_dataset_id": identity,
        "config_hash": canonical_hash(config),
        "partition_count": len(partitions),
        "partition_paths_present": True,
        "all_partition_bytes_rehashed": False,
        "held_aside_recent_diagnostic_accessed": False,
        "metadata_hashes": {
            name: sha256_file(base / name)
            for name in ("manifest.json", "partition_manifest.csv", "factor_lineage.csv")
        },
    }
    return inventory.sort_values("factor"), partitions, identity_record


def read_factor(
    partitions: pd.DataFrame, factor: str, start: Any, end: Any, *, access: list[dict]
) -> pd.DataFrame:
    left, right = development_range(start, end)
    pieces = []
    for row in partitions.to_dict("records"):
        if factor not in str(row["factors"]).split(","):
            continue
        lo, hi = (
            max(left, pd.Timestamp(row["effective_start"])),
            min(right, pd.Timestamp(row["effective_end"])),
        )
        if lo > hi:
            continue
        bounded = {**row, "effective_start": lo, "effective_end": hi}
        frame = normalize_keys(read_effective_partition(bounded, columns=[factor]))
        if not frame.empty and not frame.datetime.between(lo, hi).all():
            raise ValueError("partition reader violated requested dates")
        pieces.append(frame)
        access.append(
            {
                "kind": "factor",
                "factor": factor,
                "path": row["partition_path"],
                "requested_start": str(lo.date()),
                "requested_end": str(hi.date()),
                "rows": len(frame),
                "slice_hash": frame_hash(frame),
                "declared_parent_sha256": row["output_sha256"],
            }
        )
    if not pieces:
        raise ValueError(f"no canonical partitions for {factor} in requested dates")
    result = normalize_keys(pd.concat(pieces, ignore_index=True))
    if result.empty:
        raise ValueError(f"complete canonical data absence: {factor}")
    return result


def exact_primary_labels(
    keys: pd.DataFrame, prices: pd.DataFrame, calendar: pd.DatetimeIndex
) -> pd.DataFrame:
    keys, prices = normalize_keys(keys), normalize_keys(prices)
    prices["$close"] = pd.to_numeric(prices["$close"], errors="raise").astype("float64")
    if calendar.empty or calendar.min() < START or calendar.max() > END:
        raise ValueError("label calendar outside development")
    result, _ = build_exact_calendar_label(
        keys[KEYS],
        prices,
        calendar,
        price_column="$close",
        label_name=LABEL,
        entry_lag=1,
        holding_days=20,
    )
    if result.exit_date.dropna().gt(END).any():
        raise ValueError("label exits development range")
    return result


def common_samples(
    frame: pd.DataFrame, factor: str, *, min_count: int = 50
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Keep IC dates even when tied values cannot form five quantiles."""
    frame = normalize_keys(frame)
    if min_count < 5:
        raise ValueError("min_count must be at least five")
    value = pd.to_numeric(frame[factor], errors="raise")
    label = pd.to_numeric(frame[LABEL], errors="raise")
    finite = np.isfinite(value) & np.isfinite(label)
    base = frame.loc[finite, KEYS].assign(factor=value[finite], forward_return=label[finite])
    ic_frames, q_frames, status = [], [], []
    for date, group in base.groupby("datetime", sort=True):
        ic_ok = (
            len(group) >= min_count
            and group.factor.nunique() > 1
            and group.forward_return.nunique() > 1
        )
        q_ok = False
        if ic_ok:
            ic_frames.append(group)
            # Ties remain ties; no arbitrary instrument-order tie breaking.
            quantile = pd.qcut(group.factor, 5, labels=False, duplicates="drop")
            if quantile.nunique() == 5:
                q_frames.append(group.assign(factor_quantile=quantile + 1))
                q_ok = True
        status.append(
            {
                "datetime": date,
                "finite_pairs": len(group),
                "ic_available": ic_ok,
                "quantile_available": q_ok,
            }
        )
    ic = pd.concat(ic_frames, ignore_index=True) if ic_frames else base.iloc[:0].copy()
    quantiles = (
        pd.concat(q_frames, ignore_index=True)
        if q_frames
        else base.iloc[:0].assign(factor_quantile=pd.Series(dtype=int))
    )
    daily = pd.DataFrame(
        status, columns=["datetime", "finite_pairs", "ic_available", "quantile_available"]
    )
    daily = pd.DataFrame({"datetime": frame.datetime.unique()}).merge(
        daily, on="datetime", how="left"
    )
    daily["finite_pairs"] = daily.finite_pairs.fillna(0).astype(int)
    for column in ("ic_available", "quantile_available"):
        daily[column] = daily[column].eq(True)
    daily["canonical_rows"] = daily.datetime.map(frame.groupby("datetime").size())
    return ic, quantiles, daily


def jqfactor_returns_compat(module: Any) -> tuple[Any, dict]:
    """Keep upstream arithmetic; make its old transform-like apply explicit.

    pandas 2 adds a grouping level by default. Only the first weights groupby
    needs group_keys=False for the supported group_adjust=False primary profile.
    Source drift fails closed; no installed/reference source file is modified.
    """
    source = inspect.getsource(module.factor_returns)
    old = "factor_data.groupby(grouper)['factor']"
    new = "factor_data.groupby(grouper, group_keys=False)['factor']"
    if source.count(old) != 1:
        raise ValueError("jqfactor factor_returns compatibility patch source drift")
    patched = source.replace(old, new)
    namespace = dict(module.__dict__)
    exec(compile(patched, "<jqfactor_factor_returns_group_keys_compat>", "exec"), namespace)
    return namespace["factor_returns"], {
        "original": old,
        "replacement": new,
        "supported_group_adjust": False,
        "patched_function_sha256": hashlib.sha256(patched.encode()).hexdigest(),
    }


def native_primary_smoke(
    ic: pd.DataFrame, quantiles: pd.DataFrame, modules: dict, *, atol: float
) -> tuple[dict, dict]:
    """Use original native metrics; do not route IC through quantile dropna adapters."""
    if ic.empty:
        raise ValueError("no definable daily IC samples")
    a = ic.set_index(KEYS).rename(columns={"forward_return": "20D"})
    a.index = a.index.set_names(["date", "asset"])
    j = a.rename(columns={"20D": "period_20"})
    q = ic.set_index(KEYS)
    result = {}
    result["alphalens_ic"] = modules["alphalens"].factor_information_coefficient(a)["20D"]
    result["jqfactor_ic"] = modules["jqfactor"].factor_information_coefficient(j)["period_20"]
    pearson, rank = modules["qlib"].calc_ic(q.factor, q.forward_return)
    result["qlib_ic"], result["qlib_pearson"] = rank, pearson
    reference = rank.sort_index()
    expected_dates = pd.DatetimeIndex(ic.datetime.unique()).sort_values()
    if not reference.index.equals(expected_dates) or not np.isfinite(reference.to_numpy()).all():
        raise ValueError("Qlib reference lost input dates or produced nonfinite Rank IC")
    parity = {}
    calendar_padding = {}
    for name in ("alphalens_ic", "jqfactor_ic"):
        actual = result[name].sort_index()
        # Alphalens asfreq(None) inserts calendar-day NaNs. Remove only these
        # proven empty dates; never hide a missing signal date or finite extra IC.
        extra = actual.index.difference(reference.index)
        if not reference.index.isin(actual.index).all() or actual.loc[extra].notna().any():
            raise ValueError(f"native Rank IC date mismatch: {name}")
        calendar_padding[name] = len(extra)
        actual = actual.reindex(reference.index)
        if not np.allclose(actual, reference, atol=atol, rtol=0, equal_nan=True):
            raise ValueError(f"native Rank IC parity failed: {name}")
        parity[name] = float((actual - reference).abs().max())
    native_status = {}
    # Required metrics are explicit; optional V4 steps never run here.
    if not quantiles.empty:
        qa = quantiles.set_index(KEYS).rename(columns={"forward_return": "20D"})
        qa.index = qa.index.set_names(["date", "asset"])
        result["alphalens_quantile"], _ = modules["alphalens"].mean_return_by_quantile(
            qa, by_date=True, demeaned=False
        )
        native_status["alphalens_quantile"] = "pass"
    else:
        native_status["alphalens_quantile"] = "unavailable_no_five_bins"
    try:
        returns_function = modules.get("jqfactor_returns", modules["jqfactor"].factor_returns)
        result["jqfactor_returns"] = returns_function(j, demeaned=True, group_adjust=False)
        native_status["jqfactor_returns"] = "pass"
    except (ValueError, TypeError, KeyError) as exc:
        # Record the original incompatibility. No silent metric substitution.
        native_status["jqfactor_returns"] = f"failed: {type(exc).__name__}: {exc}"
    result["qlib_long_short"], result["qlib_cross_section_mean"] = modules[
        "qlib"
    ].calc_long_short_return(q.factor, q.forward_return)
    native_status["qlib_long_short"] = "pass"
    for name in ("jqfactor_returns", "qlib_long_short"):
        if name not in result:
            continue
        output = result[name]
        if not output.index.equals(reference.index) or not np.isfinite(output.to_numpy()).all():
            raise ValueError(f"required native output dates/nonfinite failure: {name}")
    return result, {
        "parity_status": "pass",
        "max_abs_difference": parity,
        "native_empty_calendar_padding_dates": calendar_padding,
        "native_status": native_status,
        "ic_sample_hash": frame_hash(ic),
        "quantile_sample_hash": frame_hash(quantiles),
        "candidate_status": "not_evaluated",
    }


def label_map(calendar: pd.DatetimeIndex) -> pd.DataFrame:
    return build_label_date_map(calendar, calendar, entry_lag=1, holding_days=20)


def summarize_daily_metrics(series: pd.Series, dates: pd.DataFrame, eras: dict) -> pd.DataFrame:
    """Full/annual/era views use signal dates and original daily observations."""
    values = series.copy()
    values.index = pd.DatetimeIndex(values.index)
    if values.index.has_duplicates:
        raise ValueError("duplicate daily metric dates")
    # Native calendar padding is not an extra observation.
    values = values.dropna().sort_index()
    if not values.empty:
        development_range(values.index.min(), values.index.max())
    date_map = dates.set_index("datetime")
    if not values.index.isin(date_map.index).all():
        raise ValueError("metric signal date absent from label date map")
    periods = [("full", "full", START, END, "")]
    periods += [
        (str(year), "annual", pd.Timestamp(year, 1, 1), pd.Timestamp(year, 12, 31), "")
        for year in range(2010, 2024)
    ]
    periods += [
        (name, "signal_era", pd.Timestamp(bounds[0]), pd.Timestamp(bounds[1]), name)
        for name, bounds in eras.items()
    ]
    rows = []
    for name, kind, left, right, era in periods:
        group = values.loc[(values.index >= left) & (values.index <= right)]
        std = group.std(ddof=1)
        ratio = group.mean() / std if pd.notna(std) and std > 0 else np.nan
        rows.append(
            {
                "period_id": name,
                "period_type": kind,
                "signal_era": era,
                "signal_era_start": left if era else pd.NaT,
                "signal_era_end": right if era else pd.NaT,
                "actual_signal_start": group.index.min(),
                "actual_signal_end": group.index.max(),
                "max_label_exit_date": date_map.loc[group.index, "exit_date"].max(),
                "valid_dates": len(group),
                "mean": group.mean(),
                "median": group.median(),
                "std": std,
                "mean_std_ratio": ratio,
                "annualized_mean_std_ratio": ratio * np.sqrt(252),
                "positive_ratio": float(group.gt(0).mean()) if len(group) else np.nan,
                "status": "available" if len(group) else "unavailable",
            }
        )
    return pd.DataFrame(rows)


def primary_fdr(
    inventory: pd.DataFrame,
    daily_rank_ic: dict[str, pd.Series],
    calendar: pd.DatetimeIndex,
    *,
    samples: int = 1000,
    block_length: int = 20,
    seed: int = 20260907,
) -> pd.DataFrame:
    """One planned family; caller supplies only parity-approved primary Qlib IC.

    An explicit empty series is a completed, statistically undefined job.
    Missing dictionary entries are execution failures and must not become p=1.
    """
    names = sorted(inventory.loc[inventory.research_usable, "factor"].tolist())
    if samples <= 0 or block_length <= 0:
        raise ValueError("invalid bootstrap parameters")
    if len(names) != 765 or len(set(names)) != 765 or set(daily_rank_ic) != set(names):
        raise ValueError("primary FDR requires all 765 completed factor jobs")
    if calendar.empty or calendar.has_duplicates or not calendar.is_monotonic_increasing:
        raise ValueError("invalid bootstrap calendar")
    development_range(calendar.min(), calendar.max())
    mature = label_map(calendar).dropna(subset=["exit_date"])["datetime"]
    rows = []
    for factor in names:
        series = daily_rank_ic[factor].copy()
        series.index = pd.DatetimeIndex(series.index)
        if series.index.has_duplicates or not series.dropna().index.isin(mature).all():
            raise ValueError(f"invalid primary IC dates: {factor}")
        if np.isinf(series.to_numpy(dtype=float)).any():
            raise ValueError(f"infinite primary IC: {factor}")
        complete = series.reindex(pd.DatetimeIndex(mature))
        row = {
            "factor": factor,
            "test_family": "primary_20d_full_raw_planned_765",
            "metric": "qlib_native_rank_ic",
            "status": "available",
            "observation_count": int(complete.notna().sum()),
            "raw_p_value": 1.0,
            "reason": "",
            "planned_family_count": 765,
        }
        try:
            row.update(
                gap_aware_moving_block_mean_test(
                    complete, samples=samples, block_length=block_length, seed=seed
                )
            )
        except ValueError as exc:
            if str(exc) not in (
                "insufficient observations for gap-aware block bootstrap",
                "no contiguous segment can supply one complete block",
            ):
                raise
            row.update(status="unavailable", reason=str(exc))
        rows.append(row)
    return apply_fdr(pd.DataFrame(rows), alpha=0.05)


def bounded_price_cache(
    provider: Path, instruments: list[str], start: Any, end: Any, cache_dir: Path, loader: Any
) -> tuple[pd.DataFrame, str]:
    """Reuse the repository weak-cache format, adding content-integrity checks.

    Source binary hashing can touch storage bytes outside the date range, but
    only bounded loader output may enter the cached research frame.
    """
    from qlib_baseline.cache import (
        build_cache_fingerprint,
        cache_path,
        cache_metadata_path,
        read_dataframe_cache,
        write_dataframe_cache,
        normalized_callable_ast_hash,
    )

    left, right = development_range(start, end)
    symbols = sorted(set(str(s).upper() for s in instruments))
    if not symbols:
        raise ValueError("empty price instrument request")
    sources = {}
    for symbol in symbols:
        path = provider / "features" / symbol.lower() / "close.day.bin"
        if not path.is_file():
            raise FileNotFoundError(f"missing price source: {symbol}")
        sources[symbol] = sha256_file(path)
    fingerprint = build_cache_fingerprint(
        "long_history_screening_close",
        data={
            "provider": str(provider.resolve()),
            "close_sha256": sources,
            "calendar_sha256": sha256_file(provider / "calendars/day.txt"),
        },
        computation={
            "field": "$close",
            "frequency": "day",
            "qlib_version": __import__("qlib").__version__,
            "loader_ast": normalized_callable_ast_hash(loader, normalize_keys),
            "output": "normalized keys, native close",
        },
        request={"start": str(left), "end": str(right), "instruments": symbols},
    )
    path = cache_path(cache_dir, "close", fingerprint)
    cached = read_dataframe_cache(path, fingerprint)
    if cached is not None:
        metadata = json.loads(cache_metadata_path(path).read_text(encoding="utf-8"))
        if metadata.get("diagnostics", {}).get("logical_content_hash") != frame_hash(cached):
            raise ValueError("price cache content corrupted")
        frame = normalize_keys(cached)
        cache_status = "hit"
    else:
        if path.exists() or cache_metadata_path(path).exists():
            raise ValueError("price cache incomplete or invalid; rebuild explicitly")
        frame = normalize_keys(loader(symbols, left, right))
        cache_status = "miss"
    if (
        frame.empty
        or not frame.datetime.between(left, right).all()
        or not set(frame.instrument) <= set(symbols)
    ):
        raise ValueError("price cache/loader violated request")
    if cache_status == "miss":
        write_dataframe_cache(
            path, frame, fingerprint, diagnostics={"logical_content_hash": frame_hash(frame)}
        )
    return frame, cache_status


def audit_feature_quality(
    partitions: pd.DataFrame, inventory: pd.DataFrame, calendar: pd.DatetimeIndex, output: Path
) -> pd.DataFrame:
    """Feature-only annual profiles, with bounded partition reads and checkpoints.

    No labels, old eligibility statistics, or recent values enter this audit.
    Each chunk checkpoint is diagnostic only; it is not an unchecked cache.
    """
    output.mkdir(parents=True, exist_ok=False)
    allowed = set(inventory.loc[inventory.research_usable, "factor"])
    all_rows, access = [], []
    for number, row in enumerate(partitions.to_dict("records")):
        factors = sorted(allowed.intersection(str(row["factors"]).split(",")))
        left = max(START, pd.Timestamp(row["effective_start"]))
        right = min(END, pd.Timestamp(row["effective_end"]))
        if not factors or left > right:
            continue
        for year in range(left.year, right.year + 1):
            lo, hi = max(left, pd.Timestamp(year, 1, 1)), min(right, pd.Timestamp(year, 12, 31))
            bounded = {**row, "effective_start": lo, "effective_end": hi}
            frame = normalize_keys(read_effective_partition(bounded, columns=factors))
            if frame.empty or not frame.datetime.isin(calendar).all():
                raise ValueError("quality audit empty partition or impossible trading dates")
            if not frame.datetime.between(lo, hi).all():
                raise ValueError("quality reader violated development window")
            print(f"Quality {number}/{len(partitions)} {row['partition_id']} {year}", flush=True)
            chunk = []
            for factor in factors:
                values = pd.to_numeric(frame[factor], errors="raise")
                finite = np.isfinite(values)
                finite_dates = frame.loc[finite, "datetime"]
                daily = frame.loc[finite].groupby("datetime")[factor].agg(["count", "nunique"])
                chunk.append(
                    {
                        "factor": factor,
                        "year": year,
                        "partition_id": row["partition_id"],
                        "segment_id": row["segment_id"],
                        "read_start": lo,
                        "read_end": hi,
                        "rows": len(frame),
                        "finite_count": int(finite.sum()),
                        "missing_count": int(values.isna().sum()),
                        "infinite_count": int(np.isinf(values).sum()),
                        "finite_dates": int(finite_dates.nunique()),
                        "observed_dates": frame.datetime.nunique(),
                        "first_finite_date": finite_dates.min(),
                        "last_finite_date": finite_dates.max(),
                        "constant_dates": int(daily["nunique"].eq(1).sum()),
                        "min_count_variable_dates": int(
                            (daily["count"].ge(50) & daily["nunique"].gt(1)).sum()
                        ),
                        "coverage_denominator": "canonical_partition_rows; not all historical A shares",
                    }
                )
            pd.DataFrame(chunk).to_csv(output / f"chunk_{number:04d}_{year}.csv", index=False)
            all_rows.extend(chunk)
            access.append(
                {
                    "path": row["partition_path"],
                    "start": lo,
                    "end": hi,
                    "rows": len(frame),
                    "factors": len(factors),
                    "keys_hash": frame_hash(frame[KEYS]),
                }
            )
            pd.DataFrame(access).to_csv(output / "access_audit.csv", index=False)
    detail = pd.DataFrame(all_rows)
    if set(detail.factor) != allowed:
        raise ValueError("feature audit omitted planned factors")
    annual = detail.groupby(["factor", "year"], as_index=False).agg(
        rows=("rows", "sum"),
        finite_count=("finite_count", "sum"),
        missing_count=("missing_count", "sum"),
        infinite_count=("infinite_count", "sum"),
        finite_dates=("finite_dates", "sum"),
        observed_dates=("observed_dates", "sum"),
        first_finite_date=("first_finite_date", "min"),
        last_finite_date=("last_finite_date", "max"),
        constant_dates=("constant_dates", "sum"),
        min_count_variable_dates=("min_count_variable_dates", "sum"),
    )
    annual["coverage"] = annual.finite_count / annual.rows
    annual.to_csv(output / "feature_quality_annual.csv", index=False)
    annual.groupby("factor", as_index=False).agg(
        rows=("rows", "sum"),
        finite_count=("finite_count", "sum"),
        missing_count=("missing_count", "sum"),
        infinite_count=("infinite_count", "sum"),
        first_finite_date=("first_finite_date", "min"),
        last_finite_date=("last_finite_date", "max"),
        min_count_variable_dates=("min_count_variable_dates", "sum"),
    ).to_csv(output / "feature_quality_full.csv", index=False)
    return annual
