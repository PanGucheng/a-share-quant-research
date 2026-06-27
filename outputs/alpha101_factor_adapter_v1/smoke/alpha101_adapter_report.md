# Alpha101 Adapter Smoke V1

- Source: `E:/qlib_prj/qlib_baseline/tmp/reference_repos/KunQuant`
- Source file: `tests/KunTestUtil/ref_alpha101.py`
- Source module: `KunTestUtil.ref_alpha101.Alphas`
- Source commit: `d4b9e61f729df347730aa921b539b9df3c3fe36d`
- Selected factors: `5`

## Inventory

| factor | registry_name | category | eligible | exclusion_reason | valid_rows | total_rows | coverage | missing_rate | min | max | mean | source_project | source_function | source_commit | license | required_fields |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101_alpha004 | alpha004 | alpha101 | True |  | 83863 | 89000 | 0.942281 | 0.057719 | -9.000000 | -1.000000 | -4.702157 | kunquant_alpha101 | alpha004 | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 | $low |
| kunquant_alpha101_alpha009 | alpha009 | alpha101 | True |  | 87862 | 89000 | 0.987213 | 0.012787 | -30.108887 | 35.817169 | -0.005721 | kunquant_alpha101 | alpha009 | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 | $close |
| kunquant_alpha101_alpha012 | alpha012 | alpha101 | True |  | 87862 | 89000 | 0.987213 | 0.012787 | -30.108887 | 35.817169 | -0.021063 | kunquant_alpha101 | alpha012 | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 | $close,$volume |
| kunquant_alpha101_alpha033 | alpha033 | alpha101 | True |  | 88438 | 89000 | 0.993685 | 0.006315 | 0.002004 | 1.000000 | 0.501006 | kunquant_alpha101 | alpha033 | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 | $close,$open |
| kunquant_alpha101_alpha101 | alpha101 | alpha101 | True |  | 88438 | 89000 | 0.993685 | 0.006315 | -0.999880 | 0.999946 | -0.013780 | kunquant_alpha101 | alpha101 | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 | $close,$high,$low,$open |

## Boundary

- This smoke uses KunQuant's pandas reference implementation.
- Catalog entries are disabled/non-runnable until V4 evaluation and promotion pass.
- Ginkgo_Alpha101 remains a metadata reference because no local formula implementation is available.

## Output Files

- `factor_frame.pkl`
- `alpha101_factor_inventory.csv`
- `alpha101_selected_smoke_factors.csv`
- `alpha101_factor_catalog_smoke.yaml`
- `alpha101_adapter_manifest.json`
- `alpha101_adapter_report.md`
