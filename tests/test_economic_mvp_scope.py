from copy import deepcopy
from types import SimpleNamespace

import pytest

from qlib_integration.economic_event_position import EventPosition
from qlib_integration.economic_mvp_scope import (
    Fact,
    visible_fact,
    entry_eligibility,
    holding_continuity,
    scope_account,
    bonus_claim,
)

AT = "2020-07-16 09:00"


def fact(value, **changes):
    return Fact(
        **dict(
            dict(
                value=value,
                observed_on="2020-07-15",
                effective_from="2020-07-16",
                effective_to="2020-07-16",
                known_at="2020-07-15 18:00",
                source="synthetic",
            ),
            **changes,
        )
    )


def facts():
    return {
        k: [fact(v)]
        for k, v in dict(
            asset_id="asset", quote_quality=True, events_clear=True, adv20_shares=10000.0
        ).items()
    }


def state(stock="SH600000", **changes):
    return dict(
        dict(
            instrument=stock,
            date="2020-07-16",
            board="main",
            listed=True,
            st=False,
            suspended=False,
            ordinary_session=True,
            special_session="none",
            limit_ratio=0.1,
            upper_limit=11.0,
            lower_limit=9.0,
            limit_reference=10.0,
            effective_from="2020-07-16",
            effective_to="2020-07-16",
            known_at="2020-07-15",
            publication_precision="date",
            source="synthetic",
            evidence_level="synthetic",
            ipo_session=10,
            listing_regime="approval",
        ),
        **changes,
    )


def held_facts():
    return dict(
        facts(), valuation_mark=[fact(10.0, observed_on="2020-07-16", known_at="2020-07-16 08:00")]
    )


def test_late_negative_event_never_retroactively_excludes_entry():
    f = facts()
    f["events_clear"].append(fact(False, known_at="2020-07-16 15:00"))
    assert entry_eligibility("SH600000", AT, f, state()).action == "ALLOW_ENTRY"
    assert visible_fact(f["events_clear"], "2020-07-16 16:00").value is False
    f["events_clear"].append(fact(False))
    assert entry_eligibility("SH600000", AT, f, state()).action == "NO_NEW_ENTRY"


@pytest.mark.parametrize("field", ["asset_id", "quote_quality", "events_clear", "adv20_shares"])
def test_missing_entry_evidence_is_no_entry(field):
    f = facts()
    f.pop(field)
    assert entry_eligibility("SH600000", AT, f, state()).action == "NO_NEW_ENTRY"


def test_same_day_quote_or_date_only_publication_cannot_authorize_open():
    f = facts()
    f["quote_quality"] = [fact(True, observed_on="2020-07-16", known_at="2020-07-16 08:00")]
    assert entry_eligibility("SH600000", AT, f, state()).action == "NO_NEW_ENTRY"
    assert visible_fact([fact(True, known_at="2020-07-16", precision="date")], AT) is None
    assert visible_fact([fact(True, known_at=None)], AT) is None


@pytest.mark.parametrize(
    "s",
    [
        None,
        state(suspended=True),
        state(st=True),
        state(ordinary_session=False, special_session="relisting"),
    ],
)
def test_uncertified_or_special_state_is_not_an_entry_blocker_for_the_project(s):
    assert entry_eligibility("SH600000", AT, facts(), s).action == "NO_NEW_ENTRY"
    assert holding_continuity("SH600000", AT, held_facts(), s).action in {
        "CARRY_ONLY",
        "ORDINARY_EXECUTION_CANDIDATE",
    }


def test_unheld_bad_candidate_does_not_halt_held_good_account():
    position = EventPosition(
        cash=1000.0, position_dict={"SH600000": {"amount": 100.0, "price": 10.0}}
    )
    before = deepcopy(position.__dict__)
    account = SimpleNamespace(current_position=position)
    result = scope_account(account, ["SH600999"], AT, {"SH600000": held_facts()}, {})
    assert result["account_action"] == "PREFLIGHT_PASSED"
    assert result["entries"]["SH600999"].action == "NO_NEW_ENTRY"
    assert result["holdings"]["SH600000"].action == "CARRY_ONLY"
    assert position.__dict__ == before
    result = scope_account(account, [], AT, {}, {})
    assert result["account_action"] == "HALT_RETAIN" and position.__dict__ == before


def test_receivable_only_and_bonus_only_positions_cannot_disappear():
    p = EventPosition(cash=0.0)
    p.events["cash"] = SimpleNamespace(instrument="SH600000")
    p.events["bonus"] = SimpleNamespace(instrument="SZ000001")
    p.book.receivables["cash"] = 100.0
    p.pending_bonus["bonus"] = 10
    result = scope_account(SimpleNamespace(current_position=p), [], AT, {}, {})
    assert result["preserved_exposures"] == ("SH600000", "SZ000001")
    assert result["account_action"] == "HALT_RETAIN"
    assert p.book.receivables["cash"] == 100.0 and p.pending_bonus["bonus"] == 10


def test_aliases_are_not_ranked_or_double_entered():
    p = EventPosition(cash=1000.0)
    result = scope_account(
        SimpleNamespace(current_position=p),
        ["SH600000", "SZ000001"],
        AT,
        {"SH600000": facts(), "SZ000001": facts()},
        {"SH600000": state(), "SZ000001": state("SZ000001")},
    )
    assert all(d.action == "NO_NEW_ENTRY" for d in result["entries"].values())


def test_late_mark_and_unknown_claim_block_holding_not_just_trade():
    f = held_facts()
    f["valuation_mark"] = [fact(10.0, observed_on="2020-07-16", known_at="2020-07-16 15:00")]
    assert holding_continuity("SH600000", AT, f, state()).action == "HALT_RETAIN"
    f = held_facts()
    f["events_clear"] = [fact(False)]
    assert holding_continuity("SH600000", AT, f, state()).action == "HALT_RETAIN"


def test_fractional_rights_are_exact_and_never_silently_rounded():
    claim = bonus_claim(100, "0.12345")
    assert claim["total"] == "12.34500" and claim["fractional_claim"] == "0.34500"
    assert claim["status"] == "PENDING_ALLOCATION" and claim["cash_substitute"] is None
    assert bonus_claim(100, ".1")["status"] == "EXISTING_INTEGRAL_BRIDGE"
    with pytest.raises(ValueError):
        bonus_claim(100, "NaN")


def test_no_instrument_history_outside_research_window():
    with pytest.raises(ValueError, match="boundary"):
        entry_eligibility("SH600000", "2024-01-02 09:00", facts(), state())


def test_known_cash_only_claim_does_not_require_a_stock_mark():
    p = EventPosition(cash=0.0)
    p.events["cash"] = SimpleNamespace(instrument="SH600000")
    p.book.receivables["cash"] = 100.0
    result = scope_account(SimpleNamespace(current_position=p), [], AT, {"SH600000": facts()}, {})
    assert result["account_action"] == "PREFLIGHT_PASSED"
    assert result["holdings"]["SH600000"].action == "CARRY_CASH_CLAIM"
    assert p.get_cash() == 0 and p.book.receivables["cash"] == 100.0


def test_negative_claim_cannot_be_silently_ignored():
    p = EventPosition(cash=0.0)
    p.book.receivables["cash"] = -1.0
    with pytest.raises(ValueError, match="receivable"):
        scope_account(SimpleNamespace(current_position=p), [], AT, {}, {})


def test_a_valid_mark_does_not_authorize_a_trade():
    f = held_facts()
    assert holding_continuity("SH600000", AT, f, state()).action == "CARRY_ONLY"
    f["voluntary_trade_ready"] = [fact(True)]
    assert holding_continuity("SH600000", AT, f, state()).action == "ORDINARY_EXECUTION_CANDIDATE"
    f["voluntary_trade_ready"] = [fact(False)]
    assert holding_continuity("SH600000", AT, f, state()).action == "CARRY_ONLY"


def test_order_guard_cannot_turn_carry_or_halt_into_a_fill():
    from qlib_integration.economic_mvp_scope import require_scope_order, Decision

    scope = dict(
        account_action="PREFLIGHT_PASSED",
        holdings={"SH600000": Decision("CARRY_ONLY", ())},
        entries={"SZ000001": Decision("ALLOW_ENTRY", ())},
    )
    require_scope_order(scope, "SZ000001", purpose="new_entry")
    with pytest.raises(ValueError, match="forbids"):
        require_scope_order(scope, "SH600000", purpose="holding_exit")
    scope["account_action"] = "HALT_RETAIN"
    with pytest.raises(ValueError, match="retain"):
        require_scope_order(scope, "SZ000001", purpose="new_entry")


def test_invalid_fact_intervals_and_intraday_observation_do_not_pass():
    assert visible_fact([fact(True, effective_from="0", effective_to="9")], AT) is None
    assert visible_fact([fact(True, observed_on="2020-07-15 23:00")], AT) is None
    assert visible_fact([fact(True, source=True)], AT) is None


def test_terminal_equity_cannot_use_ordinary_event_clear_to_bypass_resolution():
    assert (
        holding_continuity("SH600000", AT, held_facts(), state(listed=False)).action
        == "HALT_RETAIN"
    )
    assert (
        holding_continuity(
            "SH600000", AT, facts(), state(listed=False), needs_market_mark=False
        ).action
        == "CARRY_CASH_CLAIM"
    )
