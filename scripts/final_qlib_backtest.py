"""One saved model, one native Qlib strategy. No training or parameter search."""
# ruff: noqa: E402 -- direct script invocation needs the repository import path.
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import lightgbm as lgb
import numpy as np
import pandas as pd
import qlib
import yaml
from qlib.backtest.exchange import Exchange
from qlib.backtest.executor import SimulatorExecutor
from qlib.contrib.evaluate import backtest_daily
from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy
from qlib.data import D
from research_validation.canonical_dataset import read_effective_partition

KEYS = ['datetime', 'instrument']
PREV_CLOSE = 'Ref($close,1)'
ADV = 'Ref(Mean($volume,20),1)'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def features(partitions, factors, dates):
    """Same canonical column/key join as V3, with an explicit caller date range."""
    dates = pd.DatetimeIndex(dates)
    pieces = {name: [] for name in factors}
    for row in partitions.to_dict('records'):
        columns = [n for n in factors if n in row['factors'].split(',')]
        selected = dates[(dates >= pd.Timestamp(row['effective_start'])) & (dates <= pd.Timestamp(row['effective_end']))]
        if not columns or selected.empty:
            continue
        frame = read_effective_partition(dict(row, effective_start=selected.min(), effective_end=selected.max()), columns=columns)
        frame = frame.loc[frame.datetime.isin(selected)].set_index(KEYS).sort_index()
        for name in columns:
            pieces[name].append(frame[name].copy())
    axis, result = None, {}
    for name in factors:
        if not pieces[name]:
            raise ValueError(f'Missing feature: {name}')
        value = pd.concat(pieces[name]).sort_index()
        if value.index.has_duplicates or (axis is not None and not value.index.equals(axis)):
            raise ValueError(f'Canonical key mismatch: {name}')
        axis = value.index
        result[name] = value.to_numpy(dtype='float64')
    frame = pd.DataFrame(result, index=axis).reset_index()
    if not pd.DatetimeIndex(frame.datetime.unique()).equals(dates):
        raise ValueError('Missing canonical sessions; do not silently shorten an internal gap')
    return frame


def predict(model, frame, factors):
    if list(frame.columns) != KEYS + factors or model.feature_name() != factors:
        raise ValueError('Model feature order mismatch')
    matrix = frame[factors].to_numpy(dtype='float64', copy=True)
    matrix[~np.isfinite(matrix)] = np.nan
    valid = np.isfinite(matrix).any(axis=1)
    if frame.loc[valid, 'datetime'].nunique() != frame.datetime.nunique():
        raise ValueError('Entire signal day has no usable features')
    scores = np.full(len(frame), np.nan)
    scores[valid] = model.predict(matrix[valid], num_threads=8)
    if not np.isfinite(scores[valid]).all():
        raise ValueError('Nonfinite model scores')
    return frame[KEYS].assign(score=scores, reason=np.where(valid, 'predicted', 'all_features_missing'))


class CheckedExchange(Exchange):
    """Keep native execution; forbid its close-price and fractional-lot fallbacks."""
    def __init__(self, *, terminal_events=None, **kwargs):
        self.terminal_events = terminal_events or {}
        super().__init__(**kwargs)

    def get_quote_from_qlib(self):
        super().get_quote_from_qlib()
        q = self.quote_df
        bad_factor = q['$close'].notna() & (~np.isfinite(q['$factor']) | q['$factor'].le(0))
        if bad_factor.any() or self.trade_w_adj_price:
            raise ValueError(f'Invalid factor would disable native lots: {q.index[bad_factor].tolist()[:8]}')
        fields = ['$open', '$close', PREV_CLOSE, ADV]
        blocked = (~np.isfinite(q[fields]) | q[fields].le(0)).any(axis=1)
        q.loc[blocked, ['limit_buy', 'limit_sell']] = True
        for code, date in self.terminal_events.items():
            terminal = ((q.index.get_level_values('instrument') == code) &
                        (q.index.get_level_values('datetime') >= pd.Timestamp(date)))
            q.loc[terminal, ['limit_buy', 'limit_sell']] = True


class CheckedExecutor(SimulatorExecutor):
    """Native suspension carry, explicit zero-recovery terminal accounting."""
    def __init__(self, *, terminal_events=None, carry_log=None, **kwargs):
        super().__init__(**kwargs)
        self.terminal_events = terminal_events or {}
        self.carry_log = carry_log
        self.events, self.missing_sessions = [], {}

    def record(self, **event):
        self.events.append(event)
        if self.carry_log is not None:
            with Path(self.carry_log).open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(event) + '\n')

    def _collect_data(self, trade_decision, level=0):
        start, end = self.trade_calendar.get_step_time()
        position = self.trade_account.current_position
        terminal = []
        for code in self.trade_account.current_position.get_stock_list():
            if code in self.terminal_events and start >= pd.Timestamp(self.terminal_events[code]):
                terminal.append(code)
                continue
            close = self.trade_exchange.get_close(code, start, end)
            if close is None or not np.isfinite(close) or close <= 0:
                previous = position.get_stock_price(code)
                if (close is None or np.isnan(close)) and np.isfinite(previous) and previous > 0:
                    self.missing_sessions[code] = self.missing_sessions.get(code, 0) + 1
                    self.record(kind='native_missing_quote_carry', date=str(start.date()), instrument=code,
                                carried_price=float(previous), sessions=self.missing_sessions[code])
                    continue
                raise ValueError(f'Unvalued holding: {start.date()} {code}')
            self.missing_sessions.pop(code, None)
        result = super()._collect_data(trade_decision, level)
        for code in terminal:
            amount, price = position.get_stock_amount(code), position.get_stock_price(code)
            self.record(kind='terminal_zero_recovery', date=str(start.date()), instrument=code,
                        amount=float(amount), last_price=float(price), loss=float(amount*price), cash_recovery=0)
            position._del_stock(code)  # Move shares into the event ledger, never turn them into sale cash.
            self.missing_sessions.pop(code, None)
        return result


def run_backtest(scores, days, config, carry_log=None):
    slip, limit = config['slippage'], config['open_limit']
    codes = sorted(scores.instrument.unique())  # Includes all past candidates, not today's signal universe.
    exchange = CheckedExchange(
        freq='day', start_time=days[0], end_time=days[-1], codes=codes, terminal_events=config.get('terminal_events'),
        deal_price=(f'$open*{1+slip}', f'$open*{1-slip}'),
        limit_threshold=(f'$open/{PREV_CLOSE}-1>={limit}', f'$open/{PREV_CLOSE}-1<=-{limit}'),
        volume_threshold=('cum', f'{config["adv_fraction"]}*{ADV}'),
        subscribe_fields=['$open', PREV_CLOSE, ADV], **config['exchange'])
    signal = scores.set_index(KEYS).score.dropna().sort_index()
    strategy = TopkDropoutStrategy(signal=signal, **config['strategy'])
    executor = CheckedExecutor(time_per_step='day', generate_portfolio_metrics=True,
                               terminal_events=config.get('terminal_events'), carry_log=carry_log)
    report, positions = backtest_daily(
        start_time=days[0], end_time=days[-1], strategy=strategy,
        executor=executor,
        account=config['account'], benchmark=config['benchmark'], exchange_kwargs={'exchange': exchange})
    if not report.index.equals(days) or not np.isfinite(report[['account', 'return', 'cost', 'bench']]).all().all():
        raise ValueError('Incomplete/nonfinite account or benchmark')
    if report.cash.min() < -1e-6:
        raise ValueError('Negative cash')
    net = report['return'] - report.cost
    np.testing.assert_allclose((1 + net).cumprod(), report.account / config['account'], rtol=1e-10)
    report.attrs['valuation_events'] = executor.events
    report.attrs['unresolved_valuation'] = executor.missing_sessions
    return report, positions


def statistics(report):
    net = report['return'] - report.cost
    nav = (1 + net).cumprod()
    peak = nav.cummax().clip(lower=1)
    years = len(net) / 252
    std = net.std(ddof=1)
    return dict(total_return=float(nav.iloc[-1]-1), cagr=float(nav.iloc[-1]**(1/years)-1),
                sharpe=float(net.mean()/std*np.sqrt(252)) if std > 0 else None,
                max_drawdown=float((nav/peak-1).min()),
                benchmark_return=float((1+report.bench).prod()-1),
                average_daily_turnover=float(report.turnover.mean()),
                explicit_cost=float((report.cost * report.account / (1+net)).sum()),
                mean_cash_fraction=float((report.cash/report.account).mean()))


def write_results(out, report, positions, config, canary=False):
    report.to_csv(out/'daily_account.csv', index_label='datetime')
    pd.to_pickle(positions, out/'qlib_positions.pkl')
    holdings = [dict(datetime=date, instrument=code, **pos.position[code])
                for date, pos in positions.items() for code in pos.get_stock_list()]
    pd.DataFrame(holdings).to_csv(out/'positions.csv', index=False)
    counts = pd.Series({date: len(pos.get_stock_list()) for date, pos in positions.items()})
    summary = statistics(report)
    summary['mean_holdings'] = float(counts.mean())
    summary['start'], summary['end'] = str(report.index[0].date()), str(report.index[-1].date())
    summary['status'] = 'CANARY_PASS' if canary else 'COMPLETE'
    events = report.attrs.get('valuation_events', [])
    summary['terminal_writeoff'] = sum(e['loss'] for e in events if e['kind'] == 'terminal_zero_recovery')
    summary['unresolved_valuation'] = report.attrs.get('unresolved_valuation', {})
    summary['max_carried_sessions'] = max((e.get('sessions', 0) for e in events), default=0)
    if summary['unresolved_valuation']:
        summary['status'] = 'COMPLETE_WITH_UNRESOLVED_VALUATION'
    if canary:
        save_json(out/'summary.json', summary)
        return  # Do not interpret short-run performance or tune from it.
    yearly = pd.DataFrame([dict(year=y, **statistics(g), mean_holdings=float(counts.loc[g.index].mean()),
                                partial_year=(y == report.index[-1].year and report.index[-1].month < 12))
                           for y, g in report.groupby(report.index.year)])
    yearly.to_csv(out/'yearly.csv', index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    nav = report.account/config['account']
    benchmark = (1+report.bench).cumprod()
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(nav, label='Fixed tuned model, net')
    axes[0].plot(benchmark, label='CSI300')
    axes[0].legend()
    axes[0].set_ylabel('NAV')
    axes[1].fill_between(nav.index, nav/nav.cummax().clip(lower=1)-1, 0)
    axes[1].set_ylabel('Drawdown')
    fig.tight_layout()
    fig.savefig(out/'nav.png', dpi=160)
    plt.close(fig)
    text = f'''# 固定模型 Qlib 收尾回测

{summary['start']} — {summary['end']}；初始资金100,000元。固定最新已训练模型，无重训或调参。

- 扣费累计收益：{summary['total_return']:.2%}；CAGR：{summary['cagr']:.2%}。
- Sharpe（零无风险利率，252日年化）：{summary['sharpe']}；最大回撤：{summary['max_drawdown']:.2%}。
- 沪深300累计收益：{summary['benchmark_return']:.2%}。
- 显式交易费用：{summary['explicit_cost']:.2f}元；10bps单边滑点已计入成交价。
- 平均持仓：{summary['mean_holdings']:.2f}；平均现金比例：{summary['mean_cash_fraction']:.2%}。
- 退市零回收计提：{summary['terminal_writeoff']:.2f}元（已包含在净值损失中，不是交易费，不重复扣除）。
- 估值状态：{summary['status']}；期末仍缺行情持仓：{summary['unresolved_valuation']}；最长前价沿用：{summary['max_carried_sessions']}个交易日。

盈利：{'是' if summary['total_return'] > 0 else '否'}；跑赢沪深300：{'是' if summary['total_return'] > summary['benchmark_return'] else '否'}。
回撤是否可接受由个人风险承受能力决定，未预设通过线。逐年结果见yearly.csv，2026为不完整年度；
不把部分年度累计收益和完整年度直接比较。按年度列出结果供判断是否集中于少数时期，不据此调参。

## 已接受的近似
原生TopkDropout(8,1)，不是旧buffer策略；最低5元应用于合计费率，非逐项券商收费。
统一开盘±9.5%限制、100股单位不精确还原各板块/ST制度；使用复权行情，不另建公司行动账本。
前20日均量1%不是开盘竞价流动性保证。停牌/缺失行情按Qlib沿用前价并禁止成交，逐笔记录valuation_events.jsonl。
缺行情不等于已证明正常停牌；期末仍未恢复者明确标为估值未解决，相关净值为暂估，不能当作可清算价值。
已确认退市且无法退出者按用户接受的零回收假设计提，股数转入事件记录，不产生现金，不事后抹除历史持仓。
这是后续历史模拟，未证明此前所有项目研究都没有观察过该时期；不称全项目全新样本外证据。
固定模型未学习2023及以后新增训练样本。本结果只代表这一个模型和预先选定配置。
'''
    text += '\n## 逐年表现\n\n| 年份 | 扣费收益 | 沪深300 | 最大回撤 | 显式费用 |\n|---|---:|---:|---:|---:|\n'
    for row in yearly.itertuples():
        label = f'{row.year}' + ('（不完整）' if row.partial_year else '')
        text += f'| {label} | {row.total_return:.2%} | {row.benchmark_return:.2%} | {row.max_drawdown:.2%} | {row.explicit_cost:.2f} |\n'
    (out/'REPORT.md').write_text(text, encoding='utf-8')
    save_json(out/'summary.json', summary)  # Completion marker only after all result files exist.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['check', 'canary', 'run', 'backtest'], default='run')
    parser.add_argument('--config', default='configs/final_qlib_backtest.yaml')
    args = parser.parse_args()
    config = yaml.safe_load((ROOT/args.config).read_text(encoding='utf-8'))
    model_path = ROOT/config['model']
    if sha(model_path) != config['model_sha256']:
        raise ValueError('Saved model changed')
    model = lgb.Booster(model_file=str(model_path))
    factors = json.loads((ROOT/config['training_contract']).read_text())['factors']
    if isinstance(factors, dict):
        factors = factors['Broad494']
    if len(factors) != 494 or model.feature_name() != factors or model.current_iteration() != 150:
        raise ValueError('Not the intended 494-feature, 150-round model')
    partitions = pd.read_csv(ROOT/config['partitions'])
    qlib.init(provider_uri=str((ROOT/config['provider']).resolve()), region='cn',
              expression_cache=None, dataset_cache=None, kernels=1)
    out = ROOT/config['output']
    if args.mode == 'check':
        dates = pd.DatetimeIndex(['2023-12-28', '2023-12-29'])
        actual = predict(model, features(partitions, factors, dates), factors)
        expected = pd.read_parquet(model_path.parent/'engineering_predictions.parquet')
        expected = expected.loc[expected.datetime.isin(dates)].sort_values(KEYS).reset_index(drop=True)
        pd.testing.assert_frame_equal(actual.reset_index(drop=True), expected, check_exact=True)
        out.mkdir(parents=True, exist_ok=True)
        save_json(out/'prediction_check.json', dict(status='EXACT_PARITY', rows=len(actual), dates=[str(d.date()) for d in dates]))
        print('EXACT_PARITY', len(actual))
        return
    # Bound end by every required feature's declared coverage and the provider calendar.
    feature_end = min(max(pd.Timestamp(r.effective_end) for r in partitions.itertuples()
                          if f in r.factors.split(',')) for f in factors)
    end = min(pd.Timestamp(config['end']), feature_end)
    calendar = pd.DatetimeIndex(D.calendar(end_time=end, freq='day'))
    days = calendar[calendar >= pd.Timestamp(config['start'])]
    if args.mode == 'canary':
        days = days[:20]
        out = out/'canary'
    if days.empty:
        raise ValueError('No common backtest dates')
    signals = calendar[calendar.get_indexer(days)-1]
    prediction_dir = out
    if args.mode == 'backtest':
        original = json.loads((out/'run.json').read_text(encoding='utf-8'))
        original_config = dict(original['config'])
        current_config = {k: v for k, v in config.items() if k not in ('known_suspensions', 'terminal_events')}
        for key in ('known_suspensions', 'terminal_events'):
            original_config.pop(key, None)
        if (original_config != current_config or original['model_sha256'] != sha(model_path)
                or original['partitions_sha256'] != sha(ROOT/config['partitions'])
                or original['start'] != str(days[0].date()) or original['end'] != str(days[-1].date())):
            raise ValueError('Existing predictions do not match this model/config/date range')
        out = out/'backtest_terminal_v2'  # Preserve v1's provisional results and all predictions.
    out.mkdir(parents=True, exist_ok=True)
    binding = dict(config=config, model_sha256=sha(model_path), partitions_sha256=sha(ROOT/config['partitions']),
                   script_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
                   start=str(days[0].date()), end=str(days[-1].date()))
    if (out/'run.json').exists() and json.loads((out/'run.json').read_text(encoding='utf-8')) != binding:
        raise ValueError('Run inputs changed; preserve the old output and select a new output directory')
    save_json(out/'run.json', binding)
    if (out/'summary.json').exists():
        print('Already complete:', out)
        return
    try:
        chunks = []
        for month in signals.to_period('M').unique():
            path = prediction_dir/f'predictions_{month}.parquet'
            selected = signals[signals.to_period('M') == month]
            if not path.exists():
                if args.mode == 'backtest':
                    raise ValueError(f'Backtest-only mode cannot generate missing predictions: {path}')
                frame = predict(model, features(partitions, factors, selected), factors)
                tmp = path.with_suffix('.tmp')
                frame.to_parquet(tmp, index=False)
                tmp.replace(path)
            frame = pd.read_parquet(path)
            if frame.duplicated(KEYS).any() or not pd.DatetimeIndex(frame.datetime.unique()).equals(selected):
                raise ValueError(f'Invalid cached predictions: {path}')
            chunks.append(frame)
            action = 'Loaded existing predictions' if args.mode == 'backtest' else 'Predictions ready'
            print(f'{action}: {month}, rows={len(frame)}', flush=True)
        scores = pd.concat(chunks, ignore_index=True)
        report, positions = run_backtest(scores, days, config, carry_log=out/'valuation_events.jsonl')
        write_results(out, report, positions, config, canary=args.mode == 'canary')
        print('Complete:', out)
    except Exception as exc:
        save_json(out/'failure.json', dict(error=str(exc), type=type(exc).__name__))
        raise


if __name__ == '__main__':
    main()
