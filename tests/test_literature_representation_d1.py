"""Synthetic correctness/leakage tests; no project research values are read."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from factor_research import literature_inputs as inputs
from factor_research.literature_design import annotate, dense_identity
from factor_research.literature_representation import (
    average_children, bucket, digest, grid_center, legal_dates, rank_column, transform_day, validate_recipe,
)
from research_validation.literature_oracle import naive_day
from scripts.run_literature_representation_d1 import compare_oracle, sha, verify_chunk


def recipe():
    return dict(scope='D1_feature_only_candidate', d2_authorized=False,
        parents=['a','b','c','d','u'], u=['u'], representatives=['a','d'],
        diagnostic_policy=dict(rank_min=2, child_fraction=.5, family_fraction=.5),
        composites=[dict(id='composite', families=[
            dict(id='f1', members=[dict(factor='a', sign=1),dict(factor='b', sign=-1)]),
            dict(id='f2', members=[dict(factor='c', sign=1)]),
            dict(id='f3', members=[dict(factor='d', sign=1)])])],
        arms=dict(R=['a','d','u'], C=['composite','u'], H=['a','composite','d','u']))


def frame():
    return pd.DataFrame(dict(datetime=pd.to_datetime(['2023-12-29']*4), instrument=list('ABCD'),
        a=[1.,1.,3.,np.nan], b=[4.,4.,2.,0.], c=[1.,np.nan,3.,np.nan],
        d=[np.nan,1.,3.,np.nan], u=[0.,1.,np.nan,0.]))


def test_manual_average_ties_orientation_missing_and_hierarchy():
    actual, diag = transform_day(frame(), recipe())
    # a ranks [-1/6,-1/6,1/3,NaN], b ranks [1/4,1/4,-1/8,-3/8].
    # Three families require two; D has only f1 and must remain missing.
    wanted = np.array([(-5/24-1/4)/2, (-5/24-1/4)/2, (11/48+1/4+1/4)/3, np.nan])
    np.testing.assert_allclose(actual['C'].composite, wanted, rtol=0, atol=1e-15)
    compare_oracle(actual, naive_day(frame(), recipe()))
    assert diag['outputs'][0]['single_family_valid_rows'] == 0
    assert diag['outputs'][0]['needed_families'] == 2
    assert diag['leaves'][-1]['rank_reason'] == 'raw_U_not_ranked'
    np.testing.assert_equal(actual['C'].u.to_numpy(), frame().u.to_numpy())


@pytest.mark.parametrize('values,minimum,reason', [
    ([np.nan,np.inf],2,'all_missing'), ([4.,4.],2,'constant'),
    ([1.,2.],100,'below_rank_min'), ([1.,2.],2,'valid')])
def test_rank_failure_reasons(values, minimum, reason):
    values, stats = rank_column(values, minimum)
    assert stats['rank_reason'] == reason
    assert np.isfinite(values).any() == (reason == 'valid')


def test_rank_permutation_binary_ties_no_id_tiebreak():
    f = frame()
    r = recipe()
    original, _ = transform_day(f, r)
    permuted, _ = transform_day(f.iloc[[2,0,3,1]].reset_index(drop=True), r)
    for arm in original:
        pd.testing.assert_frame_equal(original[arm].sort_values('instrument').reset_index(drop=True),
                                      permuted[arm].sort_values('instrument').reset_index(drop=True))
    ranked, _ = rank_column([0.,0.,1.,1.], 2)
    np.testing.assert_array_equal(ranked, [-.25,-.25,.25,.25])


def test_family_nominal_weight_not_column_count_and_lower_median():
    x = np.array([-.2,.2])
    first, _, _ = average_children([x]*50,.5)
    second, _, _ = average_children([x*-1]*3,.5)
    composite, _, _ = average_children([first,second],.5)
    np.testing.assert_allclose(composite, 0, atol=1e-15)
    assert grid_center([2,3,4,5]) == 3
    assert grid_center([5,3,2,3,4]) == 3


def test_near_lag_can_change_value_but_not_fixed_active_family_weight():
    f1, _, _ = average_children([[-.2,.2]], .5)
    f1_new, _, _ = average_children([[-.2,.2],[.4,-.4]], .5)
    f2 = np.array([-.1,.1])
    before, _, _ = average_children([f1,f2],.5)
    after, _, _ = average_children([f1_new,f2],.5)
    np.testing.assert_allclose(after-before, .5*(f1_new-f1))
    assert not np.array_equal(before, after)


def test_revised_complete_family_policy_removes_semantic_drift():
    r = recipe()
    r['diagnostic_policy']['family_fraction'] = 1.
    actual, diag = transform_day(frame(), r)
    # Only C has all three families; A and B each lack one, D lacks two.
    np.testing.assert_array_equal(np.isfinite(actual['C'].composite), [False,False,True,False])
    compare_oracle(actual, naive_day(frame(),r))
    output = diag['outputs'][0]
    assert output['single_family_valid_rows'] == 0
    assert output['max_family_weight'] == 1/3
    assert output['mean_l1_weight_drift'] == 0
    assert output['raw_available_but_output_missing'] == 3


def test_exact_alias_removed_before_rank_values_masks_and_denominators():
    f = frame()
    f['alias'] = f.a
    rows = [dict(factor='a',exact_alias='a'),dict(factor='alias',exact_alias='a')]
    assert inputs.check_aliases(f,rows) == 1
    first, diag1 = transform_day(f[['datetime','instrument']+recipe()['parents']],recipe())
    second, diag2 = transform_day(frame(),recipe())
    assert diag1 == diag2
    for arm in first:
        pd.testing.assert_frame_equal(first[arm],second[arm])
    f.loc[0,'alias'] = np.nan
    with pytest.raises(ValueError,match='alias'):
        inputs.check_aliases(f,rows)


@pytest.mark.parametrize('lag,wanted', [(0,'d0'),(1,'d1_5'),(5,'d1_5'),(6,'d6_21'),(21,'d6_21'),(22,'d22_63'),(63,'d22_63')])
def test_horizon_edges(lag, wanted):
    assert bucket(lag) == wanted


def test_dense_formula_guard_and_non_dense_rolling_window():
    row = dict(factor='alpha360_CLOSE10',definition='Qlib Alpha360 expression: Ref($close, 10)/$close Alpha360 batch V4 passed.')
    assert dense_identity(row) == ('close',10)
    row['definition'] = 'Ref($close,10)/$open'
    with pytest.raises(ValueError,match='formula'):
        dense_identity(row)
    assert dense_identity(dict(factor='alpha158_STD20',definition='Std($close,20)/$close')) is None


@pytest.mark.parametrize('dates', [[],['2024-01-02'],['2009-12-31'],['2023-01-04','2023-01-03'],
    ['2023-01-03','2023-01-03'],['2023-01-03 12:00:00'],[pd.NaT]])
def test_dates_fail_before_any_io(monkeypatch, dates):
    def forbidden(*args, **kwargs):
        raise AssertionError('I/O reached')
    monkeypatch.setattr(inputs,'read_effective_partition',forbidden)
    with pytest.raises(ValueError):
        inputs.read_features(None,['a'],dates,approved=['a'],access=forbidden)


def test_label_projection_fails_before_io():
    with pytest.raises(ValueError,match='projection'):
        inputs.read_features(None,['label_20d_t1'],['2023-12-29'],approved=['a'],access=lambda _:None)


def test_reader_pushes_bounds_and_columns_into_io(monkeypatch):
    seen = []
    def bounded(row, columns):
        assert row['effective_end'] == pd.Timestamp('2023-12-29')
        assert columns == ['a']
        seen.append(row)
        return frame()[['datetime','instrument','a']]
    monkeypatch.setattr(inputs,'read_effective_partition',bounded)
    parts = pd.DataFrame([dict(factors='a,label_20d_t1',effective_start='2021-01-01',
        effective_end='2026-06-09',partition_path='metadata_only_path',output_sha256='parent')])
    events = []
    actual = inputs.read_features(parts,['a'],['2023-12-29'],approved=['a'],access=events.append)
    assert len(seen)==1 and actual.shape==(4,3) and len(events)==2


@pytest.mark.parametrize('mutation', ['duplicate','unsigned','arm','outcome','raw_overlap'])
def test_recipe_rejects_invalid_identity_or_authority(mutation):
    r = recipe()
    if mutation=='duplicate':
        r['composites'][0]['families'][1]['members'][0]['factor']='a'
    elif mutation=='unsigned':
        r['composites'][0]['families'][0]['members'][0]['sign']=0
    elif mutation=='arm':
        r['arms']['H'].remove('a')
    elif mutation=='outcome':
        r['outcomes_authorized']=True
    else:
        r['u'].append('a')
    with pytest.raises(ValueError):
        validate_recipe(r)


def test_oracle_detects_sign_and_mask_mutations():
    r = recipe()
    actual,_=transform_day(frame(),r)
    bad=deepcopy(r)
    bad['composites'][0]['families'][0]['members'][0]['sign']=-1
    with pytest.raises(ValueError,match='value'):
        compare_oracle(actual,naive_day(frame(),bad))
    actual['C'].loc[3,'composite']=0
    with pytest.raises(ValueError,match='mask'):
        compare_oracle(actual,naive_day(frame(),r))


def test_schema_and_float64_are_strict():
    f=frame()
    with pytest.raises(ValueError,match='ordered'):
        transform_day(f.assign(label=0),recipe())
    f.a=f.a.astype('float32')
    with pytest.raises(ValueError,match='float64'):
        transform_day(f,recipe())


def test_source_library_names_do_not_enter_weights_and_hash_is_deterministic():
    r=recipe()
    before,_=transform_day(frame(),r)
    r['composites'][0]['source']='renamed_library'
    after,_=transform_day(frame(),r)
    compare_oracle(before,after)
    assert digest({'b':2,'a':1})==digest({'a':1,'b':2})
    assert digest(['a','b'])!=digest(['b','a'])


def test_resume_detects_corruption(tmp_path):
    names=['leaves.parquet','families.parquet','outputs.parquet','arms.parquet','access.jsonl']
    for name in names:
        (tmp_path/name).write_bytes(b'fixture')
    receipt=dict(binding={'recipe':'x'},dates=['2023-12-29'],oracle='pass',
        files={name:sha(tmp_path/name) for name in names})
    (tmp_path/'receipt.json').write_text(json.dumps(receipt))
    verify_chunk(tmp_path,{'recipe':'x'},legal_dates(['2023-12-29']))
    (tmp_path/'outputs.parquet').write_bytes(b'changed')
    with pytest.raises(ValueError,match='corrupt'):
        verify_chunk(tmp_path,{'recipe':'x'},legal_dates(['2023-12-29']))


def test_d1_imports_exclude_training_and_outcome_modules():
    import ast
    paths=['factor_research/literature_inputs.py','factor_research/literature_design.py',
        'factor_research/literature_representation.py','research_validation/literature_oracle.py',
        'scripts/run_literature_representation_d1.py']
    root=Path(__file__).resolve().parents[1]
    for path in paths:
        tree=ast.parse((root/path).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            names=([node.module] if isinstance(node,ast.ImportFrom) else
                   [a.name for a in node.names] if isinstance(node,ast.Import) else [])
            assert all(not any(bad in (name or '') for bad in
                ['lightgbm','model_research','labels','long_history_screening','precompute']) for name in names)


def test_unknown_new_U_identity_is_not_automatically_admitted():
    row=dict(factor='ta_unknown',mechanism='unknown',replacement_hold_reason='provider_price_scale_unverified',definition='unknown')
    with pytest.raises(ValueError,match='unreviewed U'):
        annotate(row)
