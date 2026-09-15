from copy import deepcopy
from dataclasses import replace

import pandas as pd
import pytest

from test_economic_core import S, SHA, CAL, account, records
from test_economic_core import isolation as isolation
from qlib_integration.economic_core_inputs import adapt_phase, prepared_rows
from qlib_integration.economic_core_session import CoreSession, CoreHalt, Intent
from qlib_integration.economic_historical_inputs import session_state_records, known_event_records
from qlib_integration.economic_mvp_scope import entry_eligibility, visible_fact
from qlib_integration.economic_exchange import validate_prepared

DAY = "2020-07-16"


def historical(phase):
    rows = records(DAY, phase)
    result = []
    for r in rows:
        basis = ("historical_session_effective" if r.name in {"asset_id", "state", "events_clear", "reference_mark"}
                 else "prior_session_eod" if phase == "A"
                 else "daily_open_reference" if phase == "B" else "daily_close_observation")
        value = deepcopy(r.fact.value)
        if r.name == "state":
            value.pop("ipo_session")
            value.pop("listing_regime")
            value.update(prior_session_count=20, regime_basis="independent_dated_limits_with_prior_sessions")
        coverage = r.coverage
        if r.name == "events_clear":
            coverage = dict(start=DAY, end=DAY, event_ids=[], basis="synthetic known event review",
                semantics="known_session_events", coverage_complete=False, status="no_known_blocking",
                reviewed_sources=["synthetic"], review_asof=DAY)
        result.append(replace(r, fact=replace(r.fact, value=value, known_at=None,
            observed_on=r.fact.observed_on if basis == "prior_session_eod" else DAY),
            phase_basis=basis, coverage=coverage))
    return result


def adapt(rows, phase="A", mode="historical", **kwargs):
    return adapt_phase(rows, date=DAY, at=DAY + " " + {"A": "09:00", "B": "09:30", "C": "16:00"}[phase],
                       phase=phase, mode=mode, **kwargs)


def decision(rows):
    a = adapt(rows)
    return entry_eligibility(S, a.at, a.facts.get(S, {}), a.states.get(S), historical=True)


def test_historical_path_without_inventing_any_known_at():
    a = account()
    runner = CoreSession(a, CAL, mode="historical")
    snapshots = {}
    def load(ph):
        snapshots[ph] = adapt(historical(ph), ph)
        return snapshots[ph]
    result = runner.run_day(DAY, [S], [Intent(S, 100, "buy")], load)
    assert result["fills"] == 1 and result["status"] == "COMMITTED"
    assert a.current_position.get_cash() == pytest.approx(3994.98)
    assert not a.hist_positions
    for snapshot in snapshots.values():
        for fields in snapshot.facts.values():
            for facts in fields.values():
                assert all(f.known_at is None for f in facts)
    frame = prepared_rows(snapshots["A"], snapshots["B"], [S], CAL)
    assert frame.known_at.isna().all() and frame.state_known_at.isna().all() and frame.raw_close.isna().all()
    with pytest.raises(ValueError):
        validate_prepared(frame)
    fact = snapshots["A"].facts[S]["asset_id"][0]
    assert visible_fact([fact], DAY + " 09:00") is None
    assert decision(historical("A")).action == "ALLOW_ENTRY"


@pytest.mark.parametrize("missing", ["asset_id", "state", "adv20_shares", "quote_quality", "events_clear"])
def test_missing_required_historical_input_denies(missing):
    assert decision([r for r in historical("A") if r.name != missing]).action == "NO_NEW_ENTRY"


@pytest.mark.parametrize("field,value", [("listed", False), ("suspended", True), ("st", True),
    ("ordinary_session", False), ("special_session", "relisting"), ("board", "unknown"),
    ("prior_session_count", 0), ("upper_limit", 12), ("instrument", "SH600001"), ("st", None)])
def test_bad_historical_state_remains_closed(field, value):
    rows = historical("A")
    rows = [replace(r, fact=replace(r.fact, value={**r.fact.value, field: value})) if r.name == "state" else r for r in rows]
    assert decision(rows).action == "NO_NEW_ENTRY"


@pytest.mark.parametrize("name", ["asset_id", "state"])
def test_conflicting_historical_versions_deny(name):
    rows = historical("A")
    r = next(r for r in rows if r.name == name)
    value = "different" if name == "asset_id" else {**r.fact.value, "st": True}
    assert decision(rows + [replace(r, fact=replace(r.fact, value=value))]).action == "NO_NEW_ENTRY"


@pytest.mark.parametrize("status", ["known_blocking", "unresolved"])
def test_known_event_blocks_entry_and_retains_holding(status):
    rows = historical("A")
    rows = [replace(r, fact=replace(r.fact, value=False), coverage={**r.coverage, "status": status})
            if r.name == "events_clear" else r for r in rows]
    assert decision(rows).action == "NO_NEW_ENTRY"
    a = account(held=100)
    old = deepcopy(a.current_position.__dict__)
    with pytest.raises(CoreHalt, match="held_entitlement_unresolved"):
        CoreSession(a, CAL, mode="historical").run_day(DAY, [], [], lambda ph: adapt(rows))
    assert a.current_position.__dict__ == old


def test_historical_held_exit_uses_dated_reference_without_a_fake_timestamp():
    a = account(held=100)
    receipt = CoreSession(a, CAL, mode="historical").run_day(DAY, [], [Intent(S, 100, "sell")],
        lambda ph: adapt(historical(ph), ph))
    assert receipt["fills"] == 1 and a.current_position.get_stock_amount(S) == 0
    assert a.current_position.get_cash() == pytest.approx(5000 + 1000 - 5 - 1 - 0.02)


@pytest.mark.parametrize("name", ["raw_open", "open_evidence"])
def test_missing_open_has_no_close_fallback(name):
    a = account()
    def load(ph):
        rows = historical(ph)
        return adapt([r for r in rows if not (ph == "B" and r.name == name)], ph)
    receipt = CoreSession(a, CAL, mode="historical").run_day(DAY, [S], [Intent(S, 100, "buy")], load)
    assert receipt["fills"] == 0 and a.current_position.get_stock_amount(S) == 0


@pytest.mark.parametrize("fault", ["phase", "future", "source", "hash", "C_to_A"])
def test_phase_future_and_source_binding(fault):
    rows = historical("A")
    r = next(r for r in rows if r.name == "asset_id")
    bad = {"phase": replace(r, phase="C"),
           "future": replace(r, fact=replace(r.fact, observed_on="2020-07-17")),
           "source": replace(r, fact=replace(r.fact, source="")),
           "hash": replace(r, sha256="bad"),
           "C_to_A": next(x for x in historical("C") if x.name == "close_mark")}[fault]
    assert decision([x for x in rows if x != r] + [bad]).action == "NO_NEW_ENTRY"


def live_rows():
    result = []
    for r in records(DAY, "A"):
        receipt = dict(instrument=S, session=DAY, source=r.fact.source, sha256=SHA,
                       observed_at=DAY + " 08:59:30", fetched_at=DAY + " 08:59:40")
        result.append(replace(r, live_receipt=receipt))
    return result


def test_live_requires_actual_receipts_and_explicit_ttl():
    a = adapt(live_rows(), mode="live", live_ttl_seconds=60)
    assert entry_eligibility(S, a.at, a.facts[S], a.states[S]).action == "ALLOW_ENTRY"
    with pytest.raises(ValueError, match="TTL"):
        adapt(live_rows(), mode="live")
    rejected = adapt(historical("A"), mode="live", live_ttl_seconds=60)
    assert not rejected.facts and not rejected.states
    with pytest.raises(ValueError, match="live execution"):
        CoreSession(account(), CAL, mode="live")
    with pytest.raises(CoreHalt, match="mismatch"):
        CoreSession(account(), CAL).run_day(DAY, [S], [Intent(S, 100, "buy")],
                                           lambda ph: adapt(historical(ph), ph))


@pytest.mark.parametrize("key,value", [("observed_at", "2020-07-16 08:00"),
    ("fetched_at", "2020-07-16 09:01"), ("session", "2020-07-15"),
    ("instrument", "SH600001"), ("source", "other"), ("sha256", "b" * 64), ("observed_at", None)])
def test_live_stale_conflicting_or_missing_receipts_deny(key, value):
    rows = live_rows()
    rows[0] = replace(rows[0], live_receipt={**rows[0].live_receipt, key: value})
    a = adapt(rows, mode="live", live_ttl_seconds=60)
    assert entry_eligibility(S, a.at, a.facts.get(S, {}), a.states.get(S)).action == "NO_NEW_ENTRY"


def test_empty_event_table_is_not_a_review():
    with pytest.raises(ValueError):
        known_event_records(instrument=S, date=DAY, review={})
    rows = historical("A")
    rows = [replace(r, coverage={**r.coverage, "coverage_complete": True}) if r.name == "events_clear" else r for r in rows]
    assert decision(rows).action == "NO_NEW_ENTRY"


def test_source_adapter_does_not_read_current_ohlc_to_choose_state():
    days = pd.bdate_range("2020-06-18", "2020-07-16").strftime("%Y-%m-%d")
    states = pd.DataFrame(dict(date=days, code="sh.600000", isST="0", tradestatus="1", preclose="10"))
    limits = pd.DataFrame([dict(ts_code="600000.SH", trade_date="20200716", pre_close=10, up_limit=11, down_limit=9)])
    identity = dict(instrument=S, date=DAY, asset_id=S, execution_code_reference=S, board="main")
    kwargs = dict(instrument=S, date=DAY, states=states, limits=limits, identity=identity,
                  state_hash=SHA, limit_hash=SHA, identity_hash=SHA)
    clean = session_state_records(**kwargs)
    states["close"], states["high"], states["low"] = -999, 999999, -888
    assert session_state_records(**kwargs) == clean
    limits.loc[0, "ts_code"] = "600001.SH"
    with pytest.raises(ValueError, match="identity"):
        session_state_records(**kwargs)


def test_future_historical_version_does_not_reject_a_valid_past_version():
    rows = historical("A")
    state = next(r for r in rows if r.name == "state")
    future = replace(state, fact=replace(state.fact, value="malformed future state", observed_on="2020-07-17"))
    assert decision(rows + [future]).action == "ALLOW_ENTRY"


@pytest.mark.parametrize("field", ["preclose", "pre_close", "up_limit", "down_limit"])
def test_missing_independent_bounds_or_reference_never_pass_nan_comparison(field):
    states = pd.DataFrame([dict(date=DAY, code="sh.600000", isST="0", tradestatus="1", preclose=10)])
    limits = pd.DataFrame([dict(ts_code="600000.SH", trade_date="20200716", pre_close=10, up_limit=11, down_limit=9)])
    (states if field == "preclose" else limits).loc[0, field] = float("nan")
    with pytest.raises(ValueError, match="reference"):
        session_state_records(instrument=S, date=DAY, states=states, limits=limits,
            identity=dict(instrument=S, date=DAY, asset_id=S, execution_code_reference=S, board="main"),
            state_hash=SHA, limit_hash=SHA, identity_hash=SHA)
