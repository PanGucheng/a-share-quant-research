# ruff: noqa: E402
"""Bounded, offline reclassification of existing E2 incidents. No entry replay."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.reconcile_e2_semantics import SealedInputs, BASE
from qlib_integration.economic_semantic_reconciliation import economic_asset

SEALED = ROOT / "outputs/economic_translation_mvp/e2_semantic_v1"
REPORT = ROOT / "reports/economic_translation_mvp/e2_hard_closure_v1"
OUT = ROOT / "outputs/economic_translation_mvp/e2_mvp_scope_v5"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    def deny(*args, **kwargs):
        raise RuntimeError("scope audit is offline")

    socket.socket.connect = deny
    OUT.mkdir(exist_ok=False)
    binding = json.loads((REPORT / "SEMANTIC_VERIFICATION.json").read_text(encoding="utf-8"))
    assert sha(SEALED / "receipt.json") == binding["production_receipt_sha256"]
    receipt = {
        k.replace("\\", "/"): v
        for k, v in json.loads((SEALED / "receipt.json").read_text()).items()
    }
    access = {}

    def sealed(name):
        p = SEALED / name
        assert sha(p) == receipt[name], name
        access[str(p.relative_to(ROOT))] = sha(p)
        return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)

    def compact(name):
        p = REPORT / name
        h = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert h == binding["compact_evidence_sha256_lf"][name], name
        access[str(p.relative_to(ROOT)) + ":LF"] = h
        return pd.read_csv(p, dtype=str).fillna("")

    tail = sealed("terminal_candidates.csv")
    lifecycle = []
    for row in tail.itertuples():
        daily = sealed(f"daily/{row.instrument}.parquet")
        prior = daily[daily.date < row.first_missing]
        known = prior[prior.observed_status.ne("unresolved")]
        last = known.iloc[-1] if len(known) else None
        lifecycle.append(
            dict(
                incident_id=f"{row.asset_id}:{row.first_missing}",
                asset_id=row.asset_id,
                instrument=row.instrument,
                first_missing=row.first_missing,
                last_observed=last.date if last is not None else None,
                last_observed_status=last.observed_status if last is not None else None,
                special_observation_in_prior_20_sessions=bool(
                    prior.tail(20).execution_special_gap.any()
                ),
                economic_type="unknown",
                confirmed_terminal=False,
                disposition="IF_EXPOSED_RETAIN_AND_RESOLVE_IDENTITY_OR_SETTLEMENT",
                required_without_exposure=False,
            )
        )
    pd.DataFrame(lifecycle).to_csv(OUT / "lifecycle_incidents.csv", index=False)
    inputs = SealedInputs(BASE)
    cases = compact("semantic_quote_adjudications.csv")
    cases = cases[cases.status.eq("BLOCKING / UNRESOLVED")][["instrument", "date"]]
    extra = compact("semantic_other_quote_issues.csv")[["instrument", "date"]]
    cases = pd.concat([cases, extra], ignore_index=True)
    quote_cases = []
    for row in cases.itertuples():
        q = inputs.frame("quotes", row.instrument).loc[row.date]
        s = inputs.frame("states", row.instrument).set_index("date").loc[row.date]
        local, source = float(q.close), float(s.close)
        both = np.isfinite(local) and np.isfinite(source) and local > 0 and source > 0
        close_agrees = both and abs(local - source) <= 0.001
        lone_vendor = not np.isfinite(local) and np.isfinite(source) and source > 0
        action = (
            "NO_VOLUNTARY_TRADE_DATED_CLOSE_AVAILABLE"
            if close_agrees
            else (
                "NO_VOLUNTARY_TRADE_VENDOR_MARK_PROVISIONAL"
                if lone_vendor
                else "HELD_MARK_CONFLICT"
            )
        )
        quote_cases.append(
            dict(
                instrument=row.instrument,
                date=row.date,
                local_close=local,
                vendor_close=source,
                disposition=action,
                holding_mark_blocker=not (close_agrees or lone_vendor),
                entry_use="NOT_A_PIT_ENTRY_BLACKLIST",
            )
        )
    pd.DataFrame(quote_cases).to_csv(OUT / "quote_incidents.csv", index=False)
    unresolved = compact("semantic_potential_held_unresolved_events.csv")

    def family(row):
        if "announcement_record_order" in row.conflicts:
            return "historical_record_snapshot"
        if "div_listdate" in row.missing:
            return "cash_and_listing_terms"
        if row.conflicts:
            return "conflicting_entitlement_terms"
        return "unknown_cash_terms"

    unresolved["handler_family"] = [family(r) for r in unresolved.itertuples()]
    unresolved["required_without_exposure"] = False
    unresolved[
        [
            "instrument",
            "event_id",
            "record_date",
            "ex_date",
            "handler_family",
            "required_without_exposure",
        ]
    ].to_csv(OUT / "conditional_event_cases.csv", index=False)
    fractional = compact("semantic_fractional_bonus_terms.csv")
    starts = {}
    for instrument, start in inputs.scope["starts"].items():
        asset = economic_asset(instrument)
        starts[asset] = min(starts.get(asset, start), start)
    fractional = fractional[
        fractional.apply(
            lambda r: r.record_date >= starts.get(r.asset_id, "9999").replace("-", ""), axis=1
        )
    ]
    fractional["handler_family"] = "exact_fractional_claim_pending_allocation"
    fractional[
        ["asset_id", "event_id", "record_date", "ex_date", "bonus_per_share", "handler_family"]
    ].to_csv(OUT / "fractional_cases.csv", index=False)
    mismatch = compact("semantic_reference_mismatches.csv")
    resets = compact("semantic_reference_resets.csv")
    result = dict(
        e2_status="E2 STILL BLOCKED",
        entry_contract="IMPLEMENTED / SYNTHETIC VERIFIED",
        actual_entry_coverage="NOT_CERTIFIED: sealed daily observations have no preopen known_at",
        actual_held_reachability="NOT_MEASURED; no scores, strategy or holdings replay",
        proven_never_held_case_count=None,
        closed_via_all_no_entry=False,
        lifecycle_coverage_incidents=len(lifecycle),
        confirmed_true_delistings=None,
        confirmed_rights_issues=None,
        confirmed_general_conversions=None,
        known_same_share_identity_migrations=1,
        lifecycle_last_observed_status=dict(Counter(r["last_observed_status"] for r in lifecycle)),
        lifecycle_with_recent_special_observation=sum(
            r["special_observation_in_prior_20_sessions"] for r in lifecycle
        ),
        quote_incidents=len(quote_cases),
        quote_held_mark_conflicts=sum(r["holding_mark_blocker"] for r in quote_cases),
        quote_no_trade_with_cross_source_mark=sum(
            r["disposition"] == "NO_VOLUNTARY_TRADE_DATED_CLOSE_AVAILABLE" for r in quote_cases
        ),
        quote_vendor_provisional_mark=sum(
            r["disposition"] == "NO_VOLUNTARY_TRADE_VENDOR_MARK_PROVISIONAL" for r in quote_cases
        ),
        unresolved_conditional_event_keys=len(unresolved),
        unresolved_handler_families=unresolved.handler_family.value_counts().to_dict(),
        fractional_conditional_event_keys=len(fractional),
        unique_dividend_or_fractional_or_reference_event_keys=len(
            set(unresolved.event_id) | set(fractional.event_id) | set(mismatch.event_id)
        ),
        reference_bridge_diagnostics=len(mismatch),
        unclassified_reference_reset_days=len(resets),
        dedicated_special_simulator_required=False,
        retrospective_global_exclusion=False,
        scope_rule_frozen_for_e3=False,
        collection_run=False,
        outcomes_run=False,
    )
    (OUT / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    access.update({str(BASE.relative_to(ROOT)) + "/" + k: v for k, v in inputs.access.items()})
    (OUT / "inputs.json").write_text(json.dumps(access, indent=2) + "\n", encoding="utf-8")
    files = {p.name: sha(p) for p in OUT.iterdir() if p.is_file()}
    code = [
        "qlib_integration/economic_mvp_scope.py",
        "scripts/audit_e2_mvp_scope.py",
        "tests/test_economic_mvp_scope.py",
    ]
    record = dict(
        files=files,
        code_lf={
            p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p in code
        },
        baseline="bbaae7e",
        source_receipt_sha256=sha(SEALED / "receipt.json"),
    )
    (OUT / "receipt.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
