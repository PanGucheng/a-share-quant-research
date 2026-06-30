# Factor Candidate Pool V3.4 Plan

本计划承接 V3.3 因子筛选。V3.3 已经能给单个因子打状态，V3.4 的目标是把筛选结果固化成一个可版本化、可复现、可被后续组合回测读取的候选池快照。

## 1. Goal

建立因子研究到组合回测之间的轻量接口：

```text
factor_screening_v3
 -> factor_candidate_pool_v3
 -> 后续 portfolio backtest / risk control
```

本阶段仍不训练新模型、不做实盘、不引入大量新因子。

## 2. Inputs

默认输入：

```text
outputs/factor_screening_v3/liquid2000_core/factor_candidate_board.csv
```

该文件来自：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_screening_v3.py
```

## 3. Candidate Roles

将筛选状态映射为候选池角色：

```text
portfolio_test_candidate -> alpha_candidate
research_candidate       -> alpha_candidate
risk_exposure            -> risk_control
watch                    -> monitor
redundant                -> excluded
reject                   -> excluded
```

解释：

- `alpha_candidate`: 后续可以进入组合测试或继续深挖的 alpha 候选。
- `risk_control`: 不能当作干净 alpha，但可作为风险暴露、风格约束或解释变量。
- `monitor`: 方向未定义或证据不足，暂时观察。
- `excluded`: 暂不进入后续研究主线。

## 4. Outputs

默认输出目录：

```text
outputs/factor_candidate_pool_v3/liquid2000_core
```

输出文件：

```text
factor_candidate_pool.csv
factor_candidate_pool.json
factor_candidate_pool_report.md
```

## 5. Acceptance Criteria

- [x] 不重新计算因子或指标。
- [x] 直接读取 V3.3 candidate board。
- [x] 输出 CSV、JSON 和 Markdown 报告。
- [x] 当前 `rev_5` 进入 `alpha_candidate`。
- [x] 当前 `amplitude_20` 和 `std_20` 进入 `risk_control`。
- [x] 通过 smoke run。

## 6. Execution Result

完成时间：2026-06-14。

验证命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe -c "from pathlib import Path; [compile(Path(p).read_text(encoding='utf-8'), p, 'exec') for p in ['factor_research/candidate_pool_v3.py','scripts/run_factor_candidate_pool_v3.py']]; print('syntax ok')"
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_candidate_pool_v3.py
```

默认输出：

```text
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.csv
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool.json
outputs/factor_candidate_pool_v3/liquid2000_core/factor_candidate_pool_report.md
```

当前角色分布：

```text
alpha_candidate: 1
risk_control:   2
monitor:        2
```

当前候选池：

```text
rev_5        -> alpha_candidate
amplitude_20 -> risk_control
std_20       -> risk_control
ret_20       -> monitor
amount_mean_20 -> monitor
```
