# New-Source Probe Review V1

本阶段消费 `new_source_probe_diagnostics_v1` 输出，做第一轮冗余与可交易性暴露复核。它不重新计算因子，不训练模型，不把任何 probe 升级为 downstream default。

## 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_review_v1.py --config configs\new_source_probe_review_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## Contract

```text
review_board_rows: pass, rows=328
redundancy_pairs_present: pass, pairs=200
redundancy_groups_present: pass, groups=4
tradability_exposure_watchlist_present: pass, watchlist=19
oos_candidates_present: pass, candidates=3
no_downstream_default: pass, downstream_default=0
```

## Review 分层

```text
alpha101 metric_only_defer: 6
alpha101 tradability_exposure_review: 8
alpha360 frame_review_candidate: 13
alpha360 metric_only_defer: 199
alpha360 redundancy_representative_review: 3
alpha360 redundant_holdout_candidate: 84
ta frame_review_candidate: 1
ta metric_only_defer: 3
ta tradability_exposure_review: 11
```

## 严格 OOS Extension Candidates

严格过滤后只剩 3 个候选，全部来自 Alpha360 的 high-window 冗余代表：

```text
alpha360_HIGH36
alpha360_HIGH37
alpha360_HIGH40
```

这不是坏事，反而说明工具链正在发挥刹车作用：328 个 probes 中大量信号其实是高度相似的价量窗口或流动性/可交易性代理，不能直接送进训练。

## 冗余组

V1 识别出 4 个高相关冗余组，其中最大的 Alpha360 组包含 80 个 close/high/low/open/vwap lag 窗口因子。TA / Alpha101 中也存在一个混合冗余组，例如：

```text
kunquant_alpha101_alpha005
kunquant_alpha101_alpha041
kunquant_alpha101_alpha042
ta_momentum_kama
ta_trend_ema_fast
ta_trend_sma_fast
ta_volatility_kcc
ta_volatility_kch
ta_volatility_kcl
ta_volume_vwap
```

## 输出

```text
outputs/new_source_probe_review_v1/current/probe_review_board.csv
outputs/new_source_probe_review_v1/current/redundancy_pairs.csv
outputs/new_source_probe_review_v1/current/redundancy_groups.csv
outputs/new_source_probe_review_v1/current/tradability_exposure_watchlist.csv
outputs/new_source_probe_review_v1/current/oos_extension_candidates.csv
outputs/new_source_probe_review_v1/current/probe_review_contract_status.csv
outputs/new_source_probe_review_v1/current/probe_review_report.md
```

## 下一步

1. strict OOS extension 已在 `docs/ALPHA360_STRICT_OOS_EXTENSION_V1.md` 完成。
2. 对 3 个严格候选做 main vs recent OOS 稳定性对比。
3. 对 19 个 `tradability_exposure_review` 做流动性/可交易性暴露归因。
4. 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
