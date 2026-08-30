from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_universe_v2.historical_data import tushare_to_qlib  # noqa: E402
from factor_universe_v2.tushare_data import (  # noqa: E402
    classify_probe_error,
    tushare_client,
)
from research_validation.dataset_design import (  # noqa: E402
    autocorrelations,
    canonical_hash,
    effective_sample_size,
    factor_history_map,
    qlib_binary_field_coverage,
    regime_window_coverage,
    stationary_bootstrap_mean_se,
    theoretical_overlapping_return_ess,
)

def resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _public_probe(
    pro: Any,
    *,
    probe_id: str,
    api: str,
    parameters: dict[str, Any],
    pause_seconds: float = 0.35,
) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "probe_id": probe_id,
        "api": api,
        "parameters_json": json.dumps(parameters, sort_keys=True, ensure_ascii=False),
        "retrieval_time_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        frame = pro.query(api, **parameters)
        normalized = frame.copy()
        normalized.columns = [str(column) for column in normalized.columns]
        if len(normalized.columns):
            normalized = normalized.sort_values(list(normalized.columns)).reset_index(drop=True)
        serialized = normalized.to_csv(index=False).encode("utf-8")
        date_columns = [
            column
            for column in ("trade_date", "ann_date", "f_ann_date", "end_date", "list_date", "delist_date")
            if column in normalized
        ]
        result.update(
            {
                "probe_status": "accessible_nonempty" if len(normalized) else "accessible_empty",
                "row_count": len(normalized),
                "column_count": len(normalized.columns),
                "columns": ",".join(normalized.columns),
                "content_sha256": hashlib.sha256(serialized).hexdigest(),
                "date_min": min(
                    (str(normalized[column].dropna().astype(str).min()) for column in date_columns if normalized[column].notna().any()),
                    default="",
                ),
                "date_max": max(
                    (str(normalized[column].dropna().astype(str).max()) for column in date_columns if normalized[column].notna().any()),
                    default="",
                ),
                "instrument_count": int(
                    normalized["ts_code"].astype(str).nunique() if "ts_code" in normalized else 0
                ),
                "update_flag_one_rows": int(
                    pd.to_numeric(normalized.get("update_flag"), errors="coerce").eq(1).sum()
                    if "update_flag" in normalized
                    else 0
                ),
                "error_class": "",
                "error_message": "",
            }
        )
    except Exception as exc:  # live external capability receipt
        result.update(
            {
                "probe_status": classify_probe_error(exc),
                "row_count": 0,
                "column_count": 0,
                "columns": "",
                "content_sha256": "",
                "date_min": "",
                "date_max": "",
                "instrument_count": 0,
                "update_flag_one_rows": 0,
                "error_class": type(exc).__name__,
                "error_message": str(exc)[:240],
            }
        )
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    time.sleep(pause_seconds)
    return result


def run_network_probe(config: dict[str, Any], output_dir: Path) -> pd.DataFrame:
    pro = tushare_client()
    receipt_path = output_dir / "tushare_probe_receipts.csv"
    existing = pd.read_csv(receipt_path).fillna("") if receipt_path.is_file() else pd.DataFrame()
    rows: list[dict[str, Any]] = existing.to_dict("records")
    completed = set(existing.get("probe_id", pd.Series(dtype=str)).astype(str))
    calendar = pro.query(
        "trade_cal",
        exchange="SSE",
        start_date="19900101",
        end_date="20260830",
        is_open="1",
        fields="exchange,cal_date,is_open,pretrade_date",
    )
    calendar["year"] = calendar["cal_date"].astype(str).str[:4].astype(int)
    annual_dates = (
        calendar.loc[
            calendar["year"].ge(int(config["network_probe"]["annual_market_coverage_start_year"]))
            & calendar["year"].le(2026)
        ]
        .sort_values("cal_date")
        .groupby("year")["cal_date"]
        .last()
    )
    market_fields = {
        "daily": "ts_code,trade_date,open,high,low,close,vol,amount",
        "daily_basic": "ts_code,trade_date,close,turnover_rate_f,pe_ttm,pb,total_mv,circ_mv",
        "moneyflow": "ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_lg_amount,sell_lg_amount,net_mf_amount",
        "adj_factor": "ts_code,trade_date,adj_factor",
    }
    for year, trade_date in annual_dates.items():
        for api, fields in market_fields.items():
            probe_id = f"{api}_market_{int(year)}"
            if probe_id in completed:
                continue
            rows.append(
                _public_probe(
                    pro,
                    probe_id=probe_id,
                    api=api,
                    parameters={"trade_date": str(trade_date), "fields": fields},
                )
            )
    statement_fields = {
        "income": "ts_code,ann_date,f_ann_date,end_date,revenue,n_income_attr_p,update_flag",
        "balancesheet": "ts_code,ann_date,f_ann_date,end_date,total_assets,total_liab,update_flag",
        "cashflow": "ts_code,ann_date,f_ann_date,end_date,n_cashflow_act,update_flag",
        "fina_indicator": "ts_code,ann_date,end_date,roe,roa,grossprofit_margin,assets_yoy",
        "dividend": "ts_code,end_date,ann_date,div_proc,cash_div_tax,stk_div",
    }
    for ts_code in config["network_probe"]["statement_codes"]:
        for start_date, end_date in config["network_probe"]["statement_windows"]:
            for api, fields in statement_fields.items():
                probe_id = f"{api}_{ts_code}_{start_date}_{end_date}"
                if probe_id in completed:
                    continue
                rows.append(
                    _public_probe(
                        pro,
                        probe_id=probe_id,
                        api=api,
                        parameters={
                            "ts_code": ts_code,
                            "start_date": str(start_date),
                            "end_date": str(end_date),
                            "fields": fields,
                        },
                    )
                )
    for list_status in ("L", "D", "P"):
        probe_id = f"stock_basic_{list_status}"
        if probe_id in completed:
            continue
        rows.append(
            _public_probe(
                pro,
                probe_id=probe_id,
                api="stock_basic",
                parameters={
                    "exchange": "",
                    "list_status": list_status,
                    "fields": "ts_code,symbol,name,area,industry,market,list_date,delist_date,list_status",
                },
            )
        )
    for ts_code in config["network_probe"]["statement_codes"]:
        probe_id = f"namechange_{ts_code}"
        if probe_id in completed:
            continue
        rows.append(
            _public_probe(
                pro,
                probe_id=probe_id,
                api="namechange",
                parameters={
                    "ts_code": ts_code,
                    "fields": "ts_code,name,start_date,end_date,ann_date,change_reason",
                },
            )
        )
    receipt = pd.DataFrame(rows).sort_values("probe_id").reset_index(drop=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt.to_csv(output_dir / "tushare_probe_receipts.csv", index=False, encoding="utf-8")
    return receipt


def _read_qlib_series(provider_uri: Path, instrument: str, field: str) -> pd.Series:
    calendar = pd.DatetimeIndex(
        pd.to_datetime((provider_uri / "calendars/day.txt").read_text(encoding="utf-8").splitlines())
    )
    path = provider_uri / "features" / instrument.lower() / f"{field.lstrip('$').lower()}.day.bin"
    raw = np.fromfile(path, dtype="<f4")
    start = int(raw[0])
    values = raw[1:]
    index = calendar[start : start + len(values)]
    return pd.Series(values[: len(index)], index=index, name=field, dtype="float64")


def _market_descriptors(
    labels_path: Path, market_path: Path, provider_uri: Path, daily_basic_root: Path
) -> pd.DataFrame:
    labels = pd.read_parquet(labels_path, columns=["datetime", "instrument", "label_20d_t1"])
    labels["datetime"] = pd.to_datetime(labels["datetime"])
    market = pd.read_parquet(
        market_path, columns=["datetime", "instrument", "$close", "$amount", "$volume"]
    )
    market["datetime"] = pd.to_datetime(market["datetime"])
    market = market.sort_values(["instrument", "datetime"])
    market["return_1d"] = market.groupby("instrument", sort=False)["$close"].pct_change(fill_method=None)
    keys = labels[["datetime", "instrument"]]
    market = keys.merge(market, on=["datetime", "instrument"], how="left", validate="one_to_one")
    daily = (
        market.groupby("datetime", as_index=False)
        .agg(
            market_equal_weight_return_1d=("return_1d", "mean"),
            cross_section_return_dispersion=("return_1d", "std"),
            market_breadth=("return_1d", lambda value: float(value.gt(0).mean())),
            total_amount_thousand_cny=("$amount", "sum"),
            median_amihud=(
                "return_1d",
                lambda value: float("nan"),
            ),
        )
        .sort_values("datetime")
    )
    amihud = market.assign(
        amihud=market["return_1d"].abs()
        / (pd.to_numeric(market["$amount"], errors="coerce") * 1000.0).replace(0, np.nan)
    ).groupby("datetime")["amihud"].median()
    daily["median_amihud"] = daily["datetime"].map(amihud)
    daily["log_total_turnover"] = np.log1p(daily["total_amount_thousand_cny"] * 1000.0)
    daily["market_realized_volatility_20"] = (
        daily["market_equal_weight_return_1d"].rolling(20, min_periods=15).std() * np.sqrt(252)
    )
    label_daily = (
        labels.groupby("datetime", as_index=False)
        .agg(
            universe_instrument_count=("instrument", "nunique"),
            label_20d_cross_section_mean=("label_20d_t1", "mean"),
            label_20d_cross_section_median=("label_20d_t1", "median"),
            label_20d_cross_section_dispersion=("label_20d_t1", "std"),
        )
    )
    daily = daily.merge(label_daily, on="datetime", how="left", validate="one_to_one")
    benchmark_close = _read_qlib_series(provider_uri, "sh000985", "$close")
    benchmark_return = benchmark_close.pct_change(fill_method=None)
    benchmark_20d = benchmark_close.shift(-21) / benchmark_close.shift(-1) - 1
    daily["benchmark_return_1d"] = daily["datetime"].map(benchmark_return)
    daily["benchmark_return_20d_t1"] = daily["datetime"].map(benchmark_20d)

    returns_by_date = {
        date: group.set_index("instrument")["return_1d"]
        for date, group in market.groupby("datetime", sort=False)
    }
    size_spread: dict[pd.Timestamp, float] = {}
    for path in sorted(daily_basic_root.glob("*.parquet")):
        date_text = path.stem
        date = pd.to_datetime(date_text, format="%Y%m%d", errors="coerce")
        if pd.isna(date) or date not in returns_by_date:
            continue
        basic = pd.read_parquet(path, columns=["ts_code", "total_mv"])
        basic["instrument"] = basic["ts_code"].map(tushare_to_qlib)
        joined = basic.set_index("instrument")[["total_mv"]].join(returns_by_date[date].rename("return_1d")).dropna()
        if len(joined) < 100:
            continue
        ranks = joined["total_mv"].rank(pct=True, method="average")
        size_spread[date] = float(
            joined.loc[ranks.le(0.2), "return_1d"].mean()
            - joined.loc[ranks.ge(0.8), "return_1d"].mean()
        )
    daily["small_minus_large_return"] = daily["datetime"].map(size_spread)
    return daily


def _feature_distribution_drift(matrix_root: Path) -> pd.DataFrame:
    selections = {
        "mature_market.parquet": [
            "mature_momentum_12_1",
            "mature_realized_volatility_60",
            "mature_amihud_illiquidity_20",
        ],
        "mature_daily_basic.parquet": [
            "mature_log_total_market_cap",
            "mature_turnover_rate_free_float",
        ],
        "mature_moneyflow.parquet": ["mature_net_flow_to_traded_amount"],
        "mature_fundamental.parquet": ["mature_return_on_assets"],
    }
    rows: list[dict[str, Any]] = []
    for filename, factors in selections.items():
        frame = pd.read_parquet(matrix_root / filename, columns=["datetime", *factors])
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame["year"] = frame["datetime"].dt.year
        for factor in factors:
            numeric = pd.to_numeric(frame[factor], errors="coerce").replace([np.inf, -np.inf], np.nan)
            global_iqr = float(numeric.quantile(0.75) - numeric.quantile(0.25))
            annual = frame.assign(value=numeric).groupby("year")["value"]
            for year, values in annual:
                finite = values.dropna()
                median = float(finite.median()) if len(finite) else np.nan
                q25 = float(finite.quantile(0.25)) if len(finite) else np.nan
                q75 = float(finite.quantile(0.75)) if len(finite) else np.nan
                rows.append(
                    {
                        "factor": factor,
                        "year": int(year),
                        "row_count": len(values),
                        "finite_count": len(finite),
                        "coverage": float(len(finite) / len(values)) if len(values) else np.nan,
                        "median": median,
                        "q25": q25,
                        "q75": q75,
                        "global_iqr": global_iqr,
                    }
                )
    result = pd.DataFrame(rows).sort_values(["factor", "year"]).reset_index(drop=True)
    result["median_change_from_prior_year_in_global_iqr"] = (
        result.groupby("factor")["median"].diff() / result["global_iqr"].replace(0, np.nan)
    )
    return result


def _score_persistence(runtime_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(runtime_dir.glob("split_*_scores.parquet")):
        split_id = path.stem.replace("_scores", "")
        frame = pd.read_parquet(path)
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        variants = [column for column in frame.columns if column not in {"datetime", "instrument"}]
        dates = sorted(frame["datetime"].unique())
        by_date = {date: part.set_index("instrument") for date, part in frame.groupby("datetime", sort=True)}
        for lag in (1, 5, 20):
            for variant in variants:
                correlations: list[float] = []
                for position in range(lag, len(dates)):
                    left = by_date[dates[position - lag]][[variant]].rename(columns={variant: "left"})
                    right = by_date[dates[position]][[variant]].rename(columns={variant: "right"})
                    joined = left.join(right, how="inner").dropna()
                    if len(joined) >= 50:
                        correlations.append(float(joined["left"].corr(joined["right"])))
                rows.append(
                    {
                        "outer_split_id": split_id,
                        "variant_id": variant,
                        "lag": lag,
                        "mean_cross_section_score_correlation": float(np.mean(correlations)),
                        "median_cross_section_score_correlation": float(np.median(correlations)),
                        "date_pair_count": len(correlations),
                    }
                )
    return pd.DataFrame(rows)


def _dependence_outputs(
    descriptors: pd.DataFrame,
    daily_ic_path: Path,
    validation_lengths: list[int],
    max_lag: int,
    hac_lags: list[int],
    block_lengths: list[int],
    repetitions: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    series_map: dict[str, pd.Series] = {
        column: descriptors.set_index("datetime")[column].dropna()
        for column in (
            "label_20d_cross_section_mean",
            "label_20d_cross_section_median",
            "benchmark_return_20d_t1",
            "market_equal_weight_return_1d",
            "benchmark_return_1d",
        )
    }
    daily_ic = pd.read_csv(daily_ic_path, parse_dates=["datetime"])
    ic_mean = (
        daily_ic.groupby(["outer_split_id", "datetime"], as_index=False)["rank_ic"].mean()
    )
    for split_id, group in ic_mean.groupby("outer_split_id"):
        series_map[f"frozen_sleeve_cross_variant_mean_ic:{split_id}"] = group.set_index("datetime")["rank_ic"]
    for (split_id, variant_id), group in daily_ic.groupby(["outer_split_id", "variant_id"]):
        series_map[f"frozen_sleeve_ic:{split_id}:{variant_id}"] = group.set_index("datetime")["rank_ic"]

    dependence_rows: list[dict[str, Any]] = []
    ess_rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    for measure, series in series_map.items():
        rho = autocorrelations(series, max_lag)
        for lag, value in enumerate(rho):
            dependence_rows.append(
                {"measure": measure, "lag": lag, "autocorrelation": value, "series_dates": len(series)}
            )
        for nominal in validation_lengths:
            for hac_lag in hac_lags:
                inflation, effective = effective_sample_size(
                    series, nominal_dates=nominal, max_lag=hac_lag
                )
                ess_rows.append(
                    {
                        "measure": measure,
                        "nominal_dates": nominal,
                        "hac_bartlett_max_lag": hac_lag,
                        "variance_inflation": inflation,
                        "effective_dates": effective,
                        "theoretical_iid_20d_overlap_effective_dates": theoretical_overlapping_return_ess(nominal, 20),
                    }
                )
        if not measure.startswith("frozen_sleeve_ic:"):
            iid_se = float(series.std(ddof=1) / math.sqrt(len(series)))
            for block_length in block_lengths:
                bootstrap_se = stationary_bootstrap_mean_se(
                    series,
                    mean_block_length=block_length,
                    repetitions=repetitions,
                    seed=20260830 + block_length,
                )
                bootstrap_rows.append(
                    {
                        "measure": measure,
                        "series_dates": len(series),
                        "mean_block_length": block_length,
                        "repetitions": repetitions,
                        "iid_mean_standard_error": iid_se,
                        "stationary_bootstrap_mean_standard_error": bootstrap_se,
                        "bootstrap_to_iid_se_ratio": bootstrap_se / iid_se if iid_se > 0 else np.nan,
                    }
                )
    return pd.DataFrame(dependence_rows), pd.DataFrame(ess_rows), pd.DataFrame(bootstrap_rows)


def _candidate_windows(calendar: pd.DatetimeIndex, lengths: list[int]) -> pd.DataFrame:
    dates = calendar[(calendar >= "2023-05-01") & (calendar <= "2026-05-08")]
    rows: list[dict[str, Any]] = []
    for length in lengths:
        for offset in range(0, len(dates) - length + 1, 63):
            rows.append(
                {
                    "window_id": f"candidate_{length}_{offset // 63 + 1:02d}",
                    "window_family": f"candidate_{length}",
                    "nominal_dates": length,
                    "start": dates[offset],
                    "end": dates[offset + length - 1],
                }
            )
    current = pd.read_csv(
        PROJECT_ROOT / "reports/research_protocol_v2/development_environments.csv",
        parse_dates=["validation_start", "validation_end"],
    )
    for row in current.itertuples(index=False):
        rows.append(
            {
                "window_id": f"protocol_v2_{row.environment_id}",
                "window_family": "protocol_v2_current",
                "nominal_dates": int(row.validation_dates),
                "start": row.validation_start,
                "end": row.validation_end,
            }
        )
    return pd.DataFrame(rows)


def _extension_estimates(config: dict[str, Any], qlib_coverage: pd.DataFrame) -> pd.DataFrame:
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            (resolve(config["provider_uri"]) / "calendars/day.txt").read_text(encoding="utf-8").splitlines()
        )
    )
    current_start = pd.Timestamp("2020-01-17")
    current_end = pd.Timestamp("2026-06-09")
    current_dates = int(calendar.to_series().between(current_start, current_end).sum())
    current_raw_bytes = 1_138_736_197
    current_matrix_bytes = 1_070_000_000 + 7_270_000_000
    issuer_count = 3983
    rows = []
    for start in ("2010-01-04", "2015-01-05", "2018-01-02"):
        start_date = pd.Timestamp(start)
        total_dates = int(calendar.to_series().between(start_date, current_end).sum())
        additional_dates = max(0, total_dates - current_dates)
        years = (current_end - start_date).days / 365.25
        statement_windows = math.ceil(years / 5)
        rows.append(
            {
                "candidate_start": start,
                "additional_trading_dates": additional_dates,
                "daily_layer_requests_two_apis": additional_dates * 2,
                "statement_requests_four_apis_five_year_segments": issuer_count * 4 * statement_windows,
                "estimated_additional_raw_gib": current_raw_bytes * additional_dates / current_dates / 1024**3,
                "estimated_total_matrix_gib": current_matrix_bytes * total_dates / current_dates / 1024**3,
                "estimate_semantics": "linear first-order estimate; excludes retries, revisions, compression changes, and recomputation overhead",
            }
        )
    return pd.DataFrame(rows)


def _literature_map() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "topic": "overlapping_returns",
                "source": "Hansen and Hodrick (1980), Journal of Political Economy",
                "url": "https://doi.org/10.1086/260910",
                "project_use": "Overlapping k-step outcomes require dependence-aware inference; daily rows are not independent temporal evidence.",
                "transfer_limit": "The paper studies exchange-rate forecasting, not A-share cross-sectional Rank IC.",
            },
            {
                "topic": "hac",
                "source": "Newey and West (1987), Econometrica",
                "url": "https://doi.org/10.2307/1913610",
                "project_use": "Use HAC long-run variance as one ESS diagnostic, not as a leakage remedy.",
                "transfer_limit": "Bandwidth choice remains a sensitivity parameter in short samples.",
            },
            {
                "topic": "moving_block_bootstrap",
                "source": "Kunsch (1989), Annals of Statistics",
                "url": "https://doi.org/10.1214/aos/1176347265",
                "project_use": "Consecutive-block resampling preserves weak temporal dependence for uncertainty diagnostics.",
                "transfer_limit": "Requires approximate stationarity within the sampled segment.",
            },
            {
                "topic": "stationary_bootstrap",
                "source": "Politis and Romano (1994), JASA",
                "url": "https://doi.org/10.1080/01621459.1994.10476870",
                "project_use": "Block-length sensitivity can expose understatement of mean-metric uncertainty.",
                "transfer_limit": "Secondary robustness only; it does not preserve chronological selection authority.",
            },
            {
                "topic": "dependent_cv",
                "source": "Racine (2000), Journal of Econometrics",
                "url": "https://doi.org/10.1016/S0304-4076(00)00030-0",
                "project_use": "Blocked/gapped CV is motivated for dependent observations.",
                "transfer_limit": "General stationary theory does not encode project label intervals or PIT evidence roles.",
            },
            {
                "topic": "us_asset_pricing_ml",
                "source": "Gu, Kelly, and Xiu (2020), Review of Financial Studies",
                "url": "https://doi.org/10.1093/rfs/hhaa009",
                "project_use": "Chronological train/validation/test isolation and expanding refits are useful design precedents.",
                "transfer_limit": "Monthly targets, 60 years of US history, and annual refits are not directly transferable.",
            },
            {
                "topic": "china_asset_pricing_ml",
                "source": "Leippold, Wang, and Zhou (2022), Journal of Financial Economics",
                "url": "https://doi.org/10.1016/j.jfineco.2021.08.017",
                "project_use": "A-share ML precedent uses 2000-2008 train, 2009-2011 validation, rolling one-year tests, and annual refits.",
                "transfer_limit": "Monthly stock returns and multi-year validation contain far more non-overlapping temporal information than 20-day daily-overlap labels.",
            },
            {
                "topic": "backtest_overfitting",
                "source": "Bailey, Borwein, Lopez de Prado, and Zhu (2017), Journal of Computational Finance",
                "url": "https://doi.org/10.21314/JCF.2016.322",
                "project_use": "Many trial paths raise selection-overfitting risk; secondary combinatorial analysis can diagnose path dependence.",
                "transfer_limit": "CSCV/CPCV-style robustness must not replace past-only chronological authority.",
            },
            {
                "topic": "qlib_platform",
                "source": "Yang et al. (2020), Qlib paper and pinned repository",
                "url": "https://arxiv.org/abs/2009.11189",
                "project_use": "Qlib supports fixed train/valid/test and RollingGen task materialization.",
                "transfer_limit": "Official Alpha158 benchmarks use 2008-2014 train and 2015-2016 valid by example, not by a project-specific adequacy proof.",
            },
        ]
    )


def _source_capability_audit() -> pd.DataFrame:
    columns = [
        "source_layer",
        "provider_or_api",
        "theoretical_or_local_earliest",
        "bounded_probe_earliest",
        "current_snapshot_earliest",
        "coverage_stable_from",
        "pit_reliability",
        "revision_history",
        "schema_or_unit_risk",
        "current_2000_point_access",
        "research_usable_frontier",
        "confidence",
        "bottleneck_or_required_followup",
    ]
    rows = [
        ["OHLCV", "community derived Qlib", "2000-01-04", "2000-01-04", "2000-01-04", "2000-01-04 field-relative", "same-day market observation", "release snapshot only", "multi-source provenance and corporate-action events need early-history audit", "local", "price-volume core technical frontier 2000; modern-regime candidate 2008/2010", "medium", "validate old corporate actions and source-vintage stability"],
        ["amount/VWAP", "community derived Qlib", "2000-01-04", "2000-01-04", "2000-01-04", "2000-01-04 field-relative", "same-day market observation", "release snapshot only", "current adapter confirms amount=thousand CNY and direct VWAP; early years not event-sampled", "local", "price-volume core technical frontier 2000", "medium", "repeat unit/event checks before extension"],
        ["adjustment", "Qlib factor/adjclose + Tushare adj_factor", "full history", "2000 sampled", "2000-01-04", "not independently proven", "revision-sensitive", "current snapshot; historical vintage unavailable", "adjclose semantics were previously documented as unresolved", "yes", "do not make 2000 authoritative until corporate-action audit passes", "low", "highest-risk price-history semantic"],
        ["daily_basic", "Tushare daily_basic", "full history / 2000 points", "2000 annual sample", "2020-01-17", "2000 annual samples approximately match daily coverage", "row t after close", "current API snapshot", "total_mv is 10,000 CNY; current adapter converts to CNY", "yes", "extension technically supports 2000; pair with other layer frontier", "high", "download and market-wide gap audit"],
        ["moneyflow", "Tushare moneyflow", "documented 2010", "2007 partial", "2020-01-17", "2010 annual sample coverage approximately matches daily", "row t after close", "current API snapshot", "amount fields are 10,000 CNY", "yes", "full-feature hard source frontier no earlier than 2010", "high", "2007-2009 is structurally incomplete"],
        ["financial statements", "Tushare income/balancesheet/cashflow", "full history", "1998-2000 report periods in six-issuer probe", "availability from 2018-01-03", "not proven market-wide before 2018", "f_ann_date then ann_date; current no-future alignment passed", "many update_flag revisions observed, completeness not provable from current endpoint", "report types and revision duplication require deterministic priority", "yes", "2015/2018 bounded extension candidate; earlier PIT confidence low", "medium-low", "market-wide announcement/revision coverage probe required"],
        ["fina_indicator", "Tushare fina_indicator", "full history", "2000 report periods", "availability from 2018-04-04", "not proven market-wide before 2018", "ann_date only; cross-check not primary PIT source", "revision history weaker than statements", "formula definitions may differ from project ratios", "yes", "supporting cross-check only", "medium", "do not use as sole PIT authority"],
        ["dividend", "Tushare dividend / daily_basic dv_ttm", "full history", "2005 report periods in sample", "dv_ttm from 2020-01-17", "not proven", "announcement-date event data", "current endpoint snapshot", "sparse issuer events; cash/stock dividend fields differ", "yes", "V2 currently uses daily_basic dv_ttm, not raw dividend", "medium", "audit event timing only if raw dividend becomes a feature"],
        ["universe lifecycle", "Qlib all.txt intervals + PIT rolling universe", "2000-01-04", "2000-01-04", "2021-02-01 Matrix", "provider intervals complete for local features", "effective intervals and next-session membership", "release snapshot", "listing/delisting spans exist", "local", "can be regenerated earlier; selection history must be recomputed", "medium-high", "do not reuse 2021-built intervals outside their scope"],
        ["ST/suspension/tradability", "historical instrument state", "provider dependent", "not established", "blocked", "not established", "before-open state unavailable", "not established", "board/ST/IPO rule changes", "partial", "not a factor-Matrix blocker, but authoritative execution remains blocked", "high", "requires separate official-state history"],
        ["benchmark", "Qlib SH000985", "2005-01-04", "2005-01-04", "2005-01-04", "2005-01-04", "same-day index observation", "release snapshot", "index methodology/constituent evolution", "local", "sufficient for extension from 2005", "high", "use contemporaneous benchmark definition and document index history"],
    ]
    return pd.DataFrame(rows, columns=columns)


def _validation_design_comparison() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"nominal_dates": 40, "approx_months": 2, "label_overlap_theory_ess": theoretical_overlapping_return_ess(40, 20), "project_label_ess_hac40": 2.62, "individual_sleeve_ic_ess_median_hac20_40": "3.8-4.0", "regime_terciles_average": 2.25, "recommended_status": "reject_as_structured_ml_selection_authority", "reason": "only a few effective temporal observations and weak regime diversity"},
            {"nominal_dates": 60, "approx_months": 3, "label_overlap_theory_ess": theoretical_overlapping_return_ess(60, 20), "project_label_ess_hac40": 3.93, "individual_sleeve_ic_ess_median_hac20_40": "5.7-6.0", "regime_terciles_average": 2.47, "recommended_status": "diagnostic_or_latency_sensitive_only", "reason": "still noise-sensitive for candidate selection"},
            {"nominal_dates": 120, "approx_months": 6, "label_overlap_theory_ess": theoretical_overlapping_return_ess(120, 20), "project_label_ess_hac40": 7.86, "individual_sleeve_ic_ess_median_hac20_40": "11.4-12.0", "regime_terciles_average": 2.74, "recommended_status": "lower_bound_candidate_after_history_extension", "reason": "first tested scale approaching double-digit effective IC dates with materially better regimes"},
            {"nominal_dates": 252, "approx_months": 12, "label_overlap_theory_ess": theoretical_overlapping_return_ess(252, 20), "project_label_ess_hac40": 16.50, "individual_sleeve_ic_ess_median_hac20_40": "23.9-25.2", "regime_terciles_average": 2.89, "recommended_status": "strong_candidate_after_history_extension", "reason": "substantially more temporal information and near-complete descriptor-tercile coverage"},
        ]
    )


def _dataset_design_evidence_map() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["matrix_start", "2021-02-01 is a source limit", "git lineage contradicts", "first introduced by full-research config then inherited", "simple continuity", "unnecessarily short history", "high", "reject"],
            ["full_feature_history", "extend to 2018 first", "all source layers technically cover it", "current statement availability starts 2018; daily layers need backfill", "lower-risk staged extension", "pre-2018 PIT state still needs download", "medium-high", "prioritize_bounded_qualification"],
            ["full_feature_history", "investigate 2015", "moneyflow stable since 2010 and financial rows exist", "six-issuer probe shows old reports/revisions", "adds 2015 crash and more regimes", "market-wide revision completeness unknown", "medium", "probe_before_authorize"],
            ["price_volume_history", "2008/2010 modern-regime core", "Qlib fields complete from 2000; official benchmarks use 2008", "local provider field coverage is complete", "longer comparable sample", "adjustment semantics need audit", "medium", "investigate"],
            ["validation_length", "40 days", "20-day overlap implies ESS about 2.4", "project HAC ESS about 2.6; current folds 35-43 days", "fast iteration", "selection dominated by a few temporal shocks", "high", "reject"],
            ["validation_length", "120-252 days", "HAC/block bootstrap and dependent-CV literature", "IC ESS and regime coverage improve materially", "more reliable paired comparison", "fewer folds and slower iteration", "medium-high", "recommended_protocol_family"],
            ["fold_structure", "4-6 sequential long blocks", "temporal samples, not stock rows, are limiting", "40-day folds add little independent information", "balances fold count and information", "needs longer Matrix", "medium", "investigate_after_extension"],
            ["rolling_step", "63 or 126 days as coarse hypotheses", "step should reflect decay/retrain cost, not label horizon alone", "no model-decay competition has started", "controls compute and overlap", "not yet empirically selected", "low-medium", "preregister_later"],
            ["training_history", "expanding incumbent", "maximizes scarce time information", "only about 5.3 years currently", "sample efficiency", "structural drift dilution", "medium-high", "retain_incumbent"],
            ["training_history", "sliding_504", "nonstationarity hypothesis only", "no data-based two-year cutoff found", "adaptation", "throws away most already scarce regimes", "high", "not_supported_as_authority"],
            ["training_history", "one coarse 3-4 year sliding candidate", "drift exists but optimum is unknown", "market/feature annual distributions move", "tests adaptation without dense scan", "requires longer history", "medium", "investigate_after_extension"],
            ["resampling", "CPCV/blocked bootstrap secondary", "dependent-CV and overfit literature", "chronological authority already encoded by V2", "path-dependence robustness", "future training paths violate past-only authority", "high", "secondary_only"],
            ["dataset_philosophy", "full-feature common history primary", "fair candidate comparison", "41 usable factors depend on non-price layers", "representation consistency", "shorter history", "medium-high", "primary_after_extension"],
            ["dataset_philosophy", "tiered price-volume history secondary", "724 usable price-core factors can go earlier", "provider begins 2000", "more regimes", "comparison period differs", "medium", "separate_representation_study"],
        ],
        columns=["design_question", "possible_choice", "supporting_evidence", "project_specific_evidence", "benefit", "risk", "confidence", "recommended_status"],
    )


def run_analysis(config: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_uri = resolve(config["provider_uri"])
    qlib_coverage = qlib_binary_field_coverage(provider_uri, config["qlib_fields"])
    qlib_coverage.to_csv(output_dir / "qlib_field_coverage.csv", index=False)

    inventory = pd.read_csv(resolve(config["factor_inventory"]))
    qualification = pd.read_csv(resolve(config["factor_qualification"]))
    history_map = factor_history_map(inventory, qualification)
    history_map.to_csv(output_dir / "factor_family_historical_depth.csv", index=False)

    daily_basic_root = resolve(
        "outputs/factor_universe_v2_matrix_readiness/runtime/raw/daily_basic"
    )
    descriptors = _market_descriptors(
        resolve(config["matrix_labels"]),
        resolve(config["market_cache"]),
        provider_uri,
        daily_basic_root,
    )
    descriptors.to_csv(output_dir / "market_regime_descriptors.csv", index=False)
    _feature_distribution_drift(
        resolve("outputs/factor_universe_v2_matrix_readiness/runtime/matrix/full")
    ).to_csv(output_dir / "feature_distribution_drift.csv", index=False)

    dependence, ess, bootstrap = _dependence_outputs(
        descriptors,
        resolve(config["economic_daily_ic"]),
        [int(value) for value in config["validation_lengths"]],
        int(config["dependence_max_lag"]),
        [int(value) for value in config["dependence_hac_lags"]],
        [int(value) for value in config["bootstrap_block_lengths"]],
        int(config["bootstrap_repetitions"]),
    )
    dependence.to_csv(output_dir / "temporal_dependence.csv", index=False)
    ess.to_csv(output_dir / "effective_sample_size.csv", index=False)
    bootstrap.to_csv(output_dir / "block_bootstrap_sensitivity.csv", index=False)

    score_persistence = _score_persistence(resolve(config["economic_score_runtime"]))
    score_persistence.to_csv(output_dir / "frozen_signal_score_persistence.csv", index=False)

    calendar = pd.DatetimeIndex(pd.to_datetime(descriptors["datetime"]))
    windows = _candidate_windows(calendar, [int(value) for value in config["validation_lengths"]])
    windows.to_csv(output_dir / "candidate_validation_windows.csv", index=False)
    regime_columns = [
        "label_20d_cross_section_mean",
        "market_realized_volatility_20",
        "cross_section_return_dispersion",
        "market_breadth",
        "log_total_turnover",
        "median_amihud",
        "small_minus_large_return",
    ]
    regime_coverage = regime_window_coverage(descriptors, windows, regime_columns)
    regime_coverage.to_csv(output_dir / "regime_window_coverage.csv", index=False)

    _extension_estimates(config, qlib_coverage).to_csv(
        output_dir / "data_extension_feasibility.csv", index=False
    )
    _literature_map().to_csv(output_dir / "literature_evidence_map.csv", index=False)
    _source_capability_audit().to_csv(output_dir / "source_capability_audit.csv", index=False)
    _validation_design_comparison().to_csv(
        output_dir / "validation_design_comparison.csv", index=False
    )
    _dataset_design_evidence_map().to_csv(
        output_dir / "dataset_design_evidence_map.csv", index=False
    )

    lineage = pd.DataFrame(
        [
            {
                "lineage_step": 1,
                "artifact": "configs/full_research_feature_matrix_v1.yaml",
                "commit": "eae3f198e440cffe8259f89a8084ce2dcde39d65",
                "date": "2026-07-20",
                "start_date": "2021-02-01",
                "finding": "first repository introduction; full-research engineering scope",
            },
            {
                "lineage_step": 2,
                "artifact": "raw snapshot / universe v2 / Matrix v4 / labels v2",
                "commit": "multiple descendants",
                "date": "2026-07-21..2026-07-23",
                "start_date": "2021-02-01",
                "finding": "inherited without an independent historical-depth study",
            },
            {
                "lineage_step": 3,
                "artifact": "Factor Universe V2 Matrix Readiness",
                "commit": "2a4964f6d43302ad22c02c66e134f1ebb87c3016",
                "date": "2026-08-29",
                "start_date": "2021-02-01",
                "finding": "qualified the inherited range; bootstrap warm-up was derived from it",
            },
            {
                "lineage_step": 4,
                "artifact": "Research Protocol V2",
                "commit": "343ad838b6c317ebe78c484459d88a1501251189",
                "date": "2026-08-30",
                "start_date": "2021-02-01",
                "finding": "consumed Matrix boundary; did not prove its statistical adequacy",
            },
        ]
    )
    lineage.to_csv(output_dir / "matrix_start_lineage.csv", index=False)


def finalize(config_path: Path, config: dict[str, Any], output_dir: Path) -> None:
    files = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "manifest.json"
    )
    protocol = json.loads(resolve(config["research_protocol_manifest"]).read_text(encoding="utf-8"))
    matrix = json.loads(resolve(config["matrix_manifest"]).read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1,
        "stage_id": config["stage_id"],
        "artifact_status": "research_complete",
        "config_sha256": file_sha256(config_path),
        "source_matrix_artifact": matrix.get("stage_id"),
        "source_matrix_start": matrix.get("start_date"),
        "source_matrix_end": matrix.get("end_date"),
        "source_protocol_artifact_status": protocol.get("artifact_status"),
        "formal_structured_ml_competition_started": False,
        "dataset_window_selected_from_model_outcomes": False,
        "structured_ml_outcomes_read": False,
        "research_protocol_v2_changed": False,
        "frozen_matrix_changed": False,
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "authoritative_raw_snapshots_changed": False,
        "network_probe_receipts_present": (output_dir / "tushare_probe_receipts.csv").is_file(),
        "analysis_deterministic_seed": 20260830,
        "output_file_hashes": {path.name: file_sha256(path) for path in files},
        "manifest_identity": canonical_hash(
            {path.name: file_sha256(path) for path in files}
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Historical Dataset & Validation Design Study V1")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/historical_dataset_validation_design_v1.yaml"),
    )
    parser.add_argument("--stage", choices=("probe", "analyze", "finalize", "all"), default="analyze")
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = load_config(config_path)
    output_dir = resolve(config["output_dir"])
    if args.stage in {"probe", "all"}:
        run_network_probe(config, output_dir)
    if args.stage in {"analyze", "all"}:
        run_analysis(config, output_dir)
    if args.stage in {"finalize", "all"}:
        finalize(config_path, config, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
