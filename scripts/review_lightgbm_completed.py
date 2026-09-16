"""Read-only completed-run audit. No training, feature reads or artifact mutation.

Writes review evidence separately from the sealed run. All statistics below are
computed independently of the training/selection/evaluation implementation.
"""
from pathlib import Path
import hashlib
import json
import math

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'outputs/lightgbm_hyperparameter_research/lgbm_nested_20260916_v1'
BASE = ROOT / 'outputs/research_protocol_v3_precompute/v3_precompute_broad494_strict332_20260909_v1'
DEST = ROOT / 'reports/lightgbm_hyperparameter_research_v1/final_review'
KEYS = ['datetime', 'instrument']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def close(a, b):
    np.testing.assert_allclose(a, b, atol=1e-12, rtol=0, equal_nan=True)


def hac20(x):
    x = np.asarray(x, dtype=float)
    valid = np.isfinite(x)
    n = int(valid.sum())
    mean = float(x[valid].mean())
    residual = np.where(valid, x - mean, 0.)
    # Scalar lag products preserve every missing session position.
    meat = sum(v*v for v in residual)
    for lag in range(1, 21):
        meat += 2*(1-lag/21)*sum(residual[i]*residual[i-lag] for i in range(lag, len(x)))
    se = math.sqrt(meat)/n
    return dict(mean=mean, n=n, se=se, p=math.erfc(abs(mean)/se/math.sqrt(2)),
                ci95_low=mean-1.959963984540054*se, ci95_high=mean+1.959963984540054*se)


def main():
    contract = read(RUN/'contract.json')
    bound = canonical(contract)
    checked, retired = {}, []

    def receipt(folder, expected, retirement=None):
        rec = read(folder/'receipt.json')
        assert rec['status'] == 'complete' and rec['contract_hash'] == expected, folder
        checked[str((folder/'receipt.json').relative_to(ROOT))] = sha(folder/'receipt.json')
        for name, digest in rec['file_hashes'].items():
            p = folder/name
            if not p.exists() and retirement and name in retirement['files']:
                assert name.endswith('.float64') and retirement['files'][name] == digest
                retired.append(str(p.relative_to(ROOT)))
            else:
                assert sha(p) == digest, p
                checked[str(p.relative_to(ROOT))] = digest

    for name, digest in contract['code_lf'].items():
        assert hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest, name
    assert canonical(read(BASE/'contract.json')) == contract['baseline_hash']
    source = ROOT/'outputs/research_protocol_v3_mvp/v3_recompute_audit_20260909_v1'
    assert canonical(read(source/'contract.json')) == contract['source_hash']
    receipt(source/'p0', contract['source_hash'])
    intervals = pd.read_csv(source/'p0/intervals.csv', parse_dates=['feature_time', 'label_end_time']).set_index('feature_time')
    assignments = pd.read_csv(source/'p0/assignments.csv', parse_dates=['datetime'])
    for year, digest in contract['audit_receipts'].items():
        assert sha(source/'audit'/year/'receipt.json') == digest
    receipt(RUN/'verification', bound)
    receipt(RUN/'evaluation', bound)
    receipt(BASE/'verification/Broad494', contract['baseline_hash'])
    replay = read(RUN/'verification/result.json')
    replay_access = read(RUN/'verification/access.json')
    assert replay['status'] == 'all_nine_exact' and len(replay['folds']) == 9
    summary = read(RUN/'evaluation/summary.json')
    daily = pd.read_csv(RUN/'evaluation/daily.csv', parse_dates=['datetime'])
    assert daily.datetime.is_monotonic_increasing and not daily.datetime.duplicated().any()
    assert daily.datetime.dt.year.min() == 2015 and daily.datetime.dt.year.max() == 2023
    accesses = {x['fold']: x for x in read(RUN/'evaluation/access.json')}
    trials, selections, resources = [], [], []
    for year in range(2015, 2024):
        fold = f'annual_{year}'
        root = RUN/fold
        retirement = read(root/'cache_retirement.json')
        assert sha(root/'cache/receipt.json') == retirement['cache_receipt_sha256']
        receipt(root/'cache', bound, retirement)
        split = contract['splits'][fold]
        train, valid = pd.to_datetime(split['train']), pd.to_datetime(split['valid'])
        assert train.min().year == 2010 and train.max() < valid.min()
        assert intervals.loc[train, 'label_end_time'].max() < valid.min()
        assert intervals.loc[valid, 'label_end_time'].max() < pd.Timestamp(f'{year}-01-01')
        legal = assignments.loc[assignments.fold_id.eq(fold) & assignments.role.eq('train'), 'datetime']
        assert set(train) <= set(legal) and set(valid) == set(legal[legal.dt.year.eq(year-1)])
        assert set(train) == set(legal[(legal < valid.min()) & (legal.map(intervals.label_end_time) < valid.min())])
        for entries, maxyear in [(read(root/'cache/access.json'), year-1),
                                  (read(root/'outer/access.json')['access'], year),
                                  (replay_access[fold], year)]:
            for entry in entries:
                assert pd.Timestamp(entry['start']).year >= 2010
                assert pd.Timestamp(entry['end']).year <= maxyear
                assert entry['kind'] in ['feature', 'keys']
        keys = pd.read_parquet(root/'cache/inner_valid_keys.parquet')
        target = np.load(root/'cache/inner_valid_target.npy')
        assert keys.datetime.dt.year.eq(year-1).all()
        assert keys.datetime.drop_duplicates().dt.strftime('%Y-%m-%d').tolist() == split['valid']
        foldrows = []
        for name, changes in contract['trials']:
            p = root/'trials'/name
            receipt(p, bound)
            r = read(p/'result.json')
            assert r['ordered_features'] == contract['factors'] and not r['outer_labels_accessed']
            assert r['changes'] == changes
            frame = pd.read_parquet(p/'inner_predictions.parquet')
            assert frame[KEYS].equals(keys[KEYS]) and not frame[KEYS].duplicated().any()
            close(frame.target, target)
            assert np.isfinite(frame[['target', 'score']]).all().all()
            values, dates, constants = [], [], 0
            for date, part in frame.groupby('datetime', sort=True):
                constant = part.score.nunique() < 2 or part.target.nunique() < 2
                constants += int(constant)
                values.append(0. if constant else spearmanr(part.score, part.target).statistic)
                dates.append(date)
            values = np.array(values)
            stored = pd.read_csv(p/'daily.csv', parse_dates=['datetime'])
            assert stored.datetime.tolist() == dates
            close(stored.ic, values)
            close(r['mean_ic'], values.mean())
            close(r['icir'], values.mean()/values.std(ddof=1))
            assert constants == r['constant_days'] and len(values) == r['dates']
            for half in [1, 2]:
                v = values[(pd.DatetimeIndex(dates).month <= 6) == (half == 1)]
                close(r['half_year'][str(half)]['mean_ic'], v.mean())
                close(r['half_year'][str(half)]['icir'], v.mean()/v.std(ddof=1))
            curve = np.array(read(p/'curve.json')['inner']['mean_daily_rank_ic'])
            rounds = 100 if name == 'fixed100' else int(curve.argmax()+1)
            assert rounds == r['rounds'] and len(curve) == r['iterations_evaluated']
            close(curve[rounds-1], values.mean())
            assert r['budget_exhausted'] == (name != 'fixed100' and len(curve) == 800)
            model = lgb.Booster(model_file=str(p/'model.txt'))
            assert model.num_trees() == rounds and model.num_feature() == 494
            row = {k: v for k, v in r.items() if k not in ['ordered_features', 'half_year', 'changes']}
            row.update(year=year, half1_ic=r['half_year']['1']['mean_ic'], half2_ic=r['half_year']['2']['mean_ic'])
            trials.append(row); foldrows.append(row)
        best = max(r['mean_ic'] for r in foldrows)
        plateau = [r for r in foldrows if r['mean_ic'] >= best-.001]
        selected = min(plateau, key=lambda r: (r['leaves']*r['rounds'], r['leaves'], r['rounds'], foldrows.index(r)))
        receipt(root/'selection', bound)
        choice = read(root/'selection/selection.json')
        assert choice == summary['choices'][fold]
        assert choice['selected'] == selected['trial'] and choice['rounds'] == selected['rounds']
        assert choice['plateau'] == [r['trial'] for r in plateau] and not choice['outer_outcomes_used']
        close(choice['inner_best_mean'], best)
        selections.append(dict(year=year, **choice, selected_inner_ic=selected['mean_ic'], budget_exhausted=selected['budget_exhausted']))
        receipt(root/'outer', bound)
        receipt(BASE/'Broad494'/fold, contract['baseline_hash'])
        resource = read(root/'outer/resource.json')
        oldresource = read(BASE/'Broad494'/fold/'resource.json')
        assert resource['batch_receipts'] == oldresource['batch_receipts']
        assert resource['ordered_features'] == contract['factors'] and not resource['outer_labels_accessed']
        assert resource['actual_iterations'] == choice['rounds']
        model = lgb.Booster(model_file=str(root/'outer/model.txt'))
        assert hashlib.sha256(model.model_to_string().encode()).hexdigest() == resource['model_sha256']
        verification = next(x for x in replay['folds'] if x['fold'] == fold)
        assert verification['exact'] and verification['model_sha256'] == resource['model_sha256']
        old = pd.read_parquet(BASE/'Broad494'/fold/'engineering_predictions.parquet')
        new = pd.read_parquet(root/'outer/engineering_predictions.parquet')
        assert old[KEYS+['reason']].equals(new[KEYS+['reason']])
        assert np.array_equal(np.isfinite(old.score), np.isfinite(new.score))
        assert len(new) == verification['rows']
        access = accesses[fold]
        labelpath = Path(access['path'])
        assert labelpath.parent.name == str(year) and sha(labelpath) == access['sha256']
        assert sha(labelpath.parent/'receipt.json') == contract['audit_receipts'][str(year)]
        permitted = pd.to_datetime(access['dates'])
        assert (permitted.year == year).all()
        labels = pd.read_parquet(labelpath, filters=[('datetime', 'in', permitted.tolist())])
        assert labels.exit_date.max() <= pd.Timestamp('2023-12-31')
        labelcol = next(c for c in labels if c not in KEYS+['exit_date'])
        assert labels[KEYS].equals(old.loc[old.datetime.isin(permitted), KEYS].reset_index(drop=True))
        paired = old[KEYS].assign(baseline=old.score, tuned=new.score).merge(labels, on=KEYS, how='left', validate='one_to_one')
        saved = daily.loc[daily.fold.eq(fold)].set_index('datetime')
        for date, part in paired.groupby('datetime', sort=True):
            mask = np.isfinite(part[[labelcol, 'baseline', 'tuned']]).all(axis=1)
            d = saved.loc[date]
            assert d.canonical_count == len(part) and d.common_count == mask.sum()
            assert d.finite_prediction == np.isfinite(part.baseline).sum()
            assert d.finite_label == np.isfinite(part[labelcol]).sum()
            common = part.loc[mask]
            for arm in ['baseline', 'tuned']:
                v = spearmanr(common[labelcol], common[arm]).statistic if len(common) >= 100 else np.nan
                close(v, d[arm])
            close(d.delta, d.tuned-d.baseline)
        resources.append(dict(year=year, **{k: resource[k] for k in ['actual_iterations', 'fit_rows', 'fit_seconds', 'peak_rss_mib', 'prediction_rows']}))
        print(f'{fold}: all nine inner trials, selection, outer and paired IC verified', flush=True)
    frame = pd.DataFrame(trials)
    assert len(frame) == 81
    # All persisted summary trial records must match the primary result artifacts.
    for r in summary['trials']:
        assert {k: v for k, v in r.items() if k != 'fold'} == read(RUN/r['fold']/'trials'/r['trial']/'result.json')
    periods = [('overall', daily)] + [(str(y), p) for y, p in daily.groupby(daily.datetime.dt.year)]
    periods += [(f'{y}-{y+2}', daily.loc[daily.datetime.dt.year.between(y, y+2)]) for y in [2015, 2018, 2021]]
    stability = []
    for period, part in periods:
        row = dict(period=period, **hac20(part.delta))
        for arm in ['baseline', 'tuned']:
            values = part[arm].dropna()
            row[arm+'_ic'] = float(values.mean())
            row[arm+'_icir'] = float(values.mean()/values.std(ddof=1))
            expected = next(r for r in summary['descriptive'] if r['period'] == period and r['arm'] == arm)
            close(expected['mean_ic'], row[arm+'_ic']); close(expected['icir'], row[arm+'_icir'])
            assert expected['dates'] == len(values)
            close(expected['prediction_coverage'], part.finite_prediction.sum()/part.canonical_count.sum())
            close(expected['common_coverage'], part.common_count.sum()/part.canonical_count.sum())
        stability.append(row)
    for k in ['mean', 'n', 'se', 'p']:
        close(stability[0][k], summary['paired_hac20'][k])
    pivot = frame.pivot(index='year', columns='trial', values='mean_ic')
    axes = []
    for name, _ in contract['trials']:
        delta = pivot[name]-pivot.base_es
        subset = frame.loc[frame.trial.eq(name)]
        axes.append(dict(trial=name, mean_inner_ic=pivot[name].mean(), mean_delta_vs_base_es=delta.mean(),
                         positive_years_vs_base_es=int((delta > 0).sum()), min_delta=delta.min(), max_delta=delta.max(),
                         median_rounds=float(subset['rounds'].median()), budget_exhausted=int(subset.budget_exhausted.sum()),
                         selected_years=sum(s['selected'] == name for s in selections)))
    DEST.mkdir(parents=True, exist_ok=True)
    for name, data in [('all_trials', frame), ('selections', pd.DataFrame(selections)),
                       ('stability', pd.DataFrame(stability)), ('parameter_axes', pd.DataFrame(axes)),
                       ('resources', pd.DataFrame(resources))]:
        data.to_csv(DEST/f'{name}.csv', index=False)
    evidence = dict(status='COMPLETED_ARTIFACT_AUDIT_PASS', run_contract_hash=bound,
        contract_file_sha256=sha(RUN/'contract.json'), review_script_sha256=sha(Path(__file__)),
        checked_file_hashes=checked, code_lf=contract['code_lf'], retired_scratch_files=retired,
        inner_trials=81, outer_folds=9, predictions=sum(r['prediction_rows'] for r in resources),
        original_axis_days=len(daily), scoreable_days=int(daily.delta.notna().sum()),
        missing_reasons=daily.loc[daily.delta.isna(), 'reason'].value_counts().to_dict(),
        paired_hac20=stability[0], new_training=False, full_feature_replay_repeated=False,
        verification='Existing full saved-model replay receipt hash-verified; all stored inner/outer statistics independently recomputed.',
        evidence='retrospective_development_not_fresh_OOS')
    (DEST/'audit.json').write_text(json.dumps(evidence, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in evidence.items() if k not in ['checked_file_hashes', 'code_lf', 'retired_scratch_files']}, indent=2))


if __name__ == '__main__':
    main()
