"""Bounded score-blind feasibility from sealed E2 quote slices; never a backtest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from qlib_integration.small_capital_feasibility import (
    affordable_quantity, charges, hash_order, personal_fees,
)

BASE = ROOT / "outputs/economic_translation_mvp/e2_closure_v1/local"
OUT = ROOT / "outputs/economic_translation_mvp/small_capital_v1"
KS = (3, 5, 8, 12, 16, 24, 32, 50, 100, 200)
AUMS = (50_000, 100_000)
DATES = ("2015-08-28", "2020-08-28", "2023-08-28")
COLUMNS = ["date", "instrument", "close", "open", "volume", "amount", "high", "low"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def load_sealed():
    receipt_path = BASE / "receipt.json"
    verification = json.loads((ROOT / "reports/economic_translation_mvp/e2_readiness_v2/VERIFICATION.json").read_text(encoding="utf-8"))
    # Anchor the old receipt itself to committed audit evidence, not just its contents.
    expected = verification["runtime_output_hashes"]["local/receipt.json"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert expected == sha(receipt_path)
    for name in ("scope.json", "bounded_raw_units.parquet"):
        assert sha(BASE / name) == receipt[name]
    scope = json.loads((BASE / "scope.json").read_text(encoding="utf-8"))
    for dates in scope["request_dates_by_stock"].values():
        assert all("2015-01-01" <= d <= "2023-12-29" for d in dates)
    data = pd.read_parquet(BASE / "bounded_raw_units.parquet", columns=COLUMNS)
    assert data.date.between("2015-01-01", "2023-12-29").all()
    assert not data.duplicated(["date", "instrument"]).any()
    groups = [s for s in scope["groups"] if s["kind"] == "full_pool"]
    assert tuple(s["date"] for s in groups) == DATES
    return scope, data, groups, {n: receipt[n] for n in ("scope.json", "bounded_raw_units.parquet")}


def snapshot(data, spec):
    date, names = spec["date"], spec["names"]
    prior = spec["dates"][:-1]
    assert len(prior) == 20 and max(prior) < date
    f = data[data.date.eq(date)].set_index("instrument").reindex(names).copy()
    past = data[data.date.isin(prior) & data.instrument.isin(names)]
    vols = past.pivot(index="date", columns="instrument", values="volume").reindex(prior)
    f["adv20"] = vols.mean().where(vols.notna().all() & np.isfinite(vols).all() & vols.ge(0).all())
    f["reference_close"] = data[data.date.eq(prior[-1])].set_index("instrument").close
    # The prior audit found inconsistent units: flag, retain denominator, do not repair or filter.
    vwap = past.amount / past.volume.where(past.volume.gt(0))
    bad = past[vwap.notna() & ~vwap.between(past.low * .998, past.high * 1.002)].instrument
    f["unit_anomaly"] = f.index.isin(bad)
    f["board"] = ["star" if s.startswith("SH688") else "chinext" if s.startswith("SZ30") else "main" for s in names]
    f["minimum"] = np.where(f.board.eq("star"), 200, 100)
    return f


def quantities(frame, date, budget):
    records = []
    for s, r in frame.iterrows():
        fee = personal_fees(date, s[:2])
        q = affordable_quantity(r.reference_close, budget, r.board, fee)
        value = 0 if q is None else q * r.reference_close
        if q == 0:
            value = 0.0
        cost = charges(value, q or 0, "buy", fee)
        records.append(dict(instrument=s, quantity=np.nan if q is None else q,
                            value=value, buy_fee=cost))
    return frame.join(pd.DataFrame(records).set_index("instrument"))


def basket_summary(f, replacements, date, aum, k):
    budget = .95 * aum / k
    values, fees = f.value.to_numpy(), f.buy_fee.to_numpy()
    positive = values > 0
    invested = float(values.sum())
    weights = values / aum
    opening_cost = 0.0
    unknown_open = 0
    replacement_zero = replacement_unknown = replacement_lost = 0
    replacement_fees = 0.0
    for (stock, old), (newstock, new) in zip(f.iterrows(), replacements.iterrows()):
        if old.quantity > 0:
            if not np.isfinite(old.open) or old.open <= 0:
                unknown_open += 1
            else:
                v = old.quantity * old.open
                opening_cost += v + charges(v, old.quantity, "buy", personal_fees(date, stock[:2]))
        if pd.isna(old.quantity) or pd.isna(new.quantity):
            replacement_unknown += 1
            continue
        # Independent constant-price liquidation of a hypothetical already-sellable sleeve.
        sell_fee = charges(old.value, old.quantity, "sell", personal_fees(date, stock[:2]))
        sleeve_cash = budget - old.buy_fee - sell_fee
        qnew = affordable_quantity(new.reference_close, sleeve_cash, new.board, personal_fees(date, newstock[:2]))
        replacement_zero += int(qnew == 0)
        replacement_lost += int(new.quantity > 0 and qnew == 0)
        replacement_fees += sell_fee + charges(qnew * new.reference_close, qnew, "buy", personal_fees(date, newstock[:2]))
    adv_valid = f.adv20.notna() & np.isfinite(f.adv20) & f.adv20.ge(0) & ~f.unit_anomaly
    stress = {}
    for percent in (10, 20):
        amount = 0.0
        for s, r in f.iterrows():
            if r.quantity > 0:
                v = r.value * (1 + percent / 100)
                amount += v + charges(v, r.quantity, "buy", personal_fees(date, s[:2]))
        stress[f"all_buy_prices_plus_{percent}_cash_shortfall_cny"] = max(0, amount - aum)
    return dict(
        unknown_price=int(f.quantity.isna().sum()), below_lot=int(f.quantity.eq(0).sum()),
        buildable=int(positive.sum()), unknown_or_bad_adv=int((~adv_valid).sum()),
        unit_anomaly=int(f.unit_anomaly.sum()),
        adv_cap_binds=int((adv_valid & f.quantity.gt(.01 * f.adv20)).sum()),
        reference_invested_fraction=invested / aum,
        reference_cash_fraction=1 - (invested + fees.sum()) / aum,
        buy_fee_bps=float(fees.sum() / aum * 10000),
        max_weight=float(weights.max()),
        mean_absolute_target_weight_error=float(np.abs(weights - .95 / k).mean()),
        effective_names=0 if not invested else float(invested ** 2 / (values ** 2).sum()),
        unknown_open_for_orders=unknown_open,
        known_open_cost_cny=opening_cost,
        known_open_cash_shortfall_cny=max(0, opening_cost - aum),
        replacement_unknown=replacement_unknown,
        replacement_below_lot=replacement_zero,
        replacement_newly_below_lot_due_to_fees=replacement_lost,
        replacement_sell_buy_fee_bps=replacement_fees / aum * 10000,
        **stress,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    dump(OUT / "scope.json", dict(dates=DATES, aums=AUMS, ks=KS, replicates=32,
         columns=COLUMNS, reserve=.05, commission=.00025, minimum_commission=5,
         source="sealed E2 slices only", predictions=False, nav=False,
         sampling="SHA256 small-capital-v1|date|replicate|instrument; first K; next K replacement",
         plan_sha256=sha(ROOT / "docs/SMALL_CAPITAL_EXECUTION_FEASIBILITY_PLAN.md")))
    _, data, groups, inputs = load_sealed()
    results, pool, prices, samples = [], [], [], []
    for spec in groups:
        date = spec["date"]
        f = snapshot(data, spec)
        p = f.reference_close.where(f.reference_close.gt(0))
        for board, g in f.groupby("board"):
            valid = g.reference_close.where(g.reference_close.gt(0)).dropna()
            row = dict(date=date, board=board, names=len(g), unknown_price=len(g) - len(valid))
            for label, series in (("price", valid), ("minimum_notional", valid * g.loc[valid.index, "minimum"])):
                row.update({f"{label}_p{q}": float(series.quantile(q / 100)) for q in (10, 50, 90, 95)})
            prices.append(row)
        for aum in AUMS:
            for k in KS:
                budget = .95 * aum / k
                calculated = quantities(f, date, budget)
                pool.append(dict(date=date, aum=aum, k=k, names=len(f),
                    unknown_price=int(p.isna().sum()),
                    buildable=int(calculated.quantity.gt(0).sum()),
                    known_price_buildable_fraction=float(calculated.quantity.gt(0).sum() / p.notna().sum()),
                    all_names_buildable_fraction=float(calculated.quantity.gt(0).mean())))
                for replicate in range(32):
                    order = hash_order(list(f.index), date, replicate)
                    chosen, replacement = order[:k], order[k:2*k]
                    samples.append(dict(date=date, aum=aum, k=k, replicate=replicate,
                                        names=chosen, replacements=replacement))
                    results.append(dict(date=date, aum=aum, k=k, replicate=replicate,
                        **basket_summary(calculated.loc[chosen], calculated.loc[replacement], date, aum, k)))
        print(f"{date}: static small-capital arithmetic complete", flush=True)
    pd.DataFrame(results).to_csv(OUT / "baskets.csv", index=False)
    pd.DataFrame(pool).to_csv(OUT / "pool_affordability.csv", index=False)
    pd.DataFrame(prices).to_csv(OUT / "price_distribution.csv", index=False)
    dump(OUT / "samples.json", samples)
    df = pd.DataFrame(results)
    summaries = []
    for key, g in df.groupby(["date", "aum", "k"]):
        row = dict(zip(("date", "aum", "k"), key))
        for col in df.columns[4:]:
            for label, quantile in (("p10", .1), ("p50", .5), ("p90", .9)):
                row[f"{col}_{label}"] = float(g[col].quantile(quantile))
        row["all_K_price_buildable_basket_fraction"] = float(g.buildable.eq(key[2]).mean())
        summaries.append(row)
    pd.DataFrame(summaries).to_csv(OUT / "summary.csv", index=False)
    dump(OUT / "receipt.json", dict(inputs=inputs, outputs={p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
        e2_ready_for_e3_freeze=False, actual_execution=False))
    print("Complete; E2 BLOCKED; no prediction or account run.", flush=True)


if __name__ == "__main__":
    main()
