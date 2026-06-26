# Alpha101 Source Audit V1

## Source Summary

| source_project | name | implementation_role | local_path | source_file | source_status | license | license_status | source_commit | function_count | all_alpha_count | adapter_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101 | KunQuant Alpha101 | primary_formula_source | tmp/reference_repos/KunQuant | KunQuant/predefined/Alpha101.py | available | Apache-2.0 | available | d4b9e61f729df347730aa921b539b9df3c3fe36d | 82 | 82 | adapter_pending |
| ginkgo_alpha101 | Ginkgo Alpha101 | metadata_reference_only | tmp/reference_repos/Ginkgo_Alpha101 | README.md | available | MIT | available | 57cec7002698d89c130e027c7661bf53d307dcac | 0 | 0 | not_runnable_reference |

## KunQuant Inventory

- Formula functions parsed: `82`
- Functions in `all_alpha`: `82`
- Missing Alpha101 numbers from 1..101: `48,56,58,59,63,67,69,70,76,79,80,82,87,89,90,91,93,97,100`
- Metadata catalog: `outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml`

## Sample Factors

| source_project | factor | registry_name | source_function | in_all_alpha | required_fields | param_names | status | source_file | source_commit | license |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101 | kunquant_alpha101_alpha001 | alpha001 | alpha001 | True | $close | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha002 | alpha002 | alpha002 | True | $close,$open,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha003 | alpha003 | alpha003 | True | $open,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha004 | alpha004 | alpha004 | True | $low | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha005 | alpha005 | alpha005 | True | $amount,$close,$open,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha006 | alpha006 | alpha006 | True | $open,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha007 | alpha007 | alpha007 | True | $close,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha008 | alpha008 | alpha008 | True | $close,$open | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha009 | alpha009 | alpha009 | True | $close | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha010 | alpha010 | alpha010 | True | $close | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha011 | alpha011 | alpha011 | True | $amount,$close,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha012 | alpha012 | alpha012 | True | $close,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha013 | alpha013 | alpha013 | True | $close,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha014 | alpha014 | alpha014 | True | $close,$open,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha015 | alpha015 | alpha015 | True | $high,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha016 | alpha016 | alpha016 | True | $high,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha017 | alpha017 | alpha017 | True | $close,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha018 | alpha018 | alpha018 | True | $close,$open | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha019 | alpha019 | alpha019 | True | $close | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha020 | alpha020 | alpha020 | True | $close,$high,$low,$open | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha021 | alpha021 | alpha021 | True | $close,$volume | d | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha022 | alpha022 | alpha022 | True | $close,$high,$volume | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha023 | alpha023 | alpha023 | True | $high | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha024 | alpha024 | alpha024 | True | $close | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha025 | alpha025 | alpha025 | True | $amount,$close,$high,$volume | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha026 | alpha026 | alpha026 | True | $high,$volume | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha027 | alpha027 | alpha027 | True | $amount,$volume | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha028 | alpha028 | alpha028 | True | $close,$high,$low,$volume | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha029 | alpha029 | alpha029 | True | $close | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |
| kunquant_alpha101 | kunquant_alpha101_alpha030 | alpha030 | alpha030 | True | $close,$volume | self | formula_available_adapter_pending | tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py | d4b9e61f729df347730aa921b539b9df3c3fe36d | Apache-2.0 |

## Decision

- Use KunQuant as the primary Alpha101 formula source for the next adapter stage.
- Treat Ginkgo_Alpha101 as metadata/reference only because the local clone contains README/LICENSE but no formula implementation files.
- Keep all generated Alpha101 catalog entries disabled and non-runnable until adapter smoke and V4 validation pass.
