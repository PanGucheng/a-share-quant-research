# 路径感知 CI 政策

仓库使用单一 `research-validation-ci` workflow，并以 `ci-gate` 作为稳定的最终
检查。Workflow 始终启动，但只运行与变更范围匹配的重型 job。

本地与 CI 共用以下入口（从仓库根目录运行）：

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

三个 tier 可组合而不互相隐式包含：普通代码 CI 依次运行 `fast`、`full`；Qlib
runtime job 运行 `qlib`。命令失败时立即停止并返回原退出码。

## 检查分层

| 变更 | Fast docs/repository check | 完整 pytest + validators | Qlib runtime |
|---|---:|---:|---:|
| 仅 `docs/**` 或根目录 README | 是 | 否 | 否 |
| 普通代码、测试、配置、机器 evidence | 是 | 是 | 否 |
| Qlib integration/执行链、相关配置或测试 | 是 | 是 | 是 |
| workflow、CI helper、依赖锁 | 是 | 是 | 是 |

`outputs/**` 下的 Markdown 也属于机器 evidence，不走纯文档快速路径。

## 快速检查

`change-classifier / docs-check` 不安装 pandas、NumPy、SciPy、PyArrow 或 Qlib，
只执行：

- changed-path classification；
- `git diff --check`；
- changed Markdown local-link 检查；
- `docs/DOC_INDEX.md` 路径存在性检查；
- 5 MiB changed-file 上限。

研究代码适用的 `fast` quality tier 安装 lightweight validation requirements 后执行：

- Ruff lint；
- settings、doctor、atomic I/O 和 weak-cache tests；
- active CLI/import tests；
- CI classifier 与 quality-command contract tests。

Ruff 首轮范围固定为：

```text
qlib_baseline/**
daily_update/**
scripts/check_quality.py
五个 Forward Track 兼容入口
```

不执行 `ruff format`，也不 lint/format 全仓历史 scripts、factor/model research 或
tracked outputs。

`full` tier 执行完整 pytest，并逐项运行 workflow 原有的 25 个 compact/synthetic
validators。`qlib` tier只运行 `tests/test_qlib_exchange_runtime.py`，使用测试自己创建的
临时 synthetic provider。三个 tier 均不下载完整 A 股数据、不训练模型、不运行完整
矩阵或历史回测。

## 路径规则

纯文档快速路径只包括：

```text
docs/**
README.md
README.zh-CN.md
CONTRIBUTING.md
CHANGELOG.md
```

其他变更默认 fail-safe 到完整研究验证。Qlib runtime 的附加触发范围包括：

```text
qlib_integration/**
tests/test_qlib_exchange_runtime.py
tests/test_qlib_integration_contracts.py
configs/*qlib_exchange*
configs/*execution_reconciliation*
configs/*a_share_execution*
scripts 中 qlib/execution reconciliation/OOS execution 入口
requirements*
.github/workflows/**
scripts/ci/**
```

## Stable gate

`ci-gate` 接受有意跳过的重型 job，但任何适用 job 的 failure/cancellation 都会使
门禁失败。分支保护应只要求：

```text
ci-gate
```

连续推送使用 workflow concurrency 自动取消同一 PR/分支的旧运行。禁止使用
`[skip ci]` 或人工声称“只是文档”来绕过分类器。

## 仓库设置边界

截至 2026-07-25，远端 `main` 尚未启用 branch protection。Workflow 已稳定产出
`ci-gate`，但它只有在仓库管理员以后启用分支保护并将 `ci-gate` 设为唯一 required
check 后，才会成为 GitHub 层面的强制合并门禁。不得把可能按路径跳过的
`lightweight-contracts` 或 `qlib-exchange-runtime` 单独设为 required check。
