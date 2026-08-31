# A 股量化研究框架

这是一个 personal、research-first 的中国 A 股量化研究框架，主要基于
[Microsoft Qlib](https://github.com/microsoft/qlib)。Qlib 是底层框架，不是整个项目身份。
项目用于因子、模型、组合与 genuine forward research，不是生产交易系统，也不构成投资建议。

GitHub repository：
[PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)

## 当前状态

- **ACTIVE：**具有时间优先级的 Forward Track——Daily Data Update、冻结 Strategy V1
  prediction、paper portfolio 和成熟标签评价。
- **FROZEN：**Strategy V1 及全部历史/Forward evidence。
- **READY / AUTHORITY：**新 Dataset / Protocol research 使用的 canonical dataset。
- **CLOSED：**Historical Data Engineering 与已完成历史研究阶段。
- **NEXT / NOT STARTED：**Dataset / Research Protocol redesign。
- **NOT AUTHORIZED：**Structured ML、Strategy V2 和 live trading。

Canonical dataset：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

范围为 `2010-01-29` 至 `2026-06-09`；774 个 definitions 中 765 个 research-usable，
9 个 blocked。旧 frozen Matrix 和历史 extension 继续作为 immutable evidence，不是新研究
默认输入。读取合同见
[Canonical Research Dataset Authority](docs/CANONICAL_RESEARCH_DATASET.md)。

Prior Research Protocol V2 是 frozen historical evidence；其中短 development environments
不足以授权正式 Structured ML。必须先单独授权并完成 Dataset / Research Protocol redesign。

文档从 [docs/DOC_INDEX.md](docs/DOC_INDEX.md) 开始；活动命令和状态边界以
[docs/CURRENT_PIPELINE.md](docs/CURRENT_PIPELINE.md) 为准。

## 环境准备

committed [configs/project.yaml](configs/project.yaml) 保持 portable。本机 Qlib source、
provider 和 Daily Update cache 写入 ignored `configs/project.local.yaml`；模板见
[configs/project.local.example.yaml](configs/project.local.example.yaml)。

```powershell
conda activate qlib_env
python -m pip install -e .
qlib-doctor --strict
```

环境细节见 [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)。

## 活动命令

```powershell
qlib-daily-update --target-date YYYY-MM-DD
qlib-forward-predict --help
qlib-forward-label-update --help
qlib-paper-portfolio --help
qlib-forward-status
```

cutoff、Git binding、label maturity 和 append-only 规则见
[CURRENT_PIPELINE.md](docs/CURRENT_PIPELINE.md)；不要从这份短命令列表推断生产参数。

## 质量命令

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

这些 tier 不下载完整 A 股数据、不训练模型、不运行历史回测。政策见
[docs/CI_POLICY.md](docs/CI_POLICY.md)。

## 文档入口

- [项目上下文摘要](docs/PROJECT_CONTEXT_SUMMARY.md)
- [当前 Pipeline](docs/CURRENT_PIPELINE.md)
- [Canonical Research Dataset](docs/CANONICAL_RESEARCH_DATASET.md)
- [个人研究路线](docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md)
- [架构](docs/ARCHITECTURE.md)
- [输出政策](docs/OUTPUT_POLICY.md)
- [文档导航与归档地图](docs/DOC_INDEX.md)

`docs/` 保存 current authority，`docs/operations/` 保存活动 operational contracts，
`docs/_archive/` 与 `reports/` 保存 historical evidence。归档计划不是当前执行指令。

仓库工作协议见 [AGENTS.md](AGENTS.md)。
