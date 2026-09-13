# ruff: noqa: E402
# Direct script entry points bootstrap the repository before local imports.
"""Verify closed evidence and materialize independently verified alias quote overlay.

Only existing 2014 warmup / 2015-2023 slices and projected frozen keys are read.
No strategy, account or provider call. Writes a new analysis directory once.
"""

from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from qlib_integration.execution_readiness import UnitRule, normalize_quote, adv20_with_warmup

BASE = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"


def dump(path, obj):
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


def main():
    out = BASE / "analysis"
    out.mkdir(exist_ok=False)
    can = BASE / "canary"
    for folder in (can, BASE / "alias_warmup"):
        for name, digest in json.loads(
            (folder / "receipt.json").read_text(encoding="utf-8")
        ).items():
            assert (
                Path(name).name == name
                and hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
            )
    for rec in json.loads((BASE / "network/receipts.json").read_text(encoding="utf-8")):
        assert rec["status"] == "success"
        if rec["rows"]:
            assert (
                hashlib.sha256((BASE / f"network/{rec['key']}.parquet").read_bytes()).hexdigest()
                == rec["sha256"]
            )
    scope = json.loads((can / "scope.json").read_text(encoding="utf-8"))
    for name, dates in (
        ("warmup_access.json", scope["warmup_dates"]),
        ("alias_access.json", scope["alias_dates"]),
    ):
        for r in json.loads((can / name).read_text(encoding="utf-8")):
            assert r["completed"] and not r["whole_parent_hash"] and set(r["dates"]) <= set(dates)
    local = pd.read_parquet(can / "alias_local_raw_recipe.parquet")
    pair = pd.read_parquet(can / "alias_source_pairs.parquet").set_index("date")
    assert pair.cross_source_agreed.all() and len(pair) == 2065
    overlay = []
    rules = []
    for stock in ("SH601313", "SH601360"):
        active = local[local.instrument.eq(stock) & local.close.notna()]
        assert active.date.isin(pair.index).all()
        source = f"two-source-every-valid-day:{hashlib.sha256((can / 'alias_source_pairs.parquet').read_bytes()).hexdigest()}"
        mul = 1 if stock == "SH601313" else 100
        amul = 1 if stock == "SH601313" else 1000
        rule = UnitRule(
            stock,
            active.date.min(),
            active.date.max(),
            "community_adjusted",
            mul,
            amul,
            source,
            True,
        )
        for _, r in active.iterrows():
            native = r.to_dict()
            for c in ("open", "high", "low", "close"):
                native[c] = r[c] * r.factor
            native["volume"] = r.volume / r.factor / 100
            native["amount"] = r.amount / 1000
            q = normalize_quote(native, rule)
            ref = pair.loc[r.date]
            for c in ("open", "high", "low", "close", "volume", "amount"):
                assert np.isclose(q[c], ref[c + "_bao"], rtol=2e-5, atol=0.02)
            overlay.append(q)
        rules.append(
            dict(
                **rule.__dict__,
                verified_dates=active.date.tolist(),
                valid_rows=len(active),
                inference="observed dates only; missing sessions still require state; never apply to other securities",
            )
        )
    pd.DataFrame(overlay).to_parquet(out / "normalized_alias_quotes.parquet", index=False)
    dump(out / "unit_rules.json", rules)
    # 2014 rule must be independently checked, never inferred from the 2015 ratio.
    w = pd.read_parquet(can / "warmup_raw.parquet")
    bw = pd.read_parquet(BASE / "alias_warmup/baostock.parquet").set_index("date")
    tw = pd.read_parquet(BASE / "alias_warmup/tushare.parquet")
    tw["date"] = pd.to_datetime(tw.trade_date).dt.strftime("%Y-%m-%d")
    tw = tw.set_index("date")
    sw = w[w.instrument.eq("SH601313")].set_index("date")
    for d, r in sw.iterrows():
        volume = r.volume / 100
        amount = r.amount / 1000
        assert np.isclose(volume, float(bw.loc[d, "volume"]), rtol=2e-5)
        assert np.isclose(volume, tw.loc[d, "vol"] * 100, rtol=2e-5)
        assert np.isclose(amount, float(bw.loc[d, "amount"]), rtol=2e-5)
        assert np.isclose(amount, tw.loc[d, "amount"] * 1000, rtol=2e-5)
        mask = w.instrument.eq("SH601313") & w.date.eq(d)
        w.loc[mask, "volume"] = volume
        w.loc[mask, "amount"] = amount
    rows = []
    for s, g in w.groupby("instrument"):
        v = g.set_index("date").volume
        finite = np.isfinite(g.factor).all() and g.factor.gt(0).all()
        try:
            assert finite
            avg = adv20_with_warmup(v, scope["warmup_dates"], order_date="2015-01-05")
            # Independent scalar sum, including any explicit zero days.
            assert np.isclose(avg, sum(float(v[d]) for d in scope["warmup_dates"]) / 20, rtol=1e-12)
            rows.append(dict(instrument=s, status="volume_available", adv20=avg))
        except (AssertionError, ValueError):
            rows.append(dict(instrument=s, status="unknown_volume_fail_closed", adv20=None))
    pd.DataFrame(rows).to_csv(out / "warmup_adv20.csv", index=False)
    w[["instrument", "date", "volume"]].to_parquet(
        out / "warmup_volume_overlay.parquet", index=False
    )
    inv = json.loads(
        (ROOT / "reports/economic_translation_mvp/e1_inputs.json").read_text(encoding="utf-8")
    )
    coexist = []
    for y in range(2015, 2024):
        rec = inv["folds"][str(y)]["keys"]
        p = ROOT / rec["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == rec["sha256"]
        f = pd.read_parquet(
            p,
            columns=["datetime", "instrument"],
            filters=[
                ("instrument", "in", ["SH601313", "SH601360"]),
                ("datetime", ">=", pd.Timestamp(f"{y}-01-01")),
                (
                    "datetime",
                    "<=",
                    pd.Timestamp(f"{y}-12-31") if y < 2023 else pd.Timestamp("2023-12-29"),
                ),
            ],
        )
        by = f.groupby("datetime").instrument.nunique()
        dates = by[by.eq(2)].index.strftime("%Y-%m-%d").tolist()
        coexist.append(dict(year=y, coexisting_candidate_dates=len(dates), dates=dates))
    dump(out / "identity_collisions.json", coexist)
    dump(
        out / "verification.json",
        dict(
            normalized_alias_rows=len(overlay),
            independent_source_pairs=2065,
            old_code_corrected_rows=654,
            warmup_independently_corrected_rows=20,
            warmup_volume_available_stocks=sum(r["status"] == "volume_available" for r in rows),
            warmup_unknown_stocks=sum(r["status"] != "volume_available" for r in rows),
            identity_collision_days=sum(r["coexisting_candidate_dates"] for r in coexist),
            full_inventory=False,
            real_account_run=False,
            e2_ready=False,
        ),
    )
    dump(
        out / "receipt.json",
        {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},
    )
    print((out / "verification.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
