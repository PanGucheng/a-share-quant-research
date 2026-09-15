"""Separate post-replay two-arm development evaluation; never fits or selects parameters."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import research_lightgbm as job  # noqa: E402
from research_validation.frozen_prediction_statistics import hac_mean  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402


def paired_day(y, baseline, tuned, minimum=100):
    y, baseline, tuned = [np.asarray(x, dtype=float) for x in (y, baseline, tuned)]
    if y.ndim != 1 or not (y.shape == baseline.shape == tuned.shape):
        raise ValueError('pair shape mismatch')
    if not np.array_equal(np.isfinite(baseline), np.isfinite(tuned)):
        raise ValueError('prediction coverage mask changed')
    mask = np.isfinite(y) & np.isfinite(baseline) & np.isfinite(tuned)
    result = dict(canonical_count=len(y), finite_prediction=int(np.isfinite(baseline).sum()),
        finite_label=int(np.isfinite(y).sum()), common_count=int(mask.sum()), baseline=None, tuned=None,
        delta=None, reason='fewer_than_100_common_pairs')
    if mask.sum() >= minimum:
        ranks = pd.DataFrame({'y': y[mask], 'b': baseline[mask], 't': tuned[mask]}).rank(method='average')
        if ranks.nunique().min() < 2:
            result['reason'] = 'constant_label_or_arm'
        else:
            corr = ranks.corr()
            result.update(baseline=float(corr.loc['y', 'b']), tuned=float(corr.loc['y', 't']),
                          delta=float(corr.loc['y', 't']-corr.loc['y', 'b']), reason='scoreable')
    return result


def summarize(daily):
    groups = [('overall', daily)] + [(str(y), p) for y, p in daily.groupby(daily.datetime.dt.year)]
    groups += [(f'{y}-{y+2}', daily.loc[daily.datetime.dt.year.between(y, y+2)]) for y in [2015, 2018, 2021]]
    rows = []
    for period, part in groups:
        for arm in ['baseline', 'tuned']:
            rows.append(dict(period=period, arm=arm, **job.policy.describe(part[arm]),
                prediction_coverage=float(part.finite_prediction.sum()/part.canonical_count.sum()),
                common_coverage=float(part.common_count.sum()/part.canonical_count.sum())))
    for row in rows[:2]:
        annual = [r['mean_ic'] for r in rows if r['arm'] == row['arm'] and r['period'].isdigit()]
        if len(annual) != 9 or any(v is None for v in annual):
            raise ValueError('nine scoreable annual results required')
        row.update(worst_year_ic=min(annual), negative_year_count=sum(v < 0 for v in annual))
    return rows


def evaluate(stage, out, ctx, bound):
    source, _, _, protocol, _ = ctx
    if not job.v3.completed_chunk(out/'verification', bound):
        raise ValueError('independent replay required before any outer label read')
    daily, accesses = [], []
    for fold in job.base.FOLDS:
        job.verify_selection(out, fold, bound)
        if not job.v3.completed_chunk(out/fold/'outer', bound):
            raise ValueError('outer artifacts missing/changed')
        audit = source/'audit'/fold[-4:]
        if not job.v3.completed_chunk(audit, job.base.SOURCE_HASH):
            raise ValueError('evaluation cache integrity failure')
        dates = pd.DatetimeIndex(protocol['assignments'].query('fold_id == @fold and role == "evaluate"').datetime)
        job.v3.allowed_dates(protocol, fold, 'evaluate', dates)
        intervals = protocol['intervals'].set_index('feature_time').loc[dates, 'label_end_time']
        if intervals.isna().any() or intervals.max() > job.v3.END:
            raise ValueError('unmatured before I/O')
        old = pd.read_parquet(job.BASELINE/'Broad494'/fold/'engineering_predictions.parquet')
        new = pd.read_parquet(out/fold/'outer/engineering_predictions.parquet')
        if not old[job.v3.KEYS].equals(new[job.v3.KEYS]) or not old.reason.equals(new.reason):
            raise ValueError('baseline/tuned universe or missingness differs')
        if not np.array_equal(np.isfinite(old.score), np.isfinite(new.score)) or old.score.notna().mean() < .95:
            raise ValueError('annual prediction coverage failure')
        labels = pd.read_parquet(audit/'labels.parquet', filters=[('datetime', 'in', dates.tolist())],
                                 columns=[*job.v3.KEYS, job.v3.LABEL, 'exit_date'])
        expected = old.loc[old.datetime.isin(dates), job.v3.KEYS].reset_index(drop=True)
        if not labels[job.v3.KEYS].equals(expected) or not labels.exit_date.equals(labels.datetime.map(intervals)):
            raise ValueError('evaluation sample/maturity drift')
        accesses.append(dict(fold=fold, role='evaluate', dates=dates.strftime('%Y-%m-%d').tolist(),
            path=str(audit/'labels.parquet'), sha256=job.v3.sha256_file(audit/'labels.parquet')))
        combined = old[job.v3.KEYS].assign(b=old.score, t=new.score).merge(labels, on=job.v3.KEYS, how='left', validate='one_to_one')
        for date, part in combined.groupby('datetime', sort=True):
            row = paired_day(part[job.v3.LABEL], part.b, part.t)
            if row['reason'] == 'scoreable':
                common = part.loc[np.isfinite(part[[job.v3.LABEL, 'b', 't']]).all(axis=1)]
                for name, column in [('baseline', 'b'), ('tuned', 't')]:
                    oracle = spearmanr(common[job.v3.LABEL], common[column]).statistic
                    if not np.isclose(row[name], oracle, atol=1e-12, rtol=0):
                        raise ValueError('independent outer Spearman mismatch')
            if date not in dates:
                row['reason'] = 'unmatured_development_boundary'
            daily.append(dict(datetime=date, fold=fold, **row))
    frame = pd.DataFrame(daily)
    # Separate scalar oracle on saved daily axes is tested; missing dates stay on HAC session axis.
    frame.to_csv(stage/'daily.csv', index=False)
    rows = summarize(frame)
    pd.DataFrame(rows).to_csv(stage/'descriptive.csv', index=False)
    delta = hac_mean(frame.delta.to_numpy(dtype=float), 20)
    delta = {k: None if isinstance(v, float) and not np.isfinite(v) else v for k, v in delta.items()}
    choices = {fold: job.selection(out, fold) for fold in job.base.FOLDS}
    trials = [dict(fold=fold, **job.base.read_json(out/fold/'trials'/name/'result.json'))
              for fold in job.base.FOLDS for name, _ in job.policy.TRIALS]
    job.v3.atomic_write_json(stage/'summary.json', dict(status='TUNING_RUN_COMPLETE / MODEL_CANDIDATE_REVIEW_PENDING',
        recommended_model=None, choices=choices, trials=trials, descriptive=rows, paired_hac20=delta,
        evidence='retrospective_development_not_fresh_OOS', production_replacement=False))
    job.v3.atomic_write_json(stage/'access.json', accesses)
    lines = ['# LightGBM Hyperparameter Research — user-run results', '',
        '九折训练/重放和两臂评价完成。Model V2 candidate 尚待人工审阅，不自动替换 baseline。', '',
        '所有81个 inner trials、选择、曲线、模型及年度/era数据保留。当前候选是年度past-only调参流程；',
        '没有依据outer结果回填一个全期最佳静态参数。ICIR不年化，HAC20仅为development支持证据。', '',
        '| period | arm | mean daily IC | ICIR |', '|---|---|---|---|']
    lines += [f"| {r['period']} | {r['arm']} | {r['mean_ic']} | {r['icir']} |" for r in rows]
    lines += ['', '欠拟合、100轮不足、容量平台和替换建议须结合所有内层曲线/邻域与outer年度证据审阅，',
              '不能从单个最大IC自动作结论。停止，不开启后续模型或组合研究。', '']
    (stage/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='lgbm_nested_20260916_v1')
    args = parser.parse_args()
    if not re.fullmatch(r'lgbm_nested_[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run id')
    ctx = job.context()
    out = ROOT/'outputs/lightgbm_hyperparameter_research'/args.run_id
    if not (out/'contract.json').exists():
        raise ValueError('run required before evaluation')
    with job.v3.run_lock(out/'run.lock'):
        bound = job.bind(out, ctx)
        if not job.v3.completed_chunk(out/'verification', bound):
            raise ValueError('verified predictions required')
        job.v3.publish(out/'evaluation', bound, lambda stage: evaluate(stage, out, ctx, bound))
        job.v3.atomic_write_json(out/'status.json', {'status': 'TUNING_RUN_COMPLETE / MODEL_CANDIDATE_REVIEW_PENDING'})
        print('TUNING_RUN_COMPLETE / MODEL_CANDIDATE_REVIEW_PENDING', flush=True)


if __name__ == '__main__':
    main()
