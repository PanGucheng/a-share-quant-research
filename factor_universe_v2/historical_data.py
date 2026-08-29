from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .pit import prepare_pit_records
from .tushare_data import TushareSegmentStore


DAILY_BASIC_FIELDS = (
    "ts_code,trade_date,close,turnover_rate_f,volume_ratio,pe_ttm,pb,ps_ttm,"
    "dv_ttm,total_mv,circ_mv"
)
MONEYFLOW_FIELDS = (
    "ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount,"
    "buy_lg_amount,sell_lg_amount,buy_elg_amount,sell_elg_amount,net_mf_amount"
)
STATEMENT_FIELDS = {
    "income": (
        "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,revenue,oper_cost,"
        "operate_profit,n_income_attr_p,update_flag"
    ),
    "balancesheet": (
        "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_assets,"
        "total_liab,total_hldr_eqy_exc_min_int,money_cap,total_cur_assets,"
        "total_cur_liab,update_flag"
    ),
    "cashflow": (
        "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,n_cashflow_act,"
        "update_flag"
    ),
    "fina_indicator": (
        "ts_code,ann_date,end_date,current_ratio,cash_ratio,roa,debt_to_assets,"
        "netprofit_margin,grossprofit_margin,assets_yoy,or_yoy,netprofit_yoy,"
        "q_ocf_to_sales"
    ),
}


def qlib_to_tushare(instrument: str) -> str:
    value = str(instrument).upper()
    if len(value) != 8 or value[:2] not in {"SH", "SZ", "BJ"}:
        raise ValueError(f"unsupported Qlib instrument: {instrument}")
    return f"{value[2:]}.{value[:2]}"


def tushare_to_qlib(ts_code: str) -> str:
    code, exchange = str(ts_code).upper().split(".", maxsplit=1)
    if exchange not in {"SH", "SZ", "BJ"}:
        raise ValueError(f"unsupported Tushare instrument: {ts_code}")
    return f"{exchange}{code}"


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _query_with_columns(pro: Any, api: str, fields: str, **parameters: str) -> pd.DataFrame:
    frame = pro.query(api, fields=fields, **parameters)
    expected = fields.split(",")
    if frame.empty:
        return pd.DataFrame(columns=expected)
    return frame


def bootstrap_trade_date_layers(
    pro: Any,
    store: TushareSegmentStore,
    trade_dates: Iterable[pd.Timestamp | str],
    *,
    pause_seconds: float = 0.05,
    progress_every: int = 100,
) -> pd.DataFrame:
    """Fetch restartable daily_basic and moneyflow segments by trade date."""
    dates = [pd.Timestamp(value).strftime("%Y%m%d") for value in trade_dates]
    rows: list[dict[str, Any]] = []
    specs = {
        "daily_basic": (DAILY_BASIC_FIELDS, {"ts_code", "trade_date"}),
        "moneyflow": (MONEYFLOW_FIELDS, {"ts_code", "trade_date"}),
    }
    total = len(dates) * len(specs)
    completed = 0
    for api, (fields, required) in specs.items():
        for trade_date in dates:
            started = time.perf_counter()
            _, receipt = store.fetch(
                api=api,
                segment=trade_date,
                request=lambda api=api, fields=fields, trade_date=trade_date: _query_with_columns(
                    pro, api, fields, trade_date=trade_date
                ),
                required_columns=required,
                sort_columns=["trade_date", "ts_code"],
                public_parameters={"trade_date": trade_date, "fields": fields},
            )
            completed += 1
            rows.append(
                {
                    "api": api,
                    "segment": trade_date,
                    "row_count": int(receipt["row_count"]),
                    "data_sha256": receipt["data_sha256"],
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )
            if completed % progress_every == 0 or completed == total:
                print(f"daily bootstrap {completed}/{total}", flush=True)
            if pause_seconds:
                time.sleep(pause_seconds)
    return pd.DataFrame(rows)


def bootstrap_statement_layers(
    pro: Any,
    store: TushareSegmentStore,
    ts_codes: Iterable[str],
    *,
    announcement_start: str,
    announcement_end: str,
    pause_seconds: float = 0.05,
    progress_every: int = 100,
) -> pd.DataFrame:
    """Fetch restartable PIT statements one issuer at a time.

    A single issuer has fewer than each endpoint's row cap over the scoped interval,
    avoiding silent truncation on heavy market-wide announcement dates.
    """
    codes = sorted(set(str(value).upper() for value in ts_codes))
    rows: list[dict[str, Any]] = []
    total = len(codes) * len(STATEMENT_FIELDS)
    completed = 0
    for api, fields in STATEMENT_FIELDS.items():
        required = {"ts_code", "ann_date", "end_date"}
        if api != "fina_indicator":
            required.update({"f_ann_date", "update_flag"})
        for ts_code in codes:
            started = time.perf_counter()
            parameters = {
                "ts_code": ts_code,
                "start_date": announcement_start,
                "end_date": announcement_end,
                "fields": fields,
            }
            _, receipt = store.fetch(
                api=api,
                segment=ts_code,
                request=lambda api=api, fields=fields, ts_code=ts_code: _query_with_columns(
                    pro,
                    api,
                    fields,
                    ts_code=ts_code,
                    start_date=announcement_start,
                    end_date=announcement_end,
                ),
                required_columns=required,
                sort_columns=["ts_code", "end_date", "ann_date"],
                public_parameters=parameters,
            )
            completed += 1
            rows.append(
                {
                    "api": api,
                    "segment": ts_code,
                    "row_count": int(receipt["row_count"]),
                    "data_sha256": receipt["data_sha256"],
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )
            if completed % progress_every == 0 or completed == total:
                print(f"statement bootstrap {completed}/{total}", flush=True)
            if pause_seconds:
                time.sleep(pause_seconds)
    return pd.DataFrame(rows)


def load_segments(
    store: TushareSegmentStore,
    api: str,
    segments: Iterable[str],
    *,
    required_columns: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    receipts: list[dict[str, Any]] = []
    for segment in segments:
        frame, receipt = store.validate(
            api=api,
            segment=str(segment),
            required_columns=required_columns,
        )
        frames.append(frame)
        receipts.append(receipt)
    nonempty = [frame for frame in frames if not frame.empty]
    if nonempty:
        combined = pd.concat(nonempty, ignore_index=True)
    elif frames:
        combined = pd.DataFrame(columns=frames[0].columns)
    else:
        combined = pd.DataFrame()
    return combined, pd.DataFrame(receipts)


def normalize_trade_date_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["instrument"] = result["ts_code"].map(tushare_to_qlib)
    result["datetime"] = pd.to_datetime(result["trade_date"], format="%Y%m%d", errors="raise")
    if result.duplicated(["datetime", "instrument"]).any():
        raise ValueError("Tushare trade-date layer contains duplicate datetime/instrument keys")
    return result.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def prepare_statement_source(frame: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Prepare canonical consolidated source rows while retaining all revisions."""
    result = frame.copy()
    if result.empty:
        return result
    result["ts_code"] = result["ts_code"].astype(str).str.upper()
    if "report_type" in result:
        consolidated = result["report_type"].astype(str).eq("1")
        # Prefer consolidated statements, but do not erase issuers for which the
        # provider exposes only another report type.
        has_consolidated = consolidated.groupby(result["ts_code"]).transform("any")
        result = result.loc[consolidated | ~has_consolidated].copy()
    return prepare_pit_records(result, dataset=dataset)


def _same_day_revision_winner(group: pd.DataFrame) -> pd.Series:
    ordered = group.sort_values(
        ["revision_priority", "revision_sequence", "source_row_hash"]
    )
    return ordered.iloc[-1]


def statement_event_timeline(
    income: pd.DataFrame,
    balancesheet: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build issuer-level PIT events from independently revised statements.

    Each event applies only revisions public on that date, then chooses the most
    recent report period present in all three statements.  Prior-year fields are
    resolved from the state available at the same event date.
    """
    datasets = {
        "income": prepare_statement_source(income, "income"),
        "balancesheet": prepare_statement_source(balancesheet, "balancesheet"),
        "cashflow": prepare_statement_source(cashflow, "cashflow"),
    }
    audit_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    codes = sorted(set().union(*(set(frame.get("ts_code", ())) for frame in datasets.values())))
    for ts_code in codes:
        states: dict[str, dict[str, pd.Series]] = {name: {} for name in datasets}
        events: list[tuple[pd.Timestamp, str, str, pd.Series]] = []
        for name, frame in datasets.items():
            part = frame.loc[
                frame["ts_code"].eq(ts_code) & frame["information_available_date"].notna()
            ]
            for (available, period), group in part.groupby(
                ["information_available_date", "end_date"], sort=True
            ):
                winner = _same_day_revision_winner(group)
                events.append((pd.Timestamp(available), name, str(period), winner))
                audit_rows.append(
                    {
                        "ts_code": ts_code,
                        "dataset": name,
                        "end_date": period,
                        "information_available_date": pd.Timestamp(available),
                        "same_day_row_count": len(group),
                        "selected_update_flag": winner.get("update_flag", pd.NA),
                        "selected_source_row_hash": winner["source_row_hash"],
                    }
                )
        last_payload_hash = ""
        for available, name, period, row in sorted(
            events, key=lambda item: (item[0], item[1], item[2])
        ):
            states[name][period] = row
            common = set(states["income"]) & set(states["balancesheet"]) & set(states["cashflow"])
            if not common:
                continue
            current_period = max(common)
            current_date = pd.Timestamp(current_period)
            prior_period = (current_date - pd.DateOffset(years=1)).strftime("%Y%m%d")
            inc = states["income"][current_period]
            bal = states["balancesheet"][current_period]
            cfs = states["cashflow"][current_period]
            prior_inc = states["income"].get(prior_period)
            prior_bal = states["balancesheet"].get(prior_period)
            payload = {
                "instrument": tushare_to_qlib(ts_code),
                "information_available_date": available.normalize(),
                "report_period": pd.Timestamp(current_period),
                "revenue": inc.get("revenue"),
                "oper_cost": inc.get("oper_cost"),
                "operate_profit": inc.get("operate_profit"),
                "n_income_attr_p": inc.get("n_income_attr_p"),
                "total_assets": bal.get("total_assets"),
                "total_liab": bal.get("total_liab"),
                "total_hldr_eqy_exc_min_int": bal.get("total_hldr_eqy_exc_min_int"),
                "money_cap": bal.get("money_cap"),
                "total_cur_assets": bal.get("total_cur_assets"),
                "total_cur_liab": bal.get("total_cur_liab"),
                "n_cashflow_act": cfs.get("n_cashflow_act"),
                "prior_total_assets": None if prior_bal is None else prior_bal.get("total_assets"),
                "prior_revenue": None if prior_inc is None else prior_inc.get("revenue"),
                "prior_n_income_attr_p": (
                    None if prior_inc is None else prior_inc.get("n_income_attr_p")
                ),
                "income_source_row_hash": inc["source_row_hash"],
                "balancesheet_source_row_hash": bal["source_row_hash"],
                "cashflow_source_row_hash": cfs["source_row_hash"],
            }
            payload_hash = canonical_hash(payload)
            if payload_hash != last_payload_hash:
                event_rows.append(payload)
                last_payload_hash = payload_hash
    events_frame = pd.DataFrame(event_rows)
    if not events_frame.empty:
        events_frame = events_frame.sort_values(
            ["instrument", "information_available_date", "report_period"]
        ).reset_index(drop=True)
    return events_frame, pd.DataFrame(audit_rows)


def align_statement_events_to_keys(
    keys: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """As-of join PIT statement events to decision-date matrix keys."""
    parts: list[pd.DataFrame] = []
    for instrument, key_group in keys.groupby("instrument", sort=False):
        left = key_group.sort_values("datetime").copy()
        right = events.loc[events["instrument"].eq(instrument)].sort_values(
            "information_available_date"
        )
        if right.empty:
            for column in events.columns.difference(["instrument"]):
                left[column] = pd.NaT if "date" in column or column == "report_period" else np.nan
            parts.append(left)
            continue
        joined = pd.merge_asof(
            left,
            right.drop(columns="instrument"),
            left_on="datetime",
            right_on="information_available_date",
            direction="backward",
            allow_exact_matches=True,
        )
        parts.append(joined)
    return pd.concat(parts, ignore_index=True).sort_values(
        ["datetime", "instrument"]
    ).reset_index(drop=True)


def raw_snapshot_summary(root: Path) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    for receipt_path in sorted(Path(root).glob("*/*.receipt.json")):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        data_path = receipt_path.with_name(receipt_path.name.replace(".receipt.json", ".parquet"))
        actual_hash = hashlib.sha256(data_path.read_bytes()).hexdigest() if data_path.is_file() else ""
        rows.append(
            {
                "api": receipt.get("api"),
                "segment": receipt.get("segment"),
                "row_count": int(receipt.get("row_count", 0)),
                "column_count": len(receipt.get("columns", [])),
                "data_sha256": receipt.get("data_sha256"),
                "integrity_status": "pass" if actual_hash == receipt.get("data_sha256") else "fail",
            }
        )
    frame = pd.DataFrame(rows)
    identity = canonical_hash(
        frame[["api", "segment", "row_count", "data_sha256"]].to_dict("records")
        if not frame.empty
        else []
    )
    return frame, identity
