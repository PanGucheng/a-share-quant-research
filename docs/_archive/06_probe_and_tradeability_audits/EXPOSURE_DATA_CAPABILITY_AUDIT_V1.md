# Exposure Data Capability Audit V1

本阶段参考 FactorTest 与 qlib_factor_platform，审计本项目当前是否具备行业、规模/市值、Barra-style 暴露诊断的数据能力。

它只做数据能力审计，不训练模型，不做中性化回归，不调整策略。

## 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_exposure_data_capability_v1.py --config configs\exposure_data_capability_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 参考能力

FactorTest 中已识别到以下能力：

```text
SW / CITICS industry mapping
market cap / size data
industry + size neutralization
Barra data and Barra neutralization
```

qlib_factor_platform 中已识别到：

```text
neutralize_factor
```

## 当前数据能力

| capability | status | detail |
| --- | --- | --- |
| reference_industry_size_barra_design | available | present=5/5 |
| project_context_benchmark_universe | available | factor_context_v1 benchmark/universe/listing context |
| tradability_and_data_quality_prefilters | available | tradability labels and data quality outputs |
| provider_size_fields | missing | available=0/5 |
| provider_industry_fields | missing | available=0/4 |
| provider_barra_fields | missing | available=0/5 |

## 结论

当前工程已经有 benchmark/universe/context、tradability 和 data_quality 约束，可以继续作为暴露评价的前置层。但当前 provider 没有可用的市值、行业分类或 Barra-style 字段：

```text
size fields: 0/5 available
industry fields: 0/4 available
barra fields: 0/5 available
```

因此现阶段不应直接做行业/Barra 中性化。更合理的推进顺序是：

1. 先接入外部行业映射和市值数据。
2. 或先做已具备数据基础的 liquidity/tradability residualization。
3. 等行业/市值/Barra 数据 contract 通过后，再实现 FactorTest-style neutralized evaluation。

## 输出

```text
outputs/exposure_data_capability_audit_v1/current/reference_capabilities.csv
outputs/exposure_data_capability_audit_v1/current/provider_field_probe.csv
outputs/exposure_data_capability_audit_v1/current/project_data_capabilities.csv
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_board.csv
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_contract_status.csv
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_report.md
```

## 下一步

1. 设计外部行业/市值数据接入 contract。
2. 设计 liquidity residualized factor evaluation 的最小接口，先复核高流动性暴露 probes。
