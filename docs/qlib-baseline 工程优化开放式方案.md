# qlib-baseline 工程优化开放式方案

## 1. 项目背景

本项目为基于 Microsoft Qlib 构建的个人 A 股量化研究项目。

项目目前已经不仅是一个简单的 Qlib baseline，而是逐渐形成了较完整的量化研究流程，包括但不限于：

- Qlib 数据与模型基础框架
- 数据质量检查
- Tradability / 可交易性处理
- 因子计算与因子研究
- 因子评价与筛选
- Alpha158 / Alpha101 / Alpha360 / TA 等因子体系
- LightGBM 模型研究
- Historical Backtest
- Portfolio Construction
- Forward Prediction
- Paper Portfolio
- Strategy Diagnostics
- Artifact / Manifest / Receipt / Lineage
- pytest 测试
- 历史研究阶段与 Forward Track

项目当前已经具备较强的研究完整性，但随着功能和历史版本逐渐增加，工程复杂度也明显提高。

本轮工作的目标不是继续增加量化功能，也不是修改模型或策略，而是：

> 对现有工程进行一次系统性整理和轻量化，使项目结构更加清晰、可维护、可扩展，并更适合后续长期使用 AI / Codex 进行开发。

---

# 2. 本轮优化的核心目标

本轮工程优化需要重点解决以下问题：

1. 配置和环境路径分散；
2. Python 项目结构仍带有较强的脚本工程特征；
3. scripts、模块和业务逻辑之间边界不够明确；
4. outputs、artifacts、runtime results 和 Git 跟踪内容之间边界复杂；
5. `.gitignore` 已变得非常庞大；
6. 一些 pipeline 文件承担过多职责；
7. 历史 V1 / V3 / V4 等模块较多，当前 active pipeline 不够直观；
8. AI/Codex 在修改项目时可能较难快速判断哪些模块是当前有效实现；
9. cache 与代码版本之间的绑定仍可以进一步提高可靠性；
10. 项目未来可能继续扩展模型、因子和因子计算引擎，因此需要预留合理的扩展边界。

整体目标可以概括为：

> **减少工程摩擦，而不是增加工程抽象。**

---

# 3. 总体设计原则

所有工程优化都应遵守以下原则。

## 3.1 Research First

本项目首先是个人量化研究项目，而不是机构级交易平台。

工程设计必须服务于研究效率，而不能为了“架构漂亮”增加不必要复杂度。

优先级仍然应该保持：

1. 研究逻辑正确；
2. 无未来数据；
3. Train / Validation / Test / Forward 边界正确；
4. 研究结果可解释；
5. 工程可维护；
6. 实验可复现；
7. 自动化；
8. 复杂治理机制。

---

## 3.2 不破坏现有研究结果

本轮原则上属于：

> Engineering Refactor

而不是：

> Quant Research Change

不得因为工程重构而主动改变：

- 因子公式；
- Label 定义；
- Train / Validation / Test 时间划分；
- Strategy V1；
- Frozen LightGBM；
- 52-factor input；
- Top50；
- 5-day rebalance；
- 交易费用；
- Portfolio 逻辑；
- 已冻结 artifact；
- 历史实验结果。

如果重构后需要重新运行某些结果，应优先验证：

> 新旧实现数值等价。

---

## 3.3 不重新使用已观察 Holdout

`split_003` 已经被观察。

因此本轮工程优化：

- 不允许利用 split_003 调模型；
- 不允许重新筛因子；
- 不允许扫描新的 TopK；
- 不允许调整 rebalance；
- 不允许优化 LightGBM 参数；
- 不允许基于 split_003 创建新的“最佳策略”。

工程优化与量化研究优化必须严格区分。

---

# 4. 第一优先级：统一配置和路径管理

目前项目中存在较多本地路径，例如：

```text
E:/qlib_prj/qlib_clone
E:/qlib_prj/qlib_data/...
E:/anaconda_envs/qlib_env/...
```

并且这些路径可能存在于：

- Python
- YAML
- PowerShell
- README
- docs
- scripts

需要研究一种简单、统一的配置方式。

目标：

> 项目运行环境相关信息应该尽可能集中管理，而不是散落在不同源码文件中。

可以考虑但不限于：

```text
configs/project.yaml
.env
环境变量
统一 Settings / Config 模块
CLI override
```

Codex 应根据当前仓库结构选择最简单合适的方案。

最终希望：

```python
settings.qlib_data
settings.qlib_source
settings.cache_dir
```

这类配置能够替代大量：

```python
Path("E:/...")
```

硬编码。

但不要为了配置管理引入大型配置框架。

---

# 5. 第二优先级：规范 Python 工程结构

目前项目仍存在：

```python
PROJECT_ROOT = ...
sys.path.insert(...)
```

以及大量：

```text
scripts/run_xxx.py
```

直接承担较多业务逻辑的情况。

希望评估是否适合逐步转向标准 Python package 结构，例如：

```text
pyproject.toml

src/
    qlib_baseline/
        config/
        data/
        factors/
        models/
        portfolio/
        backtest/
        forward/
        diagnostics/

scripts/

configs/

tests/

docs/
```

这里只是参考方向，不要求机械照搬。

目标是：

> scripts 主要负责 CLI 和 orchestration，真正业务逻辑进入可测试、可复用的 Python package。

例如理想状态：

```text
scripts/run_forward.py
```

只负责：

```text
parse args
↓
load config
↓
call forward module
```

而不是包含大量具体业务实现。

同时逐步消除：

```python
sys.path.insert(...)
```

一类临时项目路径处理。

---

# 6. 第三优先级：重新划分 outputs 与 artifacts

当前 `.gitignore` 已经承担大量实验结果筛选逻辑，例如针对：

- Alpha158
- Alpha101
- Alpha360
- TA
- factor evaluation
- batch evaluation
- smoke
- runtime
- manifests
- reports

分别决定哪些文件进入 Git。

长期来看这会增加较大的维护成本。

需要重新考虑以下几个概念的边界：

```text
runtime output
research output
cache
report
artifact
frozen artifact
Git-tracked evidence
```

建议重点研究一种类似下面的思想：

```text
outputs/
    临时实验运行结果
    默认不进入 Git

artifacts/
    明确冻结、需要长期保存的关键研究对象

reports/
    人类可读研究报告

tmp/
    cache / scratch
```

但 Codex 应根据当前仓库实际依赖进行设计。

注意：

不能直接删除现有 artifact / manifest / lineage 机制。

已有机制可能仍承担：

- 历史证据；
- backward compatibility；
- frozen strategy；
- Forward Track；

因此应该优先：

> 新旧边界逐渐收口，而不是一次性推翻。

目标之一是最终显著简化 `.gitignore`。

---

# 7. 第四优先级：拆分职责过重的 Pipeline

需要检查当前较大的 pipeline 文件。

例如 Daily Update Pipeline 同时可能承担：

```text
数据源访问
下载
压缩包处理
hash
provider
BaoStock
universe
factor computation
validation
snapshot
output
```

需要判断是否存在：

> 一个模块承担过多职责。

可以考虑按责任拆分，例如：

```text
daily_update/

    sources/
        community.py
        baostock.py

    provider.py

    feature_builder.py

    validation.py

    snapshot.py

    pipeline.py
```

其中：

```text
pipeline.py
```

主要负责 orchestration：

```text
source
↓
normalize
↓
validate
↓
feature
↓
snapshot
```

但不要为了“单一职责原则”过度拆文件。

判断标准应该是：

> 拆分后是否真的更容易理解、测试和修改。

---

# 8. 第五优先级：增强 Cache 正确性

项目已经存在因子和 feature cache，这是需要保留并继续发展的能力。

但需要检查：

> Cache key 是否真正绑定了所有影响计算结果的条件。

例如缓存可能需要考虑：

```text
provider
data snapshot
market
universe
start/end
factor definition
factor version
code version
schema
preprocessing
```

重点防止一种情况：

```text
因子代码已经变化
↓
cache key 没变
↓
错误读取旧 cache
↓
研究结果被污染
```

可以评估是否应该加入：

```text
factor code hash
config hash
data snapshot id
factor engine version
```

等 fingerprint。

同时评估大型 dataframe cache 是否可以逐渐：

```text
pickle
↓
Parquet
```

但不要为了格式统一强制迁移所有历史 artifact。

---

# 9. 第六优先级：明确 Current Pipeline 与 Legacy Pipeline

随着项目发展，目前存在大量：

```text
V1
V2
V3
V3.3
V3.4
V3.5
V4
```

等历史模块。

这些版本对研究过程有价值，因此不能简单删除。

但是对于 AI/Codex 来说存在较大风险：

> 无法快速判断哪个版本才是当前 active implementation。

建议建立非常明确的项目架构入口，例如：

```text
docs/ARCHITECTURE.md
```

或：

```text
docs/CURRENT_PIPELINE.md
```

明确列出：

```text
CURRENT ACTIVE PIPELINE

Data Update
→ ...

Factor Calculation
→ ...

Factor Evaluation
→ ...

Factor Selection
→ ...

Model Research
→ ...

Historical Portfolio
→ ...

Forward Prediction
→ ...

Paper Portfolio
→ ...
```

同时明确：

```text
ACTIVE
FROZEN
LEGACY
ARCHIVED
EXPERIMENTAL
```

不同状态。

对于完全不再修改、仅保留历史证据的模块，可以考虑逐步移动到：

```text
legacy/
_archive/
```

但是否移动应充分考虑现有 import 和 artifact 依赖。

优先级是：

> 先建立清晰索引，再决定是否迁移文件。

---

# 10. 第七优先级：建立轻量工程质量检查

项目已经存在 pytest，应继续利用，而不是建立大型 CI 系统。

建议研究建立统一的本地质量入口，例如：

```text
ruff check
ruff format --check
pytest
smoke test
```

CI 只针对轻量内容：

```text
config loading
factor formula
label formula
T+1 semantics
cache fingerprint
schema
forward no-label-read
portfolio accounting
atomic write
```

不要让 CI：

- 下载完整中国股票数据；
- 运行完整 Alpha158；
- 运行 Alpha360；
- 完整训练 LightGBM；
- 完整历史回测。

使用：

```text
synthetic data
small fixtures
smoke config
```

即可。

CI 的目标：

> 防止 Codex 修改代码后破坏基本 contract。

而不是验证整个量化研究结果。

---

# 11. 为未来 Factor Engine 解耦预留接口

未来项目可能引入：

```text
KunQuant
```

或其他因子计算后端。

本轮不要求实现 KunQuant。

但可以检查目前：

```text
factor calculation
```

是否与：

```text
data pipeline
factor evaluation
forward pipeline
```

耦合过深。

希望逐渐形成概念上的：

```text
              Factor Engine

        ┌────────┼────────┐
        ↓        ↓        ↓
      Pandas    Qlib   KunQuant
```

上层只依赖统一的：

```text
factor matrix
```

而不是依赖具体计算后端。

可以探索类似：

```python
engine.compute(
    factors,
    universe,
    start,
    end
)
```

的抽象。

但重要原则是：

> 不要为了未来可能使用 KunQuant，现在就建立复杂插件系统。

只需要保持合理边界，使未来替换计算 backend 的工程成本较低。

---

# 12. 明确禁止的过度工程化

本项目当前不需要为了“专业”引入：

- Airflow
- Dagster
- Kafka
- Kubernetes
- 微服务
- Feature Store
- Model Serving Platform
- ML Platform
- 分布式数据库
- 复杂 Workflow Engine
- 企业级权限系统
- 大型 metadata server
- 大型 lineage 平台

除非后续出现明确实际需求，否则不应引入。

对于个人科研项目：

```text
Python
YAML
CSV / JSON / Parquet
Markdown
Git
pytest
```

通常已经足够。

---

# 13. 现有 Governance 的处理原则

当前仓库已经存在较多：

```text
manifest
hash
receipt
lineage
freeze
validator
contract
readiness gate
```

这些机制过去帮助发现过实际问题，因此：

> 不允许简单删除。

但是也不应该默认继续扩张。

建议将现有机制分成：

```text
必须保留
历史兼容
Frozen Strategy 必需
Forward Evidence 必需
可以逐渐停止扩张
可以未来归档
```

Codex 应根据实际调用关系和研究价值进行分析。

原则：

> Preserve existing evidence, simplify future engineering.

---

# 14. 建议的长期目标结构

无需一次性重构成这个结构，但可以把它作为方向参考：

```text
                 Config
                   │
                   ▼

Data ───────→ Factor Engine
                   │
                   ▼
             Factor Research
                   │
                   ▼
             Factor Selection
                   │
                   ▼
                  Model
                   │
                   ▼
                Portfolio
                /       \
               /         \
      Historical         Forward
       Backtest           Track
```

底层提供公共能力：

```text
Configuration
Data Access
Cache
Artifact
Logging
Validation
Tests
```

---

# 15. 本轮建议优先解决的四个问题

如果评估后认为无法一次完成所有重构，应优先：

## Priority 1

统一配置系统，减少硬编码本地路径。

---

## Priority 2

规范 Python package 和 scripts 边界。

---

## Priority 3

重新梳理：

```text
outputs
artifacts
reports
runtime
cache
```

之间的关系，并逐步简化 `.gitignore`。

---

## Priority 4

建立：

```text
ARCHITECTURE.md
CURRENT_PIPELINE.md
```

或等价机制，让开发者和 Codex 能明确知道：

```text
什么是 active
什么是 frozen
什么是 historical
什么是 legacy
```

---

# 16. 对 Codex 的任务要求

请不要直接开始大规模修改代码。

第一阶段只进行：

> Repository Engineering Audit + Refactor Planning

需要完整阅读当前仓库结构和关键依赖，然后自行判断：

1. 当前工程的主要结构性问题；
2. 哪些问题值得解决；
3. 哪些属于过度工程化，不应该解决；
4. 哪些历史机制必须保留；
5. 哪些模块已经过度耦合；
6. 哪些路径/config 存在重复；
7. 哪些 scripts 应逐渐变薄；
8. 哪些模块适合进入 Python package；
9. outputs/artifacts 应如何重新划分；
10. active/legacy/frozen 状态应如何管理；
11. cache fingerprint 是否足够可靠；
12. tests/CI 当前有哪些明显缺口；
13. 如何保证重构前后研究结果数值一致。

然后制定一份：

# Engineering Refactor Implementation Plan

要求：

- 分阶段实施；
- 每阶段规模尽可能小；
- 每阶段都可以独立验证；
- 避免“大爆炸式重构”；
- 明确涉及哪些文件；
- 明确新建哪些文件；
- 明确哪些旧代码暂时保留；
- 明确迁移策略；
- 明确测试方案；
- 明确 rollback 方法；
- 明确每阶段完成标准。

计划应优先：

```text
low risk
+
high engineering benefit
```

的改动。

---

# 17. 最重要的限制

本次工作是：

> 工程优化。

不是：

> 策略优化。

因此未经单独授权，不要：

```text
重新训练模型
重新筛选因子
修改 label
修改策略
优化 TopK
优化 rebalance
修改交易成本
修改 benchmark
重新使用 split_003 调参
启动 Model V2
引入 KunQuant
```

如果工程重构必须运行研究流程，只允许用于：

> regression / equivalence validation

并应验证结果与原实现一致。

---

# 18. 最终判断标准

本轮重构成功的标准不是：

> 文件变得更多、抽象变得更多。

而是：

### 一个新的 Codex 实例进入仓库后，应该能够很快回答：

```text
项目现在在做什么？
当前有效 pipeline 是什么？
从哪里运行？
配置在哪里？
数据在哪里配置？
当前模型是什么？
当前因子体系在哪里？
哪些代码不能修改？
哪些东西是历史版本？
实验输出放在哪里？
哪些东西应该进入 Git？
修改一个模块后应该运行哪些测试？
```

如果这些问题都能非常清晰地回答，同时研究正确性没有下降，那么这次工程优化就是成功的。

核心原则：

> **Make the repository easier to understand, safer for AI-assisted development, and cheaper to maintain — not more sophisticated for its own sake.**