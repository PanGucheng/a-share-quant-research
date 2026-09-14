"""Bounded additive precision overlay for nine sealed quote disagreements."""

from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def precision_only(left, right):
    """Explicit <= CNY 1 turnover budget, never a price/share discrepancy waiver."""
    fields = ["open", "high", "low", "close", "volume", "amount"]
    a = np.asarray([left[k] for k in fields], dtype=float)
    b = np.asarray([right[k] for k in fields], dtype=float)
    if not np.isfinite(a).all() or not np.isfinite(b).all() or (a <= 0).any() or (b <= 0).any():
        return False
    return bool((np.abs(a[:5] - b[:5]) <= 0.001).all() and abs(a[5] - b[5]) <= 1.0)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    base = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"
    semantic = ROOT / "outputs/economic_translation_mvp/e2_semantic_v1"
    production = json.loads((semantic / "receipt.json").read_text())
    assert sha(semantic / "input_hashes.json") == production["input_hashes.json"]
    bound = json.loads((semantic / "input_hashes.json").read_text())
    refs = json.loads((base / "recovery_states_v1/complete.json").read_text())["references"]
    independent = json.loads((semantic / "independent_verification/receipt.json").read_text())
    issues_path = semantic / "independent_verification/quote_state_issues.parquet"
    assert sha(issues_path) == independent["quote_state_issues.parquet"]
    issues = pd.read_parquet(issues_path)
    rows, patches = [], []
    for case in issues[issues.quote_status.eq("source_conflict")].itertuples():
        assert "2015-01-05" <= case.date <= "2023-12-29"
        receipt_path = base / refs[case.instrument]["path"]
        assert sha(receipt_path) == bound[str(receipt_path.relative_to(base))]
        receipt = json.loads(receipt_path.read_text())
        source_path = receipt_path.parent / next(
            k for k in receipt["files"] if k.endswith(".parquet")
        )
        quote_path = base / f"full_quotes/{case.instrument}.parquet"
        for path in [source_path, quote_path]:
            assert sha(path) == bound[str(path.relative_to(base))]
        left = pd.read_parquet(quote_path).loc[case.date]
        right = pd.read_parquet(source_path).set_index("date").loc[case.date]
        accept = precision_only(left, right)
        rows.append(
            dict(
                instrument=case.instrument,
                date=case.date,
                amount_local=float(left.amount),
                amount_source=float(right.amount),
                precision_approximation=accept,
                status="ACCEPTABLE MVP APPROXIMATION" if accept else "BLOCKING / UNRESOLVED",
            )
        )
        if accept:
            daily_path = semantic / f"daily/{case.instrument}.parquet"
            production = json.loads((semantic / "receipt.json").read_text())
            assert sha(daily_path) == production[str(daily_path.relative_to(semantic))]
            f = pd.read_parquet(daily_path)
            row = f.loc[f.date.eq(case.date)].iloc[0].copy()
            for col in ["open", "high", "low", "close", "volume", "amount"]:
                row["raw_" + col] = (
                    min(float(left[col]), float(right[col]))
                    if col == "amount"
                    else float(right[col])
                )
            row["quote_status"] = "amount_precision_mvp"
            row["valuation_mark"] = float(right.close)
            row["valuation_basis"] = "raw_close_amount_precision_mvp"
            row["account_gap"] = bool(
                row.event_unresolved
                or row.unexplained_reference_reset
                or row.observed_status == "unresolved"
            )
            row["precision_budget_cny"] = 1.0
            patches.append(row)
    assert len(rows) == 9
    out = semantic / "precision_adjudication"
    out.mkdir(exist_ok=False)
    pd.DataFrame(rows).to_csv(out / "quote_adjudications.csv", index=False)
    pd.DataFrame(patches).to_parquet(out / "daily_patches.parquet", index=False)
    result = dict(
        base_receipt_sha256=sha(semantic / "receipt.json"),
        policy="explicit CNY1 amount-only approximation; use lower amount; preopen permission unchanged",
        cases=len(rows),
        accepted=len(patches),
        unresolved=len(rows) - len(patches),
        code_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        files={p.name: sha(p) for p in out.iterdir() if p.is_file()},
    )
    (out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
