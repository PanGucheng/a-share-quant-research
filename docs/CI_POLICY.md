# 路径感知 CI 政策

仓库使用单一 `research-validation-ci` workflow，并以 `ci-gate` 作为稳定的最终
检查。Workflow 始终启动，但只运行与变更范围匹配的重型 job。

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
