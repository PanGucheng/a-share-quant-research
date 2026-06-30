# Data Field Validation

This document records the first lightweight field sanity checks for the community qlib provider.

Provider:

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609
```

## Sample

Sample instruments:

```text
SH600000
SZ000001
SH600519
```

Sample dates:

```text
2020-01-02 to 2020-01-10
```

Fields:

```text
close
volume
amount
vwap
factor
adjclose
```

## Command

```powershell
E:\anaconda_envs\qlib_env\python.exe -c 'import qlib, pandas as pd, numpy as np; from qlib.config import C; from qlib.data import D; qlib.init(provider_uri=r"E:/qlib_prj/qlib_data/cn_data_community_20260609", region="cn"); C.kernels=1; C.joblib_backend="sequential"; instruments=["SH600000","SZ000001","SH600519"]; fields=["$close","$volume","$amount","$vwap","$factor","$adjclose"]; df=D.features(instruments, fields, start_time="2020-01-02", end_time="2020-01-10").dropna(how="all"); df["amount_div_volume"] = df["$amount"] / df["$volume"]; df["vwap_div_amount_per_volume"] = df["$vwap"] / df["amount_div_volume"]; df["adjclose_div_close"] = df["$adjclose"] / df["$close"]; df["close_div_factor"] = df["$close"] / df["$factor"]; print(df[["$close","$volume","$amount","$vwap","amount_div_volume","vwap_div_amount_per_volume","$factor","$adjclose","adjclose_div_close","close_div_factor"]].groupby(level=0).mean().to_string())'
```

## Observed Means

| instrument | close | amount / volume | vwap / (amount / volume) | factor | adjclose / close |
| --- | ---: | ---: | ---: | ---: | ---: |
| SH600000 | `6.188167` | `0.619883` | `10.0` | `0.497270` | `25.569998` |
| SH600519 | `226.001816` | `22.618824` | `10.0` | `0.205873` | `35.549999` |
| SZ000001 | `4.660958` | `0.465990` | `10.0` | `0.275540` | `396.199982` |

## Initial Interpretation

- `amount`, `volume`, and `vwap` are internally consistent under a stable scale factor: `vwap = amount / volume * 10` in this sample.
- This suggests the fields are usable, but the units are not yet fully documented.
- `adjclose` is not simply `close / factor` in this sample. Its semantics need to be checked against the upstream data-source documentation or known corporate-action examples.
- For Alpha158 and the current LightGBM baseline, this does not block the second-step comparison because the workflow mostly relies on qlib's existing handler features.

## Follow-up Checks

- Confirm `amount` and `volume` units from upstream documentation or raw source tables.
- Verify `factor` and `adjclose` around known split/dividend events.
- Decide whether later custom factors should use `close`, `adjclose`, or qlib adjusted expressions.
- Add automated checks for `abs(vwap - amount / volume * 10)` once units are confirmed.
