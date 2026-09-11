import struct

import pandas as pd
import pytest

from qlib_integration.economic_data_readiness import QuoteSliceReader, synthetic_feasibility


def test_binary_reader_offsets_and_denies_unapproved_before_open(tmp_path):
    (tmp_path / "calendars").mkdir()
    (tmp_path / "calendars/day.txt").write_text("2015-01-05\n2015-01-06\n2023-12-29\n2024-01-02\n")
    stock = tmp_path / "features/sh600000"
    stock.mkdir(parents=True)
    # first calendar index=1; tail is a forbidden 2024 sentinel, never read.
    (stock / "open.day.bin").write_bytes(struct.pack("<ffff", 1, 10, 20, 999))
    reader = QuoteSliceReader(tmp_path)
    s = reader.read("sh600000", "open", ["2015-01-05", "2015-01-06", "2023-12-29"])
    assert pd.isna(s.iloc[0]) and list(s.iloc[1:]) == [10.0, 20.0]
    for stock, field, dates in [
        ("sh600000", "label", ["2015-01-06"]),
        ("sh600000", "score", ["2015-01-06"]),
        ("sh600000", "open", ["2024-01-02"]),
        ("unknown", "open", ["2015-01-06"]),
    ]:
        with pytest.raises(ValueError, match="before file open"):
            reader.read(stock, field, dates)
    assert len(reader.audit) == 1 and reader.audit[0]["completed"]


def test_synthetic_feasibility_has_no_outcomes():
    frame = synthetic_feasibility()
    assert len(frame) == 24 and set(frame.aum_cny) == {1_000_000, 5_000_000, 10_000_000}
    assert not {"nav", "return", "score", "cagr", "sharpe", "label"}.intersection(frame.columns)
    row = frame.query(
        "aum_cny == 1000000 and members == 2000 and synthetic_uniform_price_cny == 5"
    ).iloc[0]
    assert row.unbuildable_names == 2000
