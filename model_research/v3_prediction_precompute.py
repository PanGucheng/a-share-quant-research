"""V3 float64 Sequence precompute; numerical loop copied unchanged from f2f3fc3 wide_canary.

Only membership is supplied by the caller. Scratch blocks are hashed and removed
before publishing; saved models, predictions and all numerical receipts remain.
"""
from scripts.run_research_protocol_v3_mvp import (
    training_dates, _MemorySampler, read_features, cached_training_labels,
    prepare_training_batch, Float64FileSequence, fit_sequences, predict,
    atomic_write_json, sha256_file,
)
import gc
import time
import numpy as np
import pandas as pd


def precompute_fold(stage, fold_id, out, config, partitions, protocol, factors):
    days = training_dates(protocol, fold_id)
    access, receipts, sequences, targets, weights = [], [], [], [], []
    tick = time.perf_counter()
    try:
        with _MemorySampler() as sampler:
            for month in days.to_period('M').unique():
                selected = days[days.to_period('M') == month]
                features = read_features(partitions, factors, selected, access=access, protocol=protocol,
                                         fold_id=fold_id, role='train')
                labels = cached_training_labels(out, protocol, fold_id, selected)
                x, y, w, receipt = prepare_training_batch(features, labels, factors,
                    protocol=protocol, fold_id=fold_id, minimum_pairs=config['minimum_daily_pairs'])
                path = stage / f'train_{month}.float64'
                x.tofile(path)
                sequences.append(Float64FileSequence(path, len(factors)))
                targets.append(y)
                weights.append(w)
                receipts.append(dict(month=str(month), **receipt))
                print(f'{fold_id}: prepared {month}, rows={len(y)}', flush=True)
                del features, labels, x
                gc.collect()
            prepare_seconds = time.perf_counter() - tick
            model = fit_sequences(sequences, np.concatenate(targets), np.concatenate(weights), factors,
                                  fold_id=fold_id, config=config)
            model.booster.save_model(str(stage / 'model.txt'))
            import lightgbm as lgb
            restored = lgb.Booster(model_file=str(stage / 'model.txt'))
            source = protocol['assignments']
            evaluation = pd.DatetimeIndex(source.loc[
                (source.fold_id == fold_id) & (source.role == 'predict'), 'datetime'])
            predictions = []
            tick = time.perf_counter()
            for month in evaluation.to_period('M').unique():
                selected = evaluation[evaluation.to_period('M') == month]
                frame = read_features(partitions, factors, selected, access=access,
                                      protocol=protocol, fold_id=fold_id, role='predict')
                pred = predict(model, frame, protocol=protocol)
                daily = pd.concat([predict(model, part, protocol=protocol)
                                  for _, part in frame.groupby('datetime')], ignore_index=True)
                if not pred.equals(daily):
                    raise ValueError('wide month/day prediction parity failed')
                original = model.booster
                model.booster = restored
                if not pred.equals(predict(model, frame, protocol=protocol)):
                    raise ValueError('saved wide model prediction parity failed')
                model.booster = original
                predictions.append(pred)
                del frame
            predictions = pd.concat(predictions, ignore_index=True)
            predictions.to_parquet(stage / 'engineering_predictions.parquet', index=False)
            predict_seconds = time.perf_counter() - tick
    finally:
        for seq in sequences:
            seq.close()
    resource = dict(model.receipt)
    resource.update(storage='monthly_float64_sequence', feature_count=len(factors),
        peak_rss_mib=sampler.peak_mb, prepare_seconds=prepare_seconds, predict_seconds=predict_seconds,
        prediction_rows=len(predictions), prediction_coverage=float(predictions.score.notna().mean()),
        predicted_dates=int(predictions.datetime.nunique()), monthly_daily_exact_parity=True,
        saved_model_exact_parity=True, memory_budget_gib=12,
        fold_resource_within_budget=bool(sampler.peak_mb <= 12 * 1024),
        full_width_resource_qualified=False, engineering_only=True, batch_receipts=receipts)
    atomic_write_json(stage / 'resource.json', resource)
    atomic_write_json(stage / 'access.json', {'access': access})

    blocks = {seq.path.name: dict(sha256=sha256_file(seq.path), bytes=seq.path.stat().st_size)
              for seq in sequences}
    atomic_write_json(stage / 'scratch_blocks.json', blocks)
    for seq in sequences:
        if seq.path.parent.resolve() != stage.resolve() or seq.path.suffix != '.float64':
            raise ValueError('scratch path outside current unpublished fold')
        seq.path.unlink()
