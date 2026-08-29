from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from factor_research.alpha101_source import import_ref_alpha101, to_wind_wide

from .alpha101_canonical import canonical_wide_inputs
from .historical_data import (
    DAILY_BASIC_FIELDS,
    MONEYFLOW_FIELDS,
    STATEMENT_FIELDS,
    align_statement_events_to_keys,
    canonical_hash,
    load_segments,
    normalize_trade_date_frame,
    raw_snapshot_summary,
    statement_event_timeline,
)
from .local_recovery import add_local_recovered_factors
from .mature_factors import (
    DAILY_BASIC_FACTOR_NAMES,
    FUNDAMENTAL_FACTOR_NAMES,
    MARKET_FACTOR_NAMES,
    MONEYFLOW_FACTOR_NAMES,
    compute_daily_basic_factors,
    compute_fundamental_factors,
    compute_market_factors,
    compute_moneyflow_factors,
)
from .tushare_data import TushareSegmentStore


RECOVERED_ALPHA158_EXPRESSIONS = {
    "alpha158_CNTN5": "Mean($close<Ref($close, 1), 5)",
    "alpha158_IMAX5": "IdxMax($high, 5)/5",
    "alpha158_RANK5": "Rank($close, 5)",
}
RECOVERED_LOCAL_NAMES = ("ta_volume_nvi_canonical_v2", "ta_volume_vpt_canonical_v2")
RECOVERED_TA_NAMES = ("ta_volatility_bbli", "ta_volatility_kchi")


@dataclass(frozen=True)
class BuildPaths:
    project_root: Path
    runtime_dir: Path
    output_dir: Path
    report_dir: Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(project_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=project_root, text=True
    ).strip()


def tracked_worktree_clean(project_root: Path) -> bool:
    unstaged = subprocess.run(["git", "diff", "--quiet"], cwd=project_root).returncode
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=project_root
    ).returncode
    return unstaged == 0 and staged == 0


def load_qlib_market(
    provider_uri: Path,
    symbols: list[str],
    *,
    start_date: str,
    end_date: str,
    cache_path: Path,
) -> pd.DataFrame:
    fields = ["$open", "$high", "$low", "$close", "$volume", "$amount", "$vwap"]
    identity = {
        "provider_uri": provider_uri.resolve().as_posix(),
        "symbols": symbols,
        "start_date": start_date,
        "end_date": end_date,
        "fields": fields,
    }
    sidecar = cache_path.with_suffix(".receipt.json")
    if cache_path.is_file() and sidecar.is_file():
        receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        if (
            receipt.get("identity_sha256") == canonical_hash(identity)
            and receipt.get("data_sha256") == file_sha256(cache_path)
        ):
            return pd.read_parquet(cache_path)
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    frame = D.features(
        symbols, fields, start_time=start_date, end_time=end_date, freq="day"
    ).reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame = frame.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(cache_path)
    sidecar.write_text(
        json.dumps(
            {
                "identity_sha256": canonical_hash(identity),
                "data_sha256": file_sha256(cache_path),
                "row_count": len(frame),
                "columns": list(frame.columns),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return frame


def _project(frame: pd.DataFrame, keys: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    source = frame[["datetime", "instrument", *names]].copy()
    source["datetime"] = pd.to_datetime(source["datetime"])
    source["instrument"] = source["instrument"].astype(str).str.upper()
    if source.duplicated(["datetime", "instrument"]).any():
        raise ValueError("factor frame contains duplicate keys")
    result = keys.merge(source, on=["datetime", "instrument"], how="left", validate="one_to_one")
    result[names] = result[names].replace([np.inf, -np.inf], np.nan)
    return result.sort_values(["datetime", "instrument"]).reset_index(drop=True)


def _ta_recovered(frame: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    source = str(source_path.resolve())
    if source not in sys.path:
        sys.path.insert(0, source)
    from ta.volatility import BollingerBands, KeltnerChannel

    parts: list[pd.DataFrame] = []
    for instrument, group in frame.groupby("instrument", sort=False):
        ordered = group.sort_values("datetime")
        close = pd.to_numeric(ordered["$close"], errors="coerce")
        high = pd.to_numeric(ordered["$high"], errors="coerce")
        low = pd.to_numeric(ordered["$low"], errors="coerce")
        part = ordered[["datetime", "instrument"]].copy()
        part["ta_volatility_bbli"] = BollingerBands(close=close).bollinger_lband_indicator()
        part["ta_volatility_kchi"] = KeltnerChannel(
            high=high, low=low, close=close
        ).keltner_channel_hband_indicator()
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def _safe_alpha101(
    frame: pd.DataFrame,
    factor_methods: dict[str, str],
    *,
    kunquant_path: Path,
    direct_vwap: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate Alpha101 factors independently and preserve axis failures as blockers."""
    wide = canonical_wide_inputs(frame) if direct_vwap else to_wind_wide(frame)
    reference = wide["S_DQ_CLOSE"]
    source = import_ref_alpha101(kunquant_path)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        stock = source.Alphas(wide)
    if direct_vwap:
        stock.vwap = wide["S_DQ_VWAP"]
    stock.returns = stock.close.pct_change(fill_method=None)
    outputs: list[pd.Series] = []
    issues: list[dict[str, str]] = []
    for factor, method in factor_methods.items():
        try:
            values = getattr(stock, method)()
            if not isinstance(values, pd.DataFrame):
                raise TypeError(f"returned {type(values).__name__}, expected DataFrame")
            if not values.index.equals(reference.index) or not values.columns.equals(reference.columns):
                raise ValueError("result axes differ from provider axes; positional relabel forbidden")
            outputs.append(values.stack(future_stack=True).rename(factor))
        except Exception as exc:
            issues.append(
                {
                    "factor": factor,
                    "adapter_status": "blocked",
                    "block_reason": f"{type(exc).__name__}: {exc}",
                }
            )
            empty = pd.DataFrame(np.nan, index=reference.index, columns=reference.columns)
            outputs.append(empty.stack(future_stack=True).rename(factor))
    combined = pd.concat(outputs, axis=1).reset_index()
    combined = combined.rename(columns={"level_0": "datetime", "level_1": "instrument"})
    return combined, pd.DataFrame(issues)


def compute_recovered(
    masked_market: pd.DataFrame,
    keys: pd.DataFrame,
    *,
    provider_uri: Path,
    start_date: str,
    end_date: str,
    kunquant_path: Path,
    ta_source_path: Path,
    recovered_inventory: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    names = recovered_inventory["name"].astype(str).tolist()
    alpha_meta = recovered_inventory.loc[
        recovered_inventory["source"].eq("alpha101"), ["name", "registry_name"]
    ]
    alpha, issues = _safe_alpha101(
        masked_market,
        dict(zip(alpha_meta["name"].astype(str), alpha_meta["registry_name"].astype(str))),
        kunquant_path=kunquant_path,
        direct_vwap=False,
    )
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    symbols = sorted(keys["instrument"].unique())
    expressions = list(RECOVERED_ALPHA158_EXPRESSIONS.values())
    expression_frame = D.features(
        symbols, expressions, start_time=start_date, end_time=end_date, freq="day"
    ).rename(columns=dict(zip(expressions, RECOVERED_ALPHA158_EXPRESSIONS))).reset_index()
    local = add_local_recovered_factors(masked_market)
    ta_frame = _ta_recovered(masked_market, ta_source_path)
    combined = alpha
    for part in (expression_frame, local, ta_frame):
        keep = [column for column in part.columns if column in {"datetime", "instrument", *names}]
        combined = combined.merge(
            part[keep], on=["datetime", "instrument"], how="outer", validate="one_to_one"
        )
    return _project(combined, keys, names), issues


def compute_canonical(
    masked_market: pd.DataFrame,
    keys: pd.DataFrame,
    inventory: pd.DataFrame,
    kunquant_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    subset = inventory.loc[inventory["lineage_status"].eq("canonicalized")]
    result, issues = _safe_alpha101(
        masked_market,
        dict(zip(subset["name"].astype(str), subset["registry_name"].astype(str))),
        kunquant_path=kunquant_path,
        direct_vwap=True,
    )
    return _project(result, keys, subset["name"].astype(str).tolist()), issues


def compute_mature_partitions(
    masked_market: pd.DataFrame,
    keys: pd.DataFrame,
    *,
    store: TushareSegmentStore,
    trade_date_segments: list[str],
    statement_segments: list[str],
    compute_factors: bool = True,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    content_rows: list[dict[str, Any]] = []

    def content_coverage(
        api: str,
        frame: pd.DataFrame,
        *,
        observation_column: str,
        availability_columns: tuple[str, ...] = (),
    ) -> None:
        observation = pd.to_datetime(
            frame.get(observation_column), format="%Y%m%d", errors="coerce"
        )
        available = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
        for column in availability_columns:
            if column in frame:
                parsed = pd.to_datetime(frame[column], format="%Y%m%d", errors="coerce")
                available = available.where(available.notna(), parsed)
        revision_keys = [
            column
            for column in ("ts_code", observation_column, "report_type", "comp_type")
            if column in frame
        ]
        content_rows.append(
            {
                "api": api,
                "content_row_count": len(frame),
                "content_instrument_count": int(frame["ts_code"].nunique()),
                "observation_start": observation.min(),
                "observation_end": observation.max(),
                "availability_start": available.min() if availability_columns else pd.NaT,
                "availability_end": available.max() if availability_columns else pd.NaT,
                "missing_availability_count": (
                    int(available.isna().sum()) if availability_columns else 0
                ),
                "revision_row_count": (
                    int(frame.duplicated(revision_keys, keep=False).sum())
                    if revision_keys
                    else 0
                ),
            }
        )

    mature: dict[str, pd.DataFrame] = {}
    market = masked_market.copy()
    if compute_factors:
        stock_return = market.groupby("instrument", sort=False)["$close"].pct_change(
            fill_method=None
        )
        market["$market_return"] = stock_return.groupby(market["datetime"]).transform("mean")
        # Qlib community amount is thousand CNY. V2 mature liquidity factors use CNY.
        market["$amount"] = pd.to_numeric(market["$amount"], errors="coerce") * 1_000.0
        mature["mature_market"] = _project(
            compute_market_factors(market), keys, list(MARKET_FACTOR_NAMES)
        )

    daily_raw, daily_receipts = load_segments(
        store,
        "daily_basic",
        trade_date_segments,
        required_columns=set(DAILY_BASIC_FIELDS.split(",")),
    )
    content_coverage("daily_basic", daily_raw, observation_column="trade_date")
    daily = normalize_trade_date_frame(daily_raw)
    if compute_factors:
        mature["mature_daily_basic"] = _project(
            compute_daily_basic_factors(daily), keys, list(DAILY_BASIC_FACTOR_NAMES)
        )

    money_raw, money_receipts = load_segments(
        store,
        "moneyflow",
        trade_date_segments,
        required_columns=set(MONEYFLOW_FIELDS.split(",")),
    )
    content_coverage("moneyflow", money_raw, observation_column="trade_date")
    if compute_factors:
        money = normalize_trade_date_frame(money_raw)
        traded = market[["datetime", "instrument", "$amount"]].rename(
            columns={"$amount": "traded_amount_cny"}
        )
        money = money.merge(
            traded, on=["datetime", "instrument"], how="left", validate="one_to_one"
        )
        mature["mature_moneyflow"] = _project(
            compute_moneyflow_factors(money), keys, list(MONEYFLOW_FACTOR_NAMES)
        )

    statement_frames: dict[str, pd.DataFrame] = {}
    statement_receipts: list[pd.DataFrame] = []
    for api, fields in STATEMENT_FIELDS.items():
        frame, receipts = load_segments(
            store,
            api,
            statement_segments,
            required_columns=set(fields.split(",")),
        )
        statement_frames[api] = frame
        statement_receipts.append(receipts)
        content_coverage(
            api,
            frame,
            observation_column="end_date",
            availability_columns=("f_ann_date", "ann_date") if api != "fina_indicator" else ("ann_date",),
        )
    events, revision_audit = statement_event_timeline(
        statement_frames["income"],
        statement_frames["balancesheet"],
        statement_frames["cashflow"],
    )
    aligned = align_statement_events_to_keys(keys, events)
    market_cap = daily[["datetime", "instrument", "total_mv"]].copy()
    market_cap["total_mv_cny"] = pd.to_numeric(market_cap["total_mv"], errors="coerce") * 10_000.0
    aligned = aligned.merge(
        market_cap[["datetime", "instrument", "total_mv_cny"]],
        on=["datetime", "instrument"],
        how="left",
        validate="one_to_one",
    )
    if compute_factors:
        eligible = aligned.loc[aligned["information_available_date"].notna()].copy()
        fundamental_values = compute_fundamental_factors(eligible)
        mature["mature_fundamental"] = _project(
            fundamental_values, keys, list(FUNDAMENTAL_FACTOR_NAMES)
        )
    no_future = aligned["information_available_date"].dropna().le(aligned.loc[
        aligned["information_available_date"].notna(), "datetime"
    ]).all()
    supporting = {
        "daily_receipts": daily_receipts,
        "moneyflow_receipts": money_receipts,
        "statement_receipts": pd.concat(statement_receipts, ignore_index=True),
        "revision_audit": revision_audit,
        "statement_events": events,
        "statement_alignment": aligned,
        "pit_contract": pd.DataFrame(
            [{"check": "no_future_statement_access", "status": "pass" if no_future else "fail"}]
        ),
        "fina_indicator": statement_frames["fina_indicator"],
        "raw_content_coverage": pd.DataFrame(content_rows),
    }
    return mature, supporting


def write_partition(path: Path, frame: pd.DataFrame, names: list[str]) -> dict[str, Any]:
    output = frame[["datetime", "instrument", *names]].copy()
    if output.duplicated(["datetime", "instrument"]).any():
        raise ValueError(f"duplicate matrix keys in {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    output.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)
    return {
        "partition_id": path.stem,
        "partition_path": path.resolve().as_posix(),
        "factor_count": len(names),
        "row_count": len(output),
        "output_sha256": file_sha256(path),
        "output_size_bytes": path.stat().st_size,
        "reused_v1": False,
        "factors": ",".join(names),
    }


def audit_partitions(
    partition_rows: pd.DataFrame,
    inventory: pd.DataFrame,
    split_ranges: pd.DataFrame,
    *,
    minimum_factor_coverage: float,
    minimum_month_coverage: float,
    minimum_qualified_month_fraction: float,
) -> dict[str, pd.DataFrame]:
    metadata = inventory.set_index("name")
    factor_rows: list[dict[str, Any]] = []
    month_rows: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    instrument_accumulator: dict[tuple[str, str], list[int]] = {}
    family_accumulator: dict[str, list[int]] = {}
    source_accumulator: dict[str, list[int]] = {}
    for partition in partition_rows.itertuples(index=False):
        names = str(partition.factors).split(",")
        frame = pd.read_parquet(partition.partition_path, columns=["datetime", "instrument", *names])
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        months = frame["datetime"].dt.to_period("M").astype(str)
        for factor in names:
            numeric = pd.to_numeric(frame[factor], errors="coerce")
            values = numeric.to_numpy(dtype=float)
            finite = np.isfinite(values)
            valid = int(finite.sum())
            total = len(values)
            finite_values = values[finite]
            month_valid = pd.Series(finite, index=frame.index).groupby(months).agg(["sum", "count"])
            month_valid["coverage"] = month_valid["sum"] / month_valid["count"]
            qualified_fraction = float(
                month_valid["coverage"].ge(minimum_month_coverage).mean()
            )
            unique = int(pd.Series(finite_values).nunique()) if valid else 0
            std = float(np.std(finite_values)) if valid else np.nan
            inf_count = int(np.isinf(values).sum())
            materializable = valid > 0
            coverage_qualified = (
                valid / total >= minimum_factor_coverage
                and qualified_fraction >= minimum_qualified_month_fraction
            )
            research_usable = (
                materializable
                and coverage_qualified
                and unique > 1
                and std > 0
                and inf_count == 0
            )
            family = str(metadata.loc[factor, "economic_family"])
            source = str(metadata.loc[factor, "source"])
            lineage = str(metadata.loc[factor, "lineage_status"])
            factor_rows.append(
                {
                    "factor": factor,
                    "lineage_status": lineage,
                    "economic_family": family,
                    "source": source,
                    "defined": True,
                    "materializable": materializable,
                    "coverage_qualified": coverage_qualified,
                    "research_usable": research_usable,
                    "temporarily_blocked": not research_usable,
                    "valid_count": valid,
                    "row_count": total,
                    "coverage": valid / total if total else 0.0,
                    "qualified_month_fraction": qualified_fraction,
                    "unique_values": unique,
                    "zero_fraction_of_finite": (
                        float(np.equal(finite_values, 0).mean()) if valid else np.nan
                    ),
                    "mean": float(np.mean(finite_values)) if valid else np.nan,
                    "std": std,
                    "min": float(np.min(finite_values)) if valid else np.nan,
                    "q01": float(np.quantile(finite_values, 0.01)) if valid else np.nan,
                    "median": float(np.median(finite_values)) if valid else np.nan,
                    "q99": float(np.quantile(finite_values, 0.99)) if valid else np.nan,
                    "max": float(np.max(finite_values)) if valid else np.nan,
                    "inf_count": inf_count,
                    "block_reason": (
                        ""
                        if research_usable
                        else (
                            "zero_finite_values"
                            if not materializable
                            else "insufficient_historical_coverage"
                            if not coverage_qualified
                            else "non_finite_values"
                            if inf_count
                            else "constant_or_degenerate"
                        )
                    ),
                }
            )
            for month, row in month_valid.iterrows():
                month_rows.append(
                    {
                        "factor": factor,
                        "month": month,
                        "valid_count": int(row["sum"]),
                        "row_count": int(row["count"]),
                        "coverage": float(row["coverage"]),
                    }
                )
            for split in split_ranges.itertuples(index=False):
                for fold in ("train", "validation", "test"):
                    start = pd.Timestamp(getattr(split, f"{fold}_start"))
                    end = pd.Timestamp(getattr(split, f"{fold}_end"))
                    mask = frame["datetime"].between(start, end)
                    split_total = int(mask.sum())
                    split_valid = int(finite[mask.to_numpy()].sum())
                    split_rows.append(
                        {
                            "factor": factor,
                            "split_id": split.split_id,
                            "fold": fold,
                            "valid_count": split_valid,
                            "row_count": split_total,
                            "coverage": split_valid / split_total if split_total else np.nan,
                        }
                    )
            family_accumulator.setdefault(family, [0, 0])
            family_accumulator[family][0] += valid
            family_accumulator[family][1] += total
            source_accumulator.setdefault(source, [0, 0])
            source_accumulator[source][0] += valid
            source_accumulator[source][1] += total
        for family, family_names in metadata.loc[names].groupby("economic_family").groups.items():
            selected = list(family_names)
            finite_count = np.isfinite(frame[selected].to_numpy(dtype=float)).sum(axis=1)
            factor_count = len(selected)
            for instrument, positions in frame.groupby("instrument").groups.items():
                key = (str(instrument), str(family))
                instrument_accumulator.setdefault(key, [0, 0])
                instrument_accumulator[key][0] += int(finite_count[list(positions)].sum())
                instrument_accumulator[key][1] += len(positions) * factor_count
    month_frame = pd.DataFrame(month_rows)
    if not month_frame.empty:
        month_frame["missingness_class"] = "qualified"
        for factor, positions in month_frame.groupby("factor").groups.items():
            part = month_frame.loc[positions]
            nonempty = part.loc[part["valid_count"].gt(0), "month"]
            if nonempty.empty:
                month_frame.loc[positions, "missingness_class"] = "data_failure_candidate_no_history"
                continue
            first_valid = nonempty.min()
            last_valid = nonempty.max()
            low = part["coverage"].lt(minimum_month_coverage)
            before = part["month"].lt(first_valid)
            within = part["month"].between(first_valid, last_valid)
            zero = part["valid_count"].eq(0)
            month_frame.loc[part.index[low & before], "missingness_class"] = (
                "expected_warmup_or_source_start"
            )
            month_frame.loc[part.index[low & within & zero], "missingness_class"] = (
                "data_failure_candidate_temporal_gap"
            )
            month_frame.loc[part.index[low & ~(before | (within & zero))], "missingness_class"] = (
                "expected_partial_history_or_field_missingness"
            )
        temporal_gaps = (
            month_frame["missingness_class"]
            .eq("data_failure_candidate_temporal_gap")
            .groupby(month_frame["factor"])
            .sum()
        )
    else:
        temporal_gaps = pd.Series(dtype=int)
    factor_frame = pd.DataFrame(factor_rows).sort_values("factor").reset_index(drop=True)
    factor_frame["temporal_gap_candidate_count"] = (
        factor_frame["factor"].map(temporal_gaps).fillna(0).astype(int)
    )
    family_frame = pd.DataFrame(
        [
            {
                "economic_family": key,
                "valid_count": value[0],
                "row_count": value[1],
                "coverage": value[0] / value[1],
                "factor_count": int(factor_frame["economic_family"].eq(key).sum()),
                "research_usable_count": int(
                    factor_frame.loc[factor_frame["economic_family"].eq(key), "research_usable"].sum()
                ),
            }
            for key, value in family_accumulator.items()
        ]
    ).sort_values("economic_family")
    source_frame = pd.DataFrame(
        [
            {
                "source": key,
                "valid_count": value[0],
                "row_count": value[1],
                "coverage": value[0] / value[1],
            }
            for key, value in source_accumulator.items()
        ]
    ).sort_values("source")
    instrument_frame = pd.DataFrame(
        [
            {
                "instrument": key[0],
                "economic_family": key[1],
                "valid_count": value[0],
                "row_count": value[1],
                "coverage": value[0] / value[1] if value[1] else np.nan,
            }
            for key, value in instrument_accumulator.items()
        ]
    ).sort_values(["instrument", "economic_family"])
    return {
        "factor": factor_frame,
        "factor_month": month_frame,
        "factor_split": pd.DataFrame(split_rows),
        "family": family_frame,
        "source": source_frame,
        "instrument_family": instrument_frame,
    }


def raw_source_coverage(
    raw_root: Path,
    expected_trade_dates: list[str],
    expected_statement_segments: list[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    segment_frame, identity = raw_snapshot_summary(raw_root)
    rows: list[dict[str, Any]] = []
    for api in ("daily_basic", "moneyflow", *STATEMENT_FIELDS):
        part = segment_frame.loc[segment_frame["api"].eq(api)]
        expected = expected_trade_dates if api in {"daily_basic", "moneyflow"} else expected_statement_segments
        scoped = part.loc[part["segment"].isin(expected)]
        rows.append(
            {
                "api": api,
                "expected_segment_count": len(expected),
                "observed_segment_count": len(scoped),
                "nonempty_segment_count": int(scoped["row_count"].gt(0).sum()),
                "row_count": int(scoped["row_count"].sum()),
                "size_bytes": int(scoped["size_bytes"].sum()),
                "first_retrieval_time_utc": scoped["retrieval_time_utc"].min(),
                "last_retrieval_time_utc": scoped["retrieval_time_utc"].max(),
                "integrity_pass": bool(
                    len(scoped) == len(expected)
                    and scoped["integrity_status"].eq("pass").all()
                ),
            }
        )
    return pd.DataFrame(rows), {"raw_snapshot_id": identity, "segment_count": len(segment_frame)}


def compare_canonical_to_legacy(
    canonical_partition: Path,
    inventory: pd.DataFrame,
    partition_rows: pd.DataFrame,
) -> pd.DataFrame:
    canonical_meta = inventory.loc[
        inventory["lineage_status"].eq("canonicalized")
        & inventory["canonical_replacement_for"].notna()
        & inventory["canonical_replacement_for"].astype(str).ne("")
    ]
    canonical = pd.read_parquet(canonical_partition)
    rows: list[dict[str, Any]] = []
    for item in canonical_meta.itertuples(index=False):
        parent = str(item.canonical_replacement_for)
        match = partition_rows.loc[
            partition_rows["factors"].astype(str).str.split(",").map(lambda values: parent in values)
        ]
        if match.empty:
            rows.append(
                {"canonical_factor": item.name, "legacy_factor": parent, "status": "parent_not_in_matrix"}
            )
            continue
        legacy = pd.read_parquet(
            match.iloc[0]["partition_path"], columns=["datetime", "instrument", parent]
        )
        joined = canonical[["datetime", "instrument", item.name]].merge(
            legacy, on=["datetime", "instrument"], how="inner", validate="one_to_one"
        )
        pair = (
            joined[[item.name, parent]]
            .apply(pd.to_numeric, errors="coerce")
            .astype(float)
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )
        difference = pair[item.name] - pair[parent]
        rows.append(
            {
                "canonical_factor": item.name,
                "legacy_factor": parent,
                "status": "pass" if len(pair) and difference.ne(0).any() else "no_observed_difference",
                "common_finite_count": len(pair),
                "different_count": int(difference.ne(0).sum()),
                "correlation": (
                    float(pair[item.name].corr(pair[parent]))
                    if len(pair) > 1
                    and pair[item.name].nunique() > 1
                    and pair[parent].nunique() > 1
                    else np.nan
                ),
                "mean_absolute_difference": float(difference.abs().mean()) if len(pair) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def timed(stage: str, started: float, **values: Any) -> dict[str, Any]:
    try:
        import os

        import psutil

        memory = psutil.Process(os.getpid()).memory_info()
        peak_rss_mib = float(getattr(memory, "peak_wset", memory.rss)) / (1024 * 1024)
    except Exception:  # pragma: no cover - optional resource diagnostic
        peak_rss_mib = np.nan
    return {
        "stage": stage,
        "elapsed_seconds": time.perf_counter() - started,
        "peak_rss_mib": peak_rss_mib,
        **values,
    }
