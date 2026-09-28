"""Small real-Qlib tests; no training and no project market data."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest
import qlib
import yaml

from scripts.final_qlib_backtest import ROOT, features, predict, run_backtest, statistics, write_results


@pytest.fixture
def market(tmp_path):
    calendar = pd.bdate_range('2024-01-01', periods=32)
    (tmp_path/'calendars').mkdir()
    (tmp_path/'instruments').mkdir()
    (tmp_path/'calendars/day.txt').write_text('\n'.join(str(d.date()) for d in calendar))
    codes = ['SH600000', 'SH600001', 'SH000300']
    (tmp_path/'instruments/all.txt').write_text('\n'.join(f'{c}\t{calendar[0].date()}\t{calendar[-1].date()}' for c in codes))
    values = {c: {f: np.full(len(calendar), value, dtype='float32') for f, value in
                 dict(open=10, close=10, high=10, low=10, factor=1, volume=1_000_000, change=0).items()} for c in codes}

    def setup(changes=None):
        changed = deepcopy(values)
        for code, field, index, value in changes or []:
            changed[code][field][index] = value
        for code, fields in changed.items():
            folder = tmp_path/'features'/code.lower()
            folder.mkdir(parents=True, exist_ok=True)
            for field, v in fields.items():
                np.r_[np.float32(0), v].astype('<f4').tofile(folder/f'{field}.day.bin')
        qlib.init(provider_uri=str(tmp_path), region='cn', expression_cache=None, dataset_cache=None, kernels=1)
        config = yaml.safe_load((ROOT/'configs/final_qlib_backtest.yaml').read_text())
        config['strategy']['topk'] = 1
        return config
    scores = pd.DataFrame([(calendar[i], code, float((i % 2 == 0) == (code == codes[0])))
                           for i in range(24, 28) for code in codes[:2]], columns=['datetime', 'instrument', 'score'])
    return calendar, scores, setup


def test_native_lag_lots_fees_slippage_cash(market, tmp_path):
    cal, scores, setup = market
    config = setup()
    report, positions = run_backtest(scores, cal[25:29], config)
    first = positions[cal[25]]
    assert first.get_stock_list() == ['SH600000']  # Previous signal; today's prefers SH600001.
    assert first.get_stock_amount('SH600000') == 9400
    buy_price, sell_price = float(np.float32(10.01)), float(np.float32(9.99))
    spent = 9400 * buy_price  # Native Qlib expressions use provider float32 precision.
    fee = spent * 0.00026
    assert first.get_cash() == pytest.approx(100000-spent-fee)
    assert report.loc[cal[25], 'account'] == pytest.approx(100000-9400*(buy_price-10)-fee)
    assert positions[cal[26]].get_stock_list() == ['SH600001']
    sale = 9400*sell_price
    cash = 100000-spent-fee + sale - sale*0.00076
    bought = np.floor(cash*0.95/buy_price/100)*100
    expected_cash = cash-bought*buy_price-max(5, bought*buy_price*0.00026)
    assert positions[cal[26]].get_cash() == pytest.approx(expected_cash)
    write_results(tmp_path, report, positions, config)
    assert (tmp_path/'nav.png').is_file()
    assert (tmp_path/'REPORT.md').is_file()
    assert statistics(report)['explicit_cost'] == pytest.approx(report.total_cost.iloc[-1])


def test_missing_open_never_falls_back_to_close(market):
    cal, scores, setup = market
    cfg = setup([('SH600000', 'open', 25, np.nan)])
    report, pos = run_backtest(scores, cal[25:26], cfg)
    assert not pos[cal[25]].get_stock_list()
    assert report.account.iloc[0] == 100000


def test_missing_factor_rejects_fractional_lots(market):
    cal, scores, setup = market
    cfg = setup([('SH600000', 'factor', 25, np.nan)])
    with pytest.raises(ValueError, match='Invalid factor'):
        run_backtest(scores, cal[25:26], cfg)


def test_open_limit_does_not_use_close_change(market):
    cal, scores, setup = market
    cfg = setup([('SH600000', 'change', 25, 0.2)])
    _, pos = run_backtest(scores, cal[25:26], cfg)
    assert pos[cal[25]].get_stock_list() == ['SH600000']
    cfg = setup([('SH600000', 'open', 25, 11)])
    _, pos = run_backtest(scores, cal[25:26], cfg)
    assert not pos[cal[25]].get_stock_list()


def test_invalid_nonpositive_valuation_stops(market):
    cal, scores, setup = market
    cfg = setup([('SH600000', 'close', 26, 0)])
    with pytest.raises(ValueError, match=f'Unvalued holding: {cal[26].date()} SH600000'):
        run_backtest(scores, cal[25:27], cfg)


def test_native_suspension_carries_then_resumes(market, tmp_path):
    cal, scores, setup = market
    cfg = setup([('SH600000', 'close', 26, np.nan), ('SH600000', 'open', 26, np.nan)])
    scores.loc[scores.datetime <= cal[26], 'score'] = scores.instrument.map({'SH600000': 1, 'SH600001': 0})
    log = tmp_path/'carry.jsonl'
    report, pos = run_backtest(scores, cal[25:29], cfg, carry_log=log)
    assert pos[cal[26]].get_stock_amount('SH600000') == 9400
    assert report.account.iloc[1] == report.account.iloc[0]
    assert report.total_cost.iloc[1] == report.total_cost.iloc[0]
    assert log.read_text().count('SH600000') == 1
    assert pos[cal[27]].get_stock_amount('SH600000') == 9400  # Missing previous close still blocks this day.
    assert pos[cal[28]].get_stock_list() == ['SH600001']


def test_terminal_loss_no_cash_no_reentry_no_repeated_writeoff(market, tmp_path):
    cal, scores, setup = market
    cfg = setup()  # Even a stale positive provider quote cannot enable a terminal sale/re-entry.
    cfg['terminal_events'] = {'SH600000': str(cal[26].date())}
    scores = scores.loc[scores.instrument == 'SH600000']
    report, pos = run_backtest(scores, cal[25:29], cfg, carry_log=tmp_path/'events.jsonl')
    events = report.attrs['valuation_events']
    assert len(events) == 1 and events[0]['kind'] == 'terminal_zero_recovery'
    assert events[0]['amount'] == 9400 and events[0]['loss'] == 94000
    assert events[0]['cash_recovery'] == 0
    assert pos[cal[25]].get_stock_amount('SH600000') == 9400  # History is not retroactively excluded.
    for day in cal[26:29]:
        assert not pos[day].get_stock_list()
        assert pos[day].get_cash() == pos[cal[25]].get_cash()
    assert report.account.iloc[1] == pytest.approx(report.account.iloc[0]-94000)
    assert report.total_cost.iloc[1] == report.total_cost.iloc[0]
    assert report.total_turnover.iloc[1] == report.total_turnover.iloc[0]


def test_unresolved_carry_is_explicit_in_final_summary(market, tmp_path):
    cal, scores, setup = market
    cfg = setup([('SH600000', 'close', 26, np.nan), ('SH600000', 'open', 26, np.nan)])
    scores = scores.loc[scores.instrument == 'SH600000']
    report, pos = run_backtest(scores, cal[25:27], cfg)
    write_results(tmp_path, report, pos, cfg)
    import json
    result = json.loads((tmp_path/'summary.json').read_text())
    assert result['status'] == 'COMPLETE_WITH_UNRESOLVED_VALUATION'
    assert result['unresolved_valuation'] == {'SH600000': 1}
    assert result['max_carried_sessions'] == 1


def test_held_stock_leaving_signal_persists_if_sale_blocked(market):
    cal, scores, setup = market
    cfg = setup([('SH600000', 'open', 26, np.nan)])
    scores = scores.loc[~((scores.datetime == cal[25]) & (scores.instrument == 'SH600000'))]
    _, pos = run_backtest(scores, cal[25:27], cfg)
    assert pos[cal[26]].get_stock_amount('SH600000') == 9400


def test_previous_adv_caps_trade_not_today_volume(market):
    cal, scores, setup = market
    changes = [('SH600000', 'volume', i, 20000) for i in range(25)]
    cfg = setup(changes)
    report, pos = run_backtest(scores, cal[25:26], cfg)
    assert pos[cal[25]].get_stock_amount('SH600000') == 200
    assert report.total_cost.iloc[0] == pytest.approx(5)


def test_feature_projection_and_prediction_schema(tmp_path):
    days = pd.DatetimeIndex(['2024-01-02', '2024-01-03'])
    frame = pd.DataFrame(dict(datetime=days, instrument=['SH600000']*2, a=[1, np.inf], b=[2, 3]))
    path = tmp_path/'features.parquet'
    frame.to_parquet(path)
    partitions = pd.DataFrame([dict(partition_path=str(path), effective_start=days[0], effective_end=days[-1], factors='a,b')])
    actual = features(partitions, ['b', 'a'], days)
    assert list(actual) == ['datetime', 'instrument', 'b', 'a']
    class Model:
        def feature_name(self): return ['b', 'a']
        def predict(self, matrix, **kwargs):
            assert matrix.dtype == np.float64
            assert np.isnan(matrix[1, 1])
            return matrix[:, 0]
    assert predict(Model(), actual, ['b', 'a']).score.tolist() == [2, 3]
    with pytest.raises(ValueError, match='order mismatch'):
        predict(Model(), actual, ['a', 'b'])


def test_drawdown_includes_starting_cash_and_cost():
    frame = pd.DataFrame(dict(account=[90000, 99000], cash=[0, 0], return_=[-.09, .1], cost=[.01, 0],
                              total_cost=[1000, 1000], bench=[0, 0], turnover=[1, 0])).rename(columns={'return_': 'return'})
    result = statistics(frame)
    assert result['max_drawdown'] == pytest.approx(-.1)
    assert result['total_return'] == pytest.approx(-.01)
