# Project Context Summary

本文件用于在对话很长时快速恢复上下文。

## Project

路径：

```text
E:\qlib_prj\qlib_baseline
```

目标：

- 面向量化新手，基于 Qlib 和开源项目整合 A 股量化研究框架。
- 当前重点是因子研究、因子筛选、数据质量和可交易性约束。
- 不急于训练新模型，不做实盘，不替换 Qlib baseline。

## Environment

Python：

```text
E:\anaconda_envs\qlib_env\python.exe
```

Qlib 源码：

```text
E:\qlib_prj\qlib_clone
```

默认数据：

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
```

重要运行经验：

- 完整 qrun 或长任务应直接用本地普通权限运行，不要在受限沙盒里跑。
- Windows multiprocessing 需要 `freeze_support()`。
- 临时参考仓库放在 `tmp/reference_repos/`，该目录被 `.gitignore` 忽略。

## Current Factor Research Status

V2：

- 已实现因子注册、IC/Rank IC、分组收益、换手率、覆盖率、相关性、候选筛选。
- 默认结果在：

```text
outputs/factor_research_v2/liquid2000_default
```

V3：

- 已实现预处理、中性化、切片诊断和暴露相关性。
- 默认结果在：

```text
outputs/factor_research_v3/liquid2000_core
```

V3 结论：

- `amplitude_20` raw 很强，但联合中性化后基本消失，更像风险/流动性暴露。
- `std_20` 与 `amplitude_20` 高度冗余。
- `rev_5` 有一定潜力，但还不足以直接 promote。

## Open Source References

已拉取参考：

```text
tmp/reference_repos/jqfactor_analyzer
tmp/reference_repos/FactorTest
tmp/reference_repos/multi-factor
tmp/reference_repos/AlphaTrading
tmp/reference_repos/alphalens-reloaded
tmp/reference_repos/qlib_factor_platform
```

参考规则：

- 优先借鉴成熟口径和模块边界。
- 不复制无 license 项目代码。
- 不引入复杂 UI。
- 不绕过现有 data_quality/tradability。

## Next Work

当前要执行 V3.1：

- `directional_rank_icir`
- 无未来信息 `market_state`
- `--write-detail`
- `factor_exposure_report.md`
