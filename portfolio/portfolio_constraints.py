from __future__ import annotations

import math


def round_lot(shares: float, lot_size: int) -> int:
    if shares <= 0:
        return 0
    return int(math.floor(shares / lot_size) * lot_size)
