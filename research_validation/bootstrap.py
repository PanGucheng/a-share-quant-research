from __future__ import annotations

import numpy as np
import pandas as pd


def moving_block_mean_test(series: pd.Series, *, samples: int, block_length: int, seed: int) -> dict[str, float | int]:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if len(values) < max(20, block_length * 2):
        raise ValueError("insufficient observations for block bootstrap")
    if samples <= 0 or block_length <= 0 or block_length > len(values):
        raise ValueError("invalid bootstrap samples or block length")
    observed = float(values.mean())
    centered = values - observed
    rng = np.random.default_rng(seed)
    block_starts = np.arange(0, len(values) - block_length + 1)
    block_count = int(np.ceil(len(values) / block_length))
    means = np.empty(samples, dtype=float)
    for index in range(samples):
        starts = rng.choice(block_starts, size=block_count, replace=True)
        draw = np.concatenate([centered[start : start + block_length] for start in starts])[: len(values)]
        means[index] = draw.mean()
    p_value = float((1 + np.sum(np.abs(means) >= abs(observed))) / (samples + 1))
    return {
        "raw_statistic": observed,
        "bootstrap_standard_error": float(means.std(ddof=1)),
        "raw_p_value": p_value,
        "bootstrap_samples": samples,
        "block_length": block_length,
        "random_seed": seed,
        "observation_count": len(values),
    }
