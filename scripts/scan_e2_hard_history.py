# ruff: noqa: E402
# Direct script entry points bootstrap the repository before local imports.
"""User-run fixed 2015-2023 data inventories. Never runs a strategy or account.

Modes are separate so local quote audit does not silently trigger network traffic.
Completed chunks are immutable and resumable with code/input binding checks.
"""

from pathlib import Path
import argparse
import hashlib
import json
import sys
import socket

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from qlib_integration.economic_readiness_closure import ClosureQuoteReader, quote_checks
from scripts.probe_e2_hard_blockers import query, DIV_FIELDS
from data_source_audit.sources.baostock import collect_one

BASE = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def scope_inventory():
    inv = json.loads(
        (ROOT / "reports/economic_translation_mvp/e1_inputs.json").read_text(encoding="utf-8")
    )
    starts = {}
    for year in range(2015, 2024):
        rec = inv["folds"][str(year)]["keys"]
        p = ROOT / rec["path"]
        assert (
            p
            == ROOT
            / f"outputs/research_protocol_v3_mvp/v3_recompute_audit_20260909_v1/audit/{year}/keys.parquet"
        )
        assert sha(p) == rec["sha256"]
        f = pd.read_parquet(
            p,
            columns=["datetime", "instrument"],
            filters=[
                ("datetime", ">=", pd.Timestamp(f"{year}-01-01")),
                (
                    "datetime",
                    "<=",
                    pd.Timestamp(f"{year}-12-31") if year < 2023 else pd.Timestamp("2023-12-29"),
                ),
            ],
        )
        assert len(f) == rec["rows"] and f.datetime.isin(pd.to_datetime(inv["calendar"])).all()
        for s, d in f.groupby("instrument").datetime.min().items():
            starts[s] = min(starts.get(s, "9999"), str(d.date()))
    assert (
        len(starts) == 4416
        and inv["calendar"][0] == "2015-01-05"
        and inv["calendar"][-1] == "2023-12-29"
    )
    return inv["calendar"], starts


def check_chunk(folder, key):
    path = folder / f"{key}.json"
    if not path.exists():
        return False
    r = json.loads(path.read_text(encoding="utf-8"))
    if r["status"] != "complete":
        raise ValueError(f"preserved failed chunk {key}; inspect failure before retry")
    for name, digest in r["files"].items():
        assert Path(name).name == name and sha(folder / name) == digest
    return True


def scan(mode):
    days, starts = scope_inventory()
    out = BASE / f"full_{mode}"
    codes = [
        "scripts/scan_e2_hard_history.py",
        "scripts/probe_e2_hard_blockers.py",
        "qlib_integration/economic_readiness_closure.py",
        "qlib_integration/economic_data_readiness.py",
    ]
    binding = dict(
        mode=mode,
        days=days,
        starts=starts,
        code_lf={
            p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p in codes
        },
        outcome_access=False,
        execution_ready=False,
    )
    if out.exists():
        assert json.loads((out / "scope.json").read_text(encoding="utf-8")) == binding
    else:
        out.mkdir(parents=True)
        put(out / "scope.json", binding)
    if (out / "complete.json").exists():
        raise ValueError("completed scan preserved; do not rerun")
    provider = ROOT.parent / "qlib_data/cn_data_community_20260609_derived"
    reader = (
        ClosureQuoteReader(provider, [s.lower() for s in starts], days)
        if mode == "quotes"
        else None
    )
    if mode == "states":
        import baostock as bs

        socket.setdefaulttimeout(20)
        if bs.login().error_code != "0":
            raise RuntimeError("Bao login failed")
    jobs = sorted(starts) if mode != "dividends" else days
    try:
        for i, key in enumerate(jobs):
            if check_chunk(out, key):
                continue
            files = {}
            try:
                if mode == "quotes":
                    dates = [d for d in days if d >= starts[key]]
                    f = pd.DataFrame({c: reader.read(key.lower(), c, dates) for c in reader.fields})
                    for c in ("open", "high", "low", "close"):
                        f[c] = f[c] / f.factor
                    f.volume = f.volume * f.factor * 100
                    f.amount = f.amount * 1000
                    # This is an audit of the existing recipe, not certified normalization.
                    # SH601313 is intentionally not silently corrected in this scan.
                    f.index.name = "date"
                    f["instrument"] = key
                    f.to_parquet(out / f"{key}.parquet", index=True)
                    reasons = pd.DataFrame(index=f.index)
                    reasons["missing_field"] = f[list(reader.fields)].isna().any(axis=1)
                    reasons["nonpositive_price_factor"] = (
                        f[["open", "high", "low", "close", "factor"]].le(0).any(axis=1)
                    )
                    reasons["negative_volume_amount"] = f[["volume", "amount"]].lt(0).any(axis=1)
                    vwap = f.amount / f.volume.where(f.volume.gt(0))
                    reasons["implied_vwap_bad"] = vwap.notna() & ~vwap.between(
                        f.low * 0.998, f.high * 1.002
                    )
                    reasons["ohlc_bad"] = f.open.notna() & (
                        ~f.open.between(f.low - 0.001, f.high + 0.001)
                        | ~f.close.between(f.low - 0.001, f.high + 0.001)
                    )
                    reasons[reasons.any(axis=1)].to_csv(out / f"{key}_anomalies.csv")
                    put(out / f"{key}_access.json", reader.audit)
                    reader.audit = []
                    stats = []
                    for y, g in f.groupby(f.index.str[:4]):
                        stats.append(dict(year=y, **quote_checks(g)))
                    put(out / f"{key}_quality.json", stats)
                    files = {
                        name: sha(out / name)
                        for name in (
                            f"{key}.parquet",
                            f"{key}_access.json",
                            f"{key}_quality.json",
                            f"{key}_anomalies.csv",
                        )
                    }
                elif mode == "states":
                    f, status = collect_one(key, starts[key], "2023-12-29")
                    if status != "success":
                        raise RuntimeError("historical state provider failure")
                    if len(f):
                        assert f.date.between(starts[key], "2023-12-29").all()
                        assert not f.date.duplicated().any()
                    # Day-end flags only. Board/IPO/PIT state is not fabricated here.
                    f.to_parquet(out / f"{key}.parquet", index=False)
                    files = {f"{key}.parquet": sha(out / f"{key}.parquet")}
                else:
                    f, status = query("dividend", dict(ex_date=key.replace("-", "")), DIV_FIELDS)
                    if status != "success":
                        raise RuntimeError(status)
                    if len(f) >= 2000:
                        raise ValueError(
                            "dividend page may be truncated; split before continuation"
                        )
                    if len(f):
                        assert f.ex_date.eq(key.replace("-", "")).all()
                    f.to_parquet(out / f"{key}.parquet", index=False)
                    files = {f"{key}.parquet": sha(out / f"{key}.parquet")}
                put(out / f"{key}.json", dict(status="complete", rows=len(f), files=files))
            except Exception as e:
                if not (out / f"{key}.json").exists():
                    put(
                        out / f"{key}.json",
                        dict(status="failed", error_type=type(e).__name__, files=files),
                    )
                raise
            if i % 25 == 0:
                print(mode, i + 1, "/", len(jobs), flush=True)
    finally:
        if mode == "states":
            bs.logout()
    summary = []
    for key in jobs:
        assert check_chunk(out, key)
        summary.append(
            dict(key=key, **json.loads((out / f"{key}.json").read_text(encoding="utf-8")))
        )
    put(
        out / "complete.json",
        dict(
            mode=mode,
            chunks=len(jobs),
            rows=sum(r["rows"] for r in summary),
            e2_ready=False,
            coverage="ex-date query inventory only; rights/terminal/other events not covered"
            if mode == "dividends"
            else "raw audit or historical day flags; no automatic execution certification",
        ),
    )
    print(mode, "inventory complete; E2 READY not inferred", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["quotes", "states", "dividends"])
    scan(p.parse_args().mode)
