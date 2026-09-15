import copy
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from qlib_integration.economic_strategy_membership import (
    Slot, rank_scores, plan_membership, eligible_buys, confirm_membership,
)
from qlib_integration.economic_mvp_scope import Decision
from qlib_integration.economic_strategy_budget import entry_quantity, personal_fees
from qlib_integration.economic_execution_contract import MotherOrderFees
from model_research.economic_e3_projection import project, summarize


def make_plan(ranked, slots=(), *, gates=None, exits=None, identities=None, first=False):
    ids = identities or {s: s for s in ranked}
    return plan_membership(ranked, slots, gates if gates is not None else {
        s: Decision("ALLOW_ENTRY", ()) for s in ranked}, exits if exits is not None else {
        s.instrument: Decision("ORDINARY_EXECUTION_CANDIDATE", ()) for s in slots}, ids,
        first_decision=first)


def test_tie_and_score_integrity():
    assert rank_scores([("B", 1), ("A", 1), ("C", 2)]) == ["C", "A", "B"]
    for bad in ([('A', 1), ('A', 2)], [('A', float('nan'))], []):
        with pytest.raises(ValueError):
            rank_scores(bad)


def test_initialization_is_not_repeated_after_failure():
    ranked = [str(i) for i in range(20)]
    first = make_plan(ranked, first=True)
    assert len(eligible_buys(first, ())) == 8
    assert confirm_membership(first, (), {s: s for s in ranked}) == ()
    next_plan = make_plan(ranked)
    assert len(eligible_buys(next_plan, ())) == 1


def test_buffer_missing_exit_order_and_cap():
    ranked = [str(i) for i in range(30)]
    slots = tuple(Slot(s, s) for s in ['8', '15', '16', '29', 'Z', 'Y'])
    p = make_plan(ranked, slots)
    assert p.sell == 'Y' and p.buffer_retained == 2 and p.exit_backlog == 3
    assert len(eligible_buys(p, slots, full_sale_confirmed=True)) == 1


@pytest.mark.parametrize('action', ['CARRY_ONLY', 'unknown', 'NO_NEW_ENTRY'])
def test_blocked_sell_retains_slot_and_blocks_other_vacancy(action):
    slots = (Slot('old', 'old'),)
    p = make_plan(['new'], slots, exits={'old': Decision(action, ())})
    assert p.blocked_exit and eligible_buys(p, slots) == ()
    assert confirm_membership(p, slots, {'new': 'new'}) == slots
    with pytest.raises(ValueError):
        confirm_membership(p, slots, {'new': 'new'}, full_sale_confirmed=True)


def test_partial_sale_and_failed_entry_do_not_create_exposure():
    slots = (Slot('old', 'old'),)
    p = make_plan(['new'], slots)
    assert not eligible_buys(p, slots, full_sale_confirmed=False)
    assert confirm_membership(p, slots, {'new': 'new'}, full_sale_confirmed=True) == ()
    with pytest.raises(ValueError):
        confirm_membership(p, slots, {'new': 'new'}, bought=('new',))


def test_pending_right_occupies_slot_after_full_sale():
    slots = tuple(Slot(str(i), str(i), True, True) for i in range(8))
    ranked = [f'n{i}' for i in range(8)]
    p = make_plan(ranked, slots)
    assert eligible_buys(p, slots, full_sale_confirmed=True) == ()
    after = confirm_membership(p, slots, {s: s for s in ranked}, full_sale_confirmed=True)
    assert len(after) == 8 and sum(s.has_shares for s in after) == 7
    assert all(s.pending_rights for s in after)


def test_alias_gate_never_reranks_or_uses_ninth():
    ranked = [str(i) for i in range(20)]
    slots = (Slot('old', 'economic0', False, True),)
    ids = {s: s for s in ranked}
    ids['0'] = 'economic0'
    gates = {s: Decision('NO_NEW_ENTRY', ('unresolved',)) for s in ranked[:8]}
    gates['9'] = Decision('ALLOW_ENTRY', ())
    p = make_plan(ranked, slots, gates=gates, identities=ids)
    assert p.entries == () and len(p.rejected) == 8
    assert p.rejected[0][1] == 'duplicate_or_unknown_economic_identity'
    p = make_plan(ranked, gates={})
    assert p.entries == ()


def test_held_halt_and_alias_fail_closed():
    with pytest.raises(ValueError, match='HALT_RETAIN'):
        make_plan(['A'], (Slot('X', 'X'),), exits={'X': Decision('HALT_RETAIN', ('unknown_right',))})
    with pytest.raises(ValueError, match='HALT_RETAIN'):
        make_plan(['A'], (Slot('X', 'same'), Slot('Y', 'same')))


def test_early_par_value_and_fee_boundaries():
    with pytest.raises(ValueError, match='par value'):
        personal_fees('2015-01-06', 'SH')
    assert personal_fees('2015-01-06', 'SH', verified_par_value=1)['transfer_basis'] == 'par_value_cny'
    assert personal_fees('2015-01-06', 'SZ')['transfer_rate'] == 0.0000255
    assert personal_fees('2015-08-03', 'SH')['transfer_rate'] == 0.00002
    assert personal_fees('2022-04-29', 'SH')['transfer_rate'] == 0.00001
    assert personal_fees('2023-08-28', 'SH')['stamp_rate'] == 0.0005
    with pytest.raises(ValueError):
        personal_fees('2024-01-02', 'SH')


def test_budget_fee_reserve_no_credit_and_board_lot():
    fee = personal_fees('2020-08-24', 'SH')
    args = dict(prior_close=10, certified_base=100000, spendable_cash=100000, board='main', fee=fee, adv20=1000000)
    assert entry_quantity(**args) == 1100
    assert entry_quantity(**dict(args, spendable_cash=5000)) == 0
    assert entry_quantity(**dict(args, prior_close=60, board='star')) == 0
    assert entry_quantity(**dict(args, adv20=10000)) == 100
    charges, _ = MotherOrderFees().quote('one', 11000, 1100, 'buy', fee, 10)
    assert charges == dict(commission=5.0, stamp=0.0, transfer=0.22, implicit=11.0)
    ledger = MotherOrderFees()
    a, pending = ledger.quote('one', 5000, 500, 'buy', fee, 10)
    ledger.commit('one', pending)
    b, _ = ledger.quote('one', 6000, 600, 'buy', fee, 10)
    assert {k: round(a[k] + b[k], 2) for k in a} == charges


def synthetic_scores():
    calendar = pd.bdate_range('2015-12-16', periods=45)
    records = []
    for i, date in enumerate(calendar):
        for j in range(25):
            records.append(dict(datetime=date, instrument=f'S{j:02}', score=float((j + i) % 25)))
    return pd.DataFrame(records), calendar


def test_projection_independent_oracle_calendar_and_censoring():
    data, calendar = synthetic_scores()
    rows, spells = project(data, calendar)
    path = Path(__file__).resolve().parents[1] / 'scripts/verify_e3_structure.py'
    spec = importlib.util.spec_from_file_location('independent_e3', path)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    summary = summarize(rows, spells)
    assert oracle.verify_targets(data, calendar, rows, spells, summary)['target_sessions'] == 45
    assert summary['model_boundaries'] == 1 and summary['right_censored_spells'] == 8
    assert rows[0]['slots'] == 0 and rows[1]['slots'] == 8
    assert all(rows[i]['before'] == rows[i - 1]['after'] for i in range(1, len(rows)))
    broken = copy.deepcopy(rows)
    broken[2]['after'] = []
    with pytest.raises(AssertionError):
        oracle.verify_targets(data, calendar, broken, spells, summary)


def test_projection_forbids_outcome_column_and_calendar_gaps():
    data, calendar = synthetic_scores()
    with pytest.raises(ValueError, match='only B'):
        project(data.assign(label=0), calendar)
    with pytest.raises(ValueError, match='missing score'):
        project(data[data.datetime.ne(calendar[2])], calendar)
    with pytest.raises(ValueError, match='bounded calendar'):
        project(data, pd.bdate_range('2024-01-01', periods=45))


def test_original_and_recovered_state_receipt_paths():
    path = Path(__file__).resolve().parents[1] / 'scripts/preflight_e3_structure.py'
    spec = importlib.util.spec_from_file_location('preflight_e3', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    for name in ['SH600000.parquet', 'data.parquet']:
        resolved, digest = runner.state_data_path(Path('local/receipt.json'),
            dict(status='complete', files={name: 'hash'}), 'SH600000')
        assert resolved == Path('local') / name and digest == 'hash'
    with pytest.raises(ValueError):
        runner.state_data_path(Path('local/receipt.json'),
            dict(status='complete', files={'../data.parquet': 'hash'}), 'SH600000')
