# Repository Architecture

## 1. 项目定位

`qlib-baseline` 是个人 A 股量化研究仓库。架构首先服务于研究正确性、无未来数据、
时间隔离、解释性和可复现性，而不是机构级平台能力。

当前工程优化的目标是让开发者和 Codex 更快判断：

- 当前应该运行什么；
- 哪些配置和数据路径生效；
- 哪些模型、因子和策略已经冻结；
- 哪些模块属于历史研究；
- 输出应放在哪里；
- 修改后运行哪些测试。

权威研究边界见 [PERSONAL_QUANT_RESEARCH_ROADMAP.md](PERSONAL_QUANT_RESEARCH_ROADMAP.md)，
当前执行入口见 [CURRENT_PIPELINE.md](CURRENT_PIPELINE.md)。

## 2. 当前逻辑结构

```text
External Market Data
        │
        ▼
Daily Data Update ──────► Data/Feature Validation
        │
        ▼
Frozen 52-Factor Snapshot
        │
        ▼
Frozen Strategy V1 LightGBM Prediction
        │
        ├──────────────► Mature Label Evaluation
        │
        ▼
Strategy V1 Paper Portfolio
        │
        ▼
Append-only Forward Evidence
```

历史研究链路仍保留，但不是当前开发默认入口：

```text
Data / Universe
      ↓
Factor Matrix / Evaluation / Selection
      ↓
Historical Model Research
      ↓
Historical Portfolio Backtest
      ↓
Model Diagnostic V1 (closed)
```

## 3. 领域目录

| 目录 | 当前职责 | 状态 |
|---|---|---|
| `daily_update/` | Community/BaoStock source、provider bridge、冻结特征、验证与 orchestration | ACTIVE |
| `qlib_baseline/` | Project Settings、原子 I/O、doctor 与活动 CLI orchestration；不承载领域计算 | ACTIVE ENGINEERING FOUNDATION |
| `model_research/` | 历史模型研究、Forward prediction、状态和 paper portfolio | MIXED：部分 ACTIVE，部分 FROZEN/CLOSED |
| `factor_research/` | 因子定义、adapter、评价、筛选和历史研究工具 | FROZEN/HISTORICAL，按需维护 |
| `qlib_integration/` | Qlib Exchange/Executor、市场语义和组合执行 | SHARED/FROZEN CONTRACT |
| `research_validation/` | schema、lineage、artifact 和时间边界验证 | SHARED/COMPATIBILITY |
| `portfolio/` | 较早的组合研究辅助模块 | HISTORICAL |
| `data_quality/`、`tradability/`、`universes/` | 数据质量、可交易性和 PIT universe | SHARED/HISTORICAL |
| `scripts/` | CLI 与历史 stage runners | MIXED；只有 CURRENT_PIPELINE 列出的入口默认 active |
| `configs/` | 研究配置、冻结规则和历史 stage 配置 | MIXED；不得仅凭版本号判断 active |
| `tests/` | 高风险语义、contract 和回归测试 | ACTIVE |

目录存在不代表模块处于 active 状态。版本化名称如 V1、V2、V3、V4 只表示研究历史，
不表示最新版本一定是当前运行入口。

## 4. 依赖方向

活动代码应遵循以下方向：

```text
CLI / scripts
    ↓
Pipeline orchestration
    ↓
Domain modules
    ↓
Qlib integration / validation / shared I/O
```

约束：

- scripts 只负责参数解析、配置加载和 orchestration；
- 业务模块不得反向 import scripts；
- Forward prediction 不得读取 label；
- paper portfolio 只消费已完成 Git binding 的 official prediction；
- historical diagnostics 不得改变 frozen Strategy V1；
- 新模块应优先复用现有 schema、execution 和 validation，避免平行框架。

Phase 1 已建立可安装 package、统一 settings 和 doctor；Phase 2 将五个活动 CLI
迁入 `qlib_baseline.cli`。原 scripts 只保留兼容转发，业务 pipeline 调用与 frozen
contract 未改变。

## 5. 配置与运行环境

当前状态：

- 历史 Python/YAML/PowerShell/Markdown 中仍存在本机绝对路径；
- 五个活动 CLI 及 Daily Update 的 Qlib source/dump 调用已移除本机绝对默认值；
- `pyproject.toml`、`qlib_baseline.settings.ProjectSettings` 和 `qlib-doctor` 已可用；
- committed `configs/project.yaml` 的机器路径保持 `null`，当前工作站路径仅存在于
  ignored `configs/project.local.yaml`；
- Phase 4 已建立 `reports/`，并以目录级 `.gitignore` policy 让普通 outputs/tmp
  默认忽略，同时保留 artifacts/reports 和 allowlist 中 official Forward evidence
  的 tracking；未知 Forward runtime 文件默认忽略；
- 文档声明的项目解释器是 `E:/anaconda_envs/qlib_env/python.exe`。

目标边界：

- Project Settings 负责“去哪里找数据和输出”；
- `sys.executable` 代表“当前是谁在运行”；
- committed project config 不假定 Qlib source/provider 的机器目录布局；
- 本机路径只进入 ignored local config、环境变量或 CLI；
- 路径统一相对仓库根目录解析，不依赖调用时 cwd。

Phase 2 不改变解释器选择。`qlib-doctor` 报告当前 interpreter、依赖和路径；活动
CLI 消费 Project Settings，且不得向 `load_settings(project_root=...)` 传值。历史
scripts 不在本阶段批量迁移。

Phase 3A 后 Daily Update 内部依赖方向为：

```text
pipeline.py (config + orchestration + compatibility re-export)
    ├── sources/community.py
    ├── sources/baostock.py
    ├── provider.py
    ├── features.py
    └── validation.py
```

`pipeline.py` 继续保留原公开符号，现有调用者不需要迁移。拆分没有新增 manager、
registry、protocol 或新的数据 contract。

Phase 3B 后 Forward Pipeline 内部依赖方向为：

```text
forward_pipeline.py (compatibility re-export only)
    ├── forward_state.py      (atomic I/O, append-only state, calendar/window helpers)
    ├── forward_binding.py    (candidate freeze, model loading, Git commit binding)
    ├── forward_prediction.py (prediction normalization and execution)
    └── forward_labels.py     (mature-label evaluation)
```

`forward_pipeline.py` 保留原公开函数、类和调用签名，活动 CLI 与 paper portfolio 无需
迁移。prediction 模块不依赖 label 模块；label update 只消费完成 Git binding 的
official prediction。拆分没有改变 state/receipt schema、cutoff、label maturity、
模型/预处理 hash 或 frozen 52 因子顺序，也没有拆分 `paper_portfolio.py`。

## 6. Factor Matrix 边界

本轮不实现 KunQuant 或 factor-engine 插件系统。上层暂时只依赖现有矩阵 contract：

```text
keys: datetime, instrument
values: ordered factor columns
requirements: unique keys, explicit schema/order, declared data window and provenance
```

当第二个真实计算 backend 获得授权后，再从已经存在的 Pandas/Qlib 路径提取最小
engine 接口。在此之前不新增 manager、registry、protocol 或 speculative adapter。

## 7. Governance 分类

### 必须保留

- 无未来数据和 train/validation/test 时间隔离；
- `split_003` 已观察且不得用于重新选择；
- schema、日期、特征顺序和组合会计的 fail-closed 检查；
- 现有 frozen model/preprocessing 和 Strategy V1 证据。

### Forward/Frozen 必需

- candidate freeze 与内容寻址 artifact；
- prediction hash、Git binding、cutoff 和 receipt；
- append-only prediction/paper state；
- label maturity 与 prediction-stage zero-label-read；
- Strategy V1 prediction、decision、trades、positions 和 NAV 的不可覆盖性。

### 历史兼容

- 已发布的 manifests、lineage、receipts、validators 和 readiness evidence；
- Matrix v4、Labels v2、历史模型和回测的调用路径；
- docs/archive 与 tracked outputs 中的研究证据。

### 默认停止扩张

- 为普通新研究增加逐 CSV receipt；
- 新建 stage-specific gate/manager/registry；
- 继续把 Git 当通用实验数据库；
- 为未来可能需求建立服务化、分布式或企业级治理系统。

## 8. 修改纪律

开始修改前：

1. 阅读 `AGENTS.md`、本文件和 `CURRENT_PIPELINE.md`；
2. 确认 touched module 的状态；
3. 识别 frozen inputs、outputs 和证据边界；
4. 选择最小测试与等价验证；
5. 若计划成本或风险高于预期，缩小或推迟，并记录原因。

任何工程重构都不得以“重新运行”为由覆盖正式 Forward evidence。需要等价验证时，
必须使用 synthetic fixture、临时目录或明确的 dry-run 路径。
