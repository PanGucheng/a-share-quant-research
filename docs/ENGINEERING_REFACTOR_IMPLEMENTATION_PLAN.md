# Engineering Refactor Implementation Plan

## 1. 目标与执行纪律

本计划把《qlib-baseline 工程优化开放式方案》落实为小步、可验证、可回滚的
工程重构。它只改变工程组织，不授权任何量化研究变化。

严格禁止：

- 重新训练或重新选择模型；
- 重新筛选因子，或改变 frozen 52-factor input/order；
- 使用已观察的 `split_003` 调整参数、TopK、调仓周期或组合规则；
- 修改 Strategy V1 的 Top50 等权、5 个交易日调仓、费用、滑点或 T+1 语义；
- 覆盖既有 prediction、receipt、paper decision、持仓、交易、NAV 或 frozen artifact。

每个 Phase 必须单独实施、验证和汇报。未经用户明确要求，不自动进入下一 Phase。
如果实际审查发现某项成本、兼容风险或研究正确性风险显著高于预期，可以
`Stop / Skip / Defer / Simplify`，但必须记录偏离原因。

## 2. 审计基线

Phase 0 开始前的仓库事实：

- Git 共跟踪约 3,952 个文件，其中 `outputs/` 约 3,183 个；
- 共有 439 个 Python 文件、216 个 Python scripts；
- 约 194 个 Python 文件直接操作 `sys.path`；
- 尚无 `pyproject.toml`；
- `.gitignore` 约 240 行，其中大部分是 outputs 的 stage-specific 规则；
- `daily_update/pipeline.py` 同时承担数据源、provider、特征、校验和输出；
- Matrix v4 cache、manifest 与 lineage 已较成熟，不应被统一缓存工作替换；
- 当前活动主线是 Daily Data Update → frozen Strategy V1 prediction → paper portfolio；
- 2026-08-07 已有 1 条 official prediction，等待标签成熟；paper portfolio 已生成
  2026-08-07 decision，等待 2026-08-10 execution data；
- 当前 Forward Track 针对性基线测试为 `61 passed`（项目 Qlib Python 环境）；默认
  系统 Python 因缺少 `pandera` 在测试收集阶段停止。

## 3. Phase 0 — Documentation And Architecture Entry

实施内容：

- 原样复制工程优化指南到 `docs/`，并验证 SHA-256；
- 新建本实施方案；
- 新建 `ARCHITECTURE.md`、`CURRENT_PIPELINE.md`、`OUTPUT_POLICY.md`；
- 更新 `DOC_INDEX.md`、README 和 `AGENTS.md` 的工程入口；
- 将入口标记为 `ACTIVE / FROZEN / CLOSED / LEGACY / EXPERIMENTAL`；
- 将现有 governance 分类为必须保留、Forward/Frozen 必需、历史兼容和停止扩张。

完成标准：

- 新 Codex 实例能够快速定位当前流水线、冻结边界、配置、输出和测试入口；
- 文档链接、源文件副本 hash、Git diff 检查通过；
- 不修改代码、配置、`.gitignore`、outputs 或 artifacts。

## 4. Phase 1 — Settings, pyproject And Doctor

计划新增：

- `pyproject.toml`；
- `configs/project.yaml` 与 `configs/project.local.example.yaml`；
- `qlib_baseline/settings.py`、`qlib_baseline/io.py`；
- `qlib_baseline/cli/doctor.py` 及对应测试。

目标接口：

```python
@dataclass(frozen=True)
class ProjectSettings:
    project_root: Path
    qlib_source: Path | None
    qlib_provider: Path | None
    daily_update_cache: Path | None
    outputs_dir: Path
    artifacts_dir: Path
    reports_dir: Path
    tmp_dir: Path
```

配置规则：

- `project_root` 由 package 位置确定，不由 YAML 覆盖；
- committed `project.yaml` 中机器相关路径为 `null`，repo 内路径使用
  `outputs`、`artifacts`、`reports`、`tmp`；
- 当前工作站的实际 `E:/qlib_prj/...` 路径只写入被忽略的
  `configs/project.local.yaml`；
- 文件选择顺序为 CLI → `QLIB_BASELINE_CONFIG` → local YAML → committed YAML；
- 字段值顺序为 CLI → `QLIB_BASELINE_*` → YAML；
- Python interpreter 不进入 Project Settings；`qlib-doctor` 直接检查
  `sys.executable`、版本、依赖和命令所需路径；
- 不引入 `.env` 或大型配置框架。

Phase 1 只建立基础能力，不迁移业务入口。

## 5. Phase 2 — Active CLI Migration

只迁移当前 Forward Track：

- `daily_update.py`；
- `run_forward_prediction_v1.py`；
- `update_forward_labels_v1.py`；
- `run_paper_portfolio_v1.py`；
- `show_forward_status_v1.py`。

提供 `qlib-daily-update`、`qlib-forward-predict`、
`qlib-forward-label-update`、`qlib-paper-portfolio`、
`qlib-forward-status` 与 `qlib-doctor`。旧 scripts 保留为兼容包装器。

完成标准：

- 新旧命令对同一 fixture 等价；
- 活动入口的绝对本机路径和 `sys.path.insert` 为零；
- frozen model、preprocessing 与 factor-order hash 不变；
- 不批量迁移历史 scripts。

## 6. Phase 3A — Daily Update Decomposition

计划拆分为：

- `daily_update/sources/community.py`；
- `daily_update/sources/baostock.py`；
- `daily_update/provider.py`；
- `daily_update/features.py`；
- `daily_update/validation.py`；
- `daily_update/pipeline.py` 保留 orchestration 和兼容 re-export。

不得改变数据源发布时间、bridge 公式、52 因子顺序、覆盖阈值或 fail-closed 语义。

### Regression Gate A

在进入 Forward Pipeline 拆分前，必须通过：

- Daily Update synthetic；
- Forward adapter；
- Forward prediction fixture 与 contract；
- Paper Portfolio fixture；
- 当前 Forward Track 基线测试；
- 在临时目录重放已保存的 2026-08-07 输入，不写正式 evidence 路径。

Gate 只是测试和审阅结果，不新增 validator、manifest 或治理层。

## 7. Phase 3B — Forward Pipeline Decomposition

仅在 Regression Gate A 通过后实施。拆分 prediction、append-only state、
freeze/commit binding 和 mature-label update；原 `forward_pipeline.py` 保留兼容
façade 和公开函数签名。`paper_portfolio.py` 本轮默认不拆。

### Regression Gate B

- 重跑 Gate A；
- 覆盖 duplicate date、cutoff、commit binding、label maturity 和失败状态；
- score 在 `1e-12` 容差内等价；
- prediction/receipt/state schema 与 label-read 边界不变。

未通过时只回滚 Phase 3B。

## 8. Phase 4 — Output And Git Policy

目标语义：

- `outputs/`：默认不跟踪的运行结果；
- `artifacts/`：不可变、content-addressed 的冻结对象；
- `reports/`：人类可读报告与小型汇总；
- `tmp/`：cache/download/scratch；
- `outputs/forward/`：Strategy V1 append-only evidence 的明确兼容例外。

Phase 4 只修改未来 tracking policy。明确禁止：

- 对历史 outputs 运行 `git rm --cached`；
- 批量 untrack、move、rename 或 delete；
- 修改历史 manifest/hash；
- 为了减少行数牺牲规则语义。

完成标准是删除大部分 stage-specific 规则、未来普通实验无需持续修改
`.gitignore`，且修改前后 `git ls-files outputs artifacts` 集合完全一致；不设置固定
行数目标。

## 9. Phase 5 — Weak Cache Hardening

新 fingerprint 分为：

```text
Cache Schema
+ Data Fingerprint
+ Computation Fingerprint
+ Request Fingerprint
```

- Data：provider snapshot、calendar/instruments、universe、日期；
- Computation：公式/expression、metadata、preprocessing、相关 engine version；
- Request：factor names、fields、market、输出 schema；
- Diagnostic metadata：完整 producer file hash、Git commit、环境版本，仅记录在
  sidecar，不默认参与 key。

Python 计算使用实际函数及直接 helper 的规范化 AST hash，忽略注释、格式和无关
函数变化。Qlib commit 只在确实影响该计算时参与 key。

优先迁移 `factor_research/evaluator.py`、`run_factor_research_v3.py` 和
`expression_adapter.py`。新 cache 使用 Parquet + `.meta.json`；旧 pickle 保留但
不作为新 schema 默认命中。Matrix v4 cache、raw snapshot manifest 与 lineage 不改。

## 10. Phase 6 — Quality And CI Consolidation

新增统一的 `scripts/check_quality.py`：

- `fast`：Ruff 与 settings/cache/active-entry tests；
- `full`：完整 pytest 与现有 synthetic validators；
- `qlib`：现有 Qlib Exchange runtime tests。

CI 与本地使用同一入口；Ruff 首轮只覆盖新基础包、Daily Update 和活动 CLI，不
批量格式化历史仓库。CI 不下载完整 A 股数据、不训练模型、不运行完整矩阵或回测。

## 11. 最终验收与回滚

每个 Phase：

1. 开始前重新核对 touched files 与研究边界；
2. 使用独立提交；
3. 运行该 Phase 的最小测试和完整适用 gate；
4. 汇报实际变更、验证、风险及对后续 Phase 的影响；
5. 等待用户授权，不自动继续；
6. 回滚采用撤销该 Phase 提交，不清理历史 evidence。

最终状态必须保持 Strategy V1、研究时间边界、Forward evidence 和全部历史
artifacts/manifests/receipts/lineage 不变。本轮不做 `src/` 大迁移，不批量清除
历史 `sys.path`，不实现 KunQuant 或 factor-engine 插件系统。

## 12. Phase 1 实施回执（2026-08-09）

Phase 1 已按计划完成，并保持所有活动业务入口不变：

```text
pyproject_editable_install_ready      = true
portable_project_settings_ready       = true
ignored_local_override_ready          = true
runtime_doctor_ready                  = true
atomic_io_foundation_ready            = true
active_cli_migrated                   = false
daily_forward_behavior_changed        = false
```

实际实现：

- `ProjectSettings` 只管理项目与数据路径，不包含 Python executable；
- committed `configs/project.yaml` 的 Qlib source/provider/cache 为 `null`；
- `configs/project.local.yaml` 只保存当前机器路径并被 Git 忽略；
- base YAML 与 partial local/explicit YAML 合并，字段优先级为 CLI → env → YAML；
- 所有相对路径从 repository root 解析，不依赖 cwd；
- `qlib-doctor` 检查 `sys.executable`、Python 3.10、依赖和外部路径；
- `qlib_baseline.io` 提供无 pandas 依赖的 atomic path/text/JSON 写入基础；
- editable package 同时暴露现有领域 packages，但没有迁移或修改其业务代码。

验证结果：

```text
new Phase 1 tests                    = 13 passed
full pytest                          = 336 passed, 4 existing Qlib warnings
editable install                     = pass
qlib-doctor --strict                 = ready / exit 0
cross-cwd settings and console usage = pass
```

已知边界：

- `reports/` 尚未建立，doctor 按 Phase 4 计划标记为 warning，不阻塞 readiness；
- 未激活环境时 `qlib-doctor.exe` 所在 Scripts 目录可能不在 `PATH`，始终可使用
  `python -m qlib_baseline.cli.doctor`；
- 当 cwd 恰好存在名为 `qlib_baseline` 的无 `__init__.py` 目录时，bare
  `import qlib_baseline` 可能被识别为 namespace package；显式
  `qlib_baseline.settings`、module CLI 和 console script 已验证可用。Phase 2 不应依赖
  package root 的 re-export；
- 活动 scripts 的绝对路径和 `sys.path` 暂时保留，等待 Phase 2。

Phase 1 follow-up 补充了进入 Phase 2 前的环境一致性检查：

- doctor 将 LightGBM 纳入活动 Forward Prediction 的必需依赖；
- doctor 报告实际 `qlib` import origin，并在配置源码与实际导入源码不一致时 fail；
- settings 测试明确覆盖 Windows `E:/...` 绝对路径解析；
- `load_settings(project_root=...)` 仍只用于测试，活动 CLI 不得覆盖 repository root。

## 13. Phase 2 实施回执（2026-08-09）

Phase 2 只迁移活动 Forward Track CLI，没有改动 frozen Strategy V1 的计算、模型、
特征、组合或 evidence：

```text
packaged_active_cli_ready             = true
legacy_active_scripts_compatible      = true
active_entry_machine_paths            = 0
active_entry_sys_path_insert          = 0
frozen_model_or_feature_changed       = false
forward_evidence_written              = false
```

实际实现：

- 新增 `qlib-daily-update`、`qlib-forward-predict`、
  `qlib-forward-label-update`、`qlib-paper-portfolio`、`qlib-forward-status`；
- 五个旧 scripts 直接复用 packaged CLI 的同一 `main` 函数；
- 默认 output、freeze、status、paper config、Qlib source/provider 和 daily cache
  由 Project Settings 派生；
- Daily Update 的 Qlib import 不再修改 `sys.path`，fallback `dump_bin.py` 来源由
  配置的 `qlib_source` 明确传入；
- calendar、label、date、daily input、dry-run、commit binding 等业务参数和底层
  contract 保持原样；
- 没有迁移任何历史 scripts，也没有运行正式 prediction、paper 或 label update。

验证结果：

```text
active CLI migration tests           = 8 passed
Forward Track regression baseline    = 61 passed
full pytest                          = 344 passed, 4 existing Qlib warnings
editable install and pip check       = pass
six installed command help checks    = pass
five legacy wrapper help checks      = pass
qlib-doctor --strict                 = ready / exit 0
frozen outputs and artifacts diff    = empty
```

已知边界：

- 旧 scripts 为避免 `scripts/daily_update.py` 遮蔽 `daily_update` package，会启动一个
  指向 packaged module 的子 Python 进程，因此有很小的启动开销；新 console command
  没有该开销；
- 旧 scripts 依赖 Phase 1 的 editable install，不再自行修改 Python import path；
- calendar file、label directory 和单日 input 仍是显式业务参数，没有臆测新的配置；
- `daily_update/pipeline.py` 仍是单体模块，拆分只属于后续获得授权的 Phase 3A。
