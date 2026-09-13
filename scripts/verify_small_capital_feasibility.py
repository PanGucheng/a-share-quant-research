"""Independent scalar/binary-search oracle over sealed static evidence only.

Does not import the study or production lot/fee helpers; no provider or account.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/economic_translation_mvp/small_capital_v1"
BASE = ROOT / "outputs/economic_translation_mvp/e2_closure_v1/local"


def fee(value, date, sell=False):
    def cent(x):
        return float(Decimal(str(x)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP))
    return (cent(max(5, value * .00025)) + cent(value * (.00001 if date >= "2022-04-29" else .00002))
            + (cent(value * (.0005 if date >= "2023-08-28" else .001)) if sell else 0)) if value > 0 else 0.0


def oracle(price, cash, star, date):
    if not math.isfinite(price) or price <= 0:
        return None, 0.0, 0.0
    minimum, step = (200, 1) if star else (100, 100)
    if minimum * price + fee(minimum * price, date) > cash:
        return 0, 0.0, 0.0
    lo, hi = 0, max(0, (int(cash / price) - minimum) // step)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        q = minimum + step * mid
        if q * price + fee(q * price, date) <= cash:
            lo = mid
        else:
            hi = mid - 1
    q = minimum + step * lo
    return q, q * price, fee(q * price, date)


def verify():
    receipt = json.loads((OUT / "receipt.json").read_text(encoding="utf-8"))
    for folder, items in ((BASE, receipt["inputs"]), (OUT, receipt["outputs"])):
        for name, digest in items.items():
            assert Path(name).name == name
            assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
    scope = json.loads((BASE / "scope.json").read_text(encoding="utf-8"))
    for dates in scope["request_dates_by_stock"].values():
        assert all("2015-01-01" <= d <= "2023-12-29" for d in dates)
    data = pd.read_parquet(BASE / "bounded_raw_units.parquet", columns=["date", "instrument", "close"])
    assert data.date.between("2015-01-01", "2023-12-29").all()
    baskets = pd.read_csv(OUT / "baskets.csv").set_index(["date", "aum", "k", "replicate"])
    pools = pd.read_csv(OUT / "pool_affordability.csv").set_index(["date", "aum", "k"])
    samples = json.loads((OUT / "samples.json").read_text(encoding="utf-8"))
    samples = {(s["date"], s["aum"], s["k"], s["replicate"]): s for s in samples}
    count = 0
    for spec in scope["groups"]:
        if spec["kind"] != "full_pool":
            continue
        date = spec["date"]
        price = data[data.date.eq(spec["dates"][-2])].set_index("instrument").close.reindex(spec["names"])
        for aum in (50000, 100000):
            for k in (3, 5, 8, 12, 16, 24, 32, 50, 100, 200):
                budget = .95 * aum / k
                rows = {s: oracle(p, budget, s.startswith("SH688"), date) for s, p in price.items()}
                pr = pools.loc[(date, aum, k)]
                assert pr.unknown_price == sum(r[0] is None for r in rows.values())
                assert pr.buildable == sum(r[0] is not None and r[0] > 0 for r in rows.values())
                for replicate in range(32):
                    order = sorted(spec["names"], key=lambda s: (hashlib.sha256(f"small-capital-v1|{date}|{replicate}|{s}".encode()).digest(), s))
                    ids, newids = order[:k], order[k:2*k]
                    key = date, aum, k, replicate
                    assert samples[key]["names"] == ids and samples[key]["replacements"] == newids
                    r = baskets.loc[key]
                    positions = [rows[s] for s in ids]
                    value = sum(p[1] for p in positions)
                    fees = sum(p[2] for p in positions)
                    assert r.unknown_price == sum(p[0] is None for p in positions)
                    assert r.below_lot == sum(p[0] == 0 for p in positions)
                    assert r.buildable == sum(p[0] is not None and p[0] > 0 for p in positions)
                    expected = {
                        "reference_invested_fraction": value / aum,
                        "reference_cash_fraction": 1 - (value + fees) / aum,
                        "buy_fee_bps": fees / aum * 10000,
                        "effective_names": value ** 2 / sum(p[1] ** 2 for p in positions) if value else 0,
                    }
                    replacement_unknown = newly_zero = total_zero = 0
                    turn_fee = 0.0
                    for old, new in zip(ids, newids):
                        if rows[old][0] is None or rows[new][0] is None:
                            replacement_unknown += 1
                            continue
                        sold_fee = fee(rows[old][1], date, True)
                        q, _, bought_fee = oracle(price[new], budget - rows[old][2] - sold_fee, new.startswith("SH688"), date)
                        total_zero += int(q == 0)
                        newly_zero += int(rows[new][0] > 0 and q == 0)
                        turn_fee += sold_fee + bought_fee
                    assert r.replacement_unknown == replacement_unknown
                    assert r.replacement_below_lot == total_zero
                    assert r.replacement_newly_below_lot_due_to_fees == newly_zero
                    expected["replacement_sell_buy_fee_bps"] = turn_fee / aum * 10000
                    for col, v in expected.items():
                        assert np.isclose(r[col], v, atol=1e-9, rtol=1e-11), (key, col, r[col], v)
                    count += 1
    assert count == 1920 and len(baskets) == count
    return dict(independent_baskets=count, pool_cases=60, seal_verified=True,
                method="independent binary search over legal quantities and Decimal fee oracle",
                outcomes=False, e2_ready_for_e3_freeze=False)


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
