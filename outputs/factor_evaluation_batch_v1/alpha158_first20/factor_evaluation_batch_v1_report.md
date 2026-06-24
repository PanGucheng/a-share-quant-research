# Factor Evaluation Batch V1 Report

- Config: `configs/factor_evaluation_batch_v1_alpha158_first20.yaml`
- Dry run: `false`
- Batch count: `4`
- Total selected factors: `20`

## Batch Status

| status | batch_count |
| --- | --- |
| pass | 1 |
| skipped_existing | 3 |

## Batch Manifest

| batch_id | status | factor_count | factors | output_dir |
| --- | --- | --- | --- | --- |
| batch_001 | skipped_existing | 5 | alpha158_KMID,alpha158_KLEN,alpha158_KMID2,alpha158_KUP,alpha158_KUP2 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_001 |
| batch_002 | skipped_existing | 5 | alpha158_KLOW,alpha158_KLOW2,alpha158_KSFT,alpha158_KSFT2,alpha158_OPEN0 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_002 |
| batch_003 | skipped_existing | 5 | alpha158_HIGH0,alpha158_LOW0,alpha158_VWAP0,alpha158_ROC5,alpha158_ROC10 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_003 |
| batch_004 | pass | 5 | alpha158_ROC20,alpha158_ROC30,alpha158_ROC60,alpha158_MA5,alpha158_MA10 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_004 |

## Output Summary

| batch_id | status | factor_count | factors | evaluator_status_rows | failure_rows | metric_rows | context_metric_rows | output_dir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batch_001 | skipped_existing | 5 | alpha158_KMID,alpha158_KLEN,alpha158_KMID2,alpha158_KUP,alpha158_KUP2 | 15 | 10 | 90 | 960 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_001 |
| batch_002 | skipped_existing | 5 | alpha158_KLOW,alpha158_KLOW2,alpha158_KSFT,alpha158_KSFT2,alpha158_OPEN0 | 15 | 10 | 90 | 960 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_002 |
| batch_003 | skipped_existing | 5 | alpha158_HIGH0,alpha158_LOW0,alpha158_VWAP0,alpha158_ROC5,alpha158_ROC10 | 15 | 10 | 90 | 960 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_003 |
| batch_004 | pass | 5 | alpha158_ROC20,alpha158_ROC30,alpha158_ROC60,alpha158_MA5,alpha158_MA10 | 15 | 10 | 90 | 960 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_first20\runs\batch_004 |

## Output Files

- `factor_catalog_snapshot.csv`
- `selected_factor_catalog.csv`
- `factor_catalog_validation.csv`
- `generated_configs/batch_*.yaml`
- `batch_manifest.csv`
- `batch_output_summary.csv`
- `logs/batch_*.stdout.log`
- `logs/batch_*.stderr.log`
