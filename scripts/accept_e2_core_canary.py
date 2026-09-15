# ruff: noqa: E402
"""Fixed, offline C1 acceptance attempt; never executes a real account or strategy."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from qlib_integration.economic_core_inputs import adapt_phase, market_phase_records
from qlib_integration.economic_mvp_scope import entry_eligibility

REPORT = ROOT / "reports/economic_translation_mvp/e2_hard_closure_v1"
BASE = ROOT / "outputs/economic_translation_mvp/e2_hard_closure_v1"
SEMANTIC = ROOT / "outputs/economic_translation_mvp/e2_semantic_v1"
OUT = ROOT / "outputs/economic_translation_mvp/e2_core_acceptance_v4"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, data):
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def main():
    def deny(*args, **kwargs):
        raise RuntimeError("C1 canary is offline")
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    OUT.mkdir(exist_ok=False)
    scope_path = REPORT / "CORE_CANARY_SCOPE.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    put(OUT / "scope.json", scope)
    access = {str(scope_path.relative_to(ROOT)): sha(scope_path)}

    def read_json(path, expected=None):
        digest = sha(path)
        if expected is not None and digest != expected:
            raise ValueError("source receipt hash changed")
        access[str(path.relative_to(ROOT))] = digest
        return json.loads(path.read_text(encoding="utf-8"))

    def read_frame(path, digest, columns, filters):
        if sha(path) != digest:
            raise ValueError("sealed data hash changed")
        access[str(path.relative_to(ROOT))] = digest
        return pd.read_parquet(path, columns=columns, filters=filters)

    stock, day = scope["instrument"], scope["order_date"]
    try:
        calendar = read_json(BASE / "full_quotes/scope.json")["days"]
        prior = [d for d in calendar if d < day][-20:]
        assert prior[0] == scope["history_start"] and prior[-1] == scope["history_end"]
        accepted = read_json(REPORT / "SCOPE_VERIFICATION.json")
        receipt = read_json(SEMANTIC / "receipt.json", accepted["audit_receipt"]["source_receipt_sha256"])
        receipt = {k.replace("\\", "/"): v for k, v in receipt.items()}
        daily = read_frame(SEMANTIC / f"daily/{stock}.parquet", receipt[f"daily/{stock}.parquet"],
            ["date", "instrument", "quote_status", "raw_volume", "valuation_mark", "known_at",
             "ordinary_regime_certified", "state_available_phase"],
            [("date", ">=", prior[0]), ("date", "<=", day)])
        assert daily.date.tolist() == prior + [day] and daily.instrument.eq(stock).all()
        completed = read_json(REPORT / "STATES_COMPLETION.json")
        recovery = read_json(BASE / "recovery_states_v1/complete.json", completed["complete_sha256"])
        ref = recovery["references"][stock]
        state_receipt_path = BASE / ref["path"]
        state_receipt = read_json(state_receipt_path, ref["sha256"])
        state_name = next(n for n in state_receipt["files"] if n.endswith(".parquet"))
        state_hash = state_receipt["files"][state_name]
        state = read_frame(state_receipt_path.parent / state_name, state_hash,
            ["date", "code", "open", "volume", "preclose", "tradestatus", "isST"],
            [("date", ">=", prior[0]), ("date", "<=", day)])
        assert state.date.tolist() == prior + [day] and state.code.eq("sh.600000").all()
        q_receipt = read_json(BASE / f"full_quotes/{stock}.json")
        raw = read_frame(BASE / f"full_quotes/{stock}.parquet", q_receipt["files"][stock + ".parquet"],
            ["instrument", "open", "high", "low", "close", "volume", "amount", "factor"],
            [("date", ">=", prior[0]), ("date", "<=", day)])
        assert list(raw.index) == prior + [day]
        probes = read_json(ROOT / "reports/economic_translation_mvp/e2_readiness_v2/provider_probe_receipts.json")
        limit_meta = next(r for r in probes if r.get("api") == "stk_limit" and r["parameters"]["trade_date"] == "20200824")
        limit = read_frame(ROOT / "outputs/economic_translation_mvp/e2_closure_v1/network/ts_1.parquet",
            limit_meta["sha256"], ["ts_code", "trade_date", "pre_close", "up_limit", "down_limit"],
            [("trade_date", "==", "20200824")])
        assert len(limit) == 1 and limit.iloc[0].ts_code == "600000.SH"
        events = read_frame(SEMANTIC / "events.parquet", receipt["events.parquet"],
            ["asset_id", "event_id", "record_date", "ex_date", "implementation_known_date", "status"],
            [("asset_id", "==", stock), ("record_date", "<=", day.replace("-", "")),
             ("ex_date", ">=", prior[0].replace("-", "")), ("ex_date", "<=", day.replace("-", ""))])
        today = state[state.date.eq(day)].iloc[0]
        phase_records = market_phase_records(daily, instrument=stock, date=day, calendar=calendar,
            sha256=receipt[f"daily/{stock}.parquet"], opening_reference=dict(instrument=stock, date=day,
                raw_open=float(today.open), source="fixed BaoStock unadjusted open field", sha256=state_hash))
        phases = {ph: adapt_phase(rows, date=day, at=day + " " + {"A":"09:00", "B":"09:30", "C":"16:00"}[ph], phase=ph)
                  for ph, rows in phase_records.items()}
        decision = entry_eligibility(stock, phases["A"].at, phases["A"].facts.get(stock, {}), phases["A"].states.get(stock))
        # Independent arithmetic from separately sealed raw source, not the adapter.
        source_adv = sum(float(x) for x in state[state.date.isin(prior)].volume) / 20
        adapted_adv = phases["A"].facts[stock]["adv20_shares"][0].value
        assert abs(source_adv - adapted_adv) <= max(0.001, abs(source_adv) * 2e-5)
        raw_open = float(today.open)
        assert phases["B"].values[stock]["raw_open"] == raw_open
        assert abs(float(raw.loc[day, "open"]) - raw_open) < 0.001
        assert float(limit.iloc[0].down_limit) < raw_open < float(limit.iloc[0].up_limit)
        assert daily.known_at.isna().all() and not daily.ordinary_regime_certified.any()
        result = dict(
            scope_sha256=sha(scope_path), source_rows=len(daily), prior_sessions=20,
            c1_implementation="MARKET ADAPTER VERIFIED; explicit certificates required for identity/state/events",
            c1_acceptance="NOT ACCEPTED: no nonempty certified ordinary PIT path",
            entry_action=decision.action, reasons=list(decision.reasons),
            ordinary_state_certificate_present=False, complete_event_coverage_certificate_present=False,
            identity_availability_certificate_present=False,
            independent_adv20=source_adv, adapter_adv20=adapted_adv,
            positive_open_and_independent_limits=True,
            source_observed_event_rows=len(events),
            empty_event_slice_proves_absence=False,
            approximations=[x for p in phases.values() for x in p.approximations],
            no_new_collection=True, no_real_account=True, no_scores_outcomes_or_2024plus=True,
            code_sha256_lf={name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                for name in ["scripts/accept_e2_core_canary.py", "qlib_integration/economic_core_inputs.py",
                             "qlib_integration/economic_core_session.py", "tests/test_economic_core.py"]},
        )
        assert decision.action == "NO_NEW_ENTRY"
        put(OUT / "source_summary.json", result)
        put(OUT / "market_records.json", {ph: [asdict(x) for x in rows] for ph, rows in phase_records.items()})
        put(OUT / "inputs.json", access)
        put(OUT / "receipt.json", {p.name: sha(p) for p in OUT.iterdir() if p.is_file()})
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        put(OUT / "failure.json", dict(error=type(exc).__name__, reason=str(exc), inputs=access))
        raise


if __name__ == "__main__":
    main()
