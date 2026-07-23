from __future__ import annotations

import pandas as pd


def library_version() -> str:
    try:
        import akshare

        return str(akshare.__version__)
    except Exception:
        return "unavailable"


def collect_one(instrument: str, start_date: str, end_date: str) -> pd.DataFrame:
    import akshare as ak

    return ak.stock_zh_a_hist(
        symbol=instrument[-6:],
        period="daily",
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
        adjust="",
    )
