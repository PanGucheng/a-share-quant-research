# ruff: noqa: E402
# Direct script entry points bootstrap the repository before local imports.
"""Bounded alias, held-gap, event-slice and explicitly authorized warmup evidence."""

from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from qlib_integration.execution_readiness import WarmupReader
from qlib_integration.economic_readiness_closure import ClosureQuoteReader

BASE = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"
OLD = ROOT / "outputs/economic_translation_mvp/e2_closure_v1/local"
PROVIDER = ROOT.parent / "qlib_data/cn_data_community_20260609_derived"
FIELDS = ("open", "high", "low", "close", "volume", "amount", "factor")


def dump(path, obj):
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def read_stock(reader, stock, dates):
    f = pd.DataFrame({c: reader.read(stock, c, dates) for c in FIELDS})
    f["date"], f["instrument"] = f.index, stock.upper()
    for c in ("open", "high", "low", "close"):
        f[c] = f[c] / f.factor
    f["volume"] = f.volume * f.factor * 100
    f["amount"] = f.amount * 1000
    return f.reset_index(drop=True)


def main():
    out = BASE / "canary"
    out.mkdir(parents=True, exist_ok=False)
    inv = json.loads(
        (ROOT / "reports/economic_translation_mvp/e1_inputs.json").read_text(encoding="utf-8")
    )
    rec = inv["folds"]["2015"]["keys"]
    keypath = ROOT / rec["path"]
    assert hashlib.sha256(keypath.read_bytes()).hexdigest() == rec["sha256"]
    keys = pd.read_parquet(
        keypath,
        columns=["datetime", "instrument"],
        filters=[("datetime", "==", pd.Timestamp("2015-01-05"))],
    )
    names = sorted(keys.instrument.str.lower().unique())
    assert len(names) == 2000
    warm_dates = json.loads(
        (ROOT / "reports/economic_translation_mvp/e2_readiness_v2/warmup_metadata.json").read_text()
    )["prior_dates"]
    alias_dates = inv["calendar"]
    dump(
        out / "scope.json",
        dict(
            warmup_dates=warm_dates,
            warmup_instruments=names,
            alias_instruments=["sh601313", "sh601360"],
            alias_dates=alias_dates,
            fields=FIELDS,
            warmup_role="2015 ADV20 only; no prediction or outcome",
            key_sha256=rec["sha256"],
        ),
    )
    reader = WarmupReader(PROVIDER, names, warm_dates)
    warm = []
    try:
        for i, s in enumerate(names):
            warm.append(read_stock(reader, s, warm_dates))
            if i % 500 == 0:
                print("warmup approved stocks", i, flush=True)
    finally:
        dump(out / "warmup_access.json", reader.audit)
    w = pd.concat(warm, ignore_index=True)
    w.to_parquet(out / "warmup_raw.parquet", index=False)
    vwap = w.amount / w.volume.where(w.volume.gt(0))
    w["unit_bad"] = vwap.notna() & ~vwap.between(w.low * 0.998, w.high * 1.002)
    w["valid_volume"] = np.isfinite(w.volume) & w.volume.ge(0) & ~w.unit_bad
    agg = w.groupby("instrument").agg(
        valid_days=("valid_volume", "sum"),
        unit_bad=("unit_bad", "sum"),
        missing_days=("volume", lambda s: int(s.isna().sum())),
    )
    agg.to_csv(out / "warmup_coverage.csv")
    # Independent source warmup and missing historical held close checks.
    warm_cross = []
    for i, stock in ((5, "SH600000"), (6, "SZ000001"), (7, "SZ300001")):
        b = pd.read_parquet(BASE / f"network/bao_{i}.parquet")
        m = w[w.instrument.eq(stock)].merge(b, on="date", suffixes=("_local", "_bao"))
        for r in m.itertuples():
            reference = pd.to_numeric(r.volume_bao, errors="coerce")
            warm_cross.append(
                dict(
                    instrument=stock,
                    date=r.date,
                    tradestatus=r.tradestatus,
                    local_missing=bool(pd.isna(r.volume_local)),
                    volume_relative_error=float(abs(r.volume_local / reference - 1))
                    if np.isfinite(r.volume_local) and reference > 0
                    else None,
                )
            )
    pd.DataFrame(warm_cross).to_csv(out / "warmup_cross_source.csv", index=False)
    oldscope = json.loads((OLD / "scope.json").read_text())
    old = pd.read_parquet(
        OLD / "bounded_raw_units.parquet", columns=["date", "instrument", "close"]
    )
    held = []
    for i, stock in enumerate(("SH600070", "SH600120", "SH600146")):
        specs = [
            s
            for s in oldscope["groups"]
            if s["kind"] == "left_signal_universe" and stock in s["names"]
        ]
        dates = specs[0]["dates"]
        missing = old[old.instrument.eq(stock) & old.date.isin(dates) & old.close.isna()]
        b = pd.read_parquet(BASE / f"network/bao_{i}.parquet").set_index("date")
        t = pd.read_parquet(BASE / f"network/ts_{10 + i}.parquet")
        for r in missing.itertuples():
            flags = t[t.trade_date.eq(r.date.replace("-", ""))]
            held.append(
                dict(
                    instrument=stock,
                    date=r.date,
                    bao_tradestatus=b.loc[r.date, "tradestatus"],
                    tushare_full_day_suspension=bool(
                        (flags.suspend_type.eq("S") & flags.suspend_timing.fillna("").eq("")).any()
                    ),
                    preopen_announcement_certified=False,
                )
            )
    pd.DataFrame(held).to_csv(out / "held_gap_explanations.csv", index=False)
    assert len(held) == 48
    ar = ClosureQuoteReader(PROVIDER, ["sh601313", "sh601360"], alias_dates)
    try:
        local = pd.concat(
            [read_stock(ar, s, alias_dates) for s in ar.instruments], ignore_index=True
        )
    finally:
        dump(out / "alias_access.json", ar.audit)
    local.to_parquet(out / "alias_local_raw_recipe.parquet", index=False)
    b = pd.read_parquet(BASE / "network/bao_4.parquet")
    t = pd.read_parquet(BASE / "network/ts_9.parquet")
    t["date"] = pd.to_datetime(t.trade_date).dt.strftime("%Y-%m-%d")
    for c in ("open", "high", "low", "close", "volume", "amount"):
        b[c] = pd.to_numeric(b[c], errors="coerce")
    t["volume"] = t.vol * 100
    t["amount"] = t.amount * 1000
    pair = b.merge(t, on="date", suffixes=("_bao", "_ts"))
    agreed = np.ones(len(pair), dtype=bool)
    for c in ("open", "high", "low", "close", "volume", "amount"):
        agreed &= np.isclose(pair[c + "_bao"], pair[c + "_ts"], rtol=2e-5, atol=0.02)
    pair["cross_source_agreed"] = agreed
    pair.to_parquet(out / "alias_source_pairs.parquet", index=False)
    cross = []
    for r in local.itertuples():
        if not np.isfinite(r.close):
            continue
        ref = pair[pair.date.eq(r.date)]
        if ref.empty:
            continue
        ref = ref.iloc[0]
        cross.append(
            dict(
                instrument=r.instrument,
                date=r.date,
                year=int(r.date[:4]),
                source_agreed=bool(ref.cross_source_agreed),
                close_rel=float(r.close / ref.close_bao - 1),
                volume_ratio=float(r.volume / ref.volume_bao) if ref.volume_bao else None,
                amount_ratio=float(r.amount / ref.amount_bao) if ref.amount_bao else None,
            )
        )
    pd.DataFrame(cross).to_csv(out / "alias_unit_comparison.csv", index=False)
    events = []
    for i in range(9):
        p = BASE / f"network/ts_{i}.parquet"
        if p.exists():
            f = pd.read_parquet(p)
            f["sample_year"] = 2015 + i
            events.append(f)
    events = pd.concat(events, ignore_index=True)
    events.to_parquet(out / "event_date_slices.parquet", index=False)
    eventstats = []
    for y in range(2015, 2024):
        f = events[events.sample_year.eq(y)]
        eventstats.append(
            dict(
                year=y,
                queried_ex_date=f"{y}-07-16",
                rows=len(f),
                cash_positive=int(f.cash_div_tax.fillna(0).gt(0).sum()),
                bonus_positive=int(f.stk_div.fillna(0).gt(0).sum()),
                full_year_inventory=False,
            )
        )
    pd.DataFrame(eventstats).to_csv(out / "event_inventory_slices.csv", index=False)
    dump(
        out / "summary.json",
        dict(
            warmup_rows=len(w),
            warmup_valid_volume_rows=int(w.valid_volume.sum()),
            warmup_all20_stocks=int(agg.valid_days.eq(20).sum()),
            warmup_unit_bad=int(w.unit_bad.sum()),
            held_missing=48,
            held_bao_suspended=sum(r["bao_tradestatus"] == "0" for r in held),
            held_tushare_full_day=sum(r["tushare_full_day_suspension"] for r in held),
            alias_independent_pairs=len(pair),
            alias_source_agreed=int(agreed.sum()),
            events_in_slices=len(events),
            full_inventory=False,
            e2_ready=False,
        ),
    )
    dump(
        out / "receipt.json",
        {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},
    )
    print("bounded closure canary complete", flush=True)


if __name__ == "__main__":
    main()
