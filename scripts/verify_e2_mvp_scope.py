"""Independent arithmetic and evidence verification of scope incident inventory."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/economic_translation_mvp/e2_mvp_scope_v5"


def sha(path, lf=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n") if lf else data).hexdigest()


def verify():
    receipt = json.loads((OUT / "receipt.json").read_text())
    for name, digest in receipt["files"].items():
        assert Path(name).name == name and sha(OUT / name) == digest
    for name, digest in receipt["code_lf"].items():
        assert sha(ROOT / name, lf=True) == digest
    access = json.loads((OUT / "inputs.json").read_text())
    for name, digest in access.items():
        lf = name.endswith(":LF")
        path = (ROOT / (name[:-3] if lf else name)).resolve()
        assert path.is_relative_to(ROOT.resolve()) and sha(path, lf=lf) == digest
    summary = json.loads((OUT / "summary.json").read_text())
    lifecycle = pd.read_csv(OUT / "lifecycle_incidents.csv")
    assert len(lifecycle) == lifecycle.incident_id.nunique() == lifecycle.asset_id.nunique() == 148
    assert lifecycle.economic_type.eq("unknown").all() and not lifecycle.confirmed_terminal.any()
    assert (lifecycle.last_observed < lifecycle.first_missing).all()
    quote = pd.read_csv(OUT / "quote_incidents.csv")
    agrees = (quote.local_close - quote.vendor_close).abs().le(0.001)
    vendor_only = quote.local_close.isna() & quote.vendor_close.gt(0)
    assert np.array_equal(quote.holding_mark_blocker, ~(agrees | vendor_only))
    assert int(quote.holding_mark_blocker.sum()) == summary["quote_held_mark_conflicts"] == 3
    expected_unresolved = pd.read_csv(
        ROOT
        / "reports/economic_translation_mvp/e2_hard_closure_v1/semantic_potential_held_unresolved_events.csv"
    )
    actual = pd.read_csv(OUT / "conditional_event_cases.csv")
    assert set(actual.event_id) == set(expected_unresolved.event_id) and len(actual) == 528
    assert not actual.required_without_exposure.any()
    assert actual.handler_family.value_counts().to_dict() == summary["unresolved_handler_families"]
    result = dict(
        status="PASS",
        source_audit_receipt_sha256=sha(OUT / "receipt.json"),
        verified_input_files=len(access),
        verified_output_files=len(receipt["files"]),
        lifecycle_incidents=148,
        held_mark_conflicts=3,
        conditional_event_keys=528,
        never_held_inference=False,
        real_execution_or_outcome_replay=False,
        verifier_code_lf=sha(Path(__file__), lf=True),
    )
    with (OUT / "independent_verification.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    verify()
