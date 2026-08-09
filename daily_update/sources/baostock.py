from __future__ import annotations

import time as time_module
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

from data_source_audit.sources.baostock import (
    collect_daily_adjust_factor,
    collect_daily_all,
)


def baostock_release_window_open(target: date, now: datetime | None = None) -> bool:
    """Wait for the documented K-line and adjustment-factor publication window."""

    shanghai = ZoneInfo("Asia/Shanghai")
    current = now.astimezone(shanghai) if now is not None else datetime.now(shanghai)
    return target < current.date() or (
        target == current.date() and current.time() >= time(18, 0)
    )


def collect_baostock_range(start: date, end: date) -> tuple[pd.DataFrame, list[str]]:
    """Use one official batch request per calendar date, not one request per stock."""

    import baostock as bs

    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"BaoStock login failed: {login.error_code}:{login.error_msg}")
    frames: list[pd.DataFrame] = []
    failures: list[str] = []
    try:
        for current in pd.date_range(start, end, freq="D"):
            frame, status = collect_daily_all(current.date().isoformat())
            if status != "success":
                failures.append(f"{current.date().isoformat()}:{status}")
            elif not frame.empty:
                frames.append(frame)
    finally:
        bs.logout()
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), failures


def collect_baostock_factor_once(
    target: date,
    attempts: int = 2,
    retry_delay_seconds: int = 10,
) -> tuple[pd.DataFrame, str]:
    """Low-frequency factor probe; tolerate one transient BaoStock socket error."""

    import baostock as bs

    last_status = "unavailable"
    for attempt in range(max(1, attempts)):
        login = bs.login()
        if login.error_code != "0":
            last_status = f"{login.error_code}:{login.error_msg}"
        else:
            try:
                frame, status = collect_daily_adjust_factor(target.isoformat())
                if status == "success":
                    return frame, status
                last_status = status
            finally:
                bs.logout()
        if attempt + 1 < attempts:
            time_module.sleep(retry_delay_seconds)
    return pd.DataFrame(), last_status
