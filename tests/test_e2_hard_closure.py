from copy import deepcopy
import struct

import numpy as np
import pandas as pd
import pytest

from qlib_integration.execution_readiness import (
    UnitRule,
    normalize_quote,
    execution_state,
    require_continuity,
    require_distinct_assets,
    WarmupReader,
    adv20_with_warmup,
    overnight_timing,
)
from qlib_integration.economic_event_position import (
    EventPosition,
    Distribution,
    attach_event_position,
)
from qlib_integration.economic_execution_contract import RawSellableLedger


@pytest.fixture(autouse=True)
def deny_provider_values(monkeypatch, tmp_path):
    import qlib

    provider = tmp_path / "isolated"
    (provider / "calendars").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text("2020-07-15\n2020-07-16\n")
    qlib.init(provider_uri=str(provider), expression_cache=None, dataset_cache=None)
    from qlib.data import D

    def deny(*args, **kwargs):
        raise AssertionError("hard-closure tests must not read provider values")

    monkeypatch.setattr(D, "features", deny)


def state(**changes):
    return dict(
        dict(
            instrument="SH600000",
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
            ipo_session=1000,
            listing_regime="approval",
        ),
        **changes,
    )


def distribution(**changes):
    return Distribution(
        **dict(
            dict(
                event_id="d1",
                instrument="SH600000",
                record_date="2020-07-15",
                ex_date="2020-07-16",
                pay_date="2020-07-17",
                listable_date="2020-07-20",
                net_cash_per_share=1.0,
                bonus_per_share=0.1,
                announced_date="2020-07-14",
                source="synthetic",
                tax_policy="synthetic",
            ),
            **changes,
        )
    )


def test_unknown_late_and_special_state_never_becomes_ordinary():
    assert execution_state(state(), "2020-07-16 09:00") == "ordinary_known"
    for change in (
        {"st": None},
        {"known_at": "2020-07-16"},
        {"source": ""},
        {"board": "star"},
        {"upper_limit": 100000.0},
        {"limit_ratio": np.nan},
        {"upper_limit": np.nan},
        {"ipo_session": np.nan},
    ):
        assert execution_state(state(**change), "2020-07-16 09:00") == "unresolved"
    assert execution_state(state(suspended=True), "2020-07-16 09:00") == "known_suspension"
    assert (
        execution_state(
            state(ordinary_session=False, special_session="relisting"), "2020-07-16 09:00"
        )
        == "known_special_blocked"
    )
    assert execution_state(state(listed=False), "2020-07-16 09:00") == "terminal_requires_event"
    with pytest.raises(ValueError, match="cannot advance"):
        require_continuity([], {"SH600000": 100}, {}, "2020-07-16 09:00", {})
    with pytest.raises(ValueError, match="valuation"):
        require_continuity(
            [], {"SH600000": 100}, {"SH600000": state(suspended=True)}, "2020-07-16 09:00", {}
        )


def test_quote_rules_no_extrapolation_and_bad_vwap_fails():
    row = dict(
        date="2015-01-05",
        instrument="SH601313",
        open=5,
        high=5,
        low=5,
        close=5,
        volume=1000,
        amount=10000,
        factor=0.5,
    )
    rule = UnitRule(
        "SH601313", "2015-01-05", "2015-01-05", "community_adjusted", 2, 1, "synthetic", True
    )
    assert normalize_quote(row, rule)["volume"] == 1000
    assert normalize_quote(row, rule)["close"] == 10
    with pytest.raises(ValueError, match="unit interval"):
        normalize_quote(dict(row, date="2015-01-06"), rule)
    with pytest.raises(ValueError, match="VWAP"):
        normalize_quote(dict(row, amount=1e7), rule)
    with pytest.raises(ValueError, match="boundary"):
        normalize_quote(dict(row, date="2024-01-02"), rule)


def test_qlib_account_raw_cash_bonus_receivable_conservation_and_t1():
    from qlib.backtest.account import Account

    account = Account(
        init_cash=1000,
        position_dict={"SH600000": {"amount": 100, "price": 11.0, "count_day": 7}},
        benchmark_config={"benchmark": None},
        port_metr_enabled=False,
    )
    p = attach_event_position(account)
    p.register(distribution())
    p.advance_events("2020-07-15", {"SH600000": 11.0})
    p.capture_record_close("2020-07-15")
    # Ex price (11 - 1) / 1.1: 100 shares + 10 stock rights + 100 cash receivable.
    px = 100 / 11
    p.advance_events("2020-07-16", {"SH600000": px})
    assert account.current_position is p
    assert p.get_cash() == 1000 and p.get_stock_amount("SH600000") == 100
    assert p.calculate_value() == pytest.approx(2100)
    ledger = RawSellableLedger()
    ledger.start_day("2020-07-16", p.get_stock_amount_dict())
    assert ledger.sellable("SH600000") == 100  # bonus rights not prematurely sellable
    p.advance_events("2020-07-17", {"SH600000": px})
    assert p.get_cash() == 1100 and p.calculate_value() == pytest.approx(2100)
    p.advance_events("2020-07-20", {"SH600000": px})
    assert p.get_stock_amount("SH600000") == 110 and not p.pending_bonus and not p.book.receivables
    ledger.start_day("2020-07-20", p.get_stock_amount_dict())
    assert ledger.sellable("SH600000") == 110 and p.calculate_value() == pytest.approx(2100)


def test_entitlement_survives_sale_and_bonus_listing_without_live_stock():
    from qlib.backtest.decision import Order

    p = EventPosition(cash=0, position_dict={"SH600000": {"amount": 100, "price": 11.0}})
    p.register(distribution())
    p.advance_events("2020-07-15", {"SH600000": 11.0})
    p.capture_record_close("2020-07-15")
    px = 100 / 11
    p.advance_events("2020-07-16", {"SH600000": px})
    p.update_order(
        Order(
            stock_id="SH600000",
            amount=100,
            direction=Order.SELL,
            start_time=pd.Timestamp("2020-07-16"),
            end_time=pd.Timestamp("2020-07-16"),
        ),
        100 * px,
        0,
        px,
    )
    assert not p.get_stock_list() and p.calculate_value() == pytest.approx(1100)
    p.advance_events("2020-07-17", {"SH600000": px})
    p.advance_events("2020-07-20", {"SH600000": px})
    assert p.get_stock_amount("SH600000") == 10 and p.calculate_value() == pytest.approx(1100)


def test_failed_event_validation_is_non_mutating_and_terminal_retained():
    with pytest.raises(ValueError):
        distribution(pay_date="unknown").validate()
    p = EventPosition(cash=100, position_dict={"SH600000": {"amount": 101, "price": 11.0}})
    p.register(distribution())
    p.advance_events("2020-07-15", {"SH600000": 11.0})
    with pytest.raises(ValueError, match="fractional"):
        p.capture_record_close("2020-07-15")
    before = deepcopy(p.position)
    with pytest.raises(ValueError, match="record-date"):
        p.advance_events("2020-07-16", {"SH600000": 10.0})
    assert p.position == before and not p.entitlements
    with pytest.raises(ValueError, match="terminal"):
        p.terminal_unknown("SH600000")
    assert p.get_stock_amount("SH600000") == 101
    with pytest.raises(ValueError, match="tax"):
        distribution(tax_policy="assume_gross_is_net").validate()


def test_identity_same_shares_count_and_no_collision():
    with pytest.raises(ValueError, match="one economic asset"):
        require_distinct_assets(
            ["SH601313", "SH601360"], {"SH601313": "asset1", "SH601360": "asset1"}
        )
    p = EventPosition(
        cash=3, position_dict={"SH601313": {"amount": 150, "price": 10.0, "count_day": 99}}
    )
    p.advance_events("2018-02-28", {"SH601313": 10.0})
    p.rename_identity(
        "SH601313", "SH601360", date="2018-02-28", evidence="synthetic", same_share_rights=True
    )
    assert p.get_stock_amount("SH601360") == 150 and p.get_stock_count("SH601360", "day") == 99
    assert p.get_cash() == 3 and p.calculate_value() == 1503


def test_warmup_exact_bytes_and_unknown_not_zero(tmp_path):
    dates = pd.bdate_range("2014-12-04", "2014-12-31").strftime("%Y-%m-%d").tolist()
    (tmp_path / "calendars").mkdir()
    (tmp_path / "calendars/day.txt").write_text("\n".join(dates + ["2015-01-05", "2024-01-02"]))
    folder = tmp_path / "features/sh600000"
    folder.mkdir(parents=True)
    (folder / "volume.day.bin").write_bytes(struct.pack("<" + "f" * 23, 0, *range(1, 21), 777, 999))
    r = WarmupReader(tmp_path, ["sh600000"], dates)
    v = r.read("sh600000", "volume", dates)
    assert adv20_with_warmup(v, dates, order_date="2015-01-05") == 10.5
    future_dates = pd.bdate_range("2020-01-01", periods=20).strftime("%Y-%m-%d").tolist()
    with pytest.raises(ValueError, match="precede order"):
        adv20_with_warmup(pd.Series(1.0, index=future_dates), future_dates, order_date="2020-01-02")
    v.iloc[0] = np.nan
    with pytest.raises(ValueError, match="unknown volume"):
        adv20_with_warmup(v, dates, order_date="2015-01-05")
    assert adv20_with_warmup(v, dates, [dates[0]], order_date="2015-01-05") == 10.45
    for date in ("2015-01-05", "2024-01-02"):
        with pytest.raises(ValueError, match="before file open"):
            r.read("sh600000", "volume", [date])


def test_overnight_no_invented_15h_availability():
    assert (
        overnight_timing(
            "2020-07-15",
            "2020-07-16 09:00",
            {"daily_basic": "2020-07-15", "statement_pit": "2020-07-14"},
            "2020-07-16 02:00",
            accept_date_pit=True,
        )
        == "READY WITH MVP APPROXIMATION"
    )
    with pytest.raises(ValueError, match="unavailable"):
        overnight_timing(
            "2020-07-15",
            "2020-07-16 09:00",
            {"pit": "2020-07-16"},
            "2020-07-16 02:00",
            accept_date_pit=True,
        )
    with pytest.raises(ValueError, match="batch"):
        overnight_timing(
            "2020-07-15",
            "2020-07-16 09:00",
            {"pit": "2020-07-15"},
            "2020-07-16 09:01",
            accept_date_pit=True,
        )


def test_evidence_gate_is_actual_qlib_session_entry(tmp_path):
    from qlib.backtest.account import Account
    from qlib_integration.economic_event_position import EvidenceCheckedOpenExchange

    quote = dict(
        datetime=pd.Timestamp("2020-07-16"),
        instrument="SH600000",
        raw_open=10.0,
        raw_close=10.0,
        previous_close=10.0,
        adv20_shares=100000.0,
        upper_limit=11.0,
        lower_limit=9.0,
        can_buy_known=True,
        can_sell_known=True,
        suspended_known=False,
        open_evidence=True,
        board="main",
        signal_time="2020-07-15 15:00",
        known_at="2020-07-15 18:00",
        state_known_at="2020-07-15 18:00",
        adv_asof="2020-07-15 18:00",
        order_time="2020-07-16 09:00",
        executable_at="2020-07-16 09:25",
        valuation_time="2020-07-16 15:00",
        source_id="synthetic",
    )
    ex = EvidenceCheckedOpenExchange(
        execution_quotes=pd.DataFrame([quote]),
        calendar=pd.to_datetime(["2020-07-15", "2020-07-16"]),
    )
    acc = Account(
        init_cash=100,
        position_dict={"SH600000": {"amount": 100, "price": 10.0}},
        benchmark_config={"benchmark": None},
        port_metr_enabled=False,
    )
    with pytest.raises(ValueError, match="unverified session"):
        ex.begin_session("2020-07-16", acc)
    with pytest.raises(ValueError, match="cannot advance"):
        ex.begin_evidenced_session(
            "2020-07-16", acc, [], {}, {}, "2020-07-16 09:00", {"SH600000": "asset1"}
        )
    assert ex.session_date is None and acc.current_position.get_stock_amount("SH600000") == 100
    with pytest.raises(ValueError, match="contradict ordinary"):
        ex.begin_evidenced_session(
            "2020-07-16",
            acc,
            [],
            {"SH600000": state(limit_reference=20.0, upper_limit=22.0, lower_limit=18.0)},
            {"SH600000": {"date": "2020-07-16", "price": 10.0, "source": "synthetic"}},
            "2020-07-16 09:00",
            {"SH600000": "asset1"},
        )
    assert ex.session_date is None
    result = ex.begin_evidenced_session(
        "2020-07-16",
        acc,
        [],
        {"SH600000": state()},
        {"SH600000": {"date": "2020-07-16", "price": 10.0, "source": "synthetic"}},
        "2020-07-16 09:00",
        {"SH600000": "asset1"},
    )
    assert result == {"SH600000": "ordinary_known"} and ex.t_plus_one.sellable("SH600000") == 100


def test_user_scan_quotes_chunk_and_no_completed_overwrite(tmp_path, monkeypatch):
    from scripts import scan_e2_hard_history as scan
    from qlib_integration.economic_data_readiness import FIELDS

    monkeypatch.setattr(scan, "BASE", tmp_path)
    monkeypatch.setattr(
        scan, "scope_inventory", lambda: (["2015-01-05", "2015-01-06"], {"SH600000": "2015-01-05"})
    )

    class FakeReader:
        fields = FIELDS

        def __init__(self, *args):
            self.audit = []

        def read(self, stock, field, dates):
            assert stock == "sh600000" and dates == ["2015-01-05", "2015-01-06"]
            return pd.Series(
                dict(open=10, high=10, low=10, close=10, volume=100, amount=100, factor=1)[field],
                index=dates,
            )

    monkeypatch.setattr(scan, "ClosureQuoteReader", FakeReader)
    scan.scan("quotes")
    assert scan.check_chunk(tmp_path / "full_quotes", "SH600000")
    with pytest.raises(ValueError, match="completed scan"):
        scan.scan("quotes")
    (tmp_path / "full_quotes/SH600000_quality.json").write_text("{}")
    with pytest.raises(AssertionError):
        scan.check_chunk(tmp_path / "full_quotes", "SH600000")
