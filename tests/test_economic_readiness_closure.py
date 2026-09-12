import struct
import numpy as np
import pandas as pd
import pytest

from qlib_integration.economic_readiness_closure import (
    ClosureQuoteReader,
    quote_checks,
    static_ew_feasibility,
    validate_regular_limit_quote,
)


def test_vendor_ipo_placeholders_cannot_be_executable_regular_limits():
    assert (
        validate_regular_limit_quote(
            15.49, 17.04, 13.94, dict(kind="ordinary_dated", limit_ratio=0.1)
        )["upper_limit"]
        == 17.04
    )
    with pytest.raises(ValueError, match="special/no-limit"):
        validate_regular_limit_quote(
            24.26, 100000.0, 0.01, dict(kind="registration_first_five", limit_ratio=None)
        )
    with pytest.raises(ValueError, match="disagrees"):
        validate_regular_limit_quote(
            24.26, 100000.0, 0.01, dict(kind="ordinary_dated", limit_ratio=0.2)
        )


def test_reused_reader_only_reads_requested_bytes(tmp_path):
    (tmp_path / "calendars").mkdir()
    (tmp_path / "calendars/day.txt").write_text("2015-01-05\n2015-01-06\n2024-01-02\n")
    d = tmp_path / "features/sh600000"
    d.mkdir(parents=True)
    (d / "open.day.bin").write_bytes(struct.pack("<ffff", 0, 10, 11, 999999))
    reader = ClosureQuoteReader(tmp_path, ["sh600000"], ["2015-01-06"])
    assert reader.read("sh600000", "open", ["2015-01-06"]).tolist() == [11]
    for stock, field, dates in [
        ("sh600000", "open", ["2024-01-02"]),
        ("sh600000", "open", ["2015-01-05"]),
        ("sz000001", "open", ["2015-01-06"]),
        ("sh600000", "label", ["2015-01-06"]),
    ]:
        with pytest.raises(ValueError, match="before file open"):
            reader.read(stock, field, dates)
    assert len(reader.audit) == 1


@pytest.mark.parametrize("date", ["2014-12-31", "2024-01-02"])
def test_invalid_inventory_fails_before_missing_provider_io(tmp_path, date):
    with pytest.raises(ValueError, match="before provider IO"):
        ClosureQuoteReader(tmp_path, ["sh600000"], [date])


def test_full_ohlc_and_unit_anomalies():
    f = pd.DataFrame(
        dict(
            open=[10, 10, 10],
            high=[11, 11, 11],
            low=[9, 9, 9],
            close=[10, 12, 10],
            volume=[100, 100, np.nan],
            amount=[1000, 2000, 1000],
            factor=[1, 1, 1],
        )
    )
    r = quote_checks(f)
    assert r["ohlc_bad"] == 1 and r["implied_vwap_outside"] == 1 and r["missing_any"] == 1


def test_static_reference_basket_independent_hand_calculation():
    f = pd.DataFrame(
        dict(
            instrument=["SH600000", "SZ000001"],
            board=["main", "main"],
            reference_close=[10.0, 10.0],
            open=[10.0, 20.0],
            adv20=[100000.0, 100000.0],
        )
    )
    r = static_ew_feasibility(f, "2020-08-28", 10000)
    # 4750 per name -> 400 shares each; 5 + 4000*.00002 = 5.08 each.
    assert r["reference_fee_cny"] == pytest.approx(10.16)
    assert r["reference_unallocated_fraction"] == pytest.approx(1 - 8010.16 / 10000)
    assert r["open_budget_breach"] == 1 and r["known_reference_buildable"] == 2
    assert not r["actual_execution_certified"]
    f.loc[0, "reference_close"] = np.nan
    f.loc[1, "adv20"] = np.nan
    r = static_ew_feasibility(f, "2020-08-28", 10000)
    assert (
        r["names"] == 2
        and r["per_name_budget"] == 4750
        and r["unknown_price"] == 1
        and r["unknown_adv"] == 1
    )


def test_star_minimum_and_lagged_capacity_failure():
    f = pd.DataFrame(
        dict(
            instrument=["SH688001"],
            board=["star"],
            reference_close=[100.0],
            open=[1.0],
            adv20=[100.0],
        )
    )
    r = static_ew_feasibility(f, "2023-08-28", 10000)
    assert r["below_lot"] == 1 and r["adv_below_minimum"] == 1
    # A cheap later open cannot retroactively make the prior-reference order larger.
    assert r["known_reference_buildable"] == 0
