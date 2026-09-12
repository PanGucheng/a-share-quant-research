"""E2 limited quote diagnostics. No score/label reader, Qlib init or strategy runner."""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct

import numpy as np
import pandas as pd

from .market_semantics import convert_community_market_units

INSTRUMENTS = ("sh600000", "sz000001", "sz300001", "sh688001")
FIELDS = ("open", "high", "low", "close", "volume", "amount", "factor")
WINDOWS = (
    ("2015-01-05", "2015-02-13"),
    ("2015-07-01", "2015-08-10"),
    ("2020-07-20", "2020-08-25"),
    ("2022-04-01", "2022-05-06"),
    ("2023-08-01", "2023-08-29"),
    ("2023-12-01", "2023-12-29"),
)


class QuoteSliceReader:
    """Read only individually approved float32 byte offsets, never a full series.

    Calendar text is metadata; read up to development cutoff and do not parse later
    rows. Native field file headers hold calendar offsets, not market values.
    The logged hash covers approved bytes only, not the 2024+ parent file.
    """

    instruments = INSTRUMENTS
    fields = FIELDS
    windows = WINDOWS

    def __init__(self, provider):
        self.provider = Path(provider).resolve()
        self.audit = []
        self.calendar = []
        path = self.provider / "calendars/day.txt"
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                date = line.strip()
                if date > "2023-12-29":
                    break
                if date:
                    self.calendar.append(date)
        if len(self.calendar) != len(set(self.calendar)) or self.calendar != sorted(self.calendar):
            raise ValueError("provider calendar metadata integrity")
        self.offsets = {d: i for i, d in enumerate(self.calendar)}
        self.approved = tuple(d for d in self.calendar if any(a <= d <= b for a, b in self.windows))

    def read(self, stock, field, dates):
        dates = tuple(dates)
        if (
            stock not in self.instruments
            or field not in self.fields
            or not dates
            or not set(dates).issubset(self.approved)
        ):
            raise ValueError("E2 date/column/instrument access denied before file open")
        path = (self.provider / "features" / stock / f"{field}.day.bin").resolve()
        if not path.is_relative_to(self.provider):
            raise ValueError("provider path escape")
        event = dict(
            role="E2_quote_quality_only",
            instrument=stock,
            field=field,
            dates=list(dates),
            path=str(path),
            requested=True,
            completed=False,
            whole_parent_hash=False,
        )
        self.audit.append(event)
        if not path.exists():
            event.update(completed=True, missing_file=True)
            return pd.Series(np.nan, index=dates, dtype=float)
        h = hashlib.sha256()
        values = []
        with path.open("rb") as stream:
            header = stream.read(4)
            if len(header) != 4:
                raise ValueError("invalid binary header")
            first = struct.unpack("<f", header)[0]
            if not np.isfinite(first) or first < 0 or int(first) != first:
                raise ValueError("invalid binary calendar offset")
            h.update(header)
            for date in dates:
                offset = self.offsets[date] - int(first)
                if offset < 0:
                    values.append(np.nan)
                    h.update(date.encode() + b":before_file_start")
                    continue
                stream.seek(4 * (offset + 1))
                raw = stream.read(4)
                h.update(date.encode() + raw)
                values.append(struct.unpack("<f", raw)[0] if len(raw) == 4 else np.nan)
        event.update(
            completed=True,
            header_calendar_offset=int(first),
            approved_bytes_sha256=h.hexdigest(),
            returned_rows=len(values),
        )
        return pd.Series(values, index=dates, dtype=float)


def inspect_quotes(reader):
    rows = []
    for stock in INSTRUMENTS:
        fields = {name: reader.read(stock, name, reader.approved) for name in FIELDS}
        f = pd.DataFrame(fields)
        factor = f["factor"].where(f["factor"].gt(0))
        raw = {name: f[name] / factor for name in ("open", "high", "low", "close")}
        volume, amount = convert_community_market_units(
            f.volume,
            factor,
            f.amount,
            volume_lot_to_shares_multiplier=100,
            amount_to_cny_multiplier=1000,
        )
        avg = amount / volume.where(volume.gt(0))
        for a, b in WINDOWS:
            idx = f.index[(f.index >= a) & (f.index <= b)]
            valid = (
                np.isfinite(raw["open"].loc[idx])
                & np.isfinite(avg.loc[idx])
                & np.isfinite(raw["low"].loc[idx])
                & np.isfinite(raw["high"].loc[idx])
            )
            good = (avg.loc[idx] >= raw["low"].loc[idx] * (1 - 0.002)) & (
                avg.loc[idx] <= raw["high"].loc[idx] * (1 + 0.002)
            )
            order = (raw["high"].loc[idx] >= raw["low"].loc[idx]) & raw["open"].loc[idx].between(
                raw["low"].loc[idx] - 0.001, raw["high"].loc[idx] + 0.001
            )
            rows.append(
                dict(
                    instrument=stock,
                    window_start=a,
                    window_end=b,
                    scheduled=len(idx),
                    finite_open=int(np.isfinite(raw["open"].loc[idx]).sum()),
                    positive_factor=int(factor.loc[idx].notna().sum()),
                    zero_volume=int(volume.loc[idx].eq(0).sum()),
                    missing_volume=int(volume.loc[idx].isna().sum()),
                    unit_check_pairs=int(valid.sum()),
                    amount_volume_inside_ohlc=int((good & valid).sum()),
                    ohlc_order_pass=int((order & valid).sum()),
                    interpretation="small non-random quote-unit canary; no PIT, auction, lifecycle or nine-year certification",
                )
            )
    return pd.DataFrame(rows)


def synthetic_feasibility():
    """Uniform-price thought experiments; no real universe/return or price selection."""
    rows = []
    for cash in (1_000_000, 5_000_000, 10_000_000):
        for count in (200, 2000):
            for price in (5.0, 20.0, 100.0, 500.0):
                budget = 0.95 * cash / count
                # Flat synthetic price, 100-share lots; before implicit costs.
                amount = np.floor(max(0, budget - 5) / price / 100) * 100
                while (
                    amount
                    and amount * price + max(5, amount * price * 0.0003) + amount * price * 0.00001
                    > budget
                ):
                    amount -= 100
                fees = max(5, amount * price * 0.0003) + amount * price * 0.00001 if amount else 0
                capacity_limited = min(
                    amount, 200.0
                )  # one fixed synthetic ADV20=20,000 shares, 1% cap
                rows.append(
                    dict(
                        aum_cny=cash,
                        members=count,
                        synthetic_uniform_price_cny=price,
                        per_name_budget_cny=budget,
                        lot_rounded_shares=amount,
                        unbuildable_names=count if amount == 0 else 0,
                        initial_commission_cny=count * max(5, amount * price * 0.0003)
                        if amount
                        else 0,
                        lot_fee_idle_fraction=1 - count * (amount * price + fees) / cash,
                        capacity_limited_shares=capacity_limited,
                        adv20_synthetic_shares=20000.0,
                        classification="synthetic feasibility only; not benchmark path, return, NAV or capacity estimate",
                    )
                )
    return pd.DataFrame(rows)
