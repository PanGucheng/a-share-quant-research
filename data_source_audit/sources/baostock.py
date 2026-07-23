from __future__ import annotations

import pandas as pd


FIELDS = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,tradestatus,isST"


def library_version() -> str:
    try:
        from importlib.metadata import version

        return version("baostock")
    except Exception:
        return "unavailable"


def collect_one(instrument: str, start_date: str, end_date: str) -> tuple[pd.DataFrame, str]:
    import baostock as bs

    code = instrument[:2].lower() + "." + instrument[-6:]
    result = bs.query_history_k_data_plus(
        code,
        FIELDS,
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3",
    )
    rows = []
    while result.error_code == "0" and result.next():
        rows.append(result.get_row_data())
    return pd.DataFrame(rows, columns=result.fields or FIELDS.split(",")), (
        "success" if result.error_code == "0" else f"{result.error_code}:{result.error_msg}"
    )
