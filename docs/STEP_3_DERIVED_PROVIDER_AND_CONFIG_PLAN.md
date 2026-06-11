# 第三步具体计划：派生数据目录与配置模板

第二步已经完成社区数据导入、动态成分质量检查、新旧基线对比，以及股票池口径决策。第三步目标是把“候选数据”变成“可稳定复用的研究数据层”，但仍不修改原始导入目录。

## 1. 目标

完成后应达到：

- 原始社区 provider 保持只读。
- 有一个派生 provider 目录，用于放入经过审阅的自定义 universe 文件。
- `all_stock_shsz` 这类项目级股票池能被 qlib 直接引用。
- qrun 配置能从模板生成，减少手工复制 YAML。
- 完整 qrun 继续使用提权或普通 PowerShell 执行，不在 Codex 受限沙盒内跑。

## 2. 推荐目录

```text
E:/qlib_prj/qlib_data/
  cn_data_community_20260609/          # 原始导入，只读
  cn_data_community_20260609_derived/  # 派生 provider
```

派生目录第一版建议直接复制原始 provider，再只替换或新增 `instruments/` 下的项目级 universe 文件。

第一批派生 universe：

```text
all_stock_shsz.txt
```

来源：

```text
outputs/universes/community_20260609/all_stock_shsz.txt
```

## 3. 任务拆分

### 任务 1：创建派生 provider 构建脚本

状态：已完成。

新增：

```text
scripts/build_derived_provider.ps1
```

职责：

- 输入原始 provider。
- 输入派生 provider 输出目录。
- 复制 provider 目录结构。
- 将 `outputs/universes/community_20260609/all_stock_shsz.txt` 写入派生 provider 的 `instruments/all_stock_shsz.txt`。
- 输出构建日志和文件校验。

验收：

- 原始 provider 未被修改。
- 派生 provider 可被 `qlib.init(provider_uri=...)` 初始化。
- `instruments/all_stock_shsz.txt` 存在且不含 `BJ`、`SH000*`、`SZ399*`。

### 任务 2：新增 provider 初始化检查

状态：已完成。

新增：

```text
scripts/validate_provider.py
```

职责：

- 初始化 qlib provider。
- 读取指定 universe 的若干日期成分。
- 抽样读取 `close`、`volume`、`amount`。
- 输出 Markdown/JSON 检查报告。

验收：

- 对原始社区 provider 和派生 provider 都能跑通。
- 对 `all_stock_shsz` 能读到成分并抽样取数。

### 任务 3：新增 qrun 配置生成器

状态：已完成。

新增：

```text
scripts/create_workflow_config.py
```

职责：

- 读取现有基线 YAML。
- 替换 `qlib_init.provider_uri`。
- 替换 `market` 和 `data_handler_config.instruments`。
- 可选替换输出配置名。
- 保留模型、时间段和回测参数。

第一批生成：

```text
configs/workflow_lightgbm_alpha158_all_stock_shsz_community_20260609.yaml
```

验收：

- 生成 YAML 可读。
- 配置中的 provider 指向派生 provider。
- `market` 使用 `all_stock_shsz`。

### 任务 4：小样本 qlib 读取验证

状态：已完成。

先不跑完整 qrun，先执行：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\validate_provider.py --provider-uri E:/qlib_prj/qlib_data/cn_data_community_20260609_derived --market all_stock_shsz --start-time 2020-01-02 --end-time 2020-01-10 --output outputs/reports/provider_validation_all_stock_shsz_community_20260609.md
```

验收：

- 能初始化 provider。
- 能读取 universe。
- 能读取样本字段。

### 任务 5：完整 qrun 验证

状态：待专项运行。

完整 qrun 继续使用普通权限或提权执行：

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_baseline.ps1 -ConfigPath E:\qlib_prj\qlib_baseline\configs\workflow_lightgbm_alpha158_all_stock_shsz_community_20260609.yaml
```

注意：

- 不在受限沙盒内跑完整 qrun。
- 不使用 `-SafeMode` 作为最终性能评估。
- 如果运行耗时较长，先保存日志路径，再汇总 MLflow 指标。

## 4. 风险

### 风险 1：派生 provider 占用磁盘空间

处理：

- 第一版优先完整复制，降低符号链接和权限风险。
- 如果磁盘压力明显，再评估 junction 或硬链接。

### 风险 2：`all_stock_shsz` 股票池过宽

处理：

- 先做小样本读取验证。
- 完整 qrun 前先跑数据质量检查。
- 后续可增加流动性过滤股票池，例如 `all_stock_shsz_liquid`。

### 风险 3：宽股票池回测和 Alpha158 计算更慢

处理：

- 先保留 CSI500 作为速度和结果锚点。
- 宽股票池第一次 qrun 应作为专项验证，不替代 CSI500 基线。

## 5. 完成标准

- 派生 provider 已构建。
- `all_stock_shsz` 可被 qlib 读取。
- 配置生成器可生成 provider-specific qrun YAML。
- 至少完成一次小样本 provider 验证。
- 是否执行完整宽股票池 qrun，有明确日志和结果记录。

## 6. 当前执行结果

已构建派生 provider：

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
```

构建报告：

```text
outputs/reports/derived_provider_community_20260609.md
```

已生成 qrun 配置：

```text
configs/workflow_lightgbm_alpha158_all_stock_shsz_community_20260609.yaml
```

小样本验证报告：

```text
outputs/reports/provider_validation_all_stock_shsz_community_20260609.md
```

数据质量预检报告：

```text
outputs/data_quality_all_stock_shsz_preflight/all_stock_shsz_2020-01-02_2020-01-31
```

验证摘要：

| item | value |
| --- | ---: |
| universe rows | `5532` |
| sample symbols | `SH600000`, `SH600004`, `SH600006`, `SH600007`, `SH600008` |
| sample feature rows | `35` |
| `$close` non-null rows | `35` |
| `$volume` non-null rows | `35` |
| `$amount` non-null rows | `35` |

质量预检摘要：

| item | value |
| --- | ---: |
| date range | `2020-01-02` to `2020-01-31` |
| expected instruments per day | `3760` to `3775` |
| avg coverage rate | `0.9946` |
| min coverage rate | `0.9936` |
| OHLCVA missing rate | `0.5394%` |

下一步可以执行完整宽股票池 qrun。该任务预计明显慢于 CSI500 基线，应使用提权或普通 PowerShell 运行，不在受限沙盒内运行。
