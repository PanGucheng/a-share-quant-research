"""Independent receipt and scalar-source checks; does not import production adapters."""

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/economic_translation_mvp/e2_core_acceptance_v4"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((OUT / "receipt.json").read_text(encoding="utf-8"))
    for name, expected in receipt.items():
        assert Path(name).name == name and digest(OUT / name) == expected
    inputs = json.loads((OUT / "inputs.json").read_text(encoding="utf-8"))
    for name, expected in inputs.items():
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT) and digest(path) == expected
    scope = json.loads((OUT / "scope.json").read_text(encoding="utf-8"))
    assert (scope["instrument"], scope["order_date"], scope["history_start"], scope["history_end"]) == (
        "SH600000", "2020-08-24", "2020-07-27", "2020-08-21"
    )
    summary = json.loads((OUT / "source_summary.json").read_text(encoding="utf-8"))
    for name, expected in summary["code_sha256_lf"].items():
        assert hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected
    records = json.loads((OUT / "market_records.json").read_text(encoding="utf-8"))
    a = {r["name"]: r for r in records["A"]}
    b = {r["name"]: r for r in records["B"]}
    assert not {"asset_id", "state", "events_clear"} & set(a)
    assert a["adv20_shares"]["fact"]["known_at"] is None
    assert a["adv20_shares"]["phase_basis"] == "prior_session_eod"
    state_path = next(ROOT / name for name in inputs if "full_states" in name and name.endswith("SH600000.parquet"))
    state = pd.read_parquet(state_path, columns=["date", "volume", "open"], filters=[
        ("date", ">=", "2020-07-27"), ("date", "<=", "2020-08-24")])
    old = state[state.date < "2020-08-24"]
    assert len(old) == 20 and len(state) == 21
    scalar_adv = sum(float(v) for v in old.volume) / 20
    assert scalar_adv == a["adv20_shares"]["fact"]["value"] == summary["adapter_adv20"]
    assert float(state[state.date == "2020-08-24"].iloc[0].open) == b["raw_open"]["fact"]["value"]
    assert summary["entry_action"] == "NO_NEW_ENTRY" and summary["c1_acceptance"].startswith("NOT ACCEPTED")
    result = dict(status="PASS", c1_acceptance="NOT ACCEPTED", input_hashes=len(inputs),
                  output_hashes=len(receipt), independent_adv20=scalar_adv,
                  no_production_adapter_import=True, real_account_or_outcome=False,
                  source_receipt_sha256=digest(OUT / "receipt.json"),
                  verifier_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest())
    with (OUT / "independent_verification.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
