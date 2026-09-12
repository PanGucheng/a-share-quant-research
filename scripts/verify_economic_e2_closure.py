"""Read-only seal and independent static-lot verification; no provider or NAV."""

from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/economic_translation_mvp/e2_closure_v1"


def verify():
    local = BASE / "local"
    receipt = json.loads((local / "receipt.json").read_text(encoding="utf-8"))
    for name, digest in receipt.items():
        assert Path(name).name == name
        assert hashlib.sha256((local / name).read_bytes()).hexdigest() == digest
    scope = json.loads((local / "scope.json").read_text(encoding="utf-8"))
    for audit in [local / "access.json", BASE / "analysis/access.json"]:
        for row in json.loads(audit.read_text(encoding="utf-8")):
            assert row["completed"] and not row["whole_parent_hash"]
            assert row["field"] in scope["fields"]
            assert all("2015-01-01" <= d <= "2023-12-29" for d in row["dates"])
            if audit.parent == local:
                assert set(row["dates"]) <= set(scope["request_dates_by_stock"][row["instrument"]])
    data = pd.read_parquet(local / "bounded_raw_units.parquet")
    assert data.date.between("2015-01-01", "2023-12-29").all()
    result = pd.read_csv(BASE / "analysis/static_ew_feasibility.csv")
    cases = 0
    for spec in scope["groups"]:
        if spec["kind"] != "full_pool":
            continue
        date, previous, names = spec["date"], spec["dates"][-2], spec["names"]
        price = (
            data[data.date.eq(previous) & data.instrument.isin(names)].set_index("instrument").close
        )
        for cash in (1_000_000, 5_000_000, 10_000_000):
            budget = 0.95 * cash / len(names)
            rate = 0.00001 if date >= "2022-04-29" else 0.00002
            missing = zero = 0
            fees, costs = [], []
            for stock in names:
                p = price.get(stock, np.nan)
                if not np.isfinite(p) or p <= 0:
                    missing += 1
                    continue
                unit = 1 if stock.startswith("SH688") else 100
                minimum = 200 if unit == 1 else 100
                feasible = []
                # Exhaustive scalar enumeration; no production lot/cost helpers.
                for q in range(minimum, int(budget / p) + 1, unit):
                    transfer = float(
                        Decimal(str(q * p * rate)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
                    )
                    fee = (
                        5 + transfer
                    )  # all fixed budgets < 5000: minimum dominates .0003 commission
                    if q * p + fee <= budget:
                        feasible.append((q, fee))
                q, fee = feasible[-1] if feasible else (0, 0)
                zero += int(q == 0)
                fees.append(fee)
                costs.append(q * p + fee)
            row = result[result.date.eq(date) & result.aum_cny.eq(cash)].iloc[0]
            assert row.unknown_price == missing and row.below_lot == zero
            assert abs(row.reference_fee_cny - sum(fees)) < 1e-6
            assert abs(row.reference_unallocated_fraction - (1 - sum(costs) / cash)) < 1e-10
            cases += 1
    assert cases == 9
    return dict(
        sealed_files=len(receipt),
        independent_static_cases=cases,
        status="verified",
        provider_read=False,
        outcome_evaluation=False,
    )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
