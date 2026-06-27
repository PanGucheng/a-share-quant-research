# Alpha360 Batch Catalogs V1

This report prepares Qlib Alpha360 factors for resumable batch V4 evaluation.

## Catalog Summary

| catalog | path | factor_count | enabled_count | runnable_count |
| --- | --- | --- | --- | --- |
| source_all | outputs/factor_catalog_alpha360_v1/alpha360_catalog_all.yaml | 360 | 0 | 0 |
| batch_candidate | outputs/factor_catalog_alpha360_v1/alpha360_catalog_batch_candidate358.yaml | 358 | 0 | 0 |
| adapter_holdout | outputs/factor_catalog_alpha360_v1/alpha360_catalog_adapter_holdout2.yaml | 2 | 0 | 0 |
| combined | outputs/factor_catalog_alpha360_v1/alpha360_catalog_combined360.yaml | 360 | 0 | 0 |

## Holdout Rule

- Holdout names: `alpha360_CLOSE0, alpha360_VOLUME0`
- Reason: `constant_or_near_constant_normalization_identity`

## Generated Configs

- Expression adapter: `configs/alpha360_expression_adapter_batch358_v1.yaml`
- V4 batch base: `configs/alpha360_factor_evaluation_batch_base_v1.yaml`
- Batch runner: `configs/factor_evaluation_batch_v1_alpha360_candidate358.yaml`

## Next Step

Run the generated expression adapter config to build the Alpha360 batch factor frame.
Then dry-run the batch runner before executing small resumable batches.
