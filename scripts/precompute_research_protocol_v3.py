"""Broad494 then Strict332, nine annual fixed models; no outcome evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_research_protocol_v3_mvp as v3  # noqa: E402
from model_research.v3_prediction_precompute import precompute_fold  # noqa: E402
import pandas as pd  # noqa: E402

SOURCE_ID = 'v3_recompute_audit_20260909_v1'
SOURCE_HASH = 'a73a2a504c7e13d92273837c22d4bc087ac31190d1dc0d1aed7365f74671858e'
FOLDS = [f'annual_{year}' for year in range(2015, 2024)]
POOLS = ('Broad494', 'Strict332')
EXTRA_CODE = ['scripts/precompute_research_protocol_v3.py',
              'scripts/replay_research_protocol_v3_predictions.py',
              'scripts/precompute_research_protocol_v3.ps1',
              'model_research/v3_prediction_precompute.py']


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def pool_members():
    broad = sorted(pd.read_csv(ROOT / 'reports/candidate_consolidation_v0_5/working_set.csv',
                              usecols=['factor']).factor)
    board = pd.read_csv(ROOT / 'reports/long_history_multi_evaluator_screening_v1/candidate_board.csv',
                        usecols=['factor', 'pass_count'])
    strict = sorted(board.loc[board.pass_count == 3, 'factor'])
    for values, count in [(broad, 494), (strict, 332)]:
        if len(values) != count or len(set(values)) != count:
            raise ValueError('frozen pool identity changed')
    return dict(Broad494=broad, Strict332=strict)


def load_context():
    """Only receipts, metadata and pre-2024 protocol tables; no provider price reads."""
    source = ROOT / 'outputs/research_protocol_v3_mvp' / SOURCE_ID
    old = read_json(source / 'contract.json')
    if v3.canonical_hash(old) != SOURCE_HASH:
        raise ValueError('audited source contract changed')
    for folder in [source / 'p0', source / 'p1']:
        if not v3.completed_chunk(folder, SOURCE_HASH):
            raise ValueError(f'missing protocol/eligibility receipt: {folder}')
    if v3.runtime_identity() != old['runtime']:
        raise ValueError('runtime differs from float64 authority')
    for name, expected in old['code_hashes'].items():
        # git checkout on Windows can restore LF source as CRLF. Accept only
        # that reversible text encoding change for the historical source hash.
        content = (ROOT / name).read_bytes()
        if expected not in {hashlib.sha256(content).hexdigest(),
                            hashlib.sha256(content.replace(b'\r\n', b'\n')).hexdigest()}:
            raise ValueError(f'authority code changed: {name}')
    for name, expected in old['frozen_evidence'].items():
        if v3.sha256_file(ROOT / name) != expected:
            raise ValueError(f'frozen evidence changed: {name}')
    canonical = ROOT / old['config']['canonical_root']
    for name, expected in old['canonical_metadata'].items():
        if v3.sha256_file(canonical / name) != expected:
            raise ValueError(f'canonical metadata changed: {name}')
    partitions = pd.read_csv(canonical / 'partition_manifest.csv')
    partitions = partitions.loc[(pd.to_datetime(partitions.effective_start) <= v3.END) &
                                (pd.to_datetime(partitions.effective_end) >= v3.START)].copy()
    protocol = {}
    for name, columns in [('folds', ['train_start', 'last_legal_train_signal', 'train_label_end',
                                   'evaluation_start', 'evaluation_end', 'latest_mature_eval_signal', 'label_end']),
                          ('assignments', ['datetime']),
                          ('intervals', ['feature_time', 'label_start_time', 'label_end_time'])]:
        protocol[name] = pd.read_csv(source / 'p0' / f'{name}.csv', parse_dates=columns)
    protocol['intervals'] = protocol['intervals'].loc[protocol['intervals'].feature_time <= v3.END]
    validate_protocol(protocol)
    members = pool_members()
    if not set(members['Strict332']) <= set(members['Broad494']):
        raise ValueError('2023 audited feature coverage does not cover Strict332')
    eligible = pd.read_csv(source / 'p1/feature_eligibility.csv')
    for fold in FOLDS:
        allowed = set(eligible.loc[(eligible.fold_id == fold) & eligible.eligible, 'factor'])
        for pool, values in members.items():
            if not set(values) <= allowed:
                raise ValueError(f'{pool}/{fold}: identity is not fully train eligible')
    return source, old, partitions, protocol, members


def validate_protocol(protocol):
    """Independent session-index purge oracle, using only development metadata."""
    folds, assignments = protocol['folds'], protocol['assignments']
    if list(folds.fold_id) != FOLDS:
        raise ValueError('expected exactly nine chronological folds')
    days = pd.DatetimeIndex(protocol['intervals'].feature_time)
    if days.has_duplicates or not days.is_monotonic_increasing or days[0] != v3.START or days[-1] != v3.END:
        raise ValueError('invalid development calendar')
    if not assignments.datetime.between(v3.START, v3.END).all():
        raise ValueError('assignment outside development')
    for fold in FOLDS:
        prediction = days[days.year == int(fold[-4:])]
        boundary = days.get_loc(prediction[0])
        for role, expected in [('train', days[:boundary - 21]), ('predict', prediction)]:
            actual = pd.DatetimeIndex(assignments.loc[(assignments.fold_id == fold) &
                                                      (assignments.role == role), 'datetime'])
            if not actual.equals(expected):
                raise ValueError(f'{fold}/{role}: independent calendar mismatch')
        intervals = protocol['intervals'].iloc[:boundary - 21]
        if not pd.DatetimeIndex(intervals.label_end_time).equals(days[21:boundary]):
            raise ValueError('training label maturity mismatch')


def bind_run(out, context):
    source, old, partitions, protocol, members = context
    contract = dict(scope='model_prediction_precompute_only', source_run=SOURCE_ID,
                    source_contract_hash=SOURCE_HASH, config=old['config'], runtime=old['runtime'],
                    canonical_metadata=old['canonical_metadata'], ordered_pools=list(POOLS),
                    folds=FOLDS, members=members, scratch_policy='hash_then_remove_before_publication',
                    outcome_evaluation=False, pool_comparison=False, recent_access=False,
                    code_hashes={name: v3.sha256_file(ROOT / name) for name in [*v3.CODE, *EXTRA_CODE]})
    path = out / 'contract.json'
    if path.exists() and read_json(path) != contract:
        raise ValueError('run contract changed; preserve outputs and choose a new run-id')
    out.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        v3.atomic_write_json(path, contract)
    return v3.canonical_hash(contract)


def verify_inputs(context):
    source, old, partitions, protocol, members = context
    # Only training cache years are consumed. Never load audit/2023 labels.
    for path in [source / 'p0', source / 'p1', *[source / 'audit' / str(y) for y in range(2010, 2023)]]:
        if not v3.completed_chunk(path, SOURCE_HASH):
            raise ValueError(f'missing audited input: {path}')
    verify_feature_slices(context)


def verify_feature_slices(context):
    """Compare bounded reads to the previously audited slice hashes.

    Mixed-date parquet parents must NOT be hashed as whole files: that would
    physically read recent bytes. Historical access receipts already bind exact
    development slices to the canonical authority.
    """
    from factor_research.long_history_screening import normalize_keys, frame_hash
    from research_validation.canonical_dataset import read_effective_partition
    source, old, partitions, protocol, members = context
    folders = [source / 'audit' / str(y) for y in range(2010, 2023)]
    folders.append(source / 'wide_canary/annual_2023')
    seen, coverage = set(), {}
    for folder in folders:
        receipt = read_json(folder / 'receipt.json')
        path = folder / 'access.json'
        if (receipt['contract_hash'] != SOURCE_HASH or receipt['status'] != 'complete'
                or v3.sha256_file(path) != receipt['file_hashes']['access.json']):
            raise ValueError('invalid audited feature access evidence')
        for event in read_json(path)['access']:
            if event['kind'] != 'feature' or (folder.name == 'annual_2023' and event['role'] != 'predict'):
                continue
            lo, hi = pd.Timestamp(event['start']), pd.Timestamp(event['end'])
            if lo < v3.START or hi > v3.END:
                raise ValueError('audited slice outside development')
            key = (event['path'], event['start'], event['end'], tuple(event['columns']))
            if key in seen:
                continue
            seen.add(key)
            rows = partitions.loc[(partitions.partition_path == event['path']) &
                (pd.to_datetime(partitions.effective_start) <= lo) &
                (pd.to_datetime(partitions.effective_end) >= hi)]
            if len(rows) != 1 or rows.iloc[0].output_sha256 != event['parent_sha256']:
                raise ValueError('audited slice parent mismatch')
            row = rows.iloc[0].to_dict()
            frame = normalize_keys(read_effective_partition(
                {**row, 'effective_start': lo, 'effective_end': hi}, columns=event['columns']))
            if len(frame) != event['rows'] or frame_hash(frame) != event['slice_hash']:
                raise ValueError(f'development feature slice changed: {key[:3]}')
            for factor in event['columns']:
                coverage.setdefault(factor, set()).update(frame.datetime.unique())
        print(f'Bounded feature integrity verified: {folder.name}', flush=True)
    days = set(protocol['intervals'].feature_time.to_numpy())
    for factor in members['Broad494']:
        if not days <= coverage.get(factor, set()):
            raise ValueError(f'incomplete audited feature coverage: {factor}')


def run_pool(out, pool, context, bound):
    source, old, partitions, protocol, members = context
    if pool == 'Strict332' and not v3.completed_chunk(out / 'verification/Broad494', bound):
        raise ValueError('Broad494 independent replay must finish before Strict332')
    for fold in FOLDS:
        folder = out / pool / fold
        if v3.completed_chunk(folder, bound):
            print(f'Validated completed {pool}/{fold}; skipping', flush=True)
            continue
        # Only one fold of raw float64 scratch is retained at a time.
        if shutil.disk_usage(out).free < 30 * 2**30:
            raise OSError('at least 30 GiB free disk required for next fold')
        v3.atomic_write_json(out / 'status.json', dict(status='precomputing', pool=pool, fold=fold))
        v3.publish(folder, bound, lambda stage: precompute_fold(
            stage, fold, source, old['config'], partitions, protocol, members[pool]))
        print(f'Completed {pool}/{fold}', flush=True)
    v3.atomic_write_json(out / 'status.json', dict(status='awaiting_independent_replay', pool=pool))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--pool', choices=POOLS, default='Broad494')
    parser.add_argument('--preflight', action='store_true', help='metadata only; no fit, predictions or source data scan')
    args = parser.parse_args()
    if not re.fullmatch(r'v3_precompute_[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid independent run-id')
    context = load_context()
    if args.preflight:
        print(json.dumps(dict(status='metadata_preflight_pass', folds=FOLDS,
                              pools={k: len(v) for k, v in context[-1].items()},
                              free_gib=shutil.disk_usage(ROOT).free / 2**30,
                              source_data_integrity='deferred_to_user_execution'), indent=2))
        return
    out = ROOT / 'outputs/research_protocol_v3_precompute' / args.run_id
    with v3.run_lock(out / 'run.lock'):
        bound = bind_run(out, context)
        try:
            verify_inputs(context)
            run_pool(out, args.pool, context, bound)
        except Exception as error:
            v3.atomic_write_json(out / 'status.json', dict(status='failed', pool=args.pool,
                                                         error_type=type(error).__name__, error=str(error)))
            raise


if __name__ == '__main__':
    main()
