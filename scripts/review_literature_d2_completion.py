"""Read-only postrun audit: hashes, receipts, engineering metadata; no value replay."""
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model_research import literature_precompute as job  # noqa: E402
import pandas as pd


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    ctx = job.context()
    out = ROOT / 'outputs/literature_factor_representation_d2/d2_rch_20260910_v1'
    target = ROOT / 'reports/literature_factor_representation_d2/completion_v1'
    require(not target.exists(), 'completion review already exists; preserve it')
    contract = job.d1.read_json(out / 'contract.json')
    require(contract == job.contract(ctx), 'current source/runtime/run contract mismatch')
    bound = job.digest(contract)
    require(not list(out.rglob('*.incomplete')), 'incomplete stages remain')
    require(not list(out.rglob('failure.json')), 'failure evidence needs review')
    dates = job.d1.scheduled_dates(ROOT, 'full')
    receipts, cache_meta, rows, replay_rows = {}, {}, [], []
    access_count = 0
    started = time.perf_counter()

    def verify(folder):
        receipt = job.complete(folder, bound)
        require(bool(receipt), f'missing receipt: {folder}')
        receipts[folder.relative_to(out).as_posix()] = job.d1.sha(folder / 'receipt.json')
        return receipt

    def access_matches(folder, months):
        nonlocal access_count
        actual = [json.loads(line) for line in (folder / 'access.jsonl').read_text().splitlines()]
        expected = []
        for month in months:
            source = ROOT / job.freeze.SCAN / str(month)
            receipt = job.d1.read_json(source / 'receipt.json')
            path = source / 'access.jsonl'
            require(job.d1.sha(path) == receipt['files']['access.jsonl'], 'D1 access hash mismatch')
            expected.extend(json.loads(line) for line in path.read_text().splitlines())
        require(actual == expected, 'fresh access evidence differs from frozen D1 slices')
        for event in actual:
            require('2010-01-29' <= event['start'] <= event['end'] <= '2023-12-29', 'access date violation')
            require(set(event['columns']) <= {r['factor'] for r in ctx['inventory']}, 'column violation')
            access_count += event['stage'] == 'complete'

    for month in dates.to_period('M').unique():
        folder = out / 'cache' / str(month)
        verify(folder)
        meta = job.d1.read_json(folder / 'metadata.json')
        source = ROOT / job.freeze.SCAN / str(month) / 'receipt.json'
        evidence = job.d1.read_json(source)
        require(meta['source_receipt_sha256'] == job.d1.sha(source), 'cache/D1 binding mismatch')
        require(meta['dates'] == evidence['dates'] and meta['rows'] == evidence['rows'], 'cache key counts mismatch')
        require(meta['ordered_columns'] == ctx['recipe']['arms']['H'], 'cache order mismatch')
        access_matches(folder, [month])
        cache_meta[str(month)] = meta
    print('168 cache receipts, bytes and access evidence verified', flush=True)
    for arm in job.POOLS:
        for fold in job.FOLDS:
            folder, replay = out / arm / fold, out / 'replay' / arm / fold
            verify(folder)
            verify(replay)
            resource = job.d1.read_json(folder / 'resource.json')
            result = job.d1.read_json(replay / 'result.json')
            identity = job.d1.read_json(folder / 'representation.json')
            require(identity['ordered_columns'] == ctx['recipe']['arms'][arm]
                    and identity['parent_dependencies'] == job.dependencies(ctx['recipe'], arm)
                    and identity['output_types'] == job.output_types(ctx['recipe'], arm)
                    and identity['freeze_hash'] == ctx['approval']['freeze_hash']
                    and identity['recipe_hash'] == ctx['recipe']['recipe_hash'], 'model representation mismatch')
            require(resource['batch_receipts'] == ctx['anchors'][fold]['batch_receipts'], 'anchor training keys mismatch')
            require(resource['fit_rows'] == ctx['anchors'][fold]['fit_rows'], 'training count mismatch')
            require(resource['actual_iterations'] == 100 and resource['outer_labels_accessed'] is False
                    and resource['config_hash'] == job.v3.canonical_hash(ctx['config']), 'learner contract mismatch')
            require(result['status'] == 'exact' and result['model_receipt_sha256'] == job.d1.sha(folder / 'receipt.json')
                    and result['model_sha256'] == resource['model_sha256'], 'replay binding mismatch')
            require(result['rows'] == resource['prediction_rows'] == ctx['anchors'][fold]['prediction_rows']
                    and result['dates'] == resource['predicted_dates'] == ctx['anchors'][fold]['predicted_dates'], 'prediction counts mismatch')
            require(result['representation_max_abs_error'] <= 1e-12, 'representation oracle mismatch')
            inputs = job.d1.read_json(folder / 'inputs.json')
            for role in ['train', 'predict']:
                expected = ctx['protocol']['assignments']
                days = pd.DatetimeIndex(expected.loc[(expected.fold_id == fold) & (expected.role == role), 'datetime'])
                events = [e for e in inputs if e['role'] == role]
                require([d for e in events for d in e['dates']] == days.strftime('%Y-%m-%d').tolist(), 'input dates incomplete')
                for event in events:
                    require(event['cache_receipt_hash'] == receipts['cache/' + event['month']], 'input cache binding mismatch')
                if role == 'predict':
                    access_matches(replay, days.to_period('M').unique())
            rows.append(dict(arm=arm, fold=fold, train_rows=resource['fit_rows'],
                prediction_rows=resource['prediction_rows'], coverage=resource['prediction_coverage'],
                model_sha256=resource['model_sha256'], replay='exact',
                **{k: resource[k] for k in ['prepare_seconds', 'fit_seconds', 'dataset_seconds',
                    'predict_seconds', 'peak_rss_mib', 'temporary_disk_bytes']}))
            replay_rows.append(result)
        print(f'{arm}: all nine models and independent replay receipts verified', flush=True)
    verify(out / 'sealed')
    require(pd.DataFrame(rows).to_csv(index=False).encode() == (out / 'sealed/folds.csv').read_bytes(), 'sealed aggregate mismatch')
    seal = job.d1.read_json(out / 'sealed/result.json')
    require(seal['models'] == 27 and seal['arms'] == {a: 'all_nine_exact' for a in job.POOLS}, 'seal status mismatch')
    target.mkdir()
    pd.DataFrame(rows).to_csv(target / 'folds.csv', index=False, lineterminator='\n')
    job.d1.write_json(target / 'replay_results.json', replay_rows)
    job.d1.write_json(target / 'verification.json', dict(status='D2_COMPLETE_VERIFIED_ALL_FIVE_ARMS_SEALED',
        scope='receipt/byte integrity and engineering metadata audit; independent numeric replay ran in user execution; no fresh canonical or score reads',
        contract_hash=bound, freeze_hash=ctx['approval']['freeze_hash'], recipe_hash=ctx['recipe']['recipe_hash'],
        source_provenance=job.d1.read_json(out / 'provenance.json'), verified_receipts=receipts,
        cache_months=len(cache_meta), cache_rows=sum(m['rows'] for m in cache_meta.values()),
        models=27, prediction_rows=sum(r['prediction_rows'] for r in rows),
        access_slice_completions=access_count, incomplete_stages=0, failure_records=0,
        resume_history='No failed stages found; completed-unit skips are not separately journaled.',
        cache_bytes=sum((out / 'cache' / m / 'representation.parquet').stat().st_size for m in cache_meta),
        cache_wall_seconds=sum(job.d1.read_json(out / 'cache' / m / 'receipt.json')['wall_seconds'] for m in cache_meta),
        model_unit_wall_seconds=sum(job.d1.read_json(out / r['arm'] / r['fold'] / 'receipt.json')['wall_seconds'] for r in rows),
        replay_seconds=sum(r['replay_seconds'] for r in replay_rows),
        review_seconds=time.perf_counter()-started,
        reviewer_sha256_lf=job.d1.sha(Path(__file__), lf=True), outcomes_authorized=False, recent_authorized=False))
    job.d1.write_json(target / 'hashes_lf.json', {p.name: job.d1.sha(p, lf=True) for p in target.iterdir()})
    print('D2 completion audit passed', flush=True)


if __name__ == '__main__':
    main()
