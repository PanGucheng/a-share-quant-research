# Strategy V1 Paper Portfolio V1

This is the lightweight portfolio leg of the prospective Forward Track. It consumes
only committed official predictions and keeps the historical P01 rule unchanged:
long-only Top50 equal weight with a five-trading-day rebalance interval.

Run one decision after the official prediction is committed:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_paper_portfolio_v1.py `
  --date 2026-08-07 `
  --calendar-file E:\qlib_prj\qlib_data\cn_data_community_20260609\calendars\day_future.txt
```

The command verifies the prediction receipt and Git binding, derives the next
trading day from the authoritative calendar, and records the target under
`outputs/forward/paper_portfolio/decisions/`. A decision created after the next-day
09:25 Asia/Shanghai cutoff is rejected.

If execution-day Daily Data Update output is not present, the command stops at
`pending_execution`; it does not fabricate trades, positions, or NAV. Once that
daily output exists, the same command path replays all paper history through the
existing Qlib A-share execution runner and writes compact `trades.csv`,
`rejected_orders.csv`, `positions.csv`, and `daily_nav.csv` files.
Execution can also be advanced without creating another decision:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_paper_portfolio_v1.py --refresh-only
```

This remains prospective personal-research paper accounting. It does not retrain
the model, read labels, change Strategy V1, or authorize live trading.
