# 第二步具体计划：A 股数据层升级

本文档是第一步“基线固化与可复现”之后的下一阶段计划。目标是把当前旧版、只适合基线复现的数据目录，升级为可持续更新、可审计、可对比的 A 股研究数据层。

## 1. 背景

当前基线数据：

```text
E:/qlib_prj/qlib_data/cn_data
```

已知状态：

- 数据覆盖到 `2020-09-25`。
- 日频字段包含 `open`、`high`、`low`、`close`、`volume`、`factor`、`change`。
- 缺少 `amount` 字段。
- 已可支持 `LightGBM + Alpha158 + CSI500` 基线复现。
- 数据质量报告显示 `amount` 100% 缺失，且部分日期和标的覆盖率异常。

第二步不直接覆盖这份数据。它作为历史基线数据保留，用于比较新数据是否改变研究结论。

## 2. 第二步目标

完成后应达到：

- 有清晰的新旧数据目录隔离。
- 有原始数据归档目录，能追溯数据来源。
- 有一套从原始数据到 qlib bin 数据的转换流程。
- 新数据至少覆盖到较近期交易日。
- 基础字段完整性明显优于当前基线，尤其补齐或解释 `amount`。
- 数据质量检查能区分真实缺失、未上市、退市、指数成分变化等情况。
- 能用新数据复跑当前基线，并和旧数据结果做对比。

## 3. 范围

本阶段处理：

- 数据目录规划。
- 数据源选择和试采样。
- 原始数据归档。
- qlib 格式转换。
- 数据质量检查升级。
- 新旧数据基线对比。

本阶段不处理：

- 不优化模型参数。
- 不开发复杂因子库。
- 不接入真实交易。
- 不做自动下单。
- 不删除或覆盖旧 `cn_data`。

## 4. 推荐目录结构

建议在 `E:/qlib_prj` 下建立数据工作区：

```text
E:/qlib_prj/
  qlib_data/
    cn_data/                         # 当前历史基线，只读保留
    cn_data_community_latest/        # 社区 qlib bin 数据，若采用
    cn_data_akshare_latest/          # AKShare 转换后的 qlib bin 数据，若采用
  data_workspace/
    raw/
      investment_data/
      akshare/
    normalized/
      daily_bar/
      instruments/
      calendars/
      index_components/
      stock_status/
    quality_reports/
    conversion_logs/
```

原则：

- `qlib_data/cn_data` 不动。
- 每个新数据集使用独立目录。
- 原始数据和 qlib bin 数据分开存放。
- 每次转换保留日志和质量报告。

## 5. 数据源策略

### 方案 A：社区 qlib 数据优先

优点：

- 更接近 qlib 原生格式。
- 接入快，适合作为第二步第一条路线。
- 可以快速验证新旧数据差异。

建议来源：

```text
chenditc/investment_data
```

需要确认：

- 数据频率。
- 覆盖市场。
- 数据截至日期。
- 是否包含成交额 `amount`。
- 是否包含指数成分或仅包含行情数据。
- 数据许可和使用限制。

### 方案 B：AKShare 自建数据

优点：

- 可控性更强。
- 方便补充 A 股日线、成交额、指数、成分股、基础信息等。
- 后续每日更新更容易自动化。

缺点：

- 需要自己做清洗、复权、字段映射和 qlib bin 转换。
- 需要更严的数据质量检查。

建议 AKShare 优先采集内容：

```text
股票日线行情
成交额 amount
复权因子或复权价格
交易日历
股票基础信息
上市/退市日期
ST 状态
停复牌状态
指数行情
指数成分
```

### 推荐执行顺序

先走方案 A 快速拿到较新 qlib 数据，再用方案 B 补齐和校验关键字段。不要一开始就把所有数据源混在一起。

## 6. 字段标准

第二步最小字段集：

```text
open
high
low
close
volume
amount
factor
change
```

字段含义建议：

- `open/high/low/close`：复权口径需明确，优先保持 qlib 当前口径一致。
- `volume`：成交量。
- `amount`：成交额。
- `factor`：复权因子。
- `change`：涨跌幅或收益变化字段，需和原 qlib 数据定义对齐。

必须记录：

- 价格是否前复权、后复权或不复权。
- `factor` 如何计算。
- `change` 如何计算。
- `amount` 单位。
- `volume` 单位。

## 7. 执行计划

### 任务 1：冻结旧数据基线

目的：确保后续比较有锚点。

具体任务：

- 记录 `qlib_data/cn_data` 的日历范围。
- 记录 instruments 数量。
- 记录字段列表。
- 记录第一步成功 run 和指标。
- 在文档中声明该目录只读。

建议产物：

```text
docs/DATA_BASELINE_SNAPSHOT.md
```

验收标准：

- 能明确旧数据覆盖日期和字段。
- 后续不会误覆盖旧数据。

### 任务 2：选择第一条新数据路线

目的：避免同时接太多数据源导致不可控。

建议先选：

```text
chenditc/investment_data -> qlib_data/cn_data_community_latest
```

具体任务：

- 查询并下载最新可用 release。
- 解压到独立目录。
- 检查目录是否符合 qlib 格式。
- 统计字段、标的数、日历范围。

建议产物：

```text
data_workspace/conversion_logs/community_data_import_YYYYMMDD.md
docs/_archive/02_data_layer_history/DATA_SOURCE_DECISION.md
```

验收标准：

- 新数据目录能被 `qlib.init(provider_uri=...)` 成功初始化。
- 能读取至少一个标的的 `close`、`volume`、`amount` 或明确说明缺失原因。

### 任务 3：新增数据探查脚本

目的：快速比较任意 qlib 数据目录的结构。

建议新增：

```text
scripts/inspect_qlib_data.py
```

功能：

- 输入 `--provider-uri`。
- 输出日历开始/结束日期。
- 输出 instruments 文件统计。
- 输出 features 标的数。
- 输出字段列表。
- 抽样读取若干标的的字段覆盖。
- 输出 JSON 或 Markdown 报告。

建议命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\inspect_qlib_data.py --provider-uri E:\qlib_prj\qlib_data\cn_data --output outputs\reports\data_snapshot_old.md
```

验收标准：

- 对旧数据和新数据都能生成结构报告。
- 报告能一眼看出字段差异和日期范围差异。

### 任务 4：升级数据质量检查

目的：让数据质量模块适配动态股票池，不再把所有非交易期都简单视作异常。

当前模块：

```text
data_quality/
```

需要升级：

- 增加上市日期和退市日期处理。
- 增加指数成分时间区间处理。
- 增加停牌日期识别。
- 将“无数据但不应交易”和“应有数据但缺失”分开。
- `amount` 从硬性缺失变成字段完整性检查项。
- 增加新旧数据对比报告。

建议新增检查维度：

```text
calendar coverage
instrument lifecycle coverage
field availability
price consistency
volume/amount consistency
adjustment factor consistency
return outlier
limit-up/limit-down suspicious days
suspension-aware missing data
index membership coverage
```

验收标准：

- 对旧数据仍能跑通。
- 对新数据能生成报告。
- 报告能区分结构性缺失和异常缺失。

### 任务 5：新数据复跑当前基线

目的：确认新数据能支撑现有研究流水线。

建议新增配置：

```text
configs/workflow_lightgbm_alpha158_csi500_newdata.yaml
```

唯一必要变化：

```yaml
qlib_init:
    provider_uri: "E:/qlib_prj/qlib_data/<new_data_dir>"
    region: cn
```

运行方式：

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_baseline.ps1
```

注意：

- 完整 qrun 应在沙盒外或提权环境运行。
- 不要在 Codex 受限沙箱里跑完整 qrun。
- 不要用 `-SafeMode` 做最终性能评估，它只是慢速兜底。

验收标准：

- 新数据配置能完成 qrun。
- 生成 `pred.pkl`、`sig_analysis`、`portfolio_analysis`。
- 指标进入 `outputs/reports/baseline_summary.csv`。

### 任务 6：新旧数据对比

目的：判断数据升级是否改变研究结果，以及改变是否合理。

建议新增：

```text
docs/DATA_UPGRADE_COMPARISON.md
```

对比维度：

- 数据覆盖日期。
- 标的数量。
- 字段完整性。
- 缺失率。
- 异常价格数量。
- 异常收益数量。
- 基线 IC。
- Rank IC。
- 年化超额收益。
- 最大回撤。
- 成本后收益。

验收标准：

- 能解释新旧结果差异。
- 如果指标变化很大，能定位是数据覆盖、字段、复权还是股票池变化导致。

## 8. 半天级时间安排

### 第 1 个半天

- 冻结旧数据快照。
- 编写 `DATA_BASELINE_SNAPSHOT.md`。
- 明确新数据路线优先级。

### 第 2 个半天

- 获取社区 qlib 数据或完成下载准备。
- 建立新数据目录。
- 手工检查目录结构和字段。

### 第 3 个半天

- 编写 `inspect_qlib_data.py`。
- 生成旧数据结构报告。
- 生成新数据结构报告。

### 第 4 个半天

- 升级数据质量检查的报告结构。
- 先支持新旧数据字段完整性和日期覆盖对比。

### 第 5 个半天

- 用新数据复跑当前基线。
- 汇总 MLflow 指标。
- 生成新旧结果对比初稿。

### 第 6 个半天

- 补充动态股票池、上市退市、停牌、指数成分逻辑。
- 完成 `DATA_UPGRADE_COMPARISON.md`。

## 9. 第二步完成标准

以下全部满足，即认为第二步完成：

- 旧数据快照已文档化。
- 新数据目录独立存在，未覆盖旧 `cn_data`。
- 新数据可被 qlib 初始化。
- 新旧数据结构报告已生成。
- 数据质量检查能跑旧数据和新数据。
- 新数据能复跑当前 LightGBM Alpha158 CSI500 基线。
- 新旧数据的指标差异有文档解释。
- `amount` 字段是否补齐或为何缺失有明确结论。

## 10. 风险与处理

### 风险 1：数据源字段定义不一致

处理：

- 在 `DATA_SOURCE_DECISION.md` 中记录字段口径。
- 不同数据源不要直接混合，先各自独立跑通。

### 风险 2：复权口径导致指标变化

处理：

- 明确价格和 factor 的计算方式。
- 抽样核对几只股票的分红送转前后价格。

### 风险 3：股票池动态成分处理不当

处理：

- 质量检查中引入成分起止日期。
- 回测时避免未来成分泄漏。

### 风险 4：新数据跑出的收益变差

处理：

- 先看 IC 和 Rank IC 是否稳定。
- 再看交易成本、停牌、涨跌停、成交额约束。
- 不因为单次收益变差就回退数据，先查口径差异。

### 风险 5：网络下载或数据源不稳定

处理：

- 原始文件落盘归档。
- 保存下载日期、URL、校验信息。
- 必要时保留多个数据源作为候选，但不要在同一版数据里混用。

## 11. 推荐下一次执行顺序

下一次实际开工建议按这个顺序：

1. 新增 `docs/DATA_BASELINE_SNAPSHOT.md`。
2. 新增 `scripts/inspect_qlib_data.py`。
3. 先对旧 `cn_data` 生成结构报告。
4. 获取并检查社区 qlib 新数据。
5. 对新数据生成结构报告。
6. 升级数据质量检查，让报告支持新旧对比。
7. 用新数据复跑基线并记录指标。
