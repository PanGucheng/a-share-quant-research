from __future__ import annotations

import pandas as pd


def build_synthetic_frames(
    calendar: pd.DatetimeIndex,
    instruments: list[str],
    *,
    profile_name: str = "synthetic",
    research_run_family_id: str = "qlib_exchange_v1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(calendar) < 2:
        raise ValueError("synthetic execution needs at least two trading days")
    if len(instruments) < 3:
        raise ValueError("synthetic execution needs at least three instruments")
    market_rows: list[dict[str, object]] = []
    signal_rows: list[dict[str, object]] = []
    for day_index, date in enumerate(calendar):
        for instrument_index, instrument in enumerate(instruments):
            price = 10.0 + instrument_index
            market_rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": price,
                    "close": price,
                    "volume": 1_000_000.0,
                    "amount": price * 1_000_000.0,
                    "can_buy": True,
                    "can_sell": True,
                    "limit_up": False,
                    "limit_down": False,
                    "suspended": False,
                    "factor": 1.0,
                    "change": 0.0,
                    "execution_price": price,
                }
            )
            if day_index < len(calendar) - 1:
                rotating_rank = (instrument_index - day_index) % len(instruments)
                signal_rows.append(
                    {
                        "datetime": date,
                        "instrument": instrument,
                        "score": float(len(instruments) - rotating_rank),
                        "method": "synthetic_rotating_rank",
                        "signal_artifact_id": "signal:qlib-exchange-synthetic-v1",
                        "profile_name": profile_name,
                        "profile_type": "smoke",
                        "research_run_family_id": research_run_family_id,
                    }
                )
    return pd.DataFrame(signal_rows), pd.DataFrame(market_rows)
