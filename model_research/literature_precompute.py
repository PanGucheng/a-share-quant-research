"""D2 plumbing around the unchanged V3 float64 Sequence learner.

No outcome evaluator. Only legal training labels are requested; representation
cache creation and saved-model replay are feature-only operations.
"""
from __future__ import annotations

import gc
import json
import shutil
import subprocess
import time

from scripts import run_research_protocol_v3_mvp as v3
import numpy as np
import pandas as pd
from scripts import run_literature_representation_d1 as d1
from scripts import freeze_literature_representation as freeze
from scripts.precompute_research_protocol_v3 import validate_protocol, FOLDS
from factor_research.literature_inputs import read_features, check_aliases, frame_digest
from factor_research.literature_representation import KEYS, digest, legal_dates, transform_day

ROOT = d1.ROOT
POOLS = ('R', 'C', 'H')
CODE = ['model_research/literature_precompute.py',
        'research_validation/literature_prediction_replay.py',
        'scripts/precompute_literature_d2.py', 'scripts/precompute_literature_d2.ps1',
        'scripts/precompute_research_protocol_v3.py']


def context():
    approval, recipe, inventory = freeze.check()
    source = ROOT / d1.V3
    old = d1.read_json(source / 'contract.json')
    if v3.runtime_identity() != old['runtime']:
        raise ValueError('runtime differs from V3 authority')
    # Do not use the old broad context loader: it hashes unrelated outcome files.
    for name, expected in old['code_hashes'].items():
        if expected not in {d1.sha(ROOT / name), d1.sha(ROOT / name, lf=True)}:
            raise ValueError(f'V3 learner dependency changed: {name}')
    for name in ['p0', 'p1']:
        if not v3.completed_chunk(source / name, d1.V3_CONTRACT):
            raise ValueError('missing V3 protocol/eligibility evidence')
    protocol = {}
    for name, columns in [('folds', ['train_start', 'last_legal_train_signal', 'train_label_end',
                                   'evaluation_start', 'evaluation_end', 'latest_mature_eval_signal', 'label_end']),
                          ('assignments', ['datetime']),
                          ('intervals', ['feature_time', 'label_start_time', 'label_end_time'])]:
        protocol[name] = pd.read_csv(source / 'p0' / f'{name}.csv', parse_dates=columns)
    protocol['intervals'] = protocol['intervals'].loc[protocol['intervals'].feature_time <= v3.END]
    validate_protocol(protocol)
    eligibility = pd.read_csv(source / 'p1/feature_eligibility.csv')
    for fold in FOLDS:
        allowed = set(eligibility.loc[(eligibility.fold_id == fold) & eligibility.eligible, 'factor'])
        if not set(recipe['parents']) <= allowed:
            raise ValueError('a frozen parent is not train eligible')
    partitions = pd.read_csv(ROOT / d1.CANONICAL / 'partition_manifest.csv')
    anchors = anchor_metadata()
    return dict(approval=approval, recipe=recipe, inventory=inventory, source=source,
                config=old['config'], runtime=old['runtime'], protocol=protocol, partitions=partitions,
                anchors=anchors)


def anchor_metadata():
    """Only B/S receipts and engineering resources, never models or predictions."""
    base = ROOT / freeze.BS
    anchor_contract = d1.read_json(base / 'contract.json')
    bound = v3.canonical_hash(anchor_contract)
    result = {}
    for pool in ['Broad494', 'Strict332']:
        rows = {}
        for fold in FOLDS:
            folder = base / pool / fold
            receipt = d1.read_json(folder / 'receipt.json')
            if (receipt['status'] != 'complete' or receipt['contract_hash'] != bound
                    or d1.sha(folder / 'resource.json') != receipt['file_hashes']['resource.json']):
                raise ValueError('anchor resource integrity mismatch')
            resource = d1.read_json(folder / 'resource.json')
            rows[fold] = {key: resource[key] for key in ['batch_receipts', 'fit_rows', 'prediction_rows', 'predicted_dates']}
        if result and result != rows:
            raise ValueError('B/S engineering key/count axes differ; investigate compatibility')
        result = rows
    return result


def contract(ctx):
    return dict(scope='D2_fixed_model_prediction_precompute_only', freeze_hash=ctx['approval']['freeze_hash'],
        recipe_hash=ctx['recipe']['recipe_hash'], config=ctx['config'], runtime=ctx['runtime'],
        ordered_arms=ctx['recipe']['arms'], folds=FOLDS, pools=list(POOLS),
        semantics=ctx['approval']['semantics'], maximum_models=27,
        numerical_contract='V3 float64 monthly FileSequence; unchanged learner/target/daily weights',
        representation_replay=dict(atol=1e-12, rtol=0, masks='exact', independent='naive_day'),
        prediction_replay='exact keys/dates/score/reason; no tolerance fallback',
        cache='H union built per day on full dated universe; no fitted or cross-date state',
        labels='audited cache; only legal train dates; exact purge and exit_date checks',
        anchor_training_keys_and_counts=ctx['anchors'],
        outcomes_authorized=False, pool_comparison=False, recent_authorized=False,
        code_hashes_lf={p: d1.sha(ROOT / p, lf=True) for p in [*CODE, *v3.CODE]})


def bind(out, ctx):
    value = contract(ctx)
    path = out / 'contract.json'
    if path.exists():
        if d1.read_json(path) != value:
            raise ValueError('run contract mismatch; preserve evidence')
        provenance = d1.read_json(out / 'provenance.json')
        if provenance['freeze_hash'] != ctx['approval']['freeze_hash']:
            raise ValueError('run provenance mismatch')
    else:
        out.mkdir(parents=True, exist_ok=True)
        d1.write_json(path, value)
        d1.write_json(out / 'provenance.json', dict(
            git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            freeze_commit='d05e7eb', freeze_hash=ctx['approval']['freeze_hash']))
    return digest(value)


def complete(folder, bound):
    # Deterministic staging path: interruption cannot silently start another fit.
    if folder.with_name('.' + folder.name + '.incomplete').exists():
        raise ValueError(f'incomplete unit preserved; diagnose before resuming: {folder}')
    receipt = v3.completed_chunk(folder, bound)
    if receipt:
        if any(not p.is_file() for p in folder.iterdir()):
            raise ValueError('unexpected directory inside completed unit')
        files = set(receipt['file_hashes'])
        if folder.parent.name in POOLS and folder.name in FOLDS:
            expected = ({'result.json', 'access.jsonl'} if folder.parent.parent.name == 'replay'
                        else {'model.txt', 'predictions.parquet', 'resource.json', 'inputs.json',
                              'scratch_blocks.json', 'representation.json'})
            if files != expected:
                raise ValueError('unit is missing required artifacts')
        if folder.parent.name == 'cache' and files != {'access.jsonl', 'metadata.json', 'representation.parquet'}:
            raise ValueError('cache is missing required artifacts')
    return receipt


def publish(folder, bound, writer):
    if complete(folder, bound):
        return
    folder.parent.mkdir(parents=True, exist_ok=True)
    stage = folder.with_name('.' + folder.name + '.incomplete')
    stage.mkdir()
    tick = time.perf_counter()
    try:
        writer(stage)
        files = {p.name: d1.sha(p) for p in stage.iterdir() if p.is_file()}
        d1.write_json(stage / 'receipt.json', dict(status='complete', contract_hash=bound,
            file_hashes=files, wall_seconds=time.perf_counter() - tick))
        stage.rename(folder)
    except Exception as error:
        d1.write_json(stage / 'failure.json', dict(error_type=type(error).__name__, error=str(error)))
        raise


def feature_month(ctx, days, access):
    """Match fresh approved slices exactly to the already-frozen D1 evidence."""
    days = legal_dates(days)
    month = str(days[0].to_period('M'))
    expected = d1.read_json(ROOT / freeze.SCAN / month / 'receipt.json')
    if days.strftime('%Y-%m-%d').tolist() != expected['dates']:
        raise ValueError('canonical replay must request an exact frozen D1 month')
    path = ROOT / freeze.SCAN / month / 'access.jsonl'
    if d1.sha(path) != expected['files']['access.jsonl']:
        raise ValueError('D1 slice access evidence changed')
    old_events = [json.loads(line) for line in path.read_text().splitlines()]
    events = []

    def log(event):
        events.append(event)
        access(event)

    approved = sorted(r['factor'] for r in ctx['inventory'])
    frame = read_features(ctx['partitions'], approved, days, approved=approved, access=log)
    if (events != old_events or check_aliases(frame, ctx['inventory']) != 5
            or frame_digest(frame) != expected['source_slice_hash']):
        raise ValueError('canonical input differs from full D1 scan')
    return frame[KEYS + ctx['recipe']['parents']], expected


def create_cache(out, ctx, bound):
    days = d1.scheduled_dates(ROOT, 'full')
    for month in days.to_period('M').unique():
        selected = days[days.to_period('M') == month]
        folder = out / 'cache' / str(month)
        if complete(folder, bound):
            continue
        if shutil.disk_usage(out).free < 30 * 2**30:
            raise OSError('at least 30 GiB free disk required for cache construction')

        def writer(stage):
            with (stage / 'access.jsonl').open('x', encoding='utf-8') as stream:
                def log(event):
                    stream.write(json.dumps(event) + '\n')
                    stream.flush()
                with v3._MemorySampler() as memory:
                    frame, expected = feature_month(ctx, selected, log)
                    pieces = []
                    for (day, part), evidence in zip(frame.groupby('datetime'), expected['output_hashes']):
                        generated, _ = transform_day(part.reset_index(drop=True), ctx['recipe'])
                        if str(day.date()) != evidence['datetime'] or {
                                arm: frame_digest(value) for arm, value in generated.items()} != evidence['hashes']:
                            raise ValueError('production representation changed since D1')
                        pieces.append(generated['H'])
                    result = pd.concat(pieces, ignore_index=True)
                    result.to_parquet(stage / 'representation.parquet', index=False)
                d1.write_json(stage / 'metadata.json', dict(rows=len(result), dates=expected['dates'],
                    recipe_hash=ctx['recipe']['recipe_hash'], peak_rss_mib=memory.peak_mb,
                    ordered_columns=ctx['recipe']['arms']['H'], source_receipt_sha256=d1.sha(
                        ROOT / freeze.SCAN / str(month) / 'receipt.json')))
        publish(folder, bound, writer)
        print(f'Cache verified against D1: {month}', flush=True)


def cached_features(out, ctx, bound, arm, days, fold, role):
    days = legal_dates(days)
    v3.allowed_dates(ctx['protocol'], fold, role, days)  # before any cache I/O
    if len(days.to_period('M').unique()) != 1:
        raise ValueError('monthly cache request required')
    folder = out / 'cache' / str(days[0].to_period('M'))
    receipt = complete(folder, bound)
    if not receipt:
        raise ValueError('complete representation cache required')
    columns = KEYS + ctx['recipe']['arms'][arm]
    frame = pd.read_parquet(folder / 'representation.parquet', columns=columns,
                            filters=[('datetime', 'in', days.tolist())])
    if (list(frame.columns) != columns or frame.duplicated(KEYS).any()
            or not pd.DatetimeIndex(frame.datetime.unique()).equals(days)
            or not all(frame[c].dtype == np.float64 for c in columns[2:])):
        raise ValueError('representation cache schema/date/key mismatch')
    return frame, dict(month=folder.name, role=role, dates=days.strftime('%Y-%m-%d').tolist(),
                      cache_receipt_hash=d1.sha(folder / 'receipt.json'), slice_hash=frame_digest(frame))


def fit_fold(stage, out, ctx, bound, arm, fold):
    factors = ctx['recipe']['arms'][arm]
    days = v3.training_dates(ctx['protocol'], fold)
    sequences, targets, weights, batches, inputs = [], [], [], [], []
    tick = time.perf_counter()
    try:
        with v3._MemorySampler() as memory:
            for month in days.to_period('M').unique():
                selected = days[days.to_period('M') == month]
                frame, evidence = cached_features(out, ctx, bound, arm, selected, fold, 'train')
                labels = v3.cached_training_labels(ctx['source'], ctx['protocol'], fold, selected)
                evidence['legal_training_label_slice_hash'] = frame_digest(labels)
                inputs.append(evidence)
                x, y, w, batch = v3.prepare_training_batch(frame, labels, factors,
                    protocol=ctx['protocol'], fold_id=fold, minimum_pairs=ctx['config']['minimum_daily_pairs'])
                anchor = next(r for r in ctx['anchors'][fold]['batch_receipts'] if r['month'] == str(month))
                if dict(month=str(month), **batch) != anchor:
                    raise ValueError('training keys/counts differ from both frozen anchors')
                path = stage / f'train_{month}.float64'
                x.tofile(path)
                sequences.append(v3.Float64FileSequence(path, len(factors)))
                targets.append(y)
                weights.append(w)
                batches.append(dict(month=str(month), **batch))
                del frame, labels, x
                gc.collect()
                print(f'{arm}/{fold}: prepared {month}, rows={len(y)}', flush=True)
            preparation_seconds = time.perf_counter() - tick
            model = v3.fit_sequences(sequences, np.concatenate(targets), np.concatenate(weights), factors,
                                     fold_id=fold, config=ctx['config'])
            model.booster.save_model(str(stage / 'model.txt'))
            import lightgbm as lgb
            restored = lgb.Booster(model_file=str(stage / 'model.txt'))
            original = model.booster
            assignments = ctx['protocol']['assignments']
            prediction_days = pd.DatetimeIndex(assignments.loc[
                (assignments.fold_id == fold) & (assignments.role == 'predict'), 'datetime'])
            predictions = []
            tick = time.perf_counter()
            for month in prediction_days.to_period('M').unique():
                selected = prediction_days[prediction_days.to_period('M') == month]
                frame, evidence = cached_features(out, ctx, bound, arm, selected, fold, 'predict')
                inputs.append(evidence)
                pred = v3.predict(model, frame, protocol=ctx['protocol'])
                daily = pd.concat([v3.predict(model, part, protocol=ctx['protocol'])
                                   for _, part in frame.groupby('datetime')], ignore_index=True)
                pd.testing.assert_frame_equal(pred, daily, check_exact=True)
                model.booster = restored
                pd.testing.assert_frame_equal(pred, v3.predict(model, frame, protocol=ctx['protocol']), check_exact=True)
                model.booster = original
                predictions.append(pred)
            result = pd.concat(predictions, ignore_index=True)
            result.to_parquet(stage / 'predictions.parquet', index=False)
            prediction_seconds = time.perf_counter() - tick
    finally:
        for sequence in sequences:
            sequence.close()
    coverage = float(result.score.notna().mean())
    if (len(result) != ctx['anchors'][fold]['prediction_rows']
            or len(prediction_days) != ctx['anchors'][fold]['predicted_dates']):
        raise ValueError('prediction row/date count differs from anchors')
    if coverage < ctx['config']['minimum_annual_prediction_coverage']:
        raise ValueError('prediction engineering coverage below frozen V3 minimum')
    if model.booster.current_iteration() != 100:
        raise ValueError('fixed 100 iterations not realized')
    blocks = {s.path.name: dict(sha256=d1.sha(s.path), bytes=s.path.stat().st_size) for s in sequences}
    d1.write_json(stage / 'scratch_blocks.json', blocks)
    d1.write_json(stage / 'inputs.json', inputs)
    d1.write_json(stage / 'representation.json', dict(arm=arm, ordered_columns=factors,
        feature_identity_hash=digest(factors), recipe_hash=ctx['recipe']['recipe_hash'],
        freeze_hash=ctx['approval']['freeze_hash'], parent_dependencies=dependencies(ctx['recipe'], arm),
        output_types=output_types(ctx['recipe'], arm),
        semantics=ctx['approval']['semantics']))
    resource = dict(model.receipt, prepare_seconds=preparation_seconds, predict_seconds=prediction_seconds,
        storage='monthly_float64_sequence', peak_rss_mib=memory.peak_mb,
        temporary_disk_bytes=sum(x['bytes'] for x in blocks.values()),
        prediction_rows=len(result), predicted_dates=len(prediction_days), prediction_coverage=coverage,
        prediction_keys_hash=frame_digest(result[KEYS]), batch_receipts=batches,
        monthly_daily_exact_parity=True, saved_model_exact_parity=True)
    d1.write_json(stage / 'resource.json', resource)
    for sequence in sequences:
        if sequence.path.parent.resolve() != stage.resolve() or sequence.path.suffix != '.float64':
            raise ValueError('scratch path outside unpublished unit')
        sequence.path.unlink()


def dependencies(recipe, arm):
    nodes = {n['id']: n for n in recipe['composites']}
    return {name: [m['factor'] for f in nodes[name]['families'] for m in f['members']]
            if name in nodes else [name] for name in recipe['arms'][arm]}


def output_types(recipe, arm):
    nodes = {n['id']: n for n in recipe['composites']}
    limited = {'ta_trend_adx_neg', 'ta_trend_adx_pos', 'ta_volatility_atr'}
    return {name: ('quality_limited_raw_carry_through' if name in limited else
                   'common_raw_U' if name in recipe['u'] else
                   'raw_representative' if name not in nodes else
                   'multi_family_composite' if len(nodes[name]['families']) > 1 else
                   'multi_node_composite' if len(nodes[name]['families'][0]['members']) > 1 else
                   'rank_singleton') for name in recipe['arms'][arm]}


def verify_label_cache(ctx):
    # Integrity checksum of existing audited 2010-2022 files, not evaluation.
    # Numerical reads in fit_fold are predicate-limited to the exact legal train dates.
    for year in range(2010, 2023):
        folder = ctx['source'] / 'audit' / str(year)
        receipt = d1.read_json(folder / 'receipt.json')
        if (receipt['contract_hash'] != d1.V3_CONTRACT or receipt['status'] != 'complete'
                or d1.sha(folder / 'labels.parquet') != receipt['file_hashes']['labels.parquet']):
            raise ValueError('audited training label cache changed')


def run_models(out, ctx, bound, arm, folds):
    if shutil.disk_usage(out).free < 30 * 2**30:
        raise OSError('at least 30 GiB free disk required')
    verify_label_cache(ctx)
    for fold in folds:
        publish(out / arm / fold, bound, lambda stage: fit_fold(stage, out, ctx, bound, arm, fold))
        print(f'Complete and hash-verified: {arm}/{fold}', flush=True)
