# ruff: noqa: E402
# Direct script entry points bootstrap the repository before local imports.
"""Closed historical source canary. No prediction, recent data or account run."""

from pathlib import Path
import sys
import os
import json
import hashlib
import socket

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import requests
from data_source_audit.sources.baostock import collect_one

OUT = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1/network"
BAO = [
    ("SH600070", "2016-02-01", "2016-03-04"),
    ("SH600120", "2016-02-01", "2016-03-04"),
    ("SH600146", "2017-02-03", "2017-03-02"),
    ("SH601313", "2015-01-05", "2018-03-02"),
    ("SH601360", "2015-01-05", "2023-12-29"),
    ("SH600000", "2014-12-04", "2014-12-31"),
    ("SZ000001", "2014-12-04", "2014-12-31"),
    ("SZ300001", "2014-12-04", "2014-12-31"),
]
DIV_FIELDS = "ts_code,ann_date,div_proc,stk_div,stk_bo_rate,stk_co_rate,cash_div_tax,record_date,ex_date,pay_date,div_listdate,imp_ann_date"


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query(api, params, fields):
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("token missing")
    response = requests.post(
        "https://api.tushare.pro",
        json=dict(api_name=api, token=token, params=params, fields=fields),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        return pd.DataFrame(), f"denied_code_{payload.get('code')}"
    return pd.DataFrame(payload["data"]["items"], columns=payload["data"]["fields"]), "success"


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    # Fixed July 16, whether exchange session or not; not chosen by event frequency.
    ts = [("dividend", dict(ex_date=f"{y}0716"), DIV_FIELDS, "ex_date") for y in range(2015, 2024)]
    ts += [
        (
            "daily",
            dict(ts_code="601360.SH", start_date="20150105", end_date="20231229"),
            "ts_code,trade_date,open,high,low,close,vol,amount",
            "trade_date",
        )
    ]
    ts += [
        (
            "suspend_d",
            dict(
                ts_code=f"{s[-6:]}.SH", start_date=a.replace("-", ""), end_date=b.replace("-", "")
            ),
            "ts_code,trade_date,suspend_timing,suspend_type",
            "trade_date",
        )
        for s, a, b in BAO[:3]
    ]
    dump(OUT / "scope.json", dict(baostock=BAO, tushare=ts, warmup_only=True, no_retries=True))
    receipts = []

    def save(key, f, status, datecol, lo, hi):
        if len(f):
            dates = pd.to_datetime(f[datecol])
            if not dates.between(lo, hi).all():
                raise ValueError("source returned outside requested dates")
            f.to_parquet(OUT / f"{key}.parquet", index=False)
        receipts.append(
            dict(
                key=key,
                status=status,
                rows=len(f),
                sha256=hashlib.sha256((OUT / f"{key}.parquet").read_bytes()).hexdigest()
                if len(f)
                else None,
            )
        )
        dump(OUT / "receipts.json", receipts)
        print(key, status, len(f), flush=True)

    import baostock as bs

    socket.setdefaulttimeout(15)
    login = bs.login()
    try:
        if login.error_code != "0":
            raise RuntimeError("Bao login failed")
        for i, (s, a, b) in enumerate(BAO):
            try:
                f, status = collect_one(s, a, b)
                save(f"bao_{i}", f, status, "date", a, b)
            except Exception as exc:
                save(f"bao_{i}", pd.DataFrame(), type(exc).__name__, "date", a, b)
    finally:
        bs.logout()
    for i, (api, params, fields, datecol) in enumerate(ts):
        try:
            f, status = query(api, params, fields)
            lo = params.get("ex_date", params.get("start_date"))
            hi = params.get("ex_date", params.get("end_date"))
            save(f"ts_{i}", f, status, datecol, pd.Timestamp(lo), pd.Timestamp(hi))
        except Exception as exc:
            save(f"ts_{i}", pd.DataFrame(), type(exc).__name__, datecol, "2015-01-01", "2023-12-29")
    dump(OUT / "complete.json", dict(requests=len(receipts), full_inventory=False))


if __name__ == "__main__":
    main()
