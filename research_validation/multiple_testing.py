from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests


def apply_fdr(frame: pd.DataFrame, alpha: float) -> pd.DataFrame:
    required = {"factor", "test_family", "metric", "raw_p_value"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing FDR columns: {sorted(missing)}")
    result = frame.copy(deep=True)
    result["fdr_bh_q_value"] = np.nan
    result["fdr_by_q_value"] = np.nan
    result["fdr_bh_pass"] = False
    result["fdr_by_pass"] = False
    for _, index in result.groupby("test_family", sort=False).groups.items():
        valid_index = result.loc[index].index[result.loc[index, "raw_p_value"].notna()]
        if len(valid_index) == 0:
            continue
        pvalues = result.loc[valid_index, "raw_p_value"].astype(float).to_numpy()
        bh_pass, bh_q, _, _ = multipletests(pvalues, alpha=alpha, method="fdr_bh")
        by_pass, by_q, _, _ = multipletests(pvalues, alpha=alpha, method="fdr_by")
        result.loc[valid_index, "fdr_bh_q_value"] = bh_q
        result.loc[valid_index, "fdr_by_q_value"] = by_q
        result.loc[valid_index, "fdr_bh_pass"] = bh_pass
        result.loc[valid_index, "fdr_by_pass"] = by_pass
    return result
