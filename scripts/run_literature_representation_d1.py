"""Build a diagnostic recipe, or scan/replay only its 2010–2023 feature structure.

No arbitrary input path/date/column flags. Full scans are deliberately user-run.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import pyarrow

from factor_research.literature_design import build_recipe
from factor_research.literature_inputs import check_aliases, frame_digest, read_features
from factor_research.literature_representation import KEYS, digest, legal_dates, transform_day, validate_recipe
from research_validation.canonical_dataset import canonical_dataset_identity
from research_validation.literature_oracle import naive_day

PACKET = Path('reports/literature_factor_representation_d1/candidate_v1')
CANONICAL = Path('outputs/canonical_historical_dataset_assembly_v1/current')
V3 = Path('outputs/research_protocol_v3_mvp/v3_recompute_audit_20260909_v1')
REVIEW = Path('reports/candidate_consolidation_v0_5/v0_5_1')
SNAPSHOT = Path('docs/research/literature_factor_compression/AUDIT_METADATA.json')
CODE = ['factor_research/literature_design.py', 'factor_research/literature_representation.py',
        'factor_research/literature_inputs.py', 'research_validation/literature_oracle.py',
        'research_validation/canonical_dataset.py', 'scripts/run_literature_representation_d1.py']
CANONICAL_ID = 'canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423'
V3_CONTRACT = 'a73a2a504c7e13d92273837c22d4bc087ac31190d1dc0d1aed7365f74671858e'


def sha(path, *, lf=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b'\r\n', b'\n') if lf else data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def records(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def checked_sources(root):
    """Fixed metadata allowlist; never hash physical value files or sealed outputs."""
    snapshot = read_json(root / SNAPSHOT)
    pins = snapshot['source_file_sha256']
    selected = [str(REVIEW / n).replace('\\', '/') for n in
                ['economic_semantic_review.csv', 'exact_alias_registration.csv']]
    selected += ['reports/candidate_consolidation_v0_5/feature_quality.csv']
    hashes = {}
    for name in selected:
        actual = sha(root / name)
        if actual != pins[name]:
            raise ValueError(f'planning source changed: {name}')
        hashes[name] = actual
    contract = read_json(root / V3 / 'contract.json')
    if digest(contract) != V3_CONTRACT:
        raise ValueError('V3 source contract mismatch')
    hashes[(V3 / 'contract.json').as_posix()] = V3_CONTRACT
    for name, expected in contract['canonical_metadata'].items():
        path = CANONICAL / name
        if sha(root / path) != expected:
            raise ValueError(f'canonical metadata changed: {name}')
        hashes[path.as_posix()] = expected
    p0 = read_json(root / V3 / 'p0/receipt.json')
    if p0['contract_hash'] != V3_CONTRACT or p0['status'] != 'complete':
        raise ValueError('P0 receipt mismatch')
    for name in ['assignments.csv', 'folds.csv', 'intervals.csv']:
        path = V3 / 'p0' / name
        actual = sha(root / path)
        if actual != p0['file_hashes'][name]:
            raise ValueError(f'P0 calendar metadata changed: {name}')
        hashes[path.as_posix()] = actual
    # Hash source code only, never execute factor construction or label helpers.
    audit = read_json(root / REVIEW / 'SOURCE_AUDIT.json')
    for name, expected in audit['hashes'].items():
        path = Path(name)
        if sha(root / path) != expected:
            raise ValueError(f'canonical/source formula pin changed: {name}')
        hashes[path.as_posix()] = expected
    for path in [SNAPSHOT, REVIEW / 'SOURCE_AUDIT.json', REVIEW / 'representative_proposal_board.csv',
                 Path('docs/LITERATURE_GROUNDED_FACTOR_COMPRESSION_PLAN.md')]:
        hashes[path.as_posix()] = sha(root / path)
    return hashes


def build_packet(root=ROOT):
    target = root / PACKET
    if target.exists():
        raise ValueError('candidate packet exists; preserve it, use verify instead')
    hashes = checked_sources(root)
    semantics = [r for r in records(root / REVIEW / 'economic_semantic_review.csv') if r['active'] == 'True']
    aliases = records(root / REVIEW / 'exact_alias_registration.csv')
    inventory, recipe, dense = build_recipe(semantics, aliases, hashes)
    lineage = pd.read_csv(root / CANONICAL / 'factor_lineage.csv').fillna('')
    partitions = pd.read_csv(root / CANONICAL / 'partition_manifest.csv').fillna('')
    if canonical_dataset_identity(partitions, lineage) != CANONICAL_ID:
        raise ValueError('canonical dataset identity mismatch')
    lineage = lineage.set_index('factor').to_dict('index')
    quality = pd.read_csv(root / 'reports/candidate_consolidation_v0_5/feature_quality.csv').set_index('factor').to_dict('index')
    proposals = pd.read_csv(root / REVIEW / 'representative_proposal_board.csv', usecols=[
        'factor', 'proposal_role_0_995', 'reason_0_995', 'unknown_pair_count_0_995']).set_index('factor').to_dict('index')
    for row in inventory:
        line = lineage[row['factor']]
        if (line['research_usable'] is not True or line['temporarily_blocked'] is not False
                or line['block_reason'] or line['historical_semantics'] != line['authoritative_semantics']
                or line['continuation_semantics'] != line['authoritative_semantics']):
            raise ValueError(f"canonical correctness blocker: {row['factor']}")
        proposal = proposals[row['factor']]
        if proposal['proposal_role_0_995'] not in {'deferred', 'retain_semantic_or_horizon_variant', 'retain_unmerged_with_unknown_pairs'}:
            raise ValueError('new approximate-substitution evidence needs explicit review')
        row.update({'lineage_' + k: v for k, v in line.items()})
        row.update({'quality_' + k: v for k, v in quality[row['factor']].items()})
        row.update({'legacy_' + k: v for k, v in proposal.items()})
    recipe['canonical_dataset_id'] = CANONICAL_ID
    recipe['code_hashes_lf'] = {p: sha(root / p, lf=True) for p in CODE}
    recipe['literature_provenance'] = dict(plan='docs/LITERATURE_GROUNDED_FACTOR_COMPRESSION_PLAN.md',
        local_papers=snapshot_papers(root), limitation='themes motivate semantic grouping; no return-based literature clustering copied')
    recipe['recipe_hash'] = digest(recipe)
    counts = dict(identities=len(inventory), unique_parents=len(recipe['parents']), common_raw_U=len(recipe['u']),
        raw_representatives=len(recipe['representatives']), composite_outputs=len(recipe['composites']),
        rank_singletons=sum(n['type'] == 'rank_singleton' for n in recipe['composites']),
        multifamily_outputs=sum(len(n['families']) > 1 for n in recipe['composites']),
        exact_alias_removals=len(inventory)-len(recipe['parents']),
        arms={k:len(v) for k,v in recipe['arms'].items()}, dense_bucket_outputs=len(dense),
        dense_fields=len(set(r['dense_field'] for r in inventory if r['dense_field'])),
        dense_unique_nodes=sum(g['unique_lags'] for g in dense),
        dense_lag_resolution_removed=sum(g['lost_point_resolution'] for g in dense),
        unresolved_semantics=sum(r['semantic_resolved'] == 'False' for r in inventory),
        known_canonical_blockers=0, themes=dict(Counter(r['economic_theme'] for r in inventory)),
        unique_measurement_families=len(set(r['measurement_family'] for r in inventory)),
        source_horizons=len(set(r['horizon'] for r in inventory)),
        U_reasons=dict(Counter(r['replacement_hold_reason'] for r in inventory if r['disposition']=='U_RAW')))
    evaluation = dict(status='future_contract_only_not_executable', outcomes_authorized=False,
        contrasts=['S-B','R-B','C-B','H-B','C-R','H-C'], sidedness='two-sided', correction='single_Holm_family',
        alpha=.05, statistic='paired_daily_IC_delta', samples='all_five_arms_same_keys_and_dates',
        hac=dict(kernel='Bartlett', primary=20, sensitivity=40),
        bootstrap=dict(kind='moving_block', primary=20, sensitivity=40, resamples=1000, seed=20260909,
                       shared_date_indices=True, cannot_cross_calendar_gaps=True),
        noninferiority_enabled=False, no_model_or_threshold_sweep=True)
    access = dict(status='application_enforced_allowlist_not_OS_sandbox', start='2010-01-29', end='2023-12-29',
        feature_parents=sorted(r['factor'] for r in inventory), source_hashes=hashes,
        forbidden=['labels','prices_as_outcomes','predictions','importance','IC','FDR','portfolio','2024+values'],
        physical_parquet='project approved features and bounded date predicates; no whole-file hash',
        raw_policy='finite raw values unchanged; infinities become missing as in V3 float64 input',
        complete_dated_universe_before_rank=True, membership='canonical preassembled dated PIT universe',
        full_scan='2010-2023 months; diagnostics and independent naive replay, no persisted feature matrices')
    target.mkdir(parents=True)
    write_json(target / 'recipe.json', recipe)
    write_json(target / 'counts.json', counts)
    write_json(target / 'dense_groups.json', dense)
    write_json(target / 'evaluation_contract.json', evaluation)
    write_json(target / 'access_contract.json', access)
    pd.DataFrame(inventory).to_csv(target / 'inventory_494.csv', index=False, lineterminator='\n')
    for arm, columns in recipe['arms'].items():
        write_json(target / f'{arm}_candidate.json', dict(status=recipe['status'], d2_authorized=False,
            arm=arm, ordered_columns=columns, feature_identity_hash=digest(columns), recipe_hash=recipe['recipe_hash']))
    write_json(target / 'packet_hashes.json', {p.name:sha(p, lf=True) for p in sorted(target.iterdir())})
    return counts


def snapshot_papers(root):
    return read_json(root / SNAPSHOT)['local_papers']


def load_packet(root=ROOT):
    packet = root / PACKET
    for name, expected in read_json(packet / 'packet_hashes.json').items():
        if Path(name).name != name or sha(packet / name, lf=True) != expected:
            raise ValueError('candidate packet content changed')
    recipe = read_json(packet / 'recipe.json')
    expected = recipe['recipe_hash']
    if digest({k:v for k,v in recipe.items() if k != 'recipe_hash'}) != expected:
        raise ValueError('recipe digest mismatch')
    validate_recipe(recipe)
    for path, expected in recipe['code_hashes_lf'].items():
        if path not in CODE or sha(root / path, lf=True) != expected:
            raise ValueError(f'runner code changed: {path}')
    if set(recipe['code_hashes_lf']) != set(CODE) or checked_sources(root) != recipe['source_hashes']:
        raise ValueError('source/code contract changed')
    return recipe, records(packet / 'inventory_494.csv')


def scheduled_dates(root, mode):
    calendar = pd.DatetimeIndex(pd.read_csv(root / V3 / 'p0/intervals.csv', usecols=['feature_time']).feature_time)
    dates = legal_dates(calendar[(calendar >= '2010-01-29') & (calendar <= '2023-12-29')])
    if mode == 'canary':
        sampled = []
        for start, end in [(2010,2014),(2015,2017),(2018,2020),(2021,2023)]:
            era = dates[(dates.year >= start) & (dates.year <= end)]
            sampled.extend([era[0], era[(len(era)-1)//2], era[-1]])
        return legal_dates(sampled)
    if mode != 'full':
        raise ValueError('invalid scan mode')
    return dates


def compare_oracle(actual, expected):
    maximum = 0.
    for arm, frame in actual.items():
        other = expected[arm]
        if list(frame.columns) != list(other.columns) or not frame[KEYS].equals(other[KEYS]):
            raise ValueError('oracle output schema/key mismatch')
        a, b = frame.iloc[:, 2:].to_numpy(), other.iloc[:, 2:].to_numpy()
        if not np.array_equal(np.isfinite(a), np.isfinite(b)):
            raise ValueError('oracle output mask mismatch')
        finite = np.isfinite(a)
        delta = float(np.max(np.abs(a[finite]-b[finite]))) if finite.any() else 0.
        if not np.allclose(a, b, rtol=0., atol=1e-12, equal_nan=True):
            raise ValueError('oracle output value mismatch')
        maximum = max(maximum, delta)
    return maximum


def verify_chunk(folder, binding, dates):
    receipt = read_json(folder / 'receipt.json')
    if receipt['binding'] != binding or receipt['dates'] != [str(d.date()) for d in dates] or receipt['oracle'] != 'pass':
        raise ValueError('chunk receipt identity mismatch')
    if set(receipt['files']) != {'leaves.parquet','families.parquet','outputs.parquet','arms.parquet','access.jsonl'}:
        raise ValueError('incomplete chunk file set')
    for name, expected in receipt['files'].items():
        if sha(folder / name) != expected:
            raise ValueError(f'corrupt diagnostic chunk: {folder.name}/{name}')
    return receipt


def summarize_structure(root, base, months, verify_only):
    """Aggregate diagnostic counts only; P0 role metadata never enables evaluation."""
    assignments = pd.read_csv(root / V3 / 'p0/assignments.csv', parse_dates=['datetime'])
    assignments = assignments.loc[assignments.role.isin(['train','predict'])]
    groups = [(f'{fold}:{role}', pd.DatetimeIndex(rows.datetime))
              for (fold,role),rows in assignments.groupby(['fold_id','role'], sort=True)]
    output_hashes = {}
    for kind in ['leaves','outputs','arms']:
        data = pd.concat([pd.read_parquet(base / str(m) / f'{kind}.parquet') for m in months], ignore_index=True)
        data['datetime'] = pd.to_datetime(data.datetime)
        data['year'] = data.datetime.dt.year
        if kind == 'leaves':
            data['rank_suppressed_cells'] = np.where(data.rank_reason.isin(['constant','below_rank_min']),data.finite_n,0)
            for reason in ['all_missing','constant','below_rank_min','raw_U_not_ranked']:
                data[reason+'_dates'] = data.rank_reason.eq(reason).astype(int)
            key = 'factor'
            spec = dict(dates=('datetime','size'), universe_rows=('universe_n','sum'),
                finite_cells=('finite_n','sum'), n_below_100_dates=('n_below_100','sum'),
                rank_suppressed_cells=('rank_suppressed_cells','sum'), infinite_cells=('infinite_n','sum'),
                **{r+'_dates':(r+'_dates','sum') for r in ['all_missing','constant','below_rank_min','raw_U_not_ranked']})
        elif kind == 'outputs':
            data['l1_sum'] = data.mean_l1_weight_drift.fillna(0)*data.valid_rows
            key = 'output'
            spec = dict(dates=('datetime','size'), frozen_families=('frozen_families','first'),
                universe_rows=('universe_n','sum'), valid_rows=('valid_rows','sum'), missing_rows=('missing_rows','sum'),
                n_below_100_dates=('output_n_below_100','sum'), constant_dates=('constant_output','sum'),
                single_family_valid_rows=('single_family_valid_rows','sum'), effective_family_sum=('effective_family_sum','sum'),
                max_family_weight=('max_family_weight','max'), l1_sum=('l1_sum','sum'),
                raw_any_parent_rows=('raw_any_parent_rows','sum'),
                raw_available_but_output_missing=('raw_available_but_output_missing','sum'), infinite_cells=('infinite_n','sum'))
        else:
            key = 'arm'
            spec = dict(dates=('datetime','size'), universe_rows=('rows','sum'), columns=('columns','first'),
                        finite_cells=('finite_cells','sum'), cells=('cells','sum'), infinite_cells=('infinite_cells','sum'))
        year = data.groupby(['year',key], sort=True).agg(**spec).reset_index()
        by_fold = []
        for label, days in groups:
            selected = data.loc[data.datetime.isin(days)]
            if selected.empty:
                continue
            result = selected.groupby(key,sort=True).agg(**spec).reset_index()
            result.insert(0,'fold_role',label)
            by_fold.append(result)
        tables = {'year':year, 'fold':pd.concat(by_fold,ignore_index=True)}
        for scale, table in tables.items():
            if kind == 'outputs':
                table['finite_rate'] = table.valid_rows / table.universe_rows
                denominator = table.valid_rows.replace(0,np.nan)
                table['mean_effective_families'] = table.effective_family_sum / denominator
                table['single_family_share_valid'] = table.single_family_valid_rows / denominator
                table['mean_l1_weight_drift'] = table.l1_sum / denominator
                table['raw_union_availability_loss'] = table.raw_available_but_output_missing / table.raw_any_parent_rows.replace(0,np.nan)
            elif kind == 'leaves':
                table['finite_rate'] = table.finite_cells / table.universe_rows
            else:
                table['finite_rate'] = table.finite_cells / table.cells
            name = f'{scale}_{kind}.csv'
            path = base / name
            payload = table.to_csv(index=False,lineterminator='\n').encode('utf-8')
            if path.exists():
                if path.read_bytes() != payload:
                    raise ValueError('structural aggregate changed; preserve prior file')
            elif verify_only:
                raise ValueError(f'missing structural aggregate: {name}')
            else:
                with path.open('xb') as stream:
                    stream.write(payload)
            output_hashes[name] = sha(path)
    return output_hashes


def scan(root, run_id, mode, verify_only=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', run_id):
        raise ValueError('invalid run id')
    recipe, inventory = load_packet(root)
    dates = scheduled_dates(root, mode)
    base = root / 'outputs/literature_factor_representation_d1' / run_id / mode
    binding = dict(recipe_hash=recipe['recipe_hash'], mode=mode,
                   runtime=dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__, pyarrow=pyarrow.__version__))
    partitions = pd.read_csv(root / CANONICAL / 'partition_manifest.csv').fillna('')
    approved = sorted(r['factor'] for r in inventory)
    months = dates.to_period('M').unique()
    receipts = []
    for month in months:
        days = dates[dates.to_period('M') == month]
        folder = base / str(month)
        if (folder / 'receipt.json').exists():
            receipts.append(verify_chunk(folder, binding, days))
            print(f'{mode} {month}: verified existing chunk', flush=True)
            continue
        if verify_only:
            raise ValueError(f'missing chunk: {month}')
        if folder.exists():
            raise ValueError(f'incomplete chunk preserved: {folder}; inspect failure before using a fresh run id')
        folder.mkdir(parents=True)
        start = time.perf_counter()
        diagnostics = {k:[] for k in ['leaves','families','outputs','arms']}
        with (folder / 'access.jsonl').open('x', encoding='utf-8', newline='\n') as log:
            def access(event):
                log.write(json.dumps(event, sort_keys=True) + '\n')
                log.flush()
            frame = read_features(partitions, approved, days, approved=approved, access=access)
        alias_count = check_aliases(frame, inventory)
        deltas, output_hashes = [], []
        for day, daily in frame.groupby('datetime', sort=True):
            source = daily[KEYS + recipe['parents']].reset_index(drop=True)
            arms, diag = transform_day(source, recipe)
            deltas.append(compare_oracle(arms, naive_day(source, recipe)))
            for kind, values in diag.items():
                diagnostics[kind].extend(values)
            for arm, result in arms.items():
                values = result.iloc[:, 2:].to_numpy()
                diagnostics['arms'].append(dict(datetime=str(day.date()), arm=arm, rows=len(result),
                    columns=values.shape[1], finite_cells=int(np.isfinite(values).sum()), cells=int(values.size),
                    infinite_cells=int(np.isinf(values).sum())))
            output_hashes.append(dict(datetime=str(day.date()), hashes={k:frame_digest(v) for k,v in arms.items()}))
        for kind, values in diagnostics.items():
            pd.DataFrame(values).to_parquet(folder / f'{kind}.parquet', index=False)
        receipt = dict(binding=binding, dates=[str(d.date()) for d in days], rows=len(frame),
            source_slice_hash=frame_digest(frame), output_hashes=output_hashes, oracle='pass',
            oracle_atol=1e-12, oracle_max_abs_error=max(deltas), exact_alias_pairs=alias_count,
            input_frame_mib=float(frame.memory_usage(deep=True).sum()/2**20),
            wall_seconds=time.perf_counter()-start,
            files={p.name:sha(p) for p in sorted(folder.iterdir())})
        write_json(folder / 'receipt.json', receipt)
        receipts.append(verify_chunk(folder, binding, days))
        print(f'{mode} {month}: {len(days)} dates; {len(frame)} rows; oracle pass; {receipt["wall_seconds"]:.1f}s', flush=True)
    aggregate_hashes = summarize_structure(root, base, months, verify_only)
    summary = dict(status='structural_scan_replayed_policy_review_required', d2_authorized=False,
        binding=binding, dates=len(dates), chunks=len(receipts), rows=sum(r['rows'] for r in receipts),
        oracle='all_dates_pass', oracle_max_abs_error=max(r['oracle_max_abs_error'] for r in receipts),
        scan_wall_seconds=sum(r['wall_seconds'] for r in receipts),
        peak_input_frame_mib=max(r['input_frame_mib'] for r in receipts),
        resource_limit='input frame size only; not process peak RSS; full scan includes independent naive oracle',
        chunk_receipt_hashes={str(m):sha(base / str(m) / 'receipt.json') for m in months},
        aggregate_hashes=aggregate_hashes,
        limitations=['canary does not establish whole-year/fold rates' if mode=='canary' else 'policy still requires semantic review',
                     'no trained models, prediction scores, outcome statistics or recent values'])
    destination = base / 'summary.json'
    if destination.exists():
        if read_json(destination) != summary:
            raise ValueError('summary differs; preserve prior evidence')
    elif verify_only:
        raise ValueError('missing completed summary')
    else:
        write_json(destination, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build','check','canary','full','verify-canary','verify-full'])
    parser.add_argument('--run-id', default='d1_structure_20260910_v1')
    args = parser.parse_args()
    if args.action == 'build':
        result = build_packet()
    elif args.action == 'check':
        recipe, inventory = load_packet()
        result = dict(status='metadata_code_packet_verified', rows=len(inventory), recipe_hash=recipe['recipe_hash'])
    else:
        result = scan(ROOT, args.run_id, args.action.removeprefix('verify-'), args.action.startswith('verify-'))
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
