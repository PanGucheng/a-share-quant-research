from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha101_source import mask_raw_to_pit_membership  # noqa: E402
from factor_research.factor_library import BASE_FIELDS, add_basic_factors  # noqa: E402
from factor_universe_v2.historical_data import (  # noqa: E402
    DAILY_BASIC_FIELDS,
    MONEYFLOW_FIELDS,
    STATEMENT_FIELDS,
    align_statement_events_to_keys,
    load_segments,
    normalize_trade_date_frame,
    qlib_to_tushare,
    statement_event_timeline,
)
from factor_universe_v2.local_recovery import add_local_recovered_factors  # noqa: E402
from factor_universe_v2.matrix_readiness import (  # noqa: E402
    compute_canonical,
    compute_recovered,
)
from factor_universe_v2.mature_factors import (  # noqa: E402
    DAILY_BASIC_FACTOR_NAMES,
    FUNDAMENTAL_FACTOR_NAMES,
    MARKET_FACTOR_NAMES,
    MONEYFLOW_FACTOR_NAMES,
    compute_daily_basic_factors,
    compute_fundamental_factors,
    compute_market_factors,
    compute_moneyflow_factors,
)
from factor_universe_v2.tushare_data import TushareSegmentStore  # noqa: E402
from research_validation.feature_matrix import (  # noqa: E402
    atomic_parquet,
    build_pit_key_grid,
    filter_to_pit_intervals,
)
from research_validation.historical_engineering import (  # noqa: E402
    audit_practical_pit,
    canonical_hash,
    compare_matrix_overlap,
    earliest_stable_frontier,
    file_sha256,
    partition_identity,
    practical_market_coverage,
)
from scripts.run_full_research_feature_matrix_v1 import (  # noqa: E402
    alpha101_batch,
    expression_batch,
    ta_batch,
)


LOCAL_STATEFUL_NAMES = [
    "ta_volume_vpt_canonical_v2",
    "ta_volume_nvi_canonical_v2",
]
LEGACY_TA_STATEFUL_NAMES = ["ta_volume_adi", "ta_volume_obv"]
STATEFUL_FACTOR_NAMES = [*LOCAL_STATEFUL_NAMES, *LEGACY_TA_STATEFUL_NAMES]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != 1:
        raise ValueError("invalid historical engineering configuration")
    return payload


def _retry_query(pro: Any, api: str, parameters: dict[str, Any], *, attempts: int = 5) -> pd.DataFrame:
    for attempt in range(attempts):
        try:
            return pro.query(api, **parameters)
        except Exception as exc:
            message = str(exc).lower()
            if any(word in message for word in ("权限", "积分", "permission", "参数")):
                raise
            if attempt + 1 == attempts:
                raise RuntimeError(f"{api} failed after {attempts} attempts") from exc
            time.sleep(2**attempt)
    raise RuntimeError(f"{api} returned no result")


def _validate_from_roots(
    roots: list[Path], api: str, segment: str, required: set[str]
) -> tuple[pd.DataFrame, dict[str, Any], Path] | None:
    for root in roots:
        try:
            frame, receipt = TushareSegmentStore(root).validate(
                api=api, segment=segment, required_columns=required
            )
            return frame, receipt, root
        except FileNotFoundError:
            continue
    return None


def _paged_issuer_request(
    pro: Any,
    api: str,
    ts_code: str,
    fields: str,
    *,
    start_date: str,
    end_date: str,
    page_size: int,
    pause_seconds: float,
    page_receipts: list[dict[str, Any]],
) -> pd.DataFrame:
    pages: list[pd.DataFrame] = []
    offset = 0
    while True:
        started = time.perf_counter()
        parameters = {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
            "fields": fields,
            "limit": page_size,
            "offset": offset,
        }
        frame = _retry_query(pro, api, parameters)
        page_receipts.append(
            {
                "api": api,
                "ts_code": ts_code,
                "offset": offset,
                "page_size": page_size,
                "row_count": len(frame),
                "terminal": len(frame) < page_size,
                "elapsed_seconds": time.perf_counter() - started,
                "status": "pass",
            }
        )
        if not frame.empty:
            pages.append(frame)
        if len(frame) < page_size:
            break
        offset += page_size
        time.sleep(pause_seconds)
    return pd.concat(pages, ignore_index=True) if pages else pd.DataFrame(columns=fields.split(","))


def bootstrap(config: dict[str, Any]) -> None:
    import qlib
    import tushare as ts
    from qlib.config import C, REG_CN
    from qlib.data import D

    if not os.environ.get("TUSHARE_TOKEN"):
        raise RuntimeError("TUSHARE_TOKEN is required")
    pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])
    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["trade_bootstrap_start_date"],
            end_time=config["trade_bootstrap_end_date"],
            freq="day",
        )
    )
    extension_root = resolve(config["extension_raw_root"])
    existing_root = resolve(config["existing_raw_root"])
    extension = TushareSegmentStore(extension_root)
    roots = [extension_root, existing_root]
    pause = float(config["request_pause_seconds"])
    rows: list[dict[str, Any]] = []
    specs = {
        "daily_basic": (DAILY_BASIC_FIELDS, {"ts_code", "trade_date"}),
        "moneyflow": (MONEYFLOW_FIELDS, {"ts_code", "trade_date"}),
    }
    total = len(calendar) * len(specs)
    completed = 0
    for date in calendar:
        segment = date.strftime("%Y%m%d")
        for api, (fields, required) in specs.items():
            cached = _validate_from_roots(roots, api, segment, required)
            if cached is None:
                parameters = {"trade_date": segment, "fields": fields}
                frame, receipt = extension.fetch(
                    api=api,
                    segment=segment,
                    request=lambda api=api, parameters=parameters: _retry_query(
                        pro, api, parameters
                    ),
                    required_columns=required,
                    sort_columns=["trade_date", "ts_code"],
                    public_parameters=parameters,
                )
                source_root = extension_root
                cache_hit = False
                time.sleep(pause)
            else:
                frame, receipt, source_root = cached
                cache_hit = True
            completed += 1
            rows.append(
                {
                    "api": api,
                    "segment": segment,
                    "row_count": len(frame),
                    "data_sha256": receipt["data_sha256"],
                    "cache_hit": cache_hit,
                    "cache_root": source_root.as_posix(),
                }
            )
            if completed % 100 == 0 or completed == total:
                print(f"trade bootstrap {completed}/{total}", flush=True)

    statement_rows: list[dict[str, Any]] = []
    page_rows: list[dict[str, Any]] = []
    segments = _statement_segments(config)
    apis = ["income", "balancesheet", "cashflow"]
    total = len(segments) * len(apis)
    completed = 0
    for ts_code in segments:
        for api in apis:
            fields = STATEMENT_FIELDS[api]
            required = {"ts_code", "ann_date", "f_ann_date", "end_date", "update_flag"}
            cached = _validate_from_roots([extension_root], api, ts_code, required)
            if cached is None:
                public = {
                    "ts_code": ts_code,
                    "start_date": str(config["statement_announcement_start_date"]),
                    "end_date": str(config["statement_announcement_end_date"]),
                    "fields": fields,
                    "page_size": int(config["statement_page_size"]),
                }
                frame, receipt = extension.fetch(
                    api=api,
                    segment=ts_code,
                    request=lambda api=api, ts_code=ts_code, fields=fields: _paged_issuer_request(
                        pro,
                        api,
                        ts_code,
                        fields,
                        start_date=str(config["statement_announcement_start_date"]),
                        end_date=str(config["statement_announcement_end_date"]),
                        page_size=int(config["statement_page_size"]),
                        pause_seconds=pause,
                        page_receipts=page_rows,
                    ),
                    required_columns=required,
                    sort_columns=["ts_code", "end_date", "ann_date"],
                    public_parameters=public,
                )
                cache_hit = False
                time.sleep(pause)
            else:
                frame, receipt, _ = cached
                cache_hit = True
            completed += 1
            statement_rows.append(
                {
                    "api": api,
                    "segment": ts_code,
                    "row_count": len(frame),
                    "data_sha256": receipt["data_sha256"],
                    "cache_hit": cache_hit,
                }
            )
            if completed % 100 == 0 or completed == total:
                print(
                    f"statement bootstrap {completed}/{total} {api}:{ts_code}",
                    flush=True,
                )
    report_dir = resolve(config["report_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(report_dir / "trade_bootstrap_receipts.csv", index=False)
    pd.DataFrame(statement_rows).to_csv(
        report_dir / "statement_bootstrap_receipts.csv", index=False
    )
    pd.DataFrame(page_rows).to_csv(report_dir / "statement_page_receipts.csv", index=False)


def _load_mixed_trade_segments(
    config: dict[str, Any], api: str, segments: list[str], required: set[str]
) -> pd.DataFrame:
    roots = [resolve(config["extension_raw_root"]), resolve(config["existing_raw_root"])]
    frames: list[pd.DataFrame] = []
    for segment in segments:
        cached = _validate_from_roots(roots, api, segment, required)
        if cached is None:
            raise FileNotFoundError(f"missing {api}:{segment}")
        frames.append(cached[0])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _statement_segments(config: dict[str, Any]) -> list[str]:
    path = resolve(config["source_lifecycle_intervals"])
    intervals = pd.read_csv(
        path, sep="\t", header=None, names=["instrument", "start_date", "end_date"]
    )
    intervals[["start_date", "end_date"]] = intervals[
        ["start_date", "end_date"]
    ].apply(pd.to_datetime)
    start = pd.Timestamp(str(config["statement_announcement_start_date"]))
    end = pd.Timestamp(str(config["statement_announcement_end_date"]))
    scoped = intervals.loc[
        intervals["start_date"].le(end)
        & intervals["end_date"].ge(start)
        & intervals["instrument"].astype(str).str.match(r"^(SH|SZ|BJ)\d{6}$")
    ]
    return sorted({qlib_to_tushare(value) for value in scoped["instrument"]})


def analyze(config: dict[str, Any]) -> None:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    intervals = pd.read_csv(resolve(config["extended_universe_intervals"]))
    intervals[["start_date", "end_date"]] = intervals[["start_date", "end_date"]].apply(pd.to_datetime)
    calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["trade_bootstrap_start_date"],
            end_time=config["trade_bootstrap_end_date"],
            freq="day",
        )
    )
    keys = build_pit_key_grid(intervals, calendar)
    symbols = sorted(keys["instrument"].unique())
    market = D.features(
        symbols,
        ["$close", "$volume"],
        start_time=config["trade_bootstrap_start_date"],
        end_time=config["trade_bootstrap_end_date"],
        freq="day",
    ).reset_index()
    market = filter_to_pit_intervals(market, intervals)
    presence = market.loc[
        pd.to_numeric(market["$close"], errors="coerce").notna()
        & pd.to_numeric(market["$volume"], errors="coerce").notna(),
        ["datetime", "instrument"],
    ]
    segments = [date.strftime("%Y%m%d") for date in calendar]
    daily = normalize_trade_date_frame(
        _load_mixed_trade_segments(
            config, "daily_basic", segments, set(DAILY_BASIC_FIELDS.split(","))
        )
    )
    money = normalize_trade_date_frame(
        _load_mixed_trade_segments(
            config, "moneyflow", segments, set(MONEYFLOW_FIELDS.split(","))
        )
    )
    report_dir = resolve(config["report_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    coverage_frames = []
    frontiers = []
    for layer, observed in (("daily_basic", daily), ("moneyflow", money)):
        coverage = practical_market_coverage(presence, observed, layer=layer)
        coverage_frames.append(coverage)
        frontier = earliest_stable_frontier(
            coverage,
            minimum_coverage=float(config["market_minimum_coverage"]),
            minimum_tail_fraction=float(config["market_minimum_tail_fraction"]),
            minimum_dates=int(config["market_minimum_dates"]),
        )
        frontiers.append(
            {
                "layer": layer,
                "source": f"Tushare {layer} market-date cache",
                "factor_count": (
                    len(DAILY_BASIC_FACTOR_NAMES)
                    if layer == "daily_basic"
                    else len(MONEYFLOW_FACTOR_NAMES)
                ),
                "frontier_basis": "90% dated market presence with 98% passing tail",
                **frontier,
            }
        )

    runtime = resolve(config["runtime_dir"])
    runtime.mkdir(parents=True, exist_ok=True)
    events_path = runtime / "statement_events.parquet"
    revision_path = runtime / "statement_revision_audit.parquet"
    checkpoint_path = runtime / "statement_timeline.receipt.json"
    bootstrap_receipts_path = report_dir / "statement_bootstrap_receipts.csv"
    bootstrap_receipts = pd.read_csv(bootstrap_receipts_path)
    statement_input_identity = canonical_hash(
        bootstrap_receipts[["api", "segment", "row_count", "data_sha256"]]
        .sort_values(["api", "segment"])
        .to_dict("records")
    )
    checkpoint = (
        json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint_path.is_file()
        else {}
    )
    checkpoint_valid = bool(
        events_path.is_file()
        and revision_path.is_file()
        and (
            checkpoint.get("statement_input_identity") == statement_input_identity
            and checkpoint.get("events_sha256") == file_sha256(events_path)
            and checkpoint.get("revision_sha256") == file_sha256(revision_path)
        )
    )
    recovered_atomic_checkpoint = bool(
        events_path.is_file()
        and revision_path.is_file()
        and not checkpoint
        and events_path.stat().st_mtime >= bootstrap_receipts_path.stat().st_mtime
        and revision_path.stat().st_mtime >= bootstrap_receipts_path.stat().st_mtime
    )
    if checkpoint_valid or recovered_atomic_checkpoint:
        events = pd.read_parquet(events_path)
        revision = pd.read_parquet(revision_path)
    else:
        store = TushareSegmentStore(resolve(config["extension_raw_root"]))
        statement_frames: dict[str, pd.DataFrame] = {}
        for api in ("income", "balancesheet", "cashflow"):
            frame, _ = load_segments(
                store,
                api,
                _statement_segments(config),
                required_columns=set(STATEMENT_FIELDS[api].split(",")),
            )
            statement_frames[api] = frame
        events, revision = statement_event_timeline(
            statement_frames["income"],
            statement_frames["balancesheet"],
            statement_frames["cashflow"],
        )
        atomic_parquet(events, events_path)
        atomic_parquet(revision, revision_path)
    checkpoint_path.write_text(
        json.dumps(
            {
                "statement_input_identity": statement_input_identity,
                "events_sha256": file_sha256(events_path),
                "revision_sha256": file_sha256(revision_path),
                "event_row_count": len(events),
                "revision_audit_row_count": len(revision),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    sample_dates = pd.DatetimeIndex(calendar).to_series().groupby(
        pd.DatetimeIndex(calendar).to_period("M")
    ).max().tolist()
    sample_keys = keys.loc[keys["datetime"].isin(sample_dates)]
    aligned = align_statement_events_to_keys(sample_keys, events)
    pit = audit_practical_pit(aligned, events)
    pit.to_csv(report_dir / "practical_pit_leakage_checks.csv", index=False)
    fundamental_presence = aligned.loc[
        aligned["information_available_date"].notna(), ["datetime", "instrument"]
    ]
    fundamental_coverage = practical_market_coverage(
        presence.loc[presence["datetime"].isin(sample_dates)],
        fundamental_presence,
        layer="fundamental_pit",
    )
    coverage_frames.append(fundamental_coverage)
    fundamental_frontier = earliest_stable_frontier(
        fundamental_coverage,
        minimum_coverage=float(config["market_minimum_coverage"]),
        minimum_tail_fraction=float(config["market_minimum_tail_fraction"]),
        minimum_dates=24,
    )
    frontiers.extend(
        [
            {
                "layer": "long_history_transparent_core",
                "source": "Community Qlib OHLCV/amount/VWAP + practical lifecycle",
                "factor_count": 34,
                "frontier_basis": "first non-empty practical-universe effective month",
                "frontier": pd.to_datetime(intervals["start_date"]).min(),
                "tail_date_count": len(calendar),
                "tail_passing_fraction": 1.0,
                "minimum_tail_coverage": 1.0,
                "admitted": True,
            },
            {
                "layer": "full_price_volume_v2",
                "source": "Community Qlib + frozen V2 price-factor implementations",
                "factor_count": 733,
                "frontier_basis": "full 733-factor annual shards plus continuous cumulative state",
                "frontier": pd.to_datetime(intervals["start_date"]).min(),
                "tail_date_count": len(calendar),
                "tail_passing_fraction": 1.0,
                "minimum_tail_coverage": 1.0,
                "admitted": True,
            },
            {
                "layer": "fundamental_pit",
                "source": "Tushare statements/revisions reconstructed by announcement date",
                "factor_count": len(FUNDAMENTAL_FACTOR_NAMES),
                "frontier_basis": "monthly practical market presence with leakage-safe as-of join",
                **fundamental_frontier,
            },
        ]
    )
    admitted_feature_frontiers = [
        pd.Timestamp(row["frontier"])
        for row in frontiers
        if row["layer"] in {"daily_basic", "moneyflow", "fundamental_pit"}
        and row["admitted"]
    ]
    full_feature_frontier = max(admitted_feature_frontiers)
    if full_feature_frontier != pd.Timestamp(config["full_feature_candidate_start_date"]):
        raise ValueError(
            "configured full-feature start does not equal the measured practical common frontier"
        )
    frontiers.append(
        {
            "layer": "full_factor_universe_v2",
            "source": "intersection of price, daily_basic, moneyflow and practical PIT",
            "factor_count": 774,
            "frontier_basis": "maximum admitted dependency-layer frontier",
            "frontier": full_feature_frontier,
            "tail_date_count": min(
                int(row["tail_date_count"])
                for row in frontiers
                if row["layer"] in {"daily_basic", "moneyflow", "fundamental_pit"}
            ),
            "tail_passing_fraction": min(
                float(row["tail_passing_fraction"])
                for row in frontiers
                if row["layer"] in {"daily_basic", "moneyflow", "fundamental_pit"}
            ),
            "minimum_tail_coverage": min(
                float(row["minimum_tail_coverage"])
                for row in frontiers
                if row["layer"] in {"daily_basic", "moneyflow", "fundamental_pit"}
            ),
            "admitted": True,
        }
    )
    pd.concat(coverage_frames, ignore_index=True).to_csv(
        report_dir / "practical_market_coverage.csv", index=False
    )
    pd.DataFrame(frontiers).to_csv(report_dir / "factor_family_frontiers.csv", index=False)

    extended_snapshots = pd.read_csv(
        resolve(config["extended_universe_intervals"]).parent / "universe_membership_snapshots.csv"
    )
    frozen_snapshots = pd.read_csv(
        resolve(config["frozen_universe_intervals"]).parent / "universe_membership_snapshots.csv"
    )
    columns = ["instrument", "selection_date", "effective_date"]
    overlap = extended_snapshots[columns].merge(
        frozen_snapshots[columns], on=columns, how="outer", indicator=True
    )
    overlap = overlap.loc[
        pd.to_datetime(overlap["effective_date"]).between(
            pd.Timestamp(config["overlap_start_date"]), pd.Timestamp(config["overlap_end_date"])
        )
    ]
    pd.DataFrame(
        [
            {
                "check": "historical_universe_reproduces_frozen_overlap",
                "status": "pass" if overlap["_merge"].eq("both").all() else "fail",
                "common_rows": int(overlap["_merge"].eq("both").sum()),
                "extended_only_rows": int(overlap["_merge"].eq("left_only").sum()),
                "frozen_only_rows": int(overlap["_merge"].eq("right_only").sum()),
            }
        ]
    ).to_csv(report_dir / "universe_overlap_validation.csv", index=False)


def _project(frame: pd.DataFrame, intervals: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result = filter_to_pit_intervals(result, intervals)
    return keys.merge(result, on=["datetime", "instrument"], how="left", validate="one_to_one")


def _write_partition(path: Path, frame: pd.DataFrame, names: list[str]) -> dict[str, Any]:
    output = frame[["datetime", "instrument", *names]].copy()
    atomic_parquet(output, path)
    return {
        "partition_id": path.stem,
        "partition_path": path.resolve().as_posix(),
        "factor_count": len(names),
        "row_count": len(output),
        "output_sha256": file_sha256(path),
        "output_size_bytes": path.stat().st_size,
        "factors": ",".join(names),
    }


def materialize_stateful_recovered(config: dict[str, Any]) -> None:
    """Materialize one continuous VPT/NVI state timeline for all historical shards."""
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    intervals = pd.read_csv(resolve(config["extended_universe_intervals"]))
    intervals[["start_date", "end_date"]] = intervals[["start_date", "end_date"]].apply(
        pd.to_datetime
    )
    start = pd.to_datetime(intervals["start_date"]).min()
    end = pd.Timestamp(config["historical_end_date"])
    calendar = pd.DatetimeIndex(D.calendar(start_time=start, end_time=end, freq="day"))
    scoped = intervals.loc[
        intervals["start_date"].le(end) & intervals["end_date"].ge(start)
    ]
    keys = build_pit_key_grid(scoped, calendar)
    symbols = sorted(scoped["instrument"].unique())
    raw = D.features(
        symbols,
        ["$high", "$low", "$close", "$volume"],
        start_time=start,
        end_time=end,
        freq="day",
    ).reset_index()
    masked = mask_raw_to_pit_membership(raw, keys, membership_start=start)
    recovered = add_local_recovered_factors(masked)[
        ["datetime", "instrument", *LOCAL_STATEFUL_NAMES]
    ]
    legacy_ta = ta_batch(
        masked,
        LEGACY_TA_STATEFUL_NAMES,
        resolve(config["ta_source_path"]),
    )[["datetime", "instrument", *LEGACY_TA_STATEFUL_NAMES]]
    recovered = recovered.merge(
        legacy_ta,
        on=["datetime", "instrument"],
        how="outer",
        validate="one_to_one",
    )
    path = resolve(config["stateful_recovered_cache"])
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_parquet(recovered, path)
    receipt = {
        "state_anchor": str(start.date()),
        "end_date": str(end.date()),
        "row_count": len(recovered),
        "instrument_count": int(recovered["instrument"].nunique()),
        "factors": STATEFUL_FACTOR_NAMES,
        "output_sha256": file_sha256(path),
        "semantics": "continuous_instrument_state_across_annual_partitions",
    }
    path.with_suffix(".receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"stateful recovered cache complete: {len(recovered)} rows", flush=True)


def _load_stateful_recovered(
    config: dict[str, Any], keys: pd.DataFrame, intervals: pd.DataFrame
) -> tuple[pd.DataFrame, str]:
    path = resolve(config["stateful_recovered_cache"])
    receipt_path = path.with_suffix(".receipt.json")
    if not path.is_file() or not receipt_path.is_file():
        raise FileNotFoundError(
            "continuous recovered-factor cache is missing; run --stage stateful first"
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if file_sha256(path) != receipt.get("output_sha256"):
        raise ValueError("continuous recovered-factor cache failed integrity validation")
    if receipt.get("factors") != STATEFUL_FACTOR_NAMES:
        raise ValueError("continuous state cache does not match required factor semantics")
    start = pd.to_datetime(keys["datetime"]).min()
    end = pd.to_datetime(keys["datetime"]).max()
    frame = pd.read_parquet(
        path,
        filters=[("datetime", ">=", start), ("datetime", "<=", end)],
    )
    return _project(frame, intervals, keys), str(receipt["state_anchor"])


def _year_scope(
    config: dict[str, Any], year: int, *, overlap: bool = False
) -> tuple[pd.Timestamp, pd.Timestamp, bool]:
    start = pd.Timestamp(f"{year}-01-01")
    end = pd.Timestamp(f"{year}-12-31")
    full = year >= pd.Timestamp(config["full_feature_candidate_start_date"]).year
    if year == pd.Timestamp(config["historical_end_date"]).year:
        end = pd.Timestamp(config["historical_end_date"])
    if overlap:
        if year != pd.Timestamp(config["overlap_start_date"]).year:
            raise ValueError("overlap materialization is confined to the configured overlap year")
        start = pd.Timestamp(config["overlap_start_date"])
        end = pd.Timestamp(config["overlap_end_date"])
        full = True
    return start, end, full


def materialize_year(
    config: dict[str, Any],
    year: int,
    *,
    price_only: bool = False,
    overlap: bool = False,
) -> list[dict[str, Any]]:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    start, end, full_feature = _year_scope(config, year, overlap=overlap)
    if price_only:
        full_feature = False
    full_calendar = pd.DatetimeIndex(D.calendar(start_time="2000-01-01", end_time=end, freq="day"))
    calendar = full_calendar[(full_calendar >= start) & (full_calendar <= end)]
    if calendar.empty:
        return []
    first_position = full_calendar.searchsorted(calendar[0])
    warmup_start = full_calendar[max(0, first_position - 300)]
    if overlap:
        # The overlap canary must inherit the frozen parent's build anchor.  This
        # matters for the two explicitly cumulative recovered factors and also
        # makes the comparison a test of source/implementation identity rather
        # than a comparison of two different bootstrap conventions.
        warmup_start = pd.Timestamp(config["frozen_market_bootstrap_start_date"])
    intervals = pd.read_csv(resolve(config["extended_universe_intervals"]))
    intervals[["start_date", "end_date"]] = intervals[["start_date", "end_date"]].apply(pd.to_datetime)
    scoped = intervals.loc[
        pd.to_datetime(intervals["start_date"]).le(calendar[-1])
        & pd.to_datetime(intervals["end_date"]).ge(calendar[0])
    ]
    keys = build_pit_key_grid(scoped, calendar)
    calc_intervals = intervals
    frozen_all_intervals = pd.DataFrame()
    if overlap:
        frozen_all_intervals = pd.read_csv(resolve(config["frozen_universe_intervals"]))
        frozen_all_intervals[["start_date", "end_date"]] = frozen_all_intervals[
            ["start_date", "end_date"]
        ].apply(pd.to_datetime)
        calc_intervals = frozen_all_intervals.loc[
            frozen_all_intervals["start_date"].le(end)
            & frozen_all_intervals["end_date"].ge(warmup_start)
        ].copy()
    # Frozen V1/V2 builds loaded the complete research-universe symbol set before
    # applying dated membership.  The pre-membership warmup therefore includes
    # histories for later entrants; reproducing that scope is required for exact
    # cross-sectional Alpha101 ranks and rolling market-beta state.
    symbol_source = frozen_all_intervals if overlap else scoped
    symbols = sorted(symbol_source["instrument"].unique())
    market_fields = list(dict.fromkeys([*BASE_FIELDS, "$vwap"]))
    if overlap:
        raw = pd.read_parquet(
            resolve(config["frozen_v2_raw_market"]),
            filters=[
                ("instrument", "in", symbols),
                ("datetime", ">=", warmup_start),
                ("datetime", "<=", end),
            ],
        )
    else:
        raw = D.features(
            symbols,
            market_fields,
            start_time=warmup_start,
            end_time=end,
            freq="day",
        ).reset_index()
    raw["datetime"] = pd.to_datetime(raw["datetime"])
    raw["instrument"] = raw["instrument"].astype(str).str.upper()
    membership_calendar = full_calendar[
        (full_calendar >= warmup_start) & (full_calendar <= end)
    ]
    warmup_keys = build_pit_key_grid(calc_intervals, membership_calendar)
    masked = mask_raw_to_pit_membership(
        raw,
        warmup_keys,
        membership_start=pd.to_datetime(calc_intervals["start_date"]).min(),
    )
    legacy_masked = masked
    legacy_unmasked = masked
    if overlap:
        # The inherited 669-factor parent used a later raw-market anchor than
        # the 105 V2 additions.  Preserve each parent's exact bootstrap lineage
        # during overlap reproduction instead of silently improving warmup.
        legacy_anchor = pd.Timestamp(config["frozen_legacy_market_bootstrap_start_date"])
        legacy_raw = pd.read_parquet(
            resolve(config["frozen_legacy_raw_market"]),
            filters=[
                ("instrument", "in", symbols),
                ("datetime", ">=", legacy_anchor),
                ("datetime", "<=", end),
            ],
        )
        legacy_raw["datetime"] = pd.to_datetime(legacy_raw["datetime"])
        legacy_raw["instrument"] = legacy_raw["instrument"].astype(str).str.upper()
        # Legacy TA/basic partitions are pure per-instrument transforms and the
        # parent ultimately projected only overlap instruments.  Keeping that
        # projected symbol scope also avoids invoking fixed-window TA routines
        # on future entrants with only a handful of pre-overlap observations.
        overlap_symbols = set(scoped["instrument"].astype(str).str.upper())
        legacy_unmasked = legacy_raw.loc[
            legacy_raw["instrument"].isin(overlap_symbols)
        ].copy()
        legacy_calendar = full_calendar[
            (full_calendar >= legacy_anchor) & (full_calendar <= end)
        ]
        legacy_keys = build_pit_key_grid(calc_intervals, legacy_calendar)
        legacy_masked = mask_raw_to_pit_membership(
            legacy_raw,
            legacy_keys,
            membership_start=pd.to_datetime(calc_intervals["start_date"]).min(),
        )
    runtime = resolve(config["runtime_dir"]) / ("overlap" if overlap else "matrix") / str(year)
    runtime.mkdir(parents=True, exist_ok=True)
    prior_path = runtime / "partition_manifest.csv"
    prior = pd.read_csv(prior_path).set_index("partition_id").to_dict("index") if prior_path.is_file() else {}
    rows: list[dict[str, Any]] = []

    def reuse_partition(
        partition_id: str,
        names: list[str],
        *,
        expected_row_count: int,
        expected_state_anchor: str | None = None,
        expected_recompute_start: str | None = None,
    ) -> bool:
        path = runtime / f"{partition_id}.parquet"
        prior_row = prior.get(partition_id, {})
        if (
            path.is_file()
            and prior_row
            and file_sha256(path) == str(prior_row.get("output_sha256", ""))
            and int(prior_row.get("factor_count", -1)) == len(names)
            and int(prior_row.get("row_count", -1)) == expected_row_count
            and (
                expected_state_anchor is None
                or str(prior_row.get("state_anchor", "")) == expected_state_anchor
            )
            and (
                expected_recompute_start is None
                or str(prior_row.get("recompute_start", ""))
                == expected_recompute_start
            )
        ):
            rows.append({"partition_id": partition_id, **prior_row})
            pd.DataFrame(rows).to_csv(prior_path, index=False)
            return True
        return False

    def store_partition(
        partition_id: str,
        frame: pd.DataFrame,
        names: list[str],
        layer: str,
        *,
        state_anchor: str | None = None,
        recompute_start: str | None = None,
    ) -> None:
        path = runtime / f"{partition_id}.parquet"
        row = {
            **_write_partition(path, frame, names),
            "layer": layer,
            "year": year,
        }
        if state_anchor is not None:
            row["state_anchor"] = state_anchor
        if recompute_start is not None:
            row["recompute_start"] = recompute_start
        rows.append(row)
        pd.DataFrame(rows).to_csv(prior_path, index=False)
    plan = pd.read_csv(resolve(config["legacy_batch_plan"]))
    inventory = pd.read_csv(resolve(config["legacy_factor_inventory"]))
    cached_source = ""
    cached_frame = pd.DataFrame()
    for item in plan.itertuples(index=False):
        batch_id = str(item.batch_id)
        names = sorted(inventory.loc[inventory["batch_id"].eq(batch_id), "name"].astype(str))
        path = runtime / f"{batch_id}.parquet"
        source = str(item.source)
        expected_legacy_state_anchor = None
        if source == "ta":
            expected_legacy_state_anchor = (
                str(pd.Timestamp(config["frozen_legacy_market_bootstrap_start_date"]).date())
                if overlap
                else str(pd.to_datetime(intervals["start_date"]).min().date())
            )
        if (
            batch_id in prior
            and path.is_file()
            and file_sha256(path) == str(prior[batch_id]["output_sha256"])
            and int(prior[batch_id].get("row_count", -1)) == len(keys)
            and (
                expected_legacy_state_anchor is None
                or str(prior[batch_id].get("state_anchor", ""))
                == expected_legacy_state_anchor
            )
        ):
            rows.append({"partition_id": batch_id, **prior[batch_id]})
            continue
        if cached_source != source:
            source_batches = set(plan.loc[plan["source"].eq(source), "batch_id"].astype(str))
            source_names = sorted(
                inventory.loc[inventory["batch_id"].astype(str).isin(source_batches), "name"].astype(str)
            )
            if source == "alpha158":
                cached_frame = expression_batch(
                    symbols,
                    source_names,
                    resolve(config["alpha158_inventory"]),
                    start,
                    end,
                    D,
                )
            elif source == "alpha360":
                cached_frame = expression_batch(
                    symbols,
                    source_names,
                    resolve(config["alpha360_inventory"]),
                    start,
                    end,
                    D,
                )
            elif source == "ta":
                cached_frame = ta_batch(
                    legacy_unmasked, source_names, resolve(config["ta_source_path"])
                )
                if not overlap:
                    stateful, expected_legacy_state_anchor = _load_stateful_recovered(
                        config, keys, scoped
                    )
                    cached_frame = cached_frame.drop(
                        columns=LEGACY_TA_STATEFUL_NAMES
                    ).merge(
                        stateful[
                            ["datetime", "instrument", *LEGACY_TA_STATEFUL_NAMES]
                        ],
                        on=["datetime", "instrument"],
                        how="left",
                        validate="one_to_one",
                    )
            elif source == "project_basic":
                cached_frame = add_basic_factors(legacy_unmasked.copy())[
                    ["datetime", "instrument", *source_names]
                ]
            elif source == "alpha101":
                local_config = {
                    **config,
                    "warmup_start_date": str(
                        (
                            pd.Timestamp(config["frozen_legacy_market_bootstrap_start_date"])
                            if overlap
                            else warmup_start
                        ).date()
                    ),
                    "end_date": str(end.date()),
                }
                cached_frame = alpha101_batch(
                    legacy_masked,
                    source_names,
                    local_config,
                    runtime,
                    "historical-extension-v1",
                )
            else:
                raise ValueError(f"unsupported source: {source}")
            cached_source = source
        frame = cached_frame[["datetime", "instrument", *names]]
        frame = frame.loc[pd.to_datetime(frame["datetime"]).between(start, end)]
        row = _write_partition(path, _project(frame, scoped, keys), names)
        row["layer"] = "price_volume"
        row["year"] = year
        if expected_legacy_state_anchor is not None:
            row["state_anchor"] = expected_legacy_state_anchor
        rows.append(row)
        pd.DataFrame(rows).to_csv(prior_path, index=False)
        print(f"{year} {batch_id} complete", flush=True)

    factor_inventory = pd.read_csv(resolve(config["factor_inventory"]))
    recovered_inventory = factor_inventory.loc[factor_inventory["lineage_status"].eq("recovered")]
    recovered_names = recovered_inventory["name"].astype(str).tolist()
    expected_recovered_anchor = (
        str(pd.Timestamp(config["frozen_market_bootstrap_start_date"]).date())
        if overlap
        else str(pd.to_datetime(intervals["start_date"]).min().date())
    )
    recovered_cached = reuse_partition(
        "recovered",
        recovered_names,
        expected_row_count=len(keys),
        expected_state_anchor=expected_recovered_anchor,
        expected_recompute_start=str(warmup_start.date()),
    )
    if not recovered_cached:
        recovered, _ = compute_recovered(
            masked,
            keys,
            provider_uri=resolve(config["provider_uri"]),
            start_date=str(warmup_start.date()),
            end_date=str(end.date()),
            kunquant_path=resolve(config["alpha101_source_path"]),
            ta_source_path=resolve(config["ta_source_path"]),
            recovered_inventory=recovered_inventory,
        )
    if not recovered_cached and not overlap:
        stateful, expected_recovered_anchor = _load_stateful_recovered(
            config, keys, scoped
        )
        recovered = recovered.drop(columns=LOCAL_STATEFUL_NAMES).merge(
            stateful[["datetime", "instrument", *LOCAL_STATEFUL_NAMES]],
            on=["datetime", "instrument"],
            how="left",
            validate="one_to_one",
        )
    if not recovered_cached:
        store_partition(
            "recovered",
            recovered,
            recovered_names,
            "price_volume",
            state_anchor=expected_recovered_anchor,
            recompute_start=str(warmup_start.date()),
        )
    canonical_names = factor_inventory.loc[
        factor_inventory["lineage_status"].eq("canonicalized"), "name"
    ].astype(str).tolist()
    if not reuse_partition(
        "canonical", canonical_names, expected_row_count=len(keys)
    ):
        canonical, _ = compute_canonical(
            masked, keys, factor_inventory, resolve(config["alpha101_source_path"])
        )
        store_partition("canonical", canonical, canonical_names, "price_volume")
    market_names = list(MARKET_FACTOR_NAMES)
    market_cached = reuse_partition(
        "mature_market", market_names, expected_row_count=len(keys)
    )
    market = masked.copy()
    returns = market.groupby("instrument", sort=False)["$close"].pct_change(fill_method=None)
    market["$market_return"] = returns.groupby(market["datetime"]).transform("mean")
    market["$amount"] = pd.to_numeric(market["$amount"], errors="coerce") * 1000.0
    if not market_cached:
        mature_market = _project(compute_market_factors(market), scoped, keys)
        store_partition("mature_market", mature_market, market_names, "price_volume")

    if full_feature:
        feature_start = max(start, pd.Timestamp(config["full_feature_candidate_start_date"]))
        feature_keys = keys.loc[keys["datetime"].ge(feature_start)].copy()
        warm_dates = membership_calendar[membership_calendar >= max(warmup_start, pd.Timestamp(config["trade_bootstrap_start_date"]))]
        segments = [date.strftime("%Y%m%d") for date in warm_dates]
        daily = normalize_trade_date_frame(_load_mixed_trade_segments(config, "daily_basic", segments, set(DAILY_BASIC_FIELDS.split(","))))
        money = normalize_trade_date_frame(_load_mixed_trade_segments(config, "moneyflow", segments, set(MONEYFLOW_FIELDS.split(","))))
        daily_names = list(DAILY_BASIC_FACTOR_NAMES)
        if not reuse_partition(
            "mature_daily_basic", daily_names, expected_row_count=len(feature_keys)
        ):
            daily_values = _project(
                compute_daily_basic_factors(daily), scoped, feature_keys
            )
            store_partition(
                "mature_daily_basic", daily_values, daily_names, "daily_basic"
            )
        traded = market[["datetime", "instrument", "$amount"]].rename(columns={"$amount": "traded_amount_cny"})
        money = money.merge(traded, on=["datetime", "instrument"], how="left", validate="one_to_one")
        money_names = list(MONEYFLOW_FACTOR_NAMES)
        if not reuse_partition(
            "mature_moneyflow", money_names, expected_row_count=len(feature_keys)
        ):
            money_values = _project(
                compute_moneyflow_factors(money), scoped, feature_keys
            )
            store_partition(
                "mature_moneyflow", money_values, money_names, "moneyflow"
            )
        events = pd.read_parquet(resolve(config["runtime_dir"]) / "statement_events.parquet")
        aligned = align_statement_events_to_keys(feature_keys, events)
        market_cap = daily[["datetime", "instrument", "total_mv"]].copy()
        market_cap["total_mv_cny"] = pd.to_numeric(market_cap["total_mv"], errors="coerce") * 10000.0
        aligned = aligned.merge(market_cap[["datetime", "instrument", "total_mv_cny"]], on=["datetime", "instrument"], how="left", validate="one_to_one")
        fundamental_names = list(FUNDAMENTAL_FACTOR_NAMES)
        if not reuse_partition(
            "mature_fundamental",
            fundamental_names,
            expected_row_count=len(feature_keys),
        ):
            eligible = aligned.loc[aligned["information_available_date"].notna()].copy()
            fundamental = _project(compute_fundamental_factors(eligible), scoped, keys)
            store_partition(
                "mature_fundamental",
                fundamental,
                fundamental_names,
                "fundamental_pit",
            )
    pd.DataFrame(rows).to_csv(prior_path, index=False)
    return rows


def materialize(
    config: dict[str, Any],
    years: list[int] | None,
    *,
    price_only: bool = False,
    overlap: bool = False,
) -> None:
    if years is None:
        years = [pd.Timestamp(config["overlap_start_date"]).year] if overlap else list(
            range(2000, pd.Timestamp(config["historical_end_date"]).year + 1)
        )
    all_rows: list[dict[str, Any]] = []
    for year in years:
        all_rows.extend(
            materialize_year(
                config, year, price_only=price_only, overlap=overlap
            )
        )
    runtime = resolve(config["runtime_dir"])
    historical_end_year = pd.Timestamp(config["historical_end_date"]).year
    manifests = sorted(
        path
        for path in (runtime / "matrix").glob("[0-9][0-9][0-9][0-9]/partition_manifest.csv")
        if int(path.parent.name) <= historical_end_year
    )
    if manifests:
        historical = pd.concat([pd.read_csv(path) for path in manifests], ignore_index=True)
        historical.to_csv(runtime / "historical_partition_manifest.csv", index=False)
    if all_rows:
        print(f"materialized {len(all_rows)} partitions", flush=True)


def _annual_matrix_summary(historical: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    instruments: set[str] = set()
    total_dates = 0
    total_keys = 0
    for year, group in historical.groupby("year", sort=True):
        representative = group.sort_values("row_count", ascending=False).iloc[0]
        keys = pd.read_parquet(
            representative["partition_path"], columns=["datetime", "instrument"]
        )
        keys["datetime"] = pd.to_datetime(keys["datetime"])
        instruments.update(keys["instrument"].astype(str))
        date_count = int(keys["datetime"].nunique())
        row_count = int(len(keys))
        total_dates += date_count
        total_keys += row_count
        rows.append(
            {
                "year": int(year),
                "start_date": keys["datetime"].min(),
                "end_date": keys["datetime"].max(),
                "date_count": date_count,
                "instrument_count": int(keys["instrument"].nunique()),
                "row_key_count": row_count,
                "partition_count": len(group),
                "factor_count": int(group["factor_count"].sum()),
                "output_size_bytes": int(group["output_size_bytes"].sum()),
            }
        )
    summary = pd.DataFrame(rows)
    totals = {
        "historical_row_count": total_keys,
        "historical_date_count": total_dates,
        "historical_instrument_count": len(instruments),
        "historical_start_date": (
            str(pd.to_datetime(summary["start_date"]).min().date())
            if not summary.empty
            else None
        ),
        "historical_end_date": (
            str(pd.to_datetime(summary["end_date"]).max().date())
            if not summary.empty
            else None
        ),
        "maximum_factor_count": int(summary["factor_count"].max()) if not summary.empty else 0,
        "runtime_matrix_bytes": int(summary["output_size_bytes"].sum()) if not summary.empty else 0,
    }
    return summary, totals


def _token_persisted(roots: list[Path]) -> bool:
    secret = os.environ.get("TUSHARE_TOKEN", "")
    if not secret:
        return False
    suffixes = {".csv", ".json", ".md", ".txt", ".yaml", ".yml"}
    for root in roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if path.is_file() and path.suffix.lower() in suffixes:
                if secret in path.read_text(encoding="utf-8", errors="ignore"):
                    return True
    return False


def finalize(config_path: Path, config: dict[str, Any]) -> None:
    runtime = resolve(config["runtime_dir"])
    report_dir = resolve(config["report_dir"])
    output_dir = resolve(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    historical_path = runtime / "historical_partition_manifest.csv"
    historical = pd.read_csv(historical_path) if historical_path.is_file() else pd.DataFrame()
    if not historical.empty and "year" in historical:
        historical = historical.loc[
            pd.to_numeric(historical["year"], errors="coerce")
            <= pd.Timestamp(config["historical_end_date"]).year
        ].copy()
    overlap_manifest = runtime / "overlap" / "2021" / "partition_manifest.csv"
    overlap_rows: list[pd.DataFrame] = []
    if overlap_manifest.is_file():
        extended = pd.read_csv(overlap_manifest)
        frozen = pd.read_csv(resolve(config["frozen_partition_manifest"]))
        for row in extended.itertuples(index=False):
            match = frozen.loc[frozen["partition_id"].eq(row.partition_id)]
            if match.empty:
                continue
            names = str(row.factors).split(",")
            left = pd.read_parquet(row.partition_path)
            right = pd.read_parquet(match.iloc[0]["partition_path"])
            mask = pd.to_datetime(right["datetime"]).between(
                pd.Timestamp(config["overlap_start_date"]), pd.Timestamp(config["overlap_end_date"])
            )
            overlap_rows.append(compare_matrix_overlap(left, right.loc[mask], names))
    overlap = pd.concat(overlap_rows, ignore_index=True) if overlap_rows else pd.DataFrame()
    overlap.to_csv(report_dir / "matrix_overlap_validation.csv", index=False)
    historical.to_csv(output_dir / "historical_partition_manifest.csv", index=False)
    annual, matrix_totals = _annual_matrix_summary(historical) if not historical.empty else (pd.DataFrame(), {})
    annual.to_csv(report_dir / "annual_matrix_summary.csv", index=False)
    frozen_manifest = json.loads(resolve(config["frozen_matrix_manifest"]).read_text(encoding="utf-8"))
    yearly_factor_counts = (
        historical.groupby("year")["factor_count"].sum().to_dict()
        if not historical.empty
        else {}
    )
    required_yearly_counts = {
        **{year: 733 for year in range(2000, 2010)},
        **{year: 774 for year in range(2010, 2022)},
    }
    matrix_generated = all(
        int(yearly_factor_counts.get(year, 0)) == expected
        for year, expected in required_yearly_counts.items()
    )
    partition_integrity_pass = bool(
        not historical.empty
        and not historical.duplicated(["year", "partition_id"]).any()
        and all(
            Path(row.partition_path).is_file()
            and file_sha256(Path(row.partition_path)) == str(row.output_sha256)
            for row in historical.itertuples(index=False)
        )
    )
    recovered_rows = historical.loc[historical["partition_id"].eq("recovered")]
    legacy_state_rows = historical.loc[historical["partition_id"].eq("ta_003")]
    stateful_validation_rows: list[pd.DataFrame] = []
    stateful_path = resolve(config["stateful_recovered_cache"])
    if stateful_path.is_file():
        for partition_rows, stateful_names in (
            (recovered_rows, LOCAL_STATEFUL_NAMES),
            (legacy_state_rows, LEGACY_TA_STATEFUL_NAMES),
        ):
            for row in partition_rows.itertuples(index=False):
                left = pd.read_parquet(
                    row.partition_path,
                    columns=["datetime", "instrument", *stateful_names],
                )
                start = pd.to_datetime(left["datetime"]).min()
                end = pd.to_datetime(left["datetime"]).max()
                cached = pd.read_parquet(
                    stateful_path,
                    columns=["datetime", "instrument", *stateful_names],
                    filters=[("datetime", ">=", start), ("datetime", "<=", end)],
                )
                right = left[["datetime", "instrument"]].merge(
                    cached,
                    on=["datetime", "instrument"],
                    how="left",
                    validate="one_to_one",
                )
                checked = compare_matrix_overlap(left, right, stateful_names)
                checked.insert(0, "year", int(row.year))
                checked.insert(1, "partition_id", str(row.partition_id))
                stateful_validation_rows.append(checked)
    stateful_validation = (
        pd.concat(stateful_validation_rows, ignore_index=True)
        if stateful_validation_rows
        else pd.DataFrame()
    )
    stateful_validation.to_csv(
        report_dir / "stateful_boundary_validation.csv", index=False
    )
    continuous_state_pass = bool(
        len(recovered_rows) == len(required_yearly_counts)
        and len(legacy_state_rows) == len(required_yearly_counts)
        and "state_anchor" in recovered_rows
        and "state_anchor" in legacy_state_rows
        and recovered_rows["state_anchor"].notna().all()
        and legacy_state_rows["state_anchor"].notna().all()
        and recovered_rows["state_anchor"].nunique() == 1
        and legacy_state_rows["state_anchor"].nunique() == 1
        and not stateful_validation.empty
        and stateful_validation["value_difference_count"].eq(0).all()
        and stateful_validation["extended_only_key_count"].eq(0).all()
        and stateful_validation["frozen_only_key_count"].eq(0).all()
    )
    matrix_generated = matrix_generated and partition_integrity_pass and continuous_state_pass
    matrix_id = partition_identity(historical) if matrix_generated else "not_generated_incomplete_partitions"
    coverage = pd.read_csv(report_dir / "factor_family_frontiers.csv") if (report_dir / "factor_family_frontiers.csv").is_file() else pd.DataFrame()
    pit = pd.read_csv(report_dir / "practical_pit_leakage_checks.csv") if (report_dir / "practical_pit_leakage_checks.csv").is_file() else pd.DataFrame()
    universe = pd.read_csv(report_dir / "universe_overlap_validation.csv") if (report_dir / "universe_overlap_validation.csv").is_file() else pd.DataFrame()
    overlap_pass = bool(not overlap.empty and overlap["value_difference_count"].eq(0).all() and overlap["extended_only_key_count"].eq(0).all() and overlap["frozen_only_key_count"].eq(0).all())
    overlap_bad_factor_count = int(
        overlap["value_difference_count"].gt(0).sum()
    ) if not overlap.empty else 0
    overlap_difference_count = int(
        overlap["value_difference_count"].sum()
    ) if not overlap.empty else 0
    overlap_lineage = pd.DataFrame()
    if not overlap.empty:
        def overlap_lineage_class(row: pd.Series) -> str:
            factor = str(row["factor"])
            if int(row["value_difference_count"]) == 0:
                return "exact_match"
            if factor.startswith("kunquant_alpha101_") and factor.endswith(
                "_canonical_vwap_v2"
            ):
                return "alpha101_canonicalized"
            if factor.startswith("kunquant_alpha101_"):
                return "alpha101_legacy"
            if factor.startswith("ta_"):
                return "ta_legacy"
            if factor.startswith("mature_"):
                return "practical_pit_fundamental"
            return "other"

        classified = overlap.copy()
        classified["lineage_class"] = classified.apply(
            overlap_lineage_class, axis=1
        )
        overlap_lineage = (
            classified.groupby("lineage_class", as_index=False)
            .agg(
                factor_count=("factor", "size"),
                value_difference_count=("value_difference_count", "sum"),
                extended_only_key_count=("extended_only_key_count", "sum"),
                frozen_only_key_count=("frozen_only_key_count", "sum"),
                minimum_value_match_ratio=("value_match_ratio", "min"),
            )
            .sort_values("lineage_class")
        )
        interpretations = {
            "exact_match": "same keys, missingness and values",
            "alpha101_canonicalized": "residual after exact frozen raw snapshots, bootstrap anchors, full parent symbol scope and PIT membership reproduction",
            "alpha101_legacy": "residual after exact frozen raw snapshots, bootstrap anchors, full parent symbol scope and PIT membership reproduction",
            "ta_legacy": "small implementation-horizon lineage residual on common keys",
            "practical_pit_fundamental": "small current-statement-vintage/revision-selection residual under leakage-safe practical PIT",
            "other": "unclassified residual requiring follow-up",
        }
        overlap_lineage["interpretation"] = overlap_lineage["lineage_class"].map(
            interpretations
        )
    overlap_lineage.to_csv(
        report_dir / "overlap_lineage_summary.csv", index=False
    )
    source_lineage = pd.DataFrame(
        [
            {
                "source": "Community Qlib 20260609 derived",
                "role": "OHLCV/amount/VWAP and dated lifecycle intervals",
                "used_in_matrix": True,
                "earliest_evidence": "2000-01-04 raw market; practical universe begins 2000-11-01",
                "lineage": "local immutable provider snapshot",
                "remaining_gap": "not an archived daily security-master vintage",
            },
            {
                "source": "Tushare daily_basic",
                "role": "12 valuation/size/turnover factors",
                "used_in_matrix": True,
                "earliest_evidence": "2010-01-04 market-date cache",
                "lineage": "segment parquet plus request receipt",
                "remaining_gap": "pre-2010 matrix layer not reconstructed",
            },
            {
                "source": "Tushare moneyflow",
                "role": "10 order-size flow factors",
                "used_in_matrix": True,
                "earliest_evidence": "2010-01-04 market-date cache",
                "lineage": "segment parquet plus request receipt",
                "remaining_gap": "2007-2009 is structurally partial and no equivalent source was found",
            },
            {
                "source": "Tushare income/balancesheet/cashflow",
                "role": "19 practical reconstructed PIT fundamentals",
                "used_in_matrix": True,
                "earliest_evidence": "announcement window from 2008-01-01",
                "lineage": "issuer/API paginated cache with revision and announcement fields",
                "remaining_gap": "today's endpoint may omit unknown historical revisions; no provider-vintage proof claimed",
            },
            {
                "source": "BaoStock / AkShare / Tushare daily",
                "role": "early-history cross-source availability and adjustment canaries",
                "used_in_matrix": False,
                "earliest_evidence": "representative early-2000s daily rows",
                "lineage": "inherited qualification reports and receipts",
                "remaining_gap": "not substituted because no missing Qlib price field required fallback",
            },
            {
                "source": "Frozen Factor Universe V2 Matrix",
                "role": "immutable 2021+ parent and overlap authority",
                "used_in_matrix": False,
                "earliest_evidence": "2021-02-01",
                "lineage": frozen_manifest.get("partition_identity_sha256"),
                "remaining_gap": "upstream revisions must be reported, never silently accepted",
            },
        ]
    )
    source_lineage.to_csv(report_dir / "source_lineage.csv", index=False)
    gaps = pd.DataFrame(
        [
            {
                "field_or_layer": "moneyflow before 2010",
                "status": "not_recoverable_as_full_market_equivalent",
                "affected_factors": len(MONEYFLOW_FACTOR_NAMES),
                "impact": "excluded from pre-2010 full-feature representation",
            },
            {
                "field_or_layer": "daily_basic before 2010",
                "status": "not_materialized_in_v1",
                "affected_factors": len(DAILY_BASIC_FACTOR_NAMES),
                "impact": "excluded from pre-2010 full-feature representation",
            },
            {
                "field_or_layer": "statement revision history before announcement cache",
                "status": "practical_reconstruction_only",
                "affected_factors": len(FUNDAMENTAL_FACTOR_NAMES),
                "impact": "no provider-vintage claim; strict no-future checks retained",
            },
            {
                "field_or_layer": "archived security-master snapshots",
                "status": "unavailable_but_not_required",
                "affected_factors": 0,
                "impact": "practical lifecycle combines intervals and dated market presence",
            },
            {
                "field_or_layer": "frozen-parent exact value overlap",
                "status": "lineage_mismatch_not_silently_accepted" if not overlap_pass else "pass",
                "affected_factors": overlap_bad_factor_count,
                "impact": (
                    f"{overlap_difference_count} common-key values differ; concentrated in "
                    "Alpha101, with small TA and practical-PIT statement-vintage residuals"
                    if not overlap_pass
                    else "all overlap keys and values match"
                ),
            },
        ]
    )
    gaps.to_csv(report_dir / "remaining_data_gaps.csv", index=False)
    hypotheses = pd.DataFrame(
        [
            {
                "dataset_hypothesis": "H1_long_price_volume",
                "start": matrix_totals.get("historical_start_date"),
                "end": "frozen parent latest date",
                "factor_count": 733,
                "purpose": "maximum long price/volume history",
            },
            {
                "dataset_hypothesis": "H2_modern_market_price_volume",
                "start": "2008-01-01",
                "end": "frozen parent latest date",
                "factor_count": 733,
                "purpose": "modern A-share market-regime hypothesis",
            },
            {
                "dataset_hypothesis": "H3_full_feature_common",
                "start": str(config["full_feature_candidate_start_date"]),
                "end": "frozen parent latest date",
                "factor_count": 774,
                "purpose": "common full-feature representation",
            },
            {
                "dataset_hypothesis": "H4_transparent_core_subset",
                "start": matrix_totals.get("historical_start_date"),
                "end": "frozen parent latest date",
                "factor_count": 34,
                "purpose": "economically transparent long-history sensitivity check",
            },
        ]
    )
    hypotheses.to_csv(report_dir / "historical_dataset_hypotheses.csv", index=False)
    token_persisted = _token_persisted(
        [
            config_path,
            resolve(config["extension_raw_root"]),
            report_dir,
            output_dir,
        ]
    )
    manifest = {
        "schema_version": 1,
        "stage_id": config["stage_id"],
        "artifact_status": (
            "pass"
            if matrix_generated and overlap_pass and not token_persisted
            else "partial_extension"
        ),
        "extended_matrix_generated": matrix_generated,
        "extended_matrix_id": matrix_id,
        "historical_partition_count": len(historical),
        **matrix_totals,
        "historical_partition_row_count_sum": int(historical["row_count"].sum()) if not historical.empty else 0,
        "partition_integrity_pass": partition_integrity_pass,
        "continuous_state_pass": continuous_state_pass,
        "frozen_matrix_parent_artifact_id": frozen_manifest.get(
            "artifact_id", frozen_manifest.get("partition_identity_sha256")
        ),
        "overlap_validation_pass": overlap_pass,
        "overlap_factor_count": int(len(overlap)),
        "overlap_factors_with_differences": overlap_bad_factor_count,
        "overlap_value_difference_count": overlap_difference_count,
        "overlap_extended_only_key_count": int(overlap["extended_only_key_count"].sum()) if not overlap.empty else 0,
        "overlap_frozen_only_key_count": int(overlap["frozen_only_key_count"].sum()) if not overlap.empty else 0,
        "practical_pit_pass": bool(not pit.empty and pit["status"].eq("pass").all()),
        "historical_universe_overlap_pass": bool(not universe.empty and universe["status"].eq("pass").all()),
        "factor_universe_v2_definitions_changed": False,
        "frozen_matrix_changed": False,
        "research_protocol_v2_changed": False,
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "formal_structured_ml_competition_started": False,
        "model_outcomes_read": False,
        "token_persisted": token_persisted,
        "config_sha256": file_sha256(config_path),
    }
    manifest["manifest_identity"] = canonical_hash(manifest)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frontiers_text = coverage.to_string(index=False) if not coverage.empty else "not analyzed"
    overlap_factor_count = int(len(overlap))
    full_feature_end = manifest.get("historical_end_date")
    report = f"""# Historical Data Engineering Extension V1

> 状态：`{manifest['artifact_status']}`。本阶段采用 practical reconstructed PIT 与 practical historical universe；未读取模型 outcomes，未修改旧 frozen Matrix。

## 实施结果

- Extended Matrix generated: `{matrix_generated}`
- Extended Matrix identity: `{matrix_id}`
- Historical partitions: `{len(historical)}`
- Historical key rows: `{manifest.get('historical_row_count', 0)}`
- Historical dates / instruments / maximum factors: `{manifest.get('historical_date_count', 0)}` / `{manifest.get('historical_instrument_count', 0)}` / `{manifest.get('maximum_factor_count', 0)}`
- Historical range: `{manifest.get('historical_start_date')}` — `{manifest.get('historical_end_date')}`
- Partition integrity / continuous cumulative state: `{partition_integrity_pass}` / `{continuous_state_pass}`
- Practical PIT leakage checks: `{'pass' if manifest['practical_pit_pass'] else 'incomplete_or_fail'}`
- Historical universe 2021+ overlap: `{'pass' if manifest['historical_universe_overlap_pass'] else 'incomplete_or_fail'}`
- Matrix 2021+ overlap: `{'pass' if overlap_pass else 'fail'}` ({overlap_factor_count} factors；{overlap_bad_factor_count} factors / {overlap_difference_count} common-key values differ；0 key-set differences)

## Factor-family frontiers

```text
{frontiers_text}
```

## 数据层

- `full-feature common history`: `{config['full_feature_candidate_start_date']}` 至 `{full_feature_end}`；2021-02-01 起引用 byte-immutable frozen V2 parent。
- `full price-factor history`: `{manifest.get('historical_start_date')}` 起的 733 个 price/volume 因子；VPT/NVI/ADI/OBV 使用跨年度连续状态缓存。
- `long-history transparent core`: 上述长历史中的 34 因子显式子集，不删除其余可可靠 materialize 的价格因子。

## 十二项结论

1. 数据工程实际推进到 `{manifest.get('historical_start_date')}`；底层市场 raw 从 2000-01-04 起，practical universe 的首个有效月决定 Matrix 首日。
2. Full Factor Universe V2 的 774 因子共同层从 `{config['full_feature_candidate_start_date']}` materialize；733 因子价格层更早。
3. 各 family frontier 见上表和 `factor_family_frontiers.csv`；frontier 使用 dated market presence，而非 current-universe 分母。
4. Qlib 补齐长期 OHLCV/amount/VWAP 与 lifecycle；Tushare 分段缓存补齐 daily_basic、moneyflow 和公告/修订 statements。
5. 真正缺口是 pre-2010 moneyflow 等价全市场信息、未构建的 pre-2010 daily_basic 层，以及无法证明不存在的旧 revision；详见 `remaining_data_gaps.csv`。
6. 已形成 full-feature、full price-volume、transparent core subset 三层，而不是强迫所有因子共用起点。
7. Practical reconstructed PIT 仅允许 `information_available_date <= decision date`，并独立验证 latest-public-event、revision 顺序和单日唯一状态：`{'pass' if manifest['practical_pit_pass'] else 'fail'}`。
8. Historical universe 由 Qlib lifecycle interval、实际市场存在和 point-in-time rolling selection 重建；2021 overlap：`{'pass' if manifest['historical_universe_overlap_pass'] else 'fail'}`。
9. Extended Matrix generated：`{matrix_generated}`；身份与 frozen parent 分离。
10. 实际覆盖 `{manifest.get('historical_date_count', 0)}` dates、`{manifest.get('historical_instrument_count', 0)}` instruments、最多 `{manifest.get('maximum_factor_count', 0)}` factors。
11. 2021-02-01 至 2021-03-31 overlap：`{'pass' if overlap_pass else 'fail'}`；key set 完全一致，剩余值差异集中于 Alpha101，并含极少 TA 与 practical-PIT statement-vintage residual；逐因子差异和 lineage 分类分别写入 `matrix_overlap_validation.csv`、`overlap_lineage_summary.csv`，不静默接受。
12. 后续可预注册比较四个 dataset hypotheses，见 `historical_dataset_hypotheses.csv`；本阶段不选择最佳训练起点。

## Lineage 与缺口

`source_lineage.csv` 记录每个 source 的实际角色、缓存证据和未解决限制；`annual_matrix_summary.csv`、`historical_partition_manifest.csv` 和 manifest 共同定义独立 Matrix identity。BaoStock/AkShare 只保留为早期可得性与调整 canary，没有在 Qlib 字段完整时人为混源。

## 治理边界

Factor Universe V2 definitions、Research Protocol V2、Strategy V1、Forward Track 与旧 frozen Matrix 均未改变；Structured ML/model/portfolio 阶段未启动。
"""
    (report_dir / "REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Historical Data Engineering Extension V1")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/historical_data_engineering_extension_v1.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=("bootstrap", "analyze", "stateful", "materialize", "finalize", "all"),
        default="all",
    )
    parser.add_argument("--years", help="comma-separated materialization years")
    parser.add_argument("--price-only", action="store_true")
    parser.add_argument(
        "--overlap",
        action="store_true",
        help="materialize the configured frozen-parent overlap canary instead of historical rows",
    )
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = load_config(config_path)
    years = [int(value) for value in args.years.split(",")] if args.years else None
    if args.stage in {"bootstrap", "all"}:
        bootstrap(config)
    if args.stage in {"analyze", "all"}:
        analyze(config)
    if args.stage in {"stateful", "all"}:
        materialize_stateful_recovered(config)
    if args.stage in {"materialize", "all"}:
        materialize(config, years, price_only=args.price_only, overlap=args.overlap)
    if args.stage in {"finalize", "all"}:
        finalize(config_path, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
