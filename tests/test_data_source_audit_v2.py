from __future__ import annotations

import pandas as pd

from data_source_audit.alignment import compare_pair
from data_source_audit.normalizers import (
    normalize_akshare,
    normalize_baostock,
    normalize_community,
)


def test_provider_unit_normalization_fixture() -> None:
    community = pd.DataFrame(
        [
            {
                "instrument": "SZ000001",
                "date": "2025-01-02",
                "$open": 3.783203,
                "$high": 3.796104,
                "$low": 3.673545,
                "$close": 3.686446,
                "$volume": 5641746.0,
                "$amount": 2102923.07811,
                "$factor": 0.3225237,
            }
        ]
    )
    normalized = normalize_community(community).iloc[0]
    assert abs(normalized["price_raw_open"] - 11.73) < 1e-3
    assert abs(normalized["volume_shares"] - 181_959_699) < 100
    assert abs(normalized["amount_cny"] - 2_102_923_078.11) < 1


def test_baostock_and_akshare_volume_units_align() -> None:
    bao = normalize_baostock(
        pd.DataFrame(
            [
                {
                    "date": "2025-01-02",
                    "code": "sz.000001",
                    "open": "11.73",
                    "high": "11.77",
                    "low": "11.39",
                    "close": "11.43",
                    "preclose": "11.70",
                    "volume": "181959699",
                    "amount": "2102923078.11",
                    "tradestatus": "1",
                    "isST": "0",
                }
            ]
        )
    )
    ak = normalize_akshare(
        pd.DataFrame(
            [
                {
                    "日期": "2025-01-02",
                    "股票代码": "000001",
                    "开盘": 11.73,
                    "最高": 11.77,
                    "最低": 11.39,
                    "收盘": 11.43,
                    "成交量": 1819597,
                    "成交额": 2102923078.11,
                }
            ]
        )
    )
    summary, differences = compare_pair(bao, ak)
    assert summary["close_tolerance_match_rate"] == 1.0
    assert summary["volume_tolerance_match_rate"] > 0.999
    assert differences.empty
