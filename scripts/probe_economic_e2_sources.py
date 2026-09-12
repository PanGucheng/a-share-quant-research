"""Small, fixed historical provider probes; no unbounded symbol history request."""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import requests
from data_source_audit.sources.baostock import collect_one, library_version
from factor_universe_v2.tushare_data import classify_probe_error

OUT = ROOT / "outputs/economic_translation_mvp/e2_closure_v1/network"
BAO = [
    ("SZ300001", "2015-01-05", "2015-02-13"),
    ("SZ300001", "2015-07-01", "2015-08-10"),
    ("SH600000", "2015-01-05", "2015-01-30"),
    ("SH688001", "2019-07-22", "2019-07-26"),
    ("SH600000", "2020-08-24", "2020-08-28"),
    ("SH600000", "2023-08-28", "2023-08-29"),
]
TUSHARE = [
    (
        "stk_limit",
        dict(ts_code="600000.SH", trade_date=d),
        "ts_code,trade_date,pre_close,up_limit,down_limit",
        "trade_date",
    )
    for d in ["20150115", "20200824", "20230828"]
] + [
    (
        "suspend_d",
        dict(ts_code="300001.SZ", start_date="20150105", end_date="20150213"),
        "ts_code,trade_date,suspend_timing,suspend_type",
        "trade_date",
    ),
    (
        "dividend",
        dict(ex_date="20150716"),
        "ts_code,ann_date,div_proc,stk_div,stk_bo_rate,stk_co_rate,cash_div_tax,record_date,ex_date,pay_date,div_listdate,imp_ann_date",
        "ex_date",
    ),
    (
        "dividend",
        dict(ex_date="20200716"),
        "ts_code,ann_date,div_proc,stk_div,stk_bo_rate,stk_co_rate,cash_div_tax,record_date,ex_date,pay_date,div_listdate,imp_ann_date",
        "ex_date",
    ),
    (
        "namechange",
        dict(ts_code="000033.SZ", start_date="20150101", end_date="20151231"),
        "ts_code,name,start_date,ann_date,change_reason",
        "ann_date",
    ),
]


def dump(name, value):
    (OUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    dump(
        "requests.json",
        dict(
            baostock=BAO,
            tushare=TUSHARE,
            allowed_start="2015-01-01",
            allowed_end="2023-12-29",
            no_retries=True,
        ),
    )
    receipts = []

    def record(key, frame, row, datecol):
        if not frame.empty:
            dates = pd.to_datetime(frame[datecol], errors="raise")
            assert dates.between("2015-01-01", "2023-12-29").all()
            assert not frame.duplicated(
                ["code", datecol] if "code" in frame else list(frame.columns)
            ).any()
            frame.to_parquet(OUT / f"{key}.parquet", index=False)
            row.update(
                rows=len(frame),
                date_min=str(dates.min().date()),
                date_max=str(dates.max().date()),
                columns=list(frame.columns),
                sha256=hashlib.sha256((OUT / f"{key}.parquet").read_bytes()).hexdigest(),
            )
        else:
            row["rows"] = 0
        receipts.append(row)
        dump("receipts.json", receipts)
        print(key, row.get("status"), row.get("rows"), flush=True)

    import baostock as bs

    socket.setdefaulttimeout(10)
    login = bs.login()
    try:
        if login.error_code == "0":
            for i, (stock, start, end) in enumerate(BAO):
                row = dict(
                    provider="baostock",
                    version=library_version(),
                    instrument=stock,
                    start=start,
                    end=end,
                    adjustflag="3",
                )
                try:
                    f, status = collect_one(stock, start, end)
                    row["status"] = status
                    if not f.empty:
                        assert pd.to_datetime(f.date).between(start, end).all()
                    record(f"bao_{i}", f, row, "date")
                except Exception as e:
                    row.update(status="failed", error_type=type(e).__name__)
                    record(f"bao_{i}", pd.DataFrame(), row, "date")
        else:
            receipts.append(
                dict(provider="baostock", status="login_failed", error_code=login.error_code)
            )
            dump("receipts.json", receipts)
    finally:
        bs.logout()
    token = os.environ.get("TUSHARE_TOKEN")
    for i, (api, params, fields, datecol) in enumerate(TUSHARE):
        row = dict(provider="tushare", api=api, parameters=params, fields=fields)
        try:
            if not token:
                raise RuntimeError("token unavailable")
            response = requests.post(
                "https://api.tushare.pro",
                json=dict(api_name=api, token=token, params=params, fields=fields),
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(str(payload.get("msg", "source error")))
            f = pd.DataFrame(payload["data"]["items"], columns=payload["data"]["fields"])
            if not f.empty:
                if "trade_date" in params:
                    assert f[datecol].eq(params["trade_date"]).all()
                elif "ex_date" in params:
                    assert f[datecol].eq(params["ex_date"]).all()
                else:
                    assert f[datecol].between(params["start_date"], params["end_date"]).all()
            row["status"] = "accessible_nonempty" if len(f) else "accessible_empty"
            record(f"ts_{i}", f, row, datecol)
        except Exception as e:
            # No response body or exception text: tokens/headers never enter logs.
            row.update(status=classify_probe_error(e), error_type=type(e).__name__)
            record(f"ts_{i}", pd.DataFrame(), row, datecol)
        time.sleep(0.5)
    dump("complete.json", dict(probes=len(receipts), full_history_certified=False))


if __name__ == "__main__":
    main()
