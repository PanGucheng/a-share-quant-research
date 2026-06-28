# Exposure Data Capability Audit V1

- Scope: data capability audit for industry, size, and Barra-style exposure diagnostics.
- Boundary: no model training, no neutralization run, no strategy optimization.
- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| reference_capabilities_scanned | pass | present=5/5 |
| provider_fields_probed | pass | probed_fields=14 |
| project_context_available | pass | factor_context_v1 |
| prefilter_outputs_available | pass | tradability,data_quality_tradability |
| exposure_capability_board_written | pass | capabilities=6 |
| no_training_side_effect | pass | data_capability_audit_only |

## Capability Board

| capability | status | detail | next_action |
| --- | --- | --- | --- |
| reference_industry_size_barra_design | available | present=5/5 | Use reference designs as module boundaries; do not copy data vendor assumptions. |
| project_context_benchmark_universe | available | factor_context_v1 benchmark/universe/listing context | Keep as current context baseline. |
| tradability_and_data_quality_prefilters | available | tradability labels and data quality outputs | Keep mandatory before exposure evaluation. |
| provider_size_fields | missing | available=0/5 | Find or derive market-cap data before size neutralization. |
| provider_industry_fields | missing | available=0/4 | Add external SW/CITICS industry mapping before industry neutralization. |
| provider_barra_fields | missing | available=0/5 | Do not run Barra neutralization until Barra/style exposures are sourced. |

## Provider Field Status

| field_group | status | field_count |
| --- | --- | --- |
| barra | empty | 5 |
| industry | empty | 4 |
| size | empty | 5 |

## Provider Field Probe

| field_group | field | status | valid_rows | total_rows | sample_instruments | error |
| --- | --- | --- | --- | --- | --- | --- |
| size | $market_value | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| size | $total_mv | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| size | $circ_mv | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| size | $float_mv | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| size | $mkt_cap | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| industry | $industry | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| industry | $sw_l1 | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| industry | $sw_industry | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| industry | $citics_l1 | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| barra | $beta | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| barra | $momentum | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| barra | $size | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| barra | $residual_volatility | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |
| barra | $non_linear_size | empty | 0 | 0 | SH600000,SH600004,SH600006,SH600008,SH600009 |  |

## Project Outputs

| capability | path | status | expected_files | present_files |
| --- | --- | --- | --- | --- |
| factor_context | outputs/factor_context_v1/main_research_2021_2023 | available | benchmark_returns.csv,universe_membership_counts.csv,universe_membership_asof.csv | benchmark_returns.csv,universe_membership_counts.csv,universe_membership_asof.csv |
| tradability | outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29 | available | tradability_labels.csv | tradability_labels.csv |
| data_quality_tradability | outputs/data_quality_tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29 | available | data_quality_report.md | data_quality_report.md |
| tradability_exposure_attribution | outputs/tradability_exposure_attribution_v1/current | available | tradability_exposure_attribution_board.csv,tradability_exposure_contract_status.csv | tradability_exposure_attribution_board.csv,tradability_exposure_contract_status.csv |

## Reference Capabilities

| reference_project | capability | status | matched_tokens | repo_path | scanned_file_count |
| --- | --- | --- | --- | --- | --- |
| factortest | sw_industry | present | getSWIndustryData,addSWIndustry,getZXIndustryData,addXZXind | tmp/reference_repos/FactorTest | 10 |
| factortest | market_cap | present | getCMV,addXSize,RegbySize,calcNeuSize | tmp/reference_repos/FactorTest | 10 |
| factortest | industry_size_neutralization | present | Regbysize,calcNeuIndsize | tmp/reference_repos/FactorTest | 10 |
| factortest | barra | present | getBarraData,addXBarra,RegbyBarra,calcNeuBarra | tmp/reference_repos/FactorTest | 10 |
| qlib_factor_platform | neutralization_helper | present | neutralize_factor | tmp/reference_repos/qlib_factor_platform | 28 |

## Notes

- Missing provider industry or Barra fields should be treated as data gaps, not implementation failures.
- Residualized evaluation should start with any available size field; industry/Barra neutralization requires explicit data sourcing.
