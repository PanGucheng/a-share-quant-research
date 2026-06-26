# TA Batch Catalogs V1

This report prepares TA factors for resumable batch V4 evaluation.

## Catalog Summary

| catalog | path | factor_count | enabled_count | runnable_count |
| --- | --- | --- | --- | --- |
| source_smoke | E:/qlib_prj/qlib_baseline/outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke.yaml | 79 | 0 | 0 |
| passed_smoke | E:/qlib_prj/qlib_baseline/outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke_passed.yaml | 5 | 5 | 5 |
| remaining | E:/qlib_prj/qlib_baseline/outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_remaining74.yaml | 74 | 0 | 0 |
| combined | E:/qlib_prj/qlib_baseline/outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_combined79.yaml | 79 | 5 | 5 |

## Next Step

Run `scripts/run_factor_evaluation_batch_v1.py --config configs/factor_evaluation_batch_v1_ta_remaining74.yaml --dry-run` first.
Then execute small batches with `--max-batches` before full resume execution.
