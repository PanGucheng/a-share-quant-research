# A 股量化研究框架

这是一个 research-first 的个人中国 A 股量化研究框架，主要基于
[Microsoft Qlib](https://github.com/microsoft/qlib)。Qlib 是重要的底层框架，不是整个
项目的身份。项目用于因子、模型、组合与真实 forward 观察研究，不是生产交易系统，
不构成投资建议。

GitHub repository：
[PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)

## 当前状态

当前具有时间优先级的活动主线是 Forward Track：

```text
Daily Data Update
        ↓
冻结 52 因子快照
        ↓
冻结 Strategy V1 LightGBM prediction
        ↓
Top50 等权 paper decision
        ↓
标签成熟后的独立评价
```

Strategy V1、历史 prediction 与已经观察的 `split_003` 均保持冻结。`split_003` 可以
用于诊断，但不能再次用于调参后声称为新的 OOS。Model Diagnostic V1 已关闭，Phase
0–6 工程重构也已正式收口，不存在自动延伸的工程 Phase 7。

文档入口是 [docs/DOC_INDEX.md](docs/DOC_INDEX.md)；实际活动命令、时间边界和机器
状态路径以 [docs/CURRENT_PIPELINE.md](docs/CURRENT_PIPELINE.md) 为准。

## 环境准备

committed [configs/project.yaml](configs/project.yaml) 保持 portable。本机 Qlib source、
provider 与 Daily Update cache 写入被忽略的 `configs/project.local.yaml`，模板见
[configs/project.local.example.yaml](configs/project.local.example.yaml)。

```powershell
conda activate qlib_env
python -m pip install -e .
qlib-doctor --strict
```

Python interpreter 属于 runtime state（`sys.executable`），不属于 Project Settings。
Windows 工作站环境与配置优先级见 [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)。

## 活动命令

```powershell
qlib-daily-update --target-date YYYY-MM-DD
qlib-forward-predict --help
qlib-forward-label-update --help
qlib-paper-portfolio --help
qlib-forward-status
```

不要仅根据上述短命令推断生产参数。prediction cutoff、Git binding、label maturity
和 append-only 规则必须遵循 [docs/CURRENT_PIPELINE.md](docs/CURRENT_PIPELINE.md)。

## 质量命令

本地与 GitHub Actions 使用同一组入口：

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

`fast` 是有限 Ruff 范围和重点工程测试；`full` 是完整 pytest 与既有 compact/synthetic
validators；`qlib` 是 synthetic Qlib Exchange runtime tests。这些命令不会下载完整
A 股数据、训练模型或运行历史回测。详细政策见 [docs/CI_POLICY.md](docs/CI_POLICY.md)。

## 目录结构

```text
qlib_baseline/    Settings、原子 I/O、弱缓存 helper 与活动 CLI。
daily_update/     活动 Daily Update pipeline 与兼容 facade。
model_research/   冻结/forward 模型和 paper portfolio 模块。
factor_research/  因子评价与研究模块。
qlib_integration/ Qlib Exchange/Executor 集成。
configs/          portable project 与工作流配置。
scripts/          活动包装器、quality runner、validators 与历史工具。
docs/             当前权威和操作文档。
docs/_archive/    CLOSED、HISTORICAL、SUPERSEDED 计划与审计。
outputs/          runtime 结果及保留的历史/Forward evidence。
artifacts/        不可变 frozen machine objects。
reports/          适合 Git 的紧凑人类可读证据。
tmp/              被忽略的缓存、下载、参考仓库与临时文件。
```

## 权威文档

- [个人研究路线](docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md)
- [当前 Pipeline](docs/CURRENT_PIPELINE.md)
- [架构](docs/ARCHITECTURE.md)
- [输出政策](docs/OUTPUT_POLICY.md)
- [CI 政策](docs/CI_POLICY.md)
- [Phase 0–6 工程收尾](docs/ENGINEERING_REFACTOR_CLOSEOUT.md)
- [文档归档](docs/_archive/README.md)

归档计划保留项目演进证据，但不是当前执行指令。既有 manifests、receipts、lineage、
frozen artifacts 与历史 outputs 均保持不变。

## 研究边界

- 任何决策只能使用当时可得信息。
- 严格隔离 train、validation、test/holdout 与 forward label evaluation。
- 不覆盖 Strategy V1 prediction、paper decision、持仓、交易或 NAV。
- 不把历史或 post-observation diagnosis 解释为生产 readiness。
- 在保证研究正确性和证据边界的前提下采用最小工程设计。

仓库工作协议见 [AGENTS.md](AGENTS.md)。
