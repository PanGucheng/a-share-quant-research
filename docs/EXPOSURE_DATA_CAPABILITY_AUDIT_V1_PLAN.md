# Exposure Data Capability Audit V1 Plan

本阶段参考 FactorTest 与 qlib_factor_platform 的行业/风格/中性化设计，审计本项目当前数据是否支持行业、规模、市值和 Barra-style 暴露诊断。

## 目标

1. 不训练模型，不做实盘，不替换现有 Qlib baseline。
2. 不照搬无数据支撑的中性化逻辑，先确认数据能力。
3. 复用现有 `factor_context_v1`、`data_quality`、`tradability` 与 recent probe outputs。
4. 为后续 residualized factor evaluation 明确最小数据缺口。

## 参考开源设计

FactorTest 中值得借鉴的能力：

```text
getSWIndustryData / addSWIndustry
getCMV
getBarraData / addXBarra
RegbySize / calcNeuSize
Regbysize / calcNeuIndsize
RegbyBarra / calcNeuBarra
```

qlib_factor_platform 中值得借鉴的能力：

```text
neutralize_factor(factor_data, industry_data, market_cap_data)
```

## 审计项

1. 参考项目能力是否存在。
2. 当前 provider 是否有市值/行业/Barra 候选字段。
3. 当前工程是否已有 benchmark/universe/context、tradability 和 data_quality 输出。
4. 输出一个 capability board，明确 available / partial / missing。

## 输出

```text
outputs/exposure_data_capability_audit_v1/current/reference_capabilities.csv
outputs/exposure_data_capability_audit_v1/current/provider_field_probe.csv
outputs/exposure_data_capability_audit_v1/current/project_data_capabilities.csv
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_contract_status.csv
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_report.md
```

## 下一步

1. 如果市值字段可用，先做 size residualization smoke。
2. 如果行业分类缺失，先设计外部行业映射数据接入。
3. 如果 Barra 字段缺失，先不要做 Barra neutralization，只保留接口与缺口记录。
