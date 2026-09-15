# ruff: noqa: E402
"""One fixed offline engineering transaction; no strategy or outcome output."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import qlib
from qlib.data import D
from qlib.backtest.account import Account
from qlib_integration.economic_core_inputs import adapt_phase, market_phase_records
from qlib_integration.economic_core_session import CoreSession, Intent
from qlib_integration.economic_event_position import attach_event_position
from qlib_integration.economic_historical_inputs import session_state_records, known_event_records
from qlib_integration.economic_mvp_scope import entry_eligibility

REPORT = ROOT / "reports/economic_translation_mvp/e2_hard_closure_v1"
PRIOR = ROOT / "outputs/economic_translation_mvp/e2_core_acceptance_v4"
OUT = ROOT / "outputs/economic_translation_mvp/e2_historical_core_v2"
CODE = ["qlib_integration/" + name + ".py" for name in (
    "economic_core_inputs", "economic_core_session", "economic_historical_inputs",
    "economic_mvp_scope", "execution_readiness", "economic_exchange")]
CODE += ["scripts/accept_e2_historical_core.py", "scripts/verify_e2_historical_core.py",
         "tests/test_economic_historical_core.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(name, value):
    with (OUT / name).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def main():
    def deny(*args, **kwargs):
        raise RuntimeError("fixed offline canary forbids network/provider values")
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    OUT.mkdir(exist_ok=False)
    access = {}
    try:
        scope = json.loads((REPORT / "HISTORICAL_CORE_SCOPE.json").read_text(encoding="utf-8"))
        assert sha(REPORT / "CORE_CANARY_SCOPE.json") == scope["original_scope_sha256"]
        assert (scope["instrument"], scope["session"], scope["history_start"], scope["history_end"]) == (
            "SH600000", "2020-08-24", "2020-07-27", "2020-08-21")
        for p in (REPORT / "HISTORICAL_CORE_SCOPE.json", REPORT / "CORE_CANARY_SCOPE.json", PRIOR / "inputs.json"):
            access[str(p.relative_to(ROOT))] = sha(p)
        old = json.loads((PRIOR / "inputs.json").read_text(encoding="utf-8"))
        for name, expected in old.items():
            assert sha(ROOT / name) == expected
            access[name] = expected

        def path(ending):
            return next(ROOT / n for n in old if n.replace("\\", "/").endswith(ending))

        stock, day = scope["instrument"], scope["session"]
        window = [("date", ">=", scope["history_start"]), ("date", "<=", day)]
        daily = pd.read_parquet(path("daily/SH600000.parquet"), filters=window,
            columns=["date", "instrument", "asset_id", "execution_code_reference", "board",
                     "quote_status", "raw_volume", "valuation_mark"])
        states = pd.read_parquet(path("full_states/SH600000.parquet"), filters=window,
            columns=["date", "code", "tradestatus", "isST", "preclose", "open", "volume"])
        limits = pd.read_parquet(path("network/ts_1.parquet"), filters=[("trade_date", "==", "20200824")],
            columns=["ts_code", "trade_date", "pre_close", "up_limit", "down_limit"])
        # Only session schedule/announcement/status metadata, never future outcome terms.
        events = pd.read_parquet(path("e2_semantic_v1/events.parquet"), columns=[
            "asset_id", "event_id", "record_date", "ex_date", "implementation_known_date"],
            filters=[[("asset_id", "==", stock), ("record_date", "==", "20200824")],
                     [("asset_id", "==", stock), ("ex_date", "==", "20200824")]])
        events = events[events.implementation_known_date.isna() | events.implementation_known_date.le("20200824")]
        dates = daily.date.tolist()
        assert dates == states.date.tolist() and len(dates) == 21 and dates[-1] == day
        today = states[states.date.eq(day)].iloc[0]
        identity = daily[daily.date.eq(day)].iloc[0].to_dict()
        packet = market_phase_records(daily, instrument=stock, date=day, calendar=dates,
            sha256=sha(path("daily/SH600000.parquet")), opening_reference=dict(
                instrument=stock, date=day, raw_open=float(today.open),
                source="fixed sealed BaoStock raw open", sha256=sha(path("full_states/SH600000.parquet"))))
        state_packet = session_state_records(instrument=stock, date=day, states=states, limits=limits,
            identity=identity, state_hash=sha(path("full_states/SH600000.parquet")),
            limit_hash=sha(path("network/ts_1.parquet")), identity_hash=sha(path("daily/SH600000.parquet")))
        # Scope: a flat-start one-day canary. Pending legacy rights are not asserted absent.
        # Any active distribution lacks handler reconciliation here and therefore denies.
        review = dict(instrument=stock, session=day, source="bounded known session-risk review",
            sha256=sha(path("e2_semantic_v1/events.parquet")), event_ids=events.event_id.tolist(),
            status="unresolved" if len(events) else "no_known_blocking",
            reviewed_sources=[dict(path=str(path(s).relative_to(ROOT)), sha256=sha(path(s))) for s in (
                "e2_semantic_v1/events.parquet", "full_states/SH600000.parquet",
                "daily/SH600000.parquet", "network/ts_1.parquet")])
        event_packet = known_event_records(instrument=stock, date=day, review=review)
        for ph in ("A", "C"):
            packet[ph] += state_packet[ph] + event_packet[ph]
        calls, phases = [], {}

        def load(ph):
            calls.append(ph)
            phases[ph] = adapt_phase(packet[ph], date=day,
                at=day + " " + {"A": "09:00", "B": "09:30", "C": "16:00"}[ph], phase=ph, mode="historical")
            return phases[ph]

        with tempfile.TemporaryDirectory(prefix="e2_fixed_provider_") as tmp:
            provider = Path(tmp)
            (provider / "calendars").mkdir()
            (provider / "calendars/day.txt").write_text("\n".join(dates), encoding="utf-8")
            qlib.init(provider_uri=tmp, expression_cache=None, dataset_cache=None)
            D.features = deny
            account = Account(init_cash=10000, benchmark_config={"benchmark": None}, port_metr_enabled=False)
            attach_event_position(account)
            session = CoreSession(account, dates, mode="historical")
            result = session.run_day(day, [stock], [Intent(stock, 100, "buy")], load)
            a = phases["A"]
            entry = entry_eligibility(stock, a.at, a.facts[stock], a.states[stock], historical=True)
            assert entry.action == "ALLOW_ENTRY" and result["fills"] == 1 and result["status"] == "COMMITTED"
            p = account.current_position
            assert p.get_stock_amount(stock) == 100
            assert abs(p.get_stock_price(stock) - identity["valuation_mark"]) < 1e-10
            assert account.hist_positions == {} and not account.is_port_metr_enabled()
            # Independent scalar fee/budget check, no return calculation or saved account value.
            gross = float(today.open) * 100
            expected_cash = 10000 - gross - max(5, gross * 0.0003) - round(gross * 0.00002, 2)
            assert abs(p.get_cash() - expected_cash) < 1e-8
        assert calls == ["A", "B", "C"]
        assert all(r.fact.known_at is None for rs in packet.values() for r in rs)
        put("scope.json", scope)
        put("evidence.json", {ph: [asdict(r) for r in rs] for ph, rs in packet.items()})
        put("session.json", dict(result, entry_action=entry.action, phase_order=calls,
                                 quantity=100, cash_arithmetic_checked=True, close_mark_checked=True))
        put("summary.json", dict(status="PASS", c1="CLOSED / HISTORICAL APPROXIMATION ACCEPTED",
            source_rows=21, session_event_rows=len(events), event_coverage_complete=False,
            source_known_at_remains_null=True, exact_preopen_pit_certified=False,
            approximations=[x for ph in phases.values() for x in ph.approximations],
            no_strategy_path_or_outcomes=True, code_sha256_lf={n: hashlib.sha256(
                (ROOT / n).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for n in CODE}))
        put("inputs.json", access)
        put("receipt.json", {p.name: sha(p) for p in OUT.iterdir() if p.is_file()})
        print("Historical fixed canary: ALLOW_ENTRY -> one fill -> COMMITTED; no outcome output")
    except Exception as exc:
        put("failure.json", dict(error=type(exc).__name__, reason=str(exc), inputs=access))
        raise


if __name__ == "__main__":
    main()
