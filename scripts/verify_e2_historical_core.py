"""Independent source/phase/scalar validation; no production adapter imports."""

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/economic_translation_mvp/e2_historical_core_v2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main():
    receipt, inputs = read("receipt.json"), read("inputs.json")
    for name, digest in receipt.items():
        assert Path(name).name == name and sha(OUT / name) == digest
    for name, digest in inputs.items():
        assert (ROOT / name).resolve().is_relative_to(ROOT) and sha(ROOT / name) == digest
    scope, summary, session = read("scope.json"), read("summary.json"), read("session.json")
    assert (scope["instrument"], scope["session"], scope["history_start"], scope["history_end"]) == (
        "SH600000", "2020-08-24", "2020-07-27", "2020-08-21")
    for name, digest in summary["code_sha256_lf"].items():
        assert hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest
    packet = read("evidence.json")
    a, b, c = [{r["name"]: r for r in packet[ph]} for ph in ("A", "B", "C")]
    assert not {"raw_open", "close_mark"} & set(a) and "close_mark" not in b
    for ph, records in packet.items():
        for r in records:
            assert r["phase"] == ph and r["instrument"] == "SH600000" and r["fact"]["known_at"] is None
            assert r["fact"]["source"] and r["sha256"] in inputs.values()
    assert a["state"]["phase_basis"] == "historical_session_effective"
    assert b["raw_open"]["phase_basis"] == "daily_open_reference"
    assert c["close_mark"]["phase_basis"] == "daily_close_observation"
    assert a["events_clear"]["coverage"]["coverage_complete"] is False
    assert a["events_clear"]["coverage"]["status"] == "no_known_blocking"
    assert len(a["events_clear"]["coverage"]["reviewed_sources"]) == 4

    def path(suffix):
        return next(ROOT / n for n in inputs if n.replace("\\", "/").endswith(suffix))

    window = [("date", ">=", "2020-07-27"), ("date", "<=", "2020-08-24")]
    states = pd.read_parquet(path("full_states/SH600000.parquet"), filters=window,
        columns=["date", "code", "open", "volume", "tradestatus", "isST", "preclose"])
    assert len(states) == 21 and states.code.eq("sh.600000").all()
    prior, row = states[states.date.lt("2020-08-24")], states[states.date.eq("2020-08-24")].iloc[0]
    assert len(prior) == 20
    assert sum(float(v) for v in prior.volume) / 20 == a["adv20_shares"]["fact"]["value"]
    assert float(row.open) == b["raw_open"]["fact"]["value"]
    assert float(row.tradestatus) == 1 and float(row.isST) == 0
    state = a["state"]["fact"]["value"]
    assert state["prior_session_count"] == sum(float(v) == 1 for v in prior.tradestatus)
    assert not state["st"] and not state["suspended"] and state["board"] == "main"
    assert "ipo_session" not in state
    limits = pd.read_parquet(path("network/ts_1.parquet"), filters=[("trade_date", "==", "20200824")])
    limit = limits.iloc[0]
    assert len(limits) == 1 and limit.ts_code == "600000.SH"
    assert float(limit.pre_close) == float(row.preclose) == state["limit_reference"]
    assert float(limit.up_limit) == state["upper_limit"] and float(limit.down_limit) == state["lower_limit"]
    assert state["lower_limit"] < float(row.open) < state["upper_limit"]
    daily = pd.read_parquet(path("daily/SH600000.parquet"), filters=window,
        columns=["date", "instrument", "asset_id", "execution_code_reference", "board", "quote_status", "valuation_mark"])
    today = daily[daily.date.eq("2020-08-24")].iloc[0]
    assert today.instrument == today.asset_id == today.execution_code_reference == a["asset_id"]["fact"]["value"]
    assert today.board == state["board"]
    assert today.valuation_mark == c["close_mark"]["fact"]["value"] > 0
    assert daily[daily.date.eq("2020-08-21")].iloc[0].quote_status == "cross_source_agreed"
    events = pd.read_parquet(path("e2_semantic_v1/events.parquet"),
        columns=["asset_id", "event_id", "implementation_known_date"], filters=[
            [("asset_id", "==", "SH600000"), ("record_date", "==", "20200824")],
            [("asset_id", "==", "SH600000"), ("ex_date", "==", "20200824")]])
    eligible = events[events.implementation_known_date.isna() | events.implementation_known_date.le("20200824")]
    assert len(eligible) == summary["session_event_rows"] == 0
    assert session["status"] == "COMMITTED" and session["fills"] == 1 and session["quantity"] == 100
    assert session["phase_order"] == ["A", "B", "C"] and session["entry_action"] == "ALLOW_ENTRY"
    assert session["cash_arithmetic_checked"] and session["close_mark_checked"] and not session["metrics_enabled"]
    result = dict(status="PASS", input_hashes=len(inputs), output_hashes=len(receipt),
        independent_source_and_scalar_checks=True, no_production_import=True,
        no_exact_pit_or_complete_event_claim=True, source_receipt_sha256=sha(OUT / "receipt.json"))
    with (OUT / "independent_verification.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
