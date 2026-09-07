from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from factor_research.long_history_screening import (
    END,
    KEYS,
    LABEL,
    common_samples,
    development_range,
    exact_primary_labels,
    frame_hash,
    native_primary_smoke,
    normalize_keys,
    read_factor,
    summarize_daily_metrics,
    primary_fdr,
    audit_feature_quality,
    bounded_price_cache,
)


def test_reader_bounds_before_io_and_ignores_recent_mutation(tmp_path, monkeypatch):
    path = tmp_path / "partition.parquet"
    original = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2023-12-28", "2023-12-29", "2024-01-02"]),
            "instrument": ["SH600000"] * 3,
            "x": [1.0, 2.0, 3.0],
        }
    )
    original.to_parquet(path)
    partitions = pd.DataFrame(
        [
            {
                "factors": "x",
                "partition_path": str(path),
                "effective_start": "2023-01-01",
                "effective_end": "2026-06-09",
                "output_sha256": "declared",
            }
        ]
    )
    original_reader = pd.read_parquet
    calls = []

    def spy(path, **kwargs):
        calls.append(kwargs)
        assert kwargs["filters"][1][2] <= END
        return original_reader(path, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", spy)
    first = read_factor(partitions, "x", "2023-12-28", END, access=[])
    original.loc[2, "x"] = 999999
    original.to_parquet(path)
    second = read_factor(partitions, "x", "2023-12-28", END, access=[])
    pd.testing.assert_frame_equal(first, second)
    assert len(calls) == 2
    with pytest.raises(ValueError, match="outside development"):
        read_factor(partitions, "x", "2023-12-28", "2024-01-02", access=[])
    assert len(calls) == 2


def test_duplicate_normalization_and_partition_overlap_are_rejected(tmp_path):
    data = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2023-01-03"] * 2),
            "instrument": ["sh600000", "SH600000"],
            "x": [1, 1],
        }
    )
    with pytest.raises(ValueError, match="duplicate normalized"):
        normalize_keys(data)
    path = tmp_path / "p.parquet"
    data.iloc[:1].to_parquet(path)
    row = {
        "factors": "x",
        "partition_path": str(path),
        "effective_start": "2023-01-03",
        "effective_end": "2023-01-03",
        "output_sha256": "test",
    }
    with pytest.raises(ValueError, match="duplicate normalized"):
        read_factor(pd.DataFrame([row, row]), "x", "2023-01-03", "2023-01-03", access=[])


def test_exact_calendar_gap_and_maturity():
    calendar = pd.bdate_range("2023-01-02", periods=30)
    prices = pd.DataFrame(
        {"datetime": calendar, "instrument": "SH600000", "$close": np.arange(100.0, 130.0)}
    )
    keys = prices.loc[[0, 9], KEYS]
    labels = exact_primary_labels(keys, prices, calendar)
    assert labels.iloc[0][LABEL] == pytest.approx(121 / 101 - 1)
    assert pd.isna(labels.iloc[1][LABEL])  # No exit at t+21 within calendar.
    missing_entry = prices.drop(index=1)
    assert pd.isna(exact_primary_labels(keys, missing_entry, calendar).iloc[0][LABEL])
    missing_middle = prices.drop(index=5)
    assert (
        exact_primary_labels(keys, missing_middle, calendar).iloc[0][LABEL] == labels.iloc[0][LABEL]
    )
    bad_prices = pd.concat([prices, prices.iloc[[0]].assign(datetime=pd.Timestamp("2024-01-02"))])
    with pytest.raises(ValueError, match="outside development"):
        exact_primary_labels(keys, bad_prices, calendar)


def test_single_horizon_mask_ties_constants_and_finite_values():
    data = pd.DataFrame(
        {
            "datetime": pd.Timestamp("2021-01-04"),
            "instrument": [f"SH{i:06d}" for i in range(100)],
            "x": np.repeat([0.0, 1.0], 50),
            LABEL: np.arange(100.0) / 1000,
            "label_10d_t1": np.nan,
        }
    )
    ic, quantile, status = common_samples(data, "x")
    assert len(ic) == 100 and quantile.empty and status.ic_available.all()
    data.x = 1
    assert common_samples(data, "x")[0].empty
    data.x = np.arange(100, dtype=float)
    data.loc[0, "x"] = np.inf
    data.loc[1, LABEL] = np.nan
    ic, quantile, _ = common_samples(data, "x")
    assert len(ic) == len(quantile) == 98
    assert frame_hash(ic) == frame_hash(ic.iloc[::-1])
    assert common_samples(data.iloc[:49], "x")[0].empty


@pytest.mark.parametrize(
    "start,end",
    [
        ("2024-01-01", "2024-01-03"),
        ("2010-01-28", "2011-01-01"),
        ("2023-12-29", "2023-01-01"),
        ("NaT", "2023-12-29"),
    ],
)
def test_development_range_fails_closed(start, end):
    with pytest.raises(ValueError, match="outside development"):
        development_range(start, end)


@pytest.fixture(scope="module")
def native():
    root = Path(__file__).resolve().parents[1]
    if (
        not (root / "tmp/reference_repos/alphalens-reloaded/src/alphalens/performance.py").is_file()
        or not (
            root / "tmp/reference_repos/jqfactor_analyzer/jqfactor_analyzer/performance.py"
        ).is_file()
    ):
        pytest.skip("optional native reference sources not installed")
    pytest.importorskip("qlib")
    from scripts.run_long_history_multi_evaluator_screening_v1 import native_modules

    return native_modules()[0]


@pytest.mark.parametrize("direction", [1.0, -1.0])
def test_native_parity_padding_and_weighted_return_arithmetic(native, direction):
    dates = pd.to_datetime(["2021-01-08", "2021-01-11"])
    data = pd.DataFrame(
        {
            "datetime": dates.repeat(100),
            "instrument": [f"SH{i:06d}" for i in range(100)] * 2,
            "x": np.tile(np.arange(100.0), 2),
            LABEL: direction * np.tile(np.arange(100.0), 2) / 1000,
        }
    )
    ic, quantiles, _ = common_samples(data, "x")
    result, receipt = native_primary_smoke(ic, quantiles, native, atol=1e-12)
    assert receipt["parity_status"] == "pass"
    assert all(v == "pass" for v in receipt["native_status"].values())
    np.testing.assert_allclose(result["qlib_ic"], direction)
    x = np.arange(100.0)
    weights = (x - x.mean()) / np.abs(x - x.mean()).sum()
    expected = np.sum(weights * direction * x / 1000)
    np.testing.assert_allclose(result["jqfactor_returns"]["period_20"], expected)
    np.testing.assert_allclose(result["qlib_long_short"], direction * 0.04)


def test_periods_follow_signal_dates_and_full_uses_raw_daily_values():
    signals = pd.to_datetime(["2014-12-30", "2014-12-31", "2015-01-05"])
    mapping = pd.DataFrame(
        {
            "datetime": signals,
            "exit_date": pd.to_datetime(["2015-01-29", "2015-01-30", "2015-02-03"]),
        }
    )
    result = summarize_daily_metrics(
        pd.Series([1.0, 2.0, 9.0], index=signals),
        mapping,
        {"A": ["2010-01-29", "2014-12-31"], "B": ["2015-01-01", "2017-12-31"]},
    )
    by_period = result.set_index("period_id")
    assert by_period.loc["full", "mean"] == 4
    assert by_period.loc["A", "mean"] == 1.5
    assert by_period.loc["A", "max_label_exit_date"] == pd.Timestamp("2015-01-30")
    assert by_period.loc["2010", "status"] == "unavailable"


def test_primary_family_keeps_unavailable_and_rejects_missing_jobs():
    inventory = pd.DataFrame({"factor": [f"f{i:03d}" for i in range(765)], "research_usable": True})
    series = {
        factor: pd.Series(dtype=float, index=pd.DatetimeIndex([])) for factor in inventory.factor
    }
    calendar = pd.bdate_range("2020-01-02", periods=100)
    series["f000"] = pd.Series(0.01, index=calendar[:79:2])
    result = primary_fdr(inventory, series, calendar)
    assert len(result) == 765
    assert result.status.eq("unavailable").all()
    assert result.raw_p_value.eq(1).all() and result.fdr_bh_q_value.eq(1).all()
    assert "contiguous" in result.iloc[0].reason
    del series["f001"]
    with pytest.raises(ValueError, match="all 765"):
        primary_fdr(inventory, series, calendar)


def test_quality_audit_is_feature_only_and_clips_recent_rows(tmp_path):
    path = tmp_path / "values.parquet"
    pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2023-12-28", "2023-12-29", "2024-01-02"]),
            "instrument": "SH600000",
            "x": [1.0, np.nan, 999.0],
        }
    ).to_parquet(path)
    partitions = pd.DataFrame(
        [
            {
                "factors": "x",
                "partition_path": str(path),
                "partition_id": "p",
                "segment_id": "s",
                "effective_start": "2023-01-01",
                "effective_end": "2026-06-09",
            }
        ]
    )
    inventory = pd.DataFrame({"factor": ["x"], "research_usable": [True]})
    result = audit_feature_quality(
        partitions, inventory, pd.to_datetime(["2023-12-28", "2023-12-29"]), tmp_path / "out"
    )
    assert result.iloc[0].rows == 2 and result.iloc[0].finite_count == 1
    assert result.iloc[0].coverage == 0.5
    assert result.iloc[0].first_finite_date == pd.Timestamp("2023-12-28")
    assert result.iloc[0].last_finite_date == pd.Timestamp("2023-12-28")


def test_native_two_worker_results_match_sequential(native):
    from concurrent.futures import ThreadPoolExecutor

    data = pd.DataFrame(
        {
            "datetime": pd.Timestamp("2021-01-04"),
            "instrument": [f"SH{i:06d}" for i in range(100)],
            "x": np.arange(100.0),
            LABEL: np.sin(np.arange(100.0)),
        }
    )
    ic, quantiles, _ = common_samples(data, "x")
    expected, receipt = native_primary_smoke(ic, quantiles, native, atol=1e-12)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(native_primary_smoke, ic, quantiles, native, atol=1e-12) for _ in range(2)
        ]
        for future in futures:
            actual, actual_receipt = future.result()
            assert actual_receipt == receipt
            for key, value in expected.items():
                if isinstance(value, pd.Series):
                    pd.testing.assert_series_equal(value, actual[key], check_exact=True)
                else:
                    pd.testing.assert_frame_equal(value, actual[key], check_exact=True)


def test_price_cache_identity_hit_corruption_and_source_change(tmp_path):
    pytest.importorskip("qlib")
    provider = tmp_path / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text("2023-01-03\n2023-01-04\n")
    source = provider / "features/sh600000/close.day.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"first price source")
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2023-01-03", "2023-01-04"]),
            "instrument": "SH600000",
            "$close": [1.0, 2.0],
        }
    )
    calls = []

    def loader(symbols, left, right):
        calls.append((symbols, left, right))
        return frame

    args = (provider, ["SH600000"], "2023-01-03", "2023-01-04", tmp_path / "cache", loader)
    first, status = bounded_price_cache(*args)
    assert status == "miss"
    second, status = bounded_price_cache(*args)
    assert status == "hit" and len(calls) == 1
    pd.testing.assert_frame_equal(first, second)
    cached = next((tmp_path / "cache").glob("*.parquet"))
    frame.assign(**{"$close": [99.0, 100.0]}).to_parquet(cached, index=False)
    with pytest.raises(ValueError, match="corrupted"):
        bounded_price_cache(*args)
    source.write_bytes(b"new price source")
    assert bounded_price_cache(*args)[1] == "miss"
    assert len(calls) == 2
