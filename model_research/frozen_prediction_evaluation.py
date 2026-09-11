"""D3-A bounded evaluation of sealed predictions; no model, feature or price execution."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import lightgbm as lgb

from model_research import literature_precompute as d2
from research_validation.frozen_prediction_statistics import ARMS, CONTRASTS, common_day, infer

ROOT = d2.ROOT
REPORT = Path('reports/literature_factor_representation_d3a')
PACKET = REPORT / 'execution_v1'
RCH = Path('outputs/literature_factor_representation_d2/d2_rch_20260910_v1')
KEYS = ['datetime', 'instrument']
LABEL = 'label_20d_t1'
CODE = ['research_validation/frozen_prediction_statistics.py',
        'model_research/frozen_prediction_evaluation.py',
        'scripts/evaluate_literature_d3a.py', 'scripts/evaluate_literature_d3a.ps1',
        'tests/test_frozen_prediction_d3a.py',
        'docs/LITERATURE_D3A_FROZEN_PREDICTION_EVALUATION_PLAN.md']
SCOPE = dict(pool_discovery_scope='retrospective_development_2010_2023',
             representation_design_scope='outcome_blind_retrospective_metadata_and_feature_evidence',
             model_fit_scope='past_only_purged', evidence_class='retrospective_pseudo_oos_development',
             unbiased_final_estimate=False, recent_access=False,
             portfolio_authorized=False, strategy_v2_authorized=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return d2.d1.sha(path)


def read_json(path):
    return d2.d1.read_json(path)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'


def exclusive_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json_text(value))
        stream.flush()
        os.fsync(stream.fileno())


def git_head():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def receipt_check(folder, bound):
    require(not folder.with_name('.' + folder.name + '.incomplete').exists(), 'incomplete source unit')
    value = read_json(folder / 'receipt.json')
    require(value['status'] == 'complete' and value['contract_hash'] == bound, 'source receipt mismatch')
    require(bool(value['file_hashes']), 'empty receipt')
    for name, expected in value['file_hashes'].items():
        require(Path(name).name == name and name != 'receipt.json', 'unsafe receipt filename')
        require(sha(folder / name) == expected, f'source bytes changed: {folder / name}')
    return value


def dates_for(protocol, fold, role):
    assignments = protocol['assignments']
    dates = pd.DatetimeIndex(assignments.loc[(assignments.fold_id == fold) & (assignments.role == role), 'datetime'])
    return d2.v3.allowed_dates(protocol, fold, role, dates)


def date_strings(days):
    return pd.DatetimeIndex(days).strftime('%Y-%m-%d').tolist()


def preflight():
    """Checksums/metadata only: never materializes scores, labels, prices or features."""
    ctx = d2.context()
    frozen = ctx['approval']['evaluation_contract']
    require(frozen == dict(alpha=.05, bootstrap=dict(cannot_cross_calendar_gaps=True, kind='moving_block',
        primary=20, resamples=1000, seed=20260909, sensitivity=40, shared_date_indices=True),
        contrasts=list(CONTRASTS), correction='single_Holm_family',
        hac=dict(kernel='Bartlett', primary=20, sensitivity=40), no_model_or_threshold_sweep=True,
        noninferiority_enabled=False, outcomes_authorized=False, samples='all_five_arms_same_keys_and_dates',
        sidedness='two-sided', statistic='paired_daily_IC_delta', status='future_contract_only_not_executable'),
        'formal evaluation contract differs; stop instead of changing methods')
    bs, rch = ROOT / d2.freeze.BS, ROOT / RCH
    bs_contract, rch_contract = read_json(bs / 'contract.json'), read_json(rch / 'contract.json')
    require(rch_contract == d2.contract(ctx), 'D2 code/runtime/config mismatch')
    require(bs_contract['config'] == ctx['config'] and bs_contract['runtime'] == ctx['runtime'], 'B/S config mismatch')
    bs_bound, rch_bound = d2.v3.canonical_hash(bs_contract), d2.digest(rch_contract)
    require(bs_bound == 'f45bc6e4aab96d8d5897fcf69ee59c1e62ab2b12a53c8cf911ad217bd92e2130'
            and rch_bound == '25b801854c073c2fc246756a84f05eedb182aa4edfb0f880516edc846ec37f29',
            'sealed source contract identity mismatch')
    for base in [bs, rch]:
        require(not list(base.rglob('*.incomplete')) and not list(base.rglob('failure.json')), 'source failure evidence')
    snapshot = {}

    def checked(folder, bound):
        receipt = receipt_check(folder, bound)
        snapshot[(folder / 'receipt.json').relative_to(ROOT).as_posix()] = sha(folder / 'receipt.json')
        return receipt

    completion = ROOT / 'reports/literature_factor_representation_d2/completion_v1'
    for name, expected in read_json(completion / 'hashes_lf.json').items():
        require(d2.d1.sha(completion / name, lf=True) == expected, 'D2 completion evidence changed')
    review = read_json(completion / 'verification.json')
    require(review['contract_hash'] == rch_bound and review['models'] == 27, 'D2 review identity mismatch')
    for name, expected in review['verified_receipts'].items():
        require(sha(rch / name / 'receipt.json') == expected, 'D2 receipt differs from completed review')
    for month in d2.d1.scheduled_dates(ROOT, 'full').to_period('M').unique():
        checked(rch / 'cache' / str(month), rch_bound)
    checked(rch / 'sealed', rch_bound)
    require(read_json(rch / 'sealed/result.json')['arms'] == {a: 'all_nine_exact' for a in d2.POOLS}, 'R/C/H seal')
    ordered = dict(B=bs_contract['members']['Broad494'], S=bs_contract['members']['Strict332'], **ctx['recipe']['arms'])
    require([len(ordered[a]) for a in ARMS] == [494, 332, 218, 201, 358], 'arm dimensions changed')
    records = []
    for arm in ARMS:
        old = arm in ('B', 'S')
        pool = {'B': 'Broad494', 'S': 'Strict332'}.get(arm, arm)
        base, bound = (bs, bs_bound) if old else (rch, rch_bound)
        if old:
            checked(base / 'verification' / pool, bound)
            replay = read_json(base / 'verification' / pool / 'result.json')
            require(replay['status'] == 'all_nine_exact' and len(replay['folds']) == 9, 'B/S replay incomplete')
        for fold in d2.FOLDS:
            folder = base / pool / fold
            rec = checked(folder, bound)
            resource = read_json(folder / 'resource.json')
            if old:
                evidence = [r for r in replay['folds'] if r['fold'] == fold]
                require(len(evidence) == 1 and evidence[0]['exact'], 'B/S fold replay missing')
                evidence = evidence[0]
                require(resource['ordered_features'] == ordered[arm], 'B/S feature order mismatch')
            else:
                checked(base / 'replay' / pool / fold, bound)
                evidence = read_json(base / 'replay' / pool / fold / 'result.json')
                require(evidence['status'] == 'exact' and evidence['model_receipt_sha256'] == sha(folder / 'receipt.json'),
                        'R/C/H replay mismatch')
                identity = read_json(folder / 'representation.json')
                require(identity['ordered_columns'] == ordered[arm]
                        and identity['freeze_hash'] == ctx['approval']['freeze_hash']
                        and identity['parent_dependencies'] == d2.dependencies(ctx['recipe'], arm), 'representation mismatch')
            # Existing resources hash Booster serialization; file-byte SHA is a different identity.
            model = lgb.Booster(model_file=str(folder / 'model.txt'))
            semantic_sha = hashlib.sha256(model.model_to_string().encode()).hexdigest()
            require(evidence['model_sha256'] == resource['model_sha256'] == semantic_sha
                    and model.feature_name() == ordered[arm] and model.current_iteration() == 100, 'model replay binding')
            require(evidence['rows'] == resource['prediction_rows'] and evidence['dates'] == resource['predicted_dates'], 'replay counts')
            require(resource['actual_iterations'] == 100 and resource['config_hash'] == d2.v3.canonical_hash(ctx['config'])
                    and resource['batch_receipts'] == ctx['anchors'][fold]['batch_receipts'], 'learner identity changed')
            filename = 'engineering_predictions.parquet' if old else 'predictions.parquet'
            records.append(dict(arm=arm, fold=fold, path=(folder / filename).relative_to(ROOT).as_posix(),
                prediction_sha256=rec['file_hashes'][filename], model_sha256=resource['model_sha256'],
                model_file_sha256=rec['file_hashes']['model.txt'],
                receipt_sha256=sha(folder / 'receipt.json'), rows=resource['prediction_rows'],
                feature_count=len(ordered[arm]), parent_dependency_count=len(ordered[arm]) if old else len(d2.dependencies(ctx['recipe'], arm)),
                fit_seconds=resource['fit_seconds'], peak_rss_mib=resource['peak_rss_mib']))
    sources, schedules = [], {}
    for fold in d2.FOLDS:
        predict, evaluate = dates_for(ctx['protocol'], fold, 'predict'), dates_for(ctx['protocol'], fold, 'evaluate')
        interval = ctx['protocol']['intervals'].set_index('feature_time').loc[evaluate]
        require(interval.label_end_time.max() <= d2.v3.END, 'maturity ceiling')
        schedules[fold] = dict(predict=date_strings(predict), evaluate=date_strings(evaluate),
                               exits=date_strings(interval.label_end_time))
        folder = ctx['source'] / 'audit' / fold[-4:]
        receipt = checked(folder, d2.d1.V3_CONTRACT)
        # Full-year cache contains only development values. Do not hash provider parents.
        sources.append(dict(fold=fold, keys=(folder / 'keys.parquet').relative_to(ROOT).as_posix(),
            labels=(folder / 'labels.parquet').relative_to(ROOT).as_posix(),
            keys_sha256=receipt['file_hashes']['keys.parquet'], label_sha256=receipt['file_hashes']['labels.parquet'],
            audit_receipt_sha256=sha(folder / 'receipt.json')))
    return dict(version='D3-A-v1', scope=SCOPE, historical_evaluation_contract=frozen,
        authorization='2026-09-11 user requested assessment, plan and implementation of D3-A frozen five-arm evaluation; long execution user-run',
        outcomes_authorized=True, cutoff='2023-12-29', freeze_hash=ctx['approval']['freeze_hash'],
        recipe_hash=ctx['recipe']['recipe_hash'], bs_contract_hash=bs_bound, d2_contract_hash=rch_bound,
        ordered_arms=ordered, arm_identity_hashes={a: d2.digest(ordered[a]) for a in ARMS},
        predictions=records, sources=sources, schedules=schedules, source_receipts=snapshot,
        runtime=dict(v3=ctx['runtime'], python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
        numerical_policy=dict(primary='mean_daily_common_sample_Spearman_average_ties', minimum_pairs=100,
            common_constant_policy='all_arms_day_unscoreable', hac='original_session_sandwich_n_squared_no_small_sample_correction_normal_p',
            mbb='shared_all_columns_percentile_full_support_only', noninferiority_enabled=False),
        code_hashes_lf={name: d2.d1.sha(ROOT / name, lf=True) for name in CODE})


def prepare():
    value = preflight()
    path = ROOT / PACKET / 'contract.json'
    if path.exists():
        require(read_json(path) == value, 'D3-A execution contract changed; preserve packet')
    else:
        exclusive_json(path, value)
    return value


def checked_contract():
    expected = read_json(ROOT / PACKET / 'contract.json')
    require(preflight() == expected, 'D3-A preflight differs from frozen execution packet')
    return expected


def legal_request(contract, fold, kind, days):
    dates = pd.DatetimeIndex(days)
    require(kind in {'keys', 'prediction', 'label'} and fold in contract['schedules'], 'invalid read role/fold')
    require(not dates.empty and not dates.hasnans and not dates.has_duplicates
            and dates.is_monotonic_increasing and dates.equals(dates.normalize()), 'invalid dates before I/O')
    schedule = contract['schedules'][fold]
    allowed = pd.DatetimeIndex(schedule['evaluate' if kind == 'label' else 'predict'])
    require(dates.isin(allowed).all() and dates.min() >= pd.Timestamp('2015-01-01')
            and dates.max() <= pd.Timestamp(contract['cutoff']), 'out of authorized dates before I/O')
    if kind == 'label':
        exits = pd.Series(pd.to_datetime(schedule['exits']), index=pd.to_datetime(schedule['evaluate'])).loc[dates]
        require(exits.notna().all() and exits.max() <= pd.Timestamp(contract['cutoff']), 'unmatured before I/O')
    return dates


def read_bounded(root, contract, record, kind, days, log):
    fold = record['fold']
    dates = legal_request(contract, fold, kind, days)  # before opening even Parquet metadata
    name = {'keys': 'keys', 'label': 'labels', 'prediction': 'path'}[kind]
    hash_name = {'keys': 'keys_sha256', 'label': 'label_sha256', 'prediction': 'prediction_sha256'}[kind]
    columns = KEYS + ({'keys': [], 'label': [LABEL, 'exit_date'], 'prediction': ['score', 'reason']}[kind])
    path = root / record[name]
    require(sha(path) == record[hash_name], 'input changed after preflight')
    event = dict(kind=kind, fold=fold, arm=record.get('arm'), path=record[name], columns=columns,
                 dates=date_strings(dates), parent_sha256=record[hash_name])
    log(dict(stage='request', **event))
    require(pq.ParquetFile(path).schema_arrow.names == columns, 'input schema changed')
    result = pd.read_parquet(path, columns=columns, filters=[('datetime', 'in', dates.tolist())])
    require(list(result.columns) == columns and not result[KEYS].isna().any().any()
            and not result.duplicated(KEYS).any(), 'null or duplicate keys/schema')
    require(result[KEYS].equals(result.sort_values(KEYS)[KEYS].reset_index(drop=True)), 'unordered input keys')
    require(pd.DatetimeIndex(result.datetime.unique()).equals(dates), 'missing or additional input dates')
    # All evaluator requests are complete legal annual roles. Footer counts detect hidden extras.
    require(len(result) == pq.ParquetFile(path).metadata.num_rows, 'file contains keys outside complete authorized annual role')
    if kind == 'label':
        require(result[LABEL].dtype == np.float64, 'label dtype differs from float64 authority')
        expected = pd.Series(pd.to_datetime(contract['schedules'][fold]['exits']),
                             index=pd.to_datetime(contract['schedules'][fold]['evaluate']))
        require(result.exit_date.equals(result.datetime.map(expected)), 'label maturity mapping differs')
    if kind == 'prediction':
        require(result.score.dtype == np.float64, 'prediction dtype differs from float64 authority')
    log(dict(stage='complete', rows=len(result), slice_hash=d2.frame_digest(result), **event))
    return result


def evaluate_daily(root, contract, log):
    rows = []
    for source in contract['sources']:
        fold = source['fold']
        schedule = contract['schedules'][fold]
        keys = read_bounded(root, contract, source, 'keys', schedule['predict'], log)
        combined = keys.copy()
        for record in [r for r in contract['predictions'] if r['fold'] == fold]:
            pred = read_bounded(root, contract, record, 'prediction', schedule['predict'], log)
            require(pred[KEYS].equals(keys), 'prediction keys differ from canonical universe')
            require(set(pred.reason) <= {'predicted', 'all_features_missing'}, 'unknown missing prediction reason')
            require(np.array_equal(np.isfinite(pred.score), pred.reason.eq('predicted')), 'prediction reason/finite mismatch')
            combined[record['arm']] = pred.score.to_numpy()
        require(all(a in combined for a in ARMS), 'five frozen predictions required before labels')
        labels = read_bounded(root, contract, source, 'label', schedule['evaluate'], log)
        mature_keys = keys.loc[keys.datetime.isin(pd.to_datetime(schedule['evaluate']))].reset_index(drop=True)
        require(labels[KEYS].equals(mature_keys), 'label keys differ from mature canonical universe')
        combined = combined.merge(labels[KEYS + [LABEL]], on=KEYS, how='left', validate='one_to_one', sort=False)
        mature = set(pd.to_datetime(schedule['evaluate']))
        for day, part in combined.groupby('datetime', sort=True):
            result, mask = common_day(part[LABEL], part[list(ARMS)], mature=day in mature)
            result.update(datetime=day, fold=fold, common_keys_sha256=d2.frame_digest(part.loc[mask, KEYS].reset_index(drop=True)))
            rows.append(result)
        print(f'{fold}: five-arm common-sample evaluation written to memory', flush=True)
    daily = pd.DataFrame(rows)
    require(not daily.datetime.duplicated().any() and daily.datetime.is_monotonic_increasing, 'pooled date axis')
    return daily


def descriptive(daily, contract):
    rows = []
    groups = [('overall', daily)] + [(str(y), p) for y, p in daily.groupby(daily.datetime.dt.year)]
    groups += [(f'{lo}-{lo+2}', daily.loc[daily.datetime.dt.year.between(lo, lo+2)]) for lo in [2015, 2018, 2021]]
    for period, part in groups:
        mature = part.loc[part.mature]
        for arm in ARMS:
            ic = part[f'IC_{arm}'].dropna()
            std = float(ic.std(ddof=1))
            rows.append(dict(period=period, arm=arm, features=len(contract['ordered_arms'][arm]),
                mean_ic=ic.mean(), icir=ic.mean()/std if std > 0 else np.nan,
                valid_dates=len(ic), prediction_dates=len(part), mature_dates=int(part.mature.sum()),
                canonical_count=int(part.canonical_count.sum()), mature_canonical_count=int(mature.canonical_count.sum()),
                finite_label_count=int(part.mature_label_count.sum()), common_count=int(part.common_count.sum()),
                engineering_coverage=part[f'finite_{arm}'].sum()/part.canonical_count.sum(),
                finite_label_coverage=mature.mature_label_count.sum()/mature.canonical_count.sum(),
                common_coverage=part.common_count.sum()/part.canonical_count.sum(),
                mature_common_coverage=mature.common_count.sum()/mature.canonical_count.sum(),
                common_over_finite_label=part.common_count.sum()/part.mature_label_count.sum() if part.mature_label_count.sum() else np.nan))
    frame = pd.DataFrame(rows)
    for arm in ARMS:
        annual = frame.loc[(frame.arm == arm) & frame.period.isin([str(y) for y in range(2015, 2024)])]
        frame.loc[(frame.arm == arm) & (frame.period == 'overall'), 'worst_year_ic'] = annual.mean_ic.min()
        frame.loc[(frame.arm == arm) & (frame.period == 'overall'), 'negative_ic_years'] = int(annual.mean_ic.lt(0).sum())
    return frame


def markdown_table(frame):
    def fmt(x):
        if isinstance(x, (float, np.floating)):
            return 'NA' if not np.isfinite(x) else f'{x:.6g}'
        return str(x)
    return '\n'.join(['| ' + ' | '.join(frame.columns) + ' |', '| ' + ' | '.join(['---']*len(frame.columns)) + ' |'] +
                     ['| ' + ' | '.join(fmt(x) for x in row) + ' |' for row in frame.itertuples(index=False, name=None)])


def report_text(daily, desc, contrasts, support, bound):
    annual = desc.loc[desc.period.isin([str(y) for y in range(2015, 2024)])]
    overall = desc.loc[desc.period == 'overall']
    eras = desc.loc[desc.period.str.contains('-')]
    lines = ['# D3-A 五臂冻结预测评价', '',
        'D3-A COMPLETE。五臂冻结 predictions 在同日、同股票交集上评价；主估计为每日 Spearman Rank IC 等日期均值。',
        '推断仅限六项 paired daily delta，HAC20 双侧 p 经 single Holm family 校正；HAC40 和 MBB20/40 为支持性证据。',
        '这是 retrospective pseudo-OOS development evidence，不是无偏最终估计、fresh OOS 或可交易收益结论。', '',
        '## 完整性与边界', '', f'执行契约 `{bound}`。45 个冻结模型及 independent exact replay 已在揭封前校验。',
        f'预测日 {len(daily)}，边界内成熟候选日 {int(daily.mature.sum())}，共同可评分日 {int(daily.scoreable.sum())}。',
        '精确日期、模型/预测/标签源哈希、Git/runtime 见 contract.json 与 OUTCOME_ACCESS_RECEIPT.json；',
        '结果哈希见 receipt.json，访问切片见 access.jsonl。2024+、价格/特征重新读取、portfolio/Strategy V2 未授权且未执行。', '',
        '## 五臂描述统计', '', markdown_table(overall[['arm', 'features', 'mean_ic', 'icir', 'valid_dates',
            'engineering_coverage', 'finite_label_coverage', 'mature_common_coverage', 'worst_year_ic', 'negative_ic_years']]), '',
        'ICIR 为 mean/std(ddof=1)，不年化。共同 coverage 分母为成熟候选日 canonical keys；完整预测轴比例另存 descriptive.csv。', '',
        '## 六项 primary contrasts', '', markdown_table(contrasts), '',
        'MBB 为 pointwise percentile 区间，不是 Holm simultaneous CI；NA 区间的缺口/短片段原因见 bootstrap_support.json。', '',
        '## 年度描述', '', markdown_table(annual[['period', 'arm', 'mean_ic', 'valid_dates', 'common_count', 'mature_common_coverage']]), '',
        '## Era 描述', '', markdown_table(eras[['period', 'arm', 'mean_ic', 'valid_dates', 'mature_common_coverage']]), '',
        '## 覆盖与缺失', '',
        markdown_table(daily.groupby('reason', dropna=False).agg(dates=('datetime', 'size'), canonical_count=('canonical_count', 'sum'),
                       common_count=('common_count', 'sum')).reset_index()), '',
        '工程 prediction coverage、finite mature label availability、五臂共同评价 coverage 分列保存；100% 工程覆盖不等于标签全有限。',
        '没有按表现或 coverage 挑选子样本；年度工程 coverage <95% 或年度无共同可评分日会使正式总体检验 not testable。', '',
        '## Q1–Q6', '']
    questions = ['Strict 相对 Broad 的增量', 'Representative 相对 Broad 的变化', 'Composite 相对 Broad 的增量',
                 'Hybrid 相对 Broad 的增量', 'Composite 相对 Representative 的增量', '加入 raw representatives 相对 Composite 的增量']
    for i, (question, row) in enumerate(zip(questions, contrasts.to_dict('records')), 1):
        lines.append(f"Q{i} {question}（{row['contrast']}）：observed delta={row['mean_delta']:.6g}，Holm p={row['holm_p']:.6g}，{row['decision']}。")
        lines.append('')
    lines += ['未拒绝零差异不能解释为等价、无损压缩或非劣；不自动宣布 production/strategy winner。', '',
        '## 限制与停止点', '',
        '因子池发现是 retrospective development 2010–2023，表示设计使用 outcome-blind retrospective metadata/features；',
        '年度模型 past-only purged fit 不消除前序发现偏差。U61 包含未解 Alpha101 语义、价格尺度和 recursive raw carry-through 质量限制；',
        'dense bucket 是 available-lag-node average，非固定完整 lag path；跨 family 全可用的覆盖损失仍存在。',
        '没有 noninferiority margin，没有 portfolio 解释，没有 fresh untouched OOS；年度/era/worst-year 不构成新假设检验。',
        'D1/D2 保持冻结；D3-A 结束。D3-B、Strategy V2、2024+ 继续关闭。后续表示修改必须标为 post-outcome research。', '']
    return '\n'.join(lines)


def verify_sealed(folder, bound):
    rec = receipt_check(folder, bound)
    require(rec.get('outcome_opened') is True and rec.get('recent_access') is False, 'invalid outcome seal')
    expected = {'contract.json', 'OUTCOME_ACCESS_RECEIPT.json', 'access.jsonl', 'daily.csv',
                'contrasts.csv', 'descriptive.csv', 'bootstrap_support.json', 'REPORT.md'}
    require(set(rec['file_hashes']) == expected and {p.name for p in folder.iterdir()} == expected | {'receipt.json'},
            'unexpected or missing sealed artifacts')
    require(d2.digest(read_json(folder / 'contract.json')) == bound, 'sealed contract hash mismatch')
    return rec


def run_once(root, contract, run_id, commit, *, daily_evaluator=evaluate_daily):
    """Exclusive immutable opening marker; a failed opening cannot be retried by a new id."""
    bound = d2.digest(contract)
    out = root / 'outputs/literature_factor_representation_d3a' / run_id
    marker = root / REPORT / 'OUTCOME_OPENED.json'
    sealed = out / 'sealed'
    if marker.exists():
        prior = read_json(marker)
        require(prior['run_id'] == run_id and prior['contract_hash'] == bound, 'already unsealed; different run prohibited')
        require(sealed.exists(), 'outcome already opened; incomplete evidence preserved; diagnose before any recovery')
        verify_sealed(sealed, bound)
        require(sha(sealed / 'OUTCOME_ACCESS_RECEIPT.json') == sha(out / 'OUTCOME_ACCESS_RECEIPT.json'), 'opening receipt changed')
        require(read_json(out / 'OUTCOME_ACCESS_RECEIPT.json')['marker_sha256'] == sha(marker), 'opening marker changed')
        export_sealed(root, sealed, bound)
        return 'already_complete_verified'
    require(not out.exists(), 'output directory exists; preserve it')
    out.mkdir(parents=True)
    opening = dict(status='D3A_OUTCOME_OPENED_NO_LONGER_OUTCOME_BLIND', run_id=run_id,
        contract_hash=bound, git_commit=commit, time_utc=datetime.now(timezone.utc).isoformat(),
        authorization=contract['authorization'], scope=contract['scope'])
    # Conservative irreversible declaration precedes any logical value read, including failures.
    exclusive_json(marker, opening)
    access_receipt = dict(**opening, marker_sha256=sha(marker),
        freeze_hash=contract['freeze_hash'], arm_identity_hashes=contract['arm_identity_hashes'],
        predictions=contract['predictions'], label_sources=contract['sources'], exact_dates=contract['schedules'],
        maturity_cutoff=contract['cutoff'], code_hashes_lf=contract['code_hashes_lf'], environment=contract['runtime'],
        output_hash_binding='sealed/receipt.json after completion; initial access receipt never overwritten')
    exclusive_json(out / 'OUTCOME_ACCESS_RECEIPT.json', access_receipt)
    stage = out / '.sealed.incomplete'
    stage.mkdir()
    started = time.perf_counter()
    try:
        exclusive_json(stage / 'contract.json', contract)
        shutil.copyfile(out / 'OUTCOME_ACCESS_RECEIPT.json', stage / 'OUTCOME_ACCESS_RECEIPT.json')
        with (stage / 'access.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
            def log(event):
                stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            daily = daily_evaluator(root, contract, log)
        contrasts, support = infer(daily)
        desc = descriptive(daily, contract)
        for name, frame in [('daily', daily), ('contrasts', contrasts), ('descriptive', desc)]:
            frame.to_csv(stage / f'{name}.csv', index=False, lineterminator='\n')
        exclusive_json(stage / 'bootstrap_support.json', support)
        (stage / 'REPORT.md').write_text(report_text(daily, desc, contrasts, support, bound), encoding='utf-8', newline='\n')
        exclusive_json(stage / 'receipt.json', dict(status='complete', contract_hash=bound,
            outcome_opened=True, recent_access=False, models=45, arms=list(ARMS),
            prediction_dates=len(daily), mature_dates=int(daily.mature.sum()), scoreable_dates=int(daily.scoreable.sum()),
            wall_seconds=time.perf_counter()-started, file_hashes={p.name: sha(p) for p in stage.iterdir()}))
        stage.rename(sealed)
    except BaseException as error:
        exclusive_json(out / 'failure.json', dict(error_type=type(error).__name__, error=str(error),
            outcome_opened=True, recovery='Preserve evidence. No automatic retry or new run-id.'))
        raise
    verify_sealed(sealed, bound)
    export_sealed(root, sealed, bound)
    return 'complete'


def export_sealed(root, sealed, bound):
    target = root / REPORT / 'completion_v1'
    if target.exists():
        verify_sealed(target, bound)
        require(read_json(target / 'receipt.json') == read_json(sealed / 'receipt.json'), 'export differs')
        return
    stage = target.with_name('.completion_v1.incomplete')
    require(not stage.exists(), 'export incomplete; preserve and diagnose')
    shutil.copytree(sealed, stage)
    verify_sealed(stage, bound)
    stage.rename(target)
