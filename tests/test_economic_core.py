from copy import deepcopy
from dataclasses import replace
import hashlib

import pandas as pd
import pytest
import qlib
from qlib.data import D
from qlib.backtest.account import Account

from qlib_integration.economic_core_inputs import Evidence, EVENT_FAMILIES, adapt_phase, prepared_rows, market_phase_records
from qlib_integration.economic_core_session import CoreSession, CoreHalt, Intent
from qlib_integration.economic_event_position import Distribution, attach_event_position
from qlib_integration.economic_mvp_scope import Fact, scope_account
from qlib_integration.economic_execution_contract import price_bounds

CAL = pd.to_datetime(["2020-07-15", "2020-07-16", "2020-07-17", "2020-07-20", "2020-07-21"])
S = "SH600000"
SHA = hashlib.sha256(b"synthetic core fixture").hexdigest()


@pytest.fixture(autouse=True)
def isolation(tmp_path, monkeypatch):
    provider = tmp_path / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text("\n".join(str(d.date()) for d in CAL))
    qlib.init(provider_uri=str(provider), expression_cache=None, dataset_cache=None)

    def deny(*args, **kwargs):
        raise AssertionError("core tests forbid provider values")

    monkeypatch.setattr(D, "features", deny)


def account(held=0, cash=5000):
    a = Account(init_cash=cash, position_dict={S: {"amount": held, "price": 10}} if held else {},
                benchmark_config={"benchmark": None}, port_metr_enabled=False)
    attach_event_position(a)
    return a


def event(**changes):
    return Distribution(**dict(dict(event_id="d1", instrument=S, record_date="2020-07-16",
        ex_date="2020-07-17", pay_date="2020-07-20", listable_date="2020-07-21",
        net_cash_per_share=1.0, bonus_per_share=0.1, announced_date="2020-07-14",
        source="synthetic", tax_policy="synthetic"), **changes))


def records(date, phase, *, stock=S, special=False, terminal=False, events=(), price=10,
            open_evidence=True, unknown_events=False, missing_mark=False, adv=100000):
    prev = str(CAL[CAL.get_loc(pd.Timestamp(date)) - 1].date())
    coverage = dict(start=date, end=date, families=sorted(EVENT_FAMILIES),
                    event_ids=[e.event_id for e in events], basis="synthetic complete event coverage")

    def row(name, value, *, today=False):
        known = date + (" 08:00" if phase == "A" else " 09:25" if phase == "B" else " 15:01") if today else prev + " 18:00"
        fact = Fact(value, date if today else prev, date, date, known, "synthetic")
        return Evidence(stock, name, phase, fact, SHA, coverage if name == "events_clear" else None)

    if phase == "B":
        return [row("raw_open", price, today=True), row("open_evidence", open_evidence, today=True)]
    result = [row("asset_id", stock), row("events_clear", not unknown_events)]
    if not missing_mark:
        result.append(row("reference_mark" if phase == "A" else "close_mark", price, today=True))
    if phase == "A":
        lo, hi = price_bounds(price, 0.1)
        state = dict(instrument=stock, date=date, board="main", listed=not terminal, st=False,
                     suspended=False, ordinary_session=not special,
                     special_session="relisting" if special else "none", limit_ratio=0.1,
                     upper_limit=hi, lower_limit=lo, limit_reference=price, effective_from=date,
                     effective_to=date, evidence_level="synthetic", ipo_session=1000, listing_regime="approval")
        result += [row("quote_quality", True), row("adv20_shares", adv), row("state", state)]
        result += [row("distribution", e) for e in events]
    return result


def loader(date, *, calls=None, per_phase=None, **kwargs):
    def load(phase):
        if calls is not None:
            calls.append(phase)
        clock = {"A": "09:00", "B": "09:30", "C": "16:00"}[phase]
        params = {**kwargs, **(per_phase or {}).get(phase, {})}
        return adapt_phase(records(date, phase, **params), date=date, at=date + " " + clock, phase=phase)
    return load


def position_state(a):
    return deepcopy(a.current_position.__dict__)


def test_ordinary_multiday_events_sale_pending_bonus_payment_and_listing():
    a = account()
    runner = CoreSession(a, CAL)
    d = event()
    calls = []
    runner.run_day("2020-07-16", [S, "SH600999"], [Intent(S, 100, "buy"), Intent("SH600999", 100, "buy")],
                   loader("2020-07-16", calls=calls, events=[d]))
    p = a.current_position
    assert calls == ["A", "B", "C"]
    assert p.get_cash() == pytest.approx(5000 - 1000 - 5 - 0.02)
    assert p.entitlements == {"d1": 100}
    assert runner.receipts[-1]["denied"] == ["SH600999"]
    runner.run_day("2020-07-17", [], [Intent(S, 100, "sell")], loader("2020-07-17", events=[d], price=8.18))
    assert p.get_stock_amount(S) == 0
    assert p.book.receivables == {"d1": 100}
    assert p.pending_bonus == {"d1": 10}
    assert p.get_cash() == pytest.approx(3994.98 + 818 - 5 - 0.82 - 0.02)
    # No synthetic ordinary quote is needed for the unlisted right on a special day.
    runner.run_day("2020-07-20", [], [], loader("2020-07-20", events=[d], price=8.18, special=True))
    assert p.book.receivables == {} and p.pending_bonus == {"d1": 10}
    assert p.get_cash() == pytest.approx(4807.14 + 100)
    runner.run_day("2020-07-21", [], [], loader("2020-07-21", events=[d], price=8.18))
    assert p.get_stock_amount(S) == 10 and p.pending_bonus == {}
    assert p.position["now_account_value"] == pytest.approx(p.get_cash() + 81.8)
    assert not a.is_port_metr_enabled() and a.hist_positions == {} and a.accum_info.rtn == 0
    with pytest.raises(ValueError, match="duplicate"):
        runner.run_day("2020-07-21", [], [], loader("2020-07-21"))


@pytest.mark.parametrize("point", ["after_events", "after_fill", "after_close", "before_commit"])
def test_transaction_failure_keeps_all_state_and_replay_matches_clean_run(point):
    a, clean = account(), account()
    runner, oracle = CoreSession(a, CAL), CoreSession(clean, CAL)
    before = position_state(a)
    intents = [Intent(S, 100, "buy"), Intent(S, 100, "buy")]

    def fail(name):
        if name == point:
            raise RuntimeError("injected " + name)

    with pytest.raises(CoreHalt, match="injected"):
        runner.run_day("2020-07-16", [S], intents, loader("2020-07-16"), failpoint=fail)
    assert position_state(a) == before and runner.last_date is None
    assert a.accum_info.__dict__ == clean.accum_info.__dict__
    runner.run_day("2020-07-16", [S], intents, loader("2020-07-16"))
    oracle.run_day("2020-07-16", [S], intents, loader("2020-07-16"))
    assert position_state(a) == position_state(clean)
    # Minimum fee is once per mother order, not once per partial fill.
    assert a.current_position.get_cash() == pytest.approx(5000 - 2000 - 5 - 0.04)


@pytest.mark.parametrize("phase,change", [
    ("A", {"unknown_events": True}), ("C", {"unknown_events": True}),
    ("C", {"missing_mark": True}), ("A", {"terminal": True}),
])
def test_exposed_unknown_halts_before_day_commit(phase, change):
    a = account(held=100)
    runner = CoreSession(a, CAL)
    before = position_state(a)
    with pytest.raises(CoreHalt):
        runner.run_day("2020-07-16", [], [], loader("2020-07-16", per_phase={phase: change}))
    assert position_state(a) == before


def test_fractional_record_capture_halts_without_discarding_shares():
    a = account(held=101)
    before = position_state(a)
    with pytest.raises(CoreHalt, match="fractional"):
        CoreSession(a, CAL).run_day("2020-07-16", [], [], loader("2020-07-16", events=[event()]))
    assert position_state(a) == before


def test_carry_special_and_bad_unheld_candidate_do_not_require_trade_rows():
    a = account(held=100)
    r = CoreSession(a, CAL).run_day("2020-07-16", ["SH600999"],
        [Intent(S, 100, "sell"), Intent("SH600999", 100, "buy")], loader("2020-07-16", special=True))
    assert r["fills"] == 0 and set(r["denied"]) == {S, "SH600999"}
    assert a.current_position.get_stock_amount(S) == 100


def test_cash_only_claim_survives_without_stock_mark_and_pays():
    a = account(held=100)
    d = event(bonus_per_share=0, listable_date="")
    r = CoreSession(a, CAL)
    r.run_day("2020-07-16", [], [], loader("2020-07-16", events=[d]))
    r.run_day("2020-07-17", [], [Intent(S, 100, "sell")], loader("2020-07-17", events=[d]))
    before = a.current_position.get_cash()
    r.run_day("2020-07-20", [], [], loader("2020-07-20", events=[d], missing_mark=True))
    assert a.current_position.get_cash() == before + 100
    assert a.current_position.get_stock_list() == [] and a.current_position.book.receivables == {}


@pytest.mark.parametrize("evidence", [False, None])
def test_open_unconfirmed_no_fill_and_close_cannot_replace_it(evidence):
    a = account()
    result = CoreSession(a, CAL).run_day("2020-07-16", [S], [Intent(S, 100, "buy")],
        loader("2020-07-16", per_phase={"B": {"open_evidence": evidence}, "C": {"price": 999}}))
    assert result["fills"] == 0 and a.current_position.get_cash() == 5000


def test_capacity_partial_fills_and_t1_no_same_day_exit():
    a = account()
    result = CoreSession(a, CAL).run_day("2020-07-16", [S],
        [Intent(S, 200, "buy"), Intent(S, 200, "buy"), Intent(S, 100, "sell")],
        loader("2020-07-16", adv=25000))
    assert a.current_position.get_stock_amount(S) == 200
    assert result["fills"] == 1 and result["denied"] == [S]


@pytest.mark.parametrize("mutation", ["hash", "phase", "late", "coverage", "state_identity"])
def test_source_binding_and_missingness_fail_closed_per_candidate(mutation):
    recs = records("2020-07-16", "A")
    index = next(i for i, e in enumerate(recs) if e.name == "events_clear")
    if mutation == "hash":
        recs[index] = replace(recs[index], sha256="bad")
    elif mutation == "phase":
        recs[index] = replace(recs[index], phase="C")
    elif mutation == "late":
        recs[index] = replace(recs[index], fact=replace(recs[index].fact, known_at="2020-07-16 16:00"))
    elif mutation == "coverage":
        recs[index] = replace(recs[index], coverage=None)
    else:
        index = next(i for i, e in enumerate(recs) if e.name == "state")
        recs[index] = replace(recs[index], fact=replace(recs[index].fact, value={**recs[index].fact.value, "instrument": "SZ000001"}))
    phase = adapt_phase(recs, date="2020-07-16", at="2020-07-16 09:00", phase="A")
    assert scope_account(account(), [S], phase.at, phase.facts, phase.states)["entries"][S].action == "NO_NEW_ENTRY"


def test_conflicting_versions_and_future_negative_do_not_change_past_entry():
    recs = records("2020-07-16", "A")
    original = next(x for x in recs if x.name == "events_clear")
    late = replace(original, fact=replace(original.fact, value=False, known_at="2020-07-16 16:00"))
    a = adapt_phase(recs + [late], date="2020-07-16", at="2020-07-16 09:00", phase="A")
    assert scope_account(account(), [S], a.at, a.facts, a.states)["entries"][S].action == "ALLOW_ENTRY"
    conflict = replace(original, fact=replace(original.fact, value=False))
    a = adapt_phase(recs + [conflict], date="2020-07-16", at="2020-07-16 09:00", phase="A")
    assert scope_account(account(), [S], a.at, a.facts, a.states)["entries"][S].action == "NO_NEW_ENTRY"


def test_future_close_never_in_prepared_and_cross_date_denied():
    a = loader("2020-07-16")("A")
    b = loader("2020-07-16")("B")
    frame = prepared_rows(a, b, [S], CAL)
    assert frame.raw_close.isna().all()
    b.date = "2020-07-17"
    with pytest.raises(ValueError, match="mismatch"):
        prepared_rows(a, b, [S], CAL)
    with pytest.raises(ValueError, match="boundary"):
        adapt_phase([], date="2024-01-02", at="2024-01-02 09:00", phase="A")


def test_covered_event_without_terms_halts_and_not_silently_ignored():
    a = account(held=100)
    base = loader("2020-07-16")
    def missing(phase):
        result = base(phase)
        if phase == "A":
            result.covered_events[S] = ("unprovided",)
        return result
    with pytest.raises(CoreHalt, match="without a handler input"):
        CoreSession(a, CAL).run_day("2020-07-16", [], [], missing)


def test_missing_unheld_event_terms_only_deny_entry():
    a = account()
    base = loader("2020-07-16")
    def missing(phase):
        result = base(phase)
        if phase == "A":
            result.covered_events[S] = ("unprovided",)
        return result
    result = CoreSession(a, CAL).run_day("2020-07-16", [S], [Intent(S, 100, "buy")], missing)
    assert result["fills"] == 0 and result["denied"] == [S]


def test_mixed_carry_and_ordinary_buy_preserves_both_without_carry_quote():
    a = account(held=100)
    other = "SZ000001"
    def mixed(phase):
        rows = records("2020-07-16", phase, special=True)
        rows += records("2020-07-16", phase, stock=other)
        return adapt_phase(rows, date="2020-07-16", at="2020-07-16 " + {"A":"09:00","B":"09:30","C":"16:00"}[phase], phase=phase)
    result = CoreSession(a, CAL).run_day("2020-07-16", [other], [Intent(other, 100, "buy")], mixed)
    assert result["fills"] == 1
    assert a.current_position.get_stock_amount_dict() == {S:100, other:100}


def test_failed_ex_day_preserves_prior_registered_right_and_can_resume():
    a = account(held=100)
    r = CoreSession(a, CAL)
    d = event()
    r.run_day("2020-07-16", [], [], loader("2020-07-16", events=[d]))
    before = position_state(a)
    def fail(name):
        if name == "after_events":
            raise RuntimeError("after ex mutation")
    with pytest.raises(CoreHalt):
        r.run_day("2020-07-17", [], [], loader("2020-07-17", events=[d]), failpoint=fail)
    assert position_state(a) == before and r.last_date == "2020-07-16"
    r.run_day("2020-07-17", [], [], loader("2020-07-17", events=[d]))
    assert a.current_position.book.receivables == {"d1":100}
    assert a.current_position.pending_bonus == {"d1":10}


def test_daily_phase_approximation_never_creates_preopen_state():
    rows = records("2020-07-16", "A")
    state = next(x for x in rows if x.name == "state")
    unsupported = replace(state, fact=replace(state.fact, known_at=None), phase_basis="prior_session_eod")
    a = adapt_phase([unsupported], date="2020-07-16", at="2020-07-16 09:00", phase="A")
    assert a.states == {} and a.issues[S]
    opening = records("2020-07-16", "B")
    opening = [replace(x, fact=replace(x.fact, known_at=None), phase_basis="daily_open_reference") for x in opening]
    b = adapt_phase(opening, date="2020-07-16", at="2020-07-16 09:30", phase="B")
    assert b.values[S]["raw_open"] == 10 and len(b.approximations) == 2
    assert all("source_known_at=null" in item for item in b.approximations)


def test_overlay_today_diagnostics_cannot_choose_open_or_change_prior_adv():
    days = pd.bdate_range(end="2020-07-16", periods=21)
    frame = pd.DataFrame(dict(date=[str(d.date()) for d in days], instrument=S,
                              quote_status="cross_source_agreed", raw_volume=100000.0, valuation_mark=10.0))
    reference = dict(instrument=S, date="2020-07-16", raw_open=10.0, sha256=SHA, source="synthetic fixed raw source")
    def build(f):
        return market_phase_records(f, instrument=S, date="2020-07-16", calendar=days,
                                    sha256=SHA, opening_reference=reference)
    original = build(frame)
    frame.loc[20, ["quote_status", "raw_volume", "valuation_mark"]] = ["source_conflict", float("nan"), 999.0]
    changed = build(frame)
    assert changed["A"] == original["A"] and changed["B"] == original["B"]
    assert changed["C"] != original["C"]
    assert not any(r.name in {"state", "events_clear", "asset_id"} for r in changed["A"])


def test_multiple_known_event_inputs_are_not_collapsed_by_field_name():
    es = [event(bonus_per_share=0, listable_date=""), event(event_id="d2", bonus_per_share=0, listable_date="", ex_date="2020-07-20")]
    a = loader("2020-07-16", events=es)("A")
    assert {e.event_id for e in a.distributions[S]} == {"d1", "d2"}


def test_missing_held_adv_forbids_exit_but_keeps_valued_position():
    a = account(held=100)
    r = CoreSession(a, CAL).run_day("2020-07-16", [], [Intent(S, 100, "sell")],
                                   loader("2020-07-16", adv=0))
    assert r["denied"] == [S] and a.current_position.get_stock_amount(S) == 100


def test_future_malformed_event_does_not_retroactively_deny_entry():
    rows = records("2020-07-16", "A")
    future = Evidence(S, "distribution", "A",
        Fact(event(net_cash_per_share=float("nan")), "2020-07-16", "2020-07-16", "2020-07-16",
             "2020-07-16 16:00", "synthetic future revision"), SHA)
    a = adapt_phase(rows + [future], date="2020-07-16", at="2020-07-16 09:00", phase="A")
    assert scope_account(account(), [S], a.at, a.facts, a.states)["entries"][S].action == "ALLOW_ENTRY"


def test_new_close_event_without_terms_cannot_commit_uncaptured_entitlement():
    a = account(held=100)
    before = position_state(a)
    base = loader("2020-07-16")
    def close_event(phase):
        result = base(phase)
        if phase == "C":
            result.covered_events[S] = ("new_close_event",)
        return result
    with pytest.raises(CoreHalt, match="record_capture"):
        CoreSession(a, CAL).run_day("2020-07-16", [], [], close_event)
    assert position_state(a) == before
