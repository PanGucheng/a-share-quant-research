"""Validation script for liquidity residualization module (V3.39).

Self-contained assert-style validation functions using tiny synthetic pandas
frames.  Covers the hardening scenarios required by the plan:

1. residualize_daily drops a constant proxy and still residualizes
2. residualize_daily returns all NaN when proxies are missing / constant
   or samples are below min_count
3. build_residualized_factor_frame preserves row-to-residual alignment
   with intentionally unsorted input
4. compute_daily_diagnostics R^2 is bounded 0.9-1.01 for a synthetic
   near-perfect linear predictor
5. merge_tradability brings liquidity_value from a temporary
   tradability_labels.csv
6. build_residualized_factor_frame routes a constant-proxy scenario
   end-to-end (integration test)
7. partial-NaN proxy: scattered NaNs on one proxy yield NaN residuals
   for incomplete rows while complete rows produce valid residuals
8. build_residualized_factor_frame guards raise ValueError when
   residualize_daily returns mismatched length or index
9. merge_tradability normalises factor-frame datetimes that carry a
   time-of-day component against date-only tradability labels

Usage::

    E:/anaconda_envs/qlib_env/python.exe scripts/validate_liquidity_residualized_factor_evaluation_v1.py
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.liquidity_residualization import (  # noqa: E402
    DEFAULT_MIN_COUNT,
    DEFAULT_PROXIES,
    DEFAULT_SUFFIX,
    build_residualized_factor_frame,
    compute_daily_diagnostics,
    merge_tradability,
    residualize_daily,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _make_two_date_frame(n_per_day: int = 80) -> pd.DataFrame:
    """Return a frame with two trading days and *n_per_day* instruments each.

    Columns: datetime, instrument, f_raw, proxy_var, proxy_const.
    The frame is indexed by datetime for direct residualize_daily calls.
    """
    np.random.seed(42)
    dates = [pd.Timestamp("2021-01-04")] * n_per_day + [pd.Timestamp("2021-01-05")] * n_per_day
    instruments = [f"SH600{i:03d}" for i in range(n_per_day)] * 2
    f_raw = np.random.randn(2 * n_per_day).astype(float)
    proxy_var = np.random.randn(2 * n_per_day).astype(float) * 2.0 + 5.0  # non-constant
    proxy_const = np.full(2 * n_per_day, 3.0, dtype=float)  # constant
    return pd.DataFrame({
        "datetime": dates,
        "instrument": instruments,
        "f_raw": f_raw,
        "proxy_var": proxy_var,
        "proxy_const": proxy_const,
    }).set_index("datetime")


# ---------------------------------------------------------------------------
# 1. constant-proxy drop
# ---------------------------------------------------------------------------
def test_residualize_daily_drops_constant_proxy() -> None:
    """A constant proxy is dropped and residualization uses only the
    non-constant proxy, producing valid residuals."""
    frame = _make_two_date_frame(80)
    resid = residualize_daily(
        frame,
        factor="f_raw",
        proxies=["proxy_const", "proxy_var"],
        min_count=30,
        suffix=DEFAULT_SUFFIX,
    )
    # We expect non-NaN values on both days because proxy_var is non-constant
    # and we have 80 > 30 observations.
    if resid.notna().sum() == 0:
        raise ValueError(
            "residualize_daily returned all-NaN when one non-constant proxy exists"
        )
    # The residual should have the same index length as the input frame
    if len(resid) != len(frame):
        raise ValueError(
            f"residual series length {len(resid)} != frame length {len(frame)}"
        )
    print("  PASS: test_residualize_daily_drops_constant_proxy")


# ---------------------------------------------------------------------------
# 2. all-NaN returns
# ---------------------------------------------------------------------------
def test_residualize_daily_all_nan_when_every_proxy_constant() -> None:
    """All proxies constant -> all-NaN residual series."""
    frame = _make_two_date_frame(80)
    # Overwrite proxy_var to also be constant
    frame["proxy_var"] = 7.0
    resid = residualize_daily(
        frame,
        factor="f_raw",
        proxies=["proxy_const", "proxy_var"],
        min_count=30,
        suffix=DEFAULT_SUFFIX,
    )
    if resid.notna().any():
        raise ValueError(
            "Expected all-NaN when every proxy is constant, "
            f"got {resid.notna().sum()} non-NaN values"
        )
    print("  PASS: test_residualize_daily_all_nan_when_every_proxy_constant")


def test_residualize_daily_all_nan_when_no_proxy_in_frame() -> None:
    """No requested proxy column exists in the frame -> all-NaN."""
    frame = _make_two_date_frame(80)
    resid = residualize_daily(
        frame,
        factor="f_raw",
        proxies=["nonexistent_proxy_a", "nonexistent_proxy_b"],
        min_count=30,
        suffix=DEFAULT_SUFFIX,
    )
    if resid.notna().any():
        raise ValueError(
            "Expected all-NaN when no proxy columns exist in frame, "
            f"got {resid.notna().sum()} non-NaN values"
        )
    print("  PASS: test_residualize_daily_all_nan_when_no_proxy_in_frame")


def test_residualize_daily_all_nan_below_min_count() -> None:
    """Fewer valid rows than min_count -> all-NaN for that day."""
    n = 40  # < DEFAULT_MIN_COUNT=50
    np.random.seed(42)
    dates = [pd.Timestamp("2021-01-04")] * n
    instruments = [f"SH600{i:03d}" for i in range(n)]
    f_raw = np.random.randn(n).astype(float)
    proxy_var = np.random.randn(n).astype(float)
    frame = pd.DataFrame({
        "datetime": dates,
        "instrument": instruments,
        "f_raw": f_raw,
        "proxy_var": proxy_var,
    }).set_index("datetime")

    resid = residualize_daily(
        frame,
        factor="f_raw",
        proxies=["proxy_var"],
        min_count=50,  # higher than n=40
        suffix=DEFAULT_SUFFIX,
    )
    if resid.notna().any():
        raise ValueError(
            f"Expected all-NaN when n={n} < min_count=50, "
            f"got {resid.notna().sum()} non-NaN values"
        )
    print("  PASS: test_residualize_daily_all_nan_below_min_count")


# ---------------------------------------------------------------------------
# 3. row-to-residual alignment with unsorted input
# ---------------------------------------------------------------------------
def test_build_residualized_factor_frame_alignment_unsorted() -> None:
    """When input rows are unsorted by datetime/instrument the residual
    column must still align row-by-row with the correct factor value.

    We construct data where factor is an exact linear function of a single
    proxy (factor = 2.0 * proxy).  After residualization the residuals
    should be near zero for every row.  If positional assignment silently
    misaligns, many rows will carry a residual from a different instrument
    or date, producing large non-zero values.
    """
    np.random.seed(42)
    n = 120
    proxy_a = np.random.randn(n).astype(float) * 3.0 + 10.0
    factor_a = 2.0 * proxy_a  # exact linear, no noise

    # Build frame sorted by instrument (reverse alpha), then by datetime
    # descending - intentionally far from datetime-ascending order.
    dates = (
        [pd.Timestamp("2021-01-05")] * 40
        + [pd.Timestamp("2021-01-04")] * 40
        + [pd.Timestamp("2021-01-05")] * 20
        + [pd.Timestamp("2021-01-04")] * 20
    )
    instruments = sorted(
        [f"SH600{i:03d}" for i in range(n)], reverse=True
    )
    frame = pd.DataFrame({
        "datetime": pd.to_datetime(dates),
        "instrument": instruments,
        "factor_a": factor_a,
        "proxy_a": proxy_a,
    })
    # Verify the frame is NOT sorted by datetime
    dt_vals = frame["datetime"].values
    if all(dt_vals[i] <= dt_vals[i + 1] for i in range(len(dt_vals) - 1)):
        raise ValueError("Test precondition failed: frame should be unsorted by datetime")

    result = build_residualized_factor_frame(
        frame,
        factors=["factor_a"],
        proxies=["proxy_a"],
        min_count=20,
        suffix=DEFAULT_SUFFIX,
    )
    resid_col = f"factor_a{DEFAULT_SUFFIX}"
    if resid_col not in result.columns:
        raise ValueError(f"Residual column '{resid_col}' not produced")

    # Residuals should be near zero for every valid row (factor = 2*proxy,
    # z-scored factor is approximately z-scored proxy, OLS residual is approximately 0).
    valid_mask = result[resid_col].notna()
    if valid_mask.sum() == 0:
        raise ValueError("All residual values are NaN - residualization failed")
    abs_resid = result.loc[valid_mask, resid_col].abs()
    mean_abs = float(abs_resid.mean())
    max_abs = float(abs_resid.max())
    # With exact linear relationship, z-score preserves it, so residuals
    # are tiny (floating-point noise only).  Allow a generous tolerance
    # while still catching gross misalignment.
    if mean_abs > 1e-3 or max_abs > 1e-2:
        raise ValueError(
            f"Residuals too large for exact linear factor=2*proxy: "
            f"mean_abs={mean_abs:.6f} max_abs={max_abs:.6f}. "
            f"Positional misalignment suspected."
        )

    # Also verify that factor NaN rows have NaN residuals.
    # Because build_residualized_factor_frame re-sorts by datetime, we must
    # find the NaN-factor row by value, not by original integer position.
    frame2 = frame.copy()
    nan_instrument = "SH600999"  # unique key to locate the NaN row after sorting
    frame2.loc[0, "instrument"] = nan_instrument
    frame2.loc[0, "factor_a"] = np.nan
    result2 = build_residualized_factor_frame(
        frame2,
        factors=["factor_a"],
        proxies=["proxy_a"],
        min_count=20,
        suffix=DEFAULT_SUFFIX,
    )
    nan_rows = result2[result2["instrument"] == nan_instrument]
    if nan_rows.empty:
        raise ValueError("Could not locate NaN-factor row by instrument key")
    nan_residual = nan_rows.iloc[0][resid_col]
    if not pd.isna(nan_residual):
        raise ValueError(
            f"Row with NaN factor should produce NaN residual, got {nan_residual}"
        )

    print("  PASS: test_build_residualized_factor_frame_alignment_unsorted")


# ---------------------------------------------------------------------------
# 4. compute_daily_diagnostics R^2 bounded
# ---------------------------------------------------------------------------
def test_compute_daily_diagnostics_r2_bounded() -> None:
    """For a synthetic factor that is nearly perfectly explained by a proxy
    (factor = proxy + tiny noise), the computed R^2 in z-score space must
    be high and bounded between 0.9 and 1.01."""
    np.random.seed(42)
    n_per_day = 150
    dates = (
        [pd.Timestamp("2021-01-04")] * n_per_day
        + [pd.Timestamp("2021-01-05")] * n_per_day
    )
    instruments = [f"SH600{i:03d}" for i in range(n_per_day)] * 2
    proxy_raw = np.random.randn(2 * n_per_day).astype(float) * 2.0 + 5.0
    # Factor = proxy + tiny noise (0.1% of proxy std)
    noise = np.random.randn(2 * n_per_day).astype(float) * 0.002
    factor_raw = proxy_raw + noise

    frame = pd.DataFrame({
        "datetime": pd.to_datetime(dates),
        "instrument": instruments,
        "factor_raw": factor_raw,
        "proxy_raw": proxy_raw,
    })

    # Build residualized frame
    result = build_residualized_factor_frame(
        frame,
        factors=["factor_raw"],
        proxies=["proxy_raw"],
        min_count=30,
        suffix=DEFAULT_SUFFIX,
    )

    diag = compute_daily_diagnostics(
        result,
        factors=["factor_raw"],
        proxies=["proxy_raw"],
        suffix=DEFAULT_SUFFIX,
    )
    if diag.empty:
        raise ValueError("compute_daily_diagnostics returned empty DataFrame")

    r2_values = diag["r2_approx"].dropna()
    if len(r2_values) == 0:
        raise ValueError("No R^2 values computed")

    for r2 in r2_values:
        if not (0.90 <= r2 <= 1.01):
            raise ValueError(
                f"R^2={r2:.6f} outside expected bounds [0.90, 1.01]. "
                f"Factor=proxy+tiny_noise should yield near-perfect R^2."
            )

    print(f"  PASS: test_compute_daily_diagnostics_r2_bounded  (R^2 values: {list(r2_values)})")


# ---------------------------------------------------------------------------
# 5. merge_tradability brings liquidity_value
# ---------------------------------------------------------------------------
def test_merge_tradability_brings_liquidity_value() -> None:
    """merge_tradability must load liquidity_value from tradability_labels.csv
    because the global load_tradability_labels does not return it.

    We create a temporary tradability_labels.csv with liquidity_value present
    and verify it appears in the merged frame.
    """
    np.random.seed(42)
    n = 60
    dates = [pd.Timestamp("2021-01-04")] * n
    instruments = [f"SH600{i:03d}" for i in range(n)]
    frame = pd.DataFrame({
        "datetime": pd.to_datetime(dates),
        "instrument": instruments,
        "factor_a": np.random.randn(n).astype(float),
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        tradability_dir = Path(tmpdir)

        # Build a tradability_labels.csv with the columns load_tradability_labels
        # requires (datetime, instrument, can_buy, liquidity_bucket, tradability_score)
        # plus liquidity_value which merge_tradability loads separately.
        labels_df = pd.DataFrame({
            "datetime": pd.to_datetime(dates),
            "instrument": instruments,
            "can_buy": True,
            "liquidity_bucket": np.random.randint(1, 6, n),
            "tradability_score": np.random.randint(60, 100, n).astype(float),
            "liquidity_value": np.random.randn(n).astype(float) * 1000.0 + 5000.0,
            "can_sell": True,
            "data_quality_status": "ok",
            "has_core_missing": False,
            "disabled_reason": "",
        })
        labels_df.to_csv(tradability_dir / "tradability_labels.csv", index=False)

        merged = merge_tradability(frame, tradability_dir)

        if "liquidity_value" not in merged.columns:
            raise ValueError(
                "merge_tradability did not produce 'liquidity_value' column"
            )
        lv = merged["liquidity_value"]
        if lv.isna().all():
            raise ValueError("liquidity_value column is all-NaN after merge")
        if lv.notna().sum() < n:
            raise ValueError(
                f"Only {lv.notna().sum()}/{n} liquidity_value values non-NaN "
                f"after merge"
            )

    print("  PASS: test_merge_tradability_brings_liquidity_value")


# ---------------------------------------------------------------------------
# 6. build_residualized_factor_frame constant-proxy integration
# ---------------------------------------------------------------------------
def test_build_residualized_factor_frame_with_constant_proxy() -> None:
    """Route a constant-proxy scenario through build_residualized_factor_frame
    (not just residualize_daily) and verify non-NaN residuals are produced
    because the non-constant proxy is retained."""
    np.random.seed(42)
    n_per_day = 80
    dates = (
        [pd.Timestamp("2021-01-04")] * n_per_day
        + [pd.Timestamp("2021-01-05")] * n_per_day
    )
    instruments = [f"SH600{i:03d}" for i in range(n_per_day)] * 2
    f_raw = np.random.randn(2 * n_per_day).astype(float)
    proxy_var = np.random.randn(2 * n_per_day).astype(float) * 2.0 + 5.0
    proxy_const = np.full(2 * n_per_day, 3.0, dtype=float)

    frame = pd.DataFrame({
        "datetime": pd.to_datetime(dates),
        "instrument": instruments,
        "f_raw": f_raw,
        "proxy_var": proxy_var,
        "proxy_const": proxy_const,
    })

    result = build_residualized_factor_frame(
        frame,
        factors=["f_raw"],
        proxies=["proxy_const", "proxy_var"],
        min_count=30,
        suffix=DEFAULT_SUFFIX,
    )

    resid_col = f"f_raw{DEFAULT_SUFFIX}"
    if resid_col not in result.columns:
        raise ValueError(f"Residual column '{resid_col}' not produced")
    valid_count = int(result[resid_col].notna().sum())
    if valid_count == 0:
        raise ValueError(
            "build_residualized_factor_frame returned all-NaN residuals "
            "when one non-constant proxy exists"
        )
    # Most rows should be valid since proxy_var is non-constant on both days
    total = len(result)
    if valid_count < total * 0.5:
        raise ValueError(
            f"Only {valid_count}/{total} residuals non-NaN; "
            f"expected majority to be valid with non-constant proxy"
        )
    print("  PASS: test_build_residualized_factor_frame_with_constant_proxy")


# ---------------------------------------------------------------------------
# 7. partial-NaN proxy
# ---------------------------------------------------------------------------
def test_partial_nan_proxy_residualization() -> None:
    """One proxy has scattered NaNs; another proxy is clean and non-constant.

    Rows where the NaN proxy is missing must produce NaN residuals.
    Rows where both proxies are present and there are at least min_count complete
    rows on that day must produce non-NaN residuals."""
    np.random.seed(42)
    n_per_day = 100
    # Two days: day1 enough complete rows, day2 also enough
    dates = (
        [pd.Timestamp("2021-01-04")] * n_per_day
        + [pd.Timestamp("2021-01-05")] * n_per_day
    )
    instruments = [f"SH600{i:03d}" for i in range(n_per_day)] * 2
    n_total = len(dates)
    f_raw = np.random.randn(n_total).astype(float)
    proxy_clean = np.random.randn(n_total).astype(float) * 2.0 + 5.0
    # proxy_partial: scattered NaNs (~20% of rows)
    proxy_partial = np.random.randn(n_total).astype(float)
    nan_mask = np.random.choice(n_total, size=int(n_total * 0.20), replace=False)
    proxy_partial[nan_mask] = np.nan

    frame = pd.DataFrame({
        "datetime": pd.to_datetime(dates),
        "instrument": instruments,
        "f_raw": f_raw,
        "proxy_clean": proxy_clean,
        "proxy_partial": proxy_partial,
    })

    resid = residualize_daily(
        frame.set_index("datetime"),
        factor="f_raw",
        proxies=["proxy_partial", "proxy_clean"],
        min_count=50,
        suffix=DEFAULT_SUFFIX,
    )

    # Rows where proxy_partial is NaN should have NaN residual
    partial_nan_rows = frame["proxy_partial"].isna()
    resid_nan_for_partial = resid.loc[partial_nan_rows.values]
    if resid_nan_for_partial.notna().any():
        n = resid_nan_for_partial.notna().sum()
        raise ValueError(
            f"Expected NaN residuals for rows with NaN proxy, "
            f"but got {n} non-NaN values"
        )

    # Rows where both proxies are non-NaN should mostly have non-NaN residuals
    # because proxy_clean is non-constant and we have enough complete rows
    complete_rows = frame["proxy_partial"].notna()
    resid_complete = resid.loc[complete_rows.values]
    if resid_complete.notna().sum() == 0:
        raise ValueError(
            "Expected non-NaN residuals for rows with complete proxy data, "
            "but all are NaN"
        )
    # At least 70% of complete rows should have valid residuals
    complete_valid = int(resid_complete.notna().sum())
    complete_total = int(complete_rows.sum())
    if complete_valid < complete_total * 0.7:
        raise ValueError(
            f"Only {complete_valid}/{complete_total} complete rows have "
            f"non-NaN residuals (expected >= 70%)"
        )

    print("  PASS: test_partial_nan_proxy_residualization")


# ---------------------------------------------------------------------------
# 8. build_residualized_factor_frame guard (negative test)
# ---------------------------------------------------------------------------
def test_build_residualized_factor_frame_guard_valueerror() -> None:
    """build_residualized_factor_frame must raise ValueError when
    residualize_daily returns a mismatched-length or mismatched-index Series.

    Uses safe monkeypatching of residualize_daily, restoring the original
    in a finally block."""
    np.random.seed(42)
    n_per_day = 60
    dates = (
        [pd.Timestamp("2021-01-04")] * n_per_day
        + [pd.Timestamp("2021-01-05")] * n_per_day
    )
    instruments = [f"SH600{i:03d}" for i in range(n_per_day)] * 2
    f_raw = np.random.randn(2 * n_per_day).astype(float)
    proxy_var = np.random.randn(2 * n_per_day).astype(float) * 2.0 + 5.0

    frame = pd.DataFrame({
        "datetime": pd.to_datetime(dates),
        "instrument": instruments,
        "f_raw": f_raw,
        "proxy_var": proxy_var,
    })

    import factor_research.liquidity_residualization as lr_mod

    original = lr_mod.residualize_daily

    try:
        # --- test 1: mismatched length ---
        def _bad_length(*args, **kwargs):
            fake_index = pd.DatetimeIndex(
                [pd.Timestamp("2021-01-04")] * (n_per_day - 5)
                + [pd.Timestamp("2021-01-05")] * n_per_day
            )
            return pd.Series(np.zeros(len(fake_index)), index=fake_index, name="f_raw__resid_liquidity")

        lr_mod.residualize_daily = _bad_length

        errored = False
        try:
            build_residualized_factor_frame(
                frame,
                factors=["f_raw"],
                proxies=["proxy_var"],
                min_count=20,
                suffix=DEFAULT_SUFFIX,
            )
        except ValueError as e:
            errored = True
            if "rows but frame has" not in str(e):
                raise AssertionError(
                    f"Expected length-mismatch ValueError, got: {e}"
                )

        if not errored:
            raise AssertionError(
                "build_residualized_factor_frame did not raise ValueError "
                "when residualize_daily returned mismatched length"
            )

        # --- test 2: mismatched index ---
        def _bad_index(*args, **kwargs):
            fake_dates = (
                [pd.Timestamp("2021-01-04")] * n_per_day
                + [pd.Timestamp("2021-01-05")] * n_per_day
            )
            # Swap the order of the two days
            fake_index = pd.DatetimeIndex(
                [pd.Timestamp("2021-01-05")] * n_per_day
                + [pd.Timestamp("2021-01-04")] * n_per_day
            )
            return pd.Series(np.zeros(len(fake_index)), index=fake_index, name="f_raw__resid_liquidity")

        lr_mod.residualize_daily = _bad_index

        errored = False
        try:
            build_residualized_factor_frame(
                frame,
                factors=["f_raw"],
                proxies=["proxy_var"],
                min_count=20,
                suffix=DEFAULT_SUFFIX,
            )
        except ValueError as e:
            errored = True
            if "index differs from frame index" not in str(e):
                raise AssertionError(
                    f"Expected index-mismatch ValueError, got: {e}"
                )

        if not errored:
            raise AssertionError(
                "build_residualized_factor_frame did not raise ValueError "
                "when residualize_daily returned mismatched index"
            )

    finally:
        lr_mod.residualize_daily = original

    print("  PASS: test_build_residualized_factor_frame_guard_valueerror")


# ---------------------------------------------------------------------------
# 9. merge_tradability normalises time-of-day datetimes
# ---------------------------------------------------------------------------
def test_merge_tradability_normalizes_datetime() -> None:
    """Factor-frame datetimes include time-of-day (e.g. 09:30:00) while
    tradability labels are date-only.  merge_tradability must normalize()
    both sides so the merge succeeds."""
    np.random.seed(42)
    n = 60
    # Factor frame with time-of-day datetimes
    frame_dates = [
        pd.Timestamp("2021-01-04 09:30:00"),
        pd.Timestamp("2021-01-04 10:00:00"),
        pd.Timestamp("2021-01-04 14:30:00"),
        pd.Timestamp("2021-01-05 09:31:00"),
    ]
    # Repeat to reach n rows but keep varied times
    dates = []
    for i in range(n):
        dates.append(frame_dates[i % len(frame_dates)])
    instruments = [f"SH600{i:03d}" for i in range(n)]
    frame = pd.DataFrame({
        "datetime": dates,
        "instrument": instruments,
        "factor_a": np.random.randn(n).astype(float),
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        tradability_dir = Path(tmpdir)

        # Labels are date-only (no time component)
        label_dates = [
            pd.Timestamp("2021-01-04"),
            pd.Timestamp("2021-01-05"),
        ]
        # 30 rows per date
        labels_df = pd.DataFrame({
            "datetime": label_dates * (n // 2),
            "instrument": instruments,
            "can_buy": True,
            "liquidity_bucket": np.random.randint(1, 6, n).astype(float),
            "tradability_score": np.random.randint(60, 100, n).astype(float),
            "liquidity_value": np.random.randn(n).astype(float) * 1000.0 + 5000.0,
            "can_sell": True,
            "data_quality_status": "ok",
            "has_core_missing": False,
            "disabled_reason": "",
        })
        labels_df.to_csv(tradability_dir / "tradability_labels.csv", index=False)

        merged = merge_tradability(frame, tradability_dir)

        if "liquidity_value" not in merged.columns:
            raise ValueError(
                "merge_tradability did not produce 'liquidity_value' column"
            )
        lv = merged["liquidity_value"]
        if lv.isna().all():
            raise ValueError(
                "liquidity_value column is all-NaN after merge - "
                "datetime normalisation may have failed"
            )
        if lv.notna().sum() < n * 0.5:
            raise ValueError(
                f"Only {lv.notna().sum()}/{n} liquidity_value values non-NaN "
                f"after merge with time-of-day datetimes"
            )
        # Verify merged datetimes are now date-only
        merged_dts = pd.to_datetime(merged["datetime"])
        for dt in merged_dts:
            if dt.hour != 0 or dt.minute != 0 or dt.second != 0:
                raise ValueError(
                    f"merge_tradability did not normalise datetime to date-only: {dt}"
                )

    print("  PASS: test_merge_tradability_normalizes_datetime")


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
def validate_all() -> None:
    print("=== validate_liquidity_residualized_factor_evaluation_v1 ===")
    test_residualize_daily_drops_constant_proxy()
    test_residualize_daily_all_nan_when_every_proxy_constant()
    test_residualize_daily_all_nan_when_no_proxy_in_frame()
    test_residualize_daily_all_nan_below_min_count()
    test_build_residualized_factor_frame_alignment_unsorted()
    test_compute_daily_diagnostics_r2_bounded()
    test_merge_tradability_brings_liquidity_value()
    test_build_residualized_factor_frame_with_constant_proxy()
    test_partial_nan_proxy_residualization()
    test_build_residualized_factor_frame_guard_valueerror()
    test_merge_tradability_normalizes_datetime()
    print("=== All validations passed ===")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate liquidity residualization module (V3.39)."
    )
    return parser


def main() -> None:
    _args = build_parser().parse_args()
    validate_all()


if __name__ == "__main__":
    main()
