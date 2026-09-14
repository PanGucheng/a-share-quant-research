import json

import numpy as np
import pandas as pd
import pytest

from qlib_integration.economic_semantic_reconciliation import (
    reconcile_events,
    reconcile_stock,
    segments,
)


def event(**kwargs):
    return dict(
        dict(
            ts_code="600000.SH",
            ann_date="20150102",
            div_proc="实施",
            stk_div=0.1,
            cash_div_tax=1.0,
            record_date="20150105",
            ex_date="20150106",
            pay_date="20150107",
            div_listdate="20150108",
            imp_ann_date="20150102",
            source_row_id="one",
        ),
        **kwargs,
    )


def quote_pair():
    dates = ["2015-01-05", "2015-01-06", "2015-01-07"]
    q = pd.DataFrame(
        dict(
            open=[11.0, 10.0, 10.0],
            high=[11.0, 10.0, 10.0],
            low=[11.0, 10.0, 10.0],
            close=[11.0, 10.0, 10.0],
            volume=[1000.0] * 3,
            amount=[11000.0, 10000.0, 10000.0],
            factor=[1.0] * 3,
        ),
        index=dates,
    )
    s = q.drop(columns="factor").assign(
        preclose=[11.0, 11.0, 10.0], tradestatus=[1, 1, 1], isST=[0, 0, 0]
    )
    return dates, q, s


def test_equivalent_versions_and_corroboration_preserve_sources():
    f = pd.DataFrame([event(cash_div_tax=np.nan), event(ann_date="20150101", source_row_id="two")])
    r = reconcile_events(f).iloc[0]
    assert r.status == "resolved_gross_entitlement" and r.gross_cash_per_share == 1
    assert r.corroborated_cash_missing_rows == 1 and json.loads(r.source_row_ids) == ["one", "two"]
    assert r.source_rows == 2


def test_real_conflict_and_unknown_cash_never_select_first_or_zero():
    for f in [
        pd.DataFrame([event(), event(cash_div_tax=2.0)]),
        pd.DataFrame([event(cash_div_tax=np.nan)]),
    ]:
        r = reconcile_events(f).iloc[0]
        assert r.status == "unresolved" and pd.isna(r.gross_cash_per_share)
    r = reconcile_events(pd.DataFrame([event(div_listdate=None)])).iloc[0]
    assert r.status == "unresolved" and "div_listdate" in r.missing


def test_nonimplementation_cannot_override_and_late_implementation_fails():
    r = reconcile_events(pd.DataFrame([event(), event(div_proc="预案", cash_div_tax=9.0)])).iloc[0]
    assert r.status == "resolved_gross_entitlement" and r.gross_cash_per_share == 1
    r = reconcile_events(pd.DataFrame([event(imp_ann_date="20150107")])).iloc[0]
    assert r.status == "unresolved"
    with pytest.raises(ValueError, match="boundary"):
        reconcile_events(pd.DataFrame([event(ex_date="20240102")]))


def test_suspension_mark_and_tail_never_delete_held_id():
    dates, q, s = quote_pair()
    q.loc[dates[1], :] = np.nan
    s.loc[dates[1], "tradestatus"] = 0
    s = s.iloc[:2]
    events = reconcile_events(pd.DataFrame([event(div_proc="预案")]))
    r, _ = reconcile_stock("SH600000", q, s, dates, events)
    assert len(r) == 3 and r.loc[1, "valuation_mark"] == 10
    assert r.loc[1, "quote_status"] == "known_suspension_no_fill"
    assert r.loc[2, "terminal_candidate_gap"] and r.loc[2, "account_gap"]
    assert not r.can_buy_preopen.any() and r.known_at.isna().all()


def test_cross_source_conflict_does_not_silently_fallback():
    dates, q, s = quote_pair()
    s.loc[dates[0], ["open", "high", "low", "close"]] = 12.0
    s.loc[dates[0], "amount"] = 12000.0
    r, _ = reconcile_stock(
        "SH600000", q, s, dates, reconcile_events(pd.DataFrame([event(div_proc="预案")]))
    )
    assert r.loc[0, "quote_status"] == "source_conflict" and pd.isna(r.loc[0, "raw_close"])
    assert r.loc[0, "account_gap"]


def test_reference_bridge_and_missing_entitlement_persist_without_account():
    dates, q, s = quote_pair()
    q.loc[dates[1], ["open", "high", "low", "close"]] = 100 / 11
    q.loc[dates[1], "amount"] = 1000 * 100 / 11
    s.loc[dates[1], ["open", "high", "low", "close", "preclose"]] = 100 / 11
    s.loc[dates[1], "amount"] = 1000 * 100 / 11
    ev = reconcile_events(pd.DataFrame([event()]))
    _, bridge = reconcile_stock("SH600000", q, s, dates, ev)
    assert bridge.reference_bridge_match.all()
    ev = reconcile_events(pd.DataFrame([event(cash_div_tax=np.nan)]))
    r, _ = reconcile_stock("SH600000", q, s, dates, ev)
    assert r.event_unresolved.all()
    q.index = ["2024-01-02"] * 3
    with pytest.raises(ValueError, match="boundary"):
        reconcile_stock("SH600000", q, s, ["2024-01-02"], ev)


def test_segment_counts_respect_internal_holes():
    r = segments(
        pd.DataFrame(
            dict(date=["2015-01-05", "2015-01-06", "2015-01-07"], bad=[True, False, True])
        ),
        "bad",
    )
    assert [x["sessions"] for x in r] == [1, 1, 1]


def test_explicit_gross_event_bridge_does_not_claim_net_cash():
    from qlib_integration.economic_semantic_reconciliation import distribution_from_semantic
    from qlib_integration.economic_event_position import EventPosition

    row = reconcile_events(pd.DataFrame([event()])).iloc[0]
    e = distribution_from_semantic(row, "SH600000", tax_policy="before_dividend_income_tax")
    assert e.net_cash_per_share == 0 and e.gross_cash_per_share == 1
    position = EventPosition(cash=0, position_dict={"SH600000": {"amount": 100, "price": 11.0}})
    position.register(e)
    position.advance_events("2015-01-05", {"SH600000": 11.0})
    position.capture_record_close("2015-01-05")
    position.advance_events("2015-01-06", {"SH600000": 100 / 11})
    assert position.get_cash() == 0 and position.calculate_value() == pytest.approx(1100)
    position.advance_events("2015-01-07", {"SH600000": 100 / 11})
    assert position.get_cash() == 100
    with pytest.raises(ValueError, match="basis"):
        distribution_from_semantic(row, "SH600000", tax_policy="after_tax")


def test_prior_window_announcement_metadata_is_not_prior_market_data():
    from qlib_integration.economic_semantic_reconciliation import distribution_from_semantic

    row = reconcile_events(pd.DataFrame([event(imp_ann_date="20141231")])).iloc[0]
    e = distribution_from_semantic(row, "SH600000", tax_policy="before_dividend_income_tax")
    assert e.announced_date == "2014-12-31" and e.record_date == "2015-01-05"
    e.validate()
