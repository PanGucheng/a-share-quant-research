# Factor Evaluation Batch V1 Report

- Config: `configs/factor_evaluation_batch_v1_alpha158_remaining138.yaml`
- Dry run: `false`
- Batch count: `1`
- Total selected factors: `10`

## Batch Status

| status | batch_count |
| --- | --- |
| pass | 1 |

## Batch Manifest

| batch_id | status | factor_count | factors | output_dir |
| --- | --- | --- | --- | --- |
| batch_001 | pass | 10 | alpha158_MA20,alpha158_MA30,alpha158_MA60,alpha158_STD5,alpha158_STD10,alpha158_STD20,alpha158_STD30,alpha158_STD60,alpha158_BETA5,alpha158_BETA10 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_remaining138\runs\batch_001 |

## Output Summary

| batch_id | status | factor_count | factors | evaluator_status_rows | failure_rows | metric_rows | context_metric_rows | output_dir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batch_001 | pass | 10 | alpha158_MA20,alpha158_MA30,alpha158_MA60,alpha158_STD5,alpha158_STD10,alpha158_STD20,alpha158_STD30,alpha158_STD60,alpha158_BETA5,alpha158_BETA10 | 30 | 20 | 180 | 1920 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha158_remaining138\runs\batch_001 |

## Output Files

- `factor_catalog_snapshot.csv`
- `selected_factor_catalog.csv`
- `factor_catalog_validation.csv`
- `generated_configs/batch_*.yaml`
- `batch_manifest.csv`
- `batch_output_summary.csv`
- `logs/batch_*.stdout.log`
- `logs/batch_*.stderr.log`
