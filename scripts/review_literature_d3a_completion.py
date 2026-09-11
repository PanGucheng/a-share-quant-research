"""Postrun receipt/access audit and aggregate-only statistical verification."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from model_research import frozen_prediction_evaluation as e  # noqa: E402


def main():
    contract = e.checked_contract()  # source bytes/metadata only
    bound = e.d2.digest(contract)
    marker_path = ROOT / e.REPORT / 'OUTCOME_OPENED.json'
    marker = e.read_json(marker_path)
    out = ROOT / 'outputs/literature_factor_representation_d3a' / marker['run_id']
    sealed, exported = out / 'sealed', ROOT / e.REPORT / 'completion_v1'
    target = ROOT / e.REPORT / 'POSTRUN_VERIFICATION.json'
    e.require(not target.exists(), 'postrun verification already exists; preserve evidence')
    e.require(not list(out.rglob('*.incomplete')) and not list(out.rglob('failure.json')), 'run incomplete/failed')
    receipt = e.verify_sealed(sealed, bound)
    e.require(e.verify_sealed(exported, bound) == receipt, 'export receipt differs')
    opening = e.read_json(out / 'OUTCOME_ACCESS_RECEIPT.json')
    e.require(e.sha(out / 'OUTCOME_ACCESS_RECEIPT.json') == e.sha(sealed / 'OUTCOME_ACCESS_RECEIPT.json'), 'access receipt mismatch')
    e.require(opening['marker_sha256'] == e.sha(marker_path), 'opening marker mismatch')
    for key, value in marker.items():
        e.require(opening[key] == value, f'opening field mismatch: {key}')
    for key, source in [('freeze_hash', 'freeze_hash'), ('arm_identity_hashes', 'arm_identity_hashes'),
                        ('predictions', 'predictions'), ('label_sources', 'sources'), ('exact_dates', 'schedules'),
                        ('maturity_cutoff', 'cutoff'), ('code_hashes_lf', 'code_hashes_lf'), ('environment', 'runtime')]:
        e.require(opening[key] == contract[source], f'opening/contract mismatch: {key}')
    e.require(marker['contract_hash'] == bound and marker['scope'] == contract['scope'], 'scope mismatch')

    daily = pd.read_csv(sealed / 'daily.csv', parse_dates=['datetime'], float_precision='round_trip')
    expected_dates = [d for s in contract['schedules'].values() for d in s['predict']]
    mature_dates = {d for s in contract['schedules'].values() for d in s['evaluate']}
    e.require(e.date_strings(daily.datetime) == expected_dates, 'pooled session axis mismatch')
    e.require(daily.mature.tolist() == [d in mature_dates for d in expected_dates], 'maturity mask mismatch')
    e.require(daily.fold.tolist() == [f'annual_{y}' for y in daily.datetime.dt.year], 'fold mismatch')
    e.require(daily.scoreable.eq(daily.mature).all(), 'unexpected missing mature score dates; review required')
    e.require(daily.loc[daily.scoreable, 'common_count'].ge(100).all(), 'common sample minimum')
    e.require(daily.common_count.le(daily.mature_label_count).all(), 'common exceeds labels')
    e.require(daily.loc[~daily.mature, 'common_count'].eq(0).all(), 'immature dates scored')
    e.require(daily.loc[~daily.mature, 'reason'].eq('unscored_development_boundary').all(), 'boundary reason')
    for arm in e.ARMS:
        e.require(daily[f'finite_{arm}'].eq(daily.canonical_count).all(), 'engineering coverage mismatch')
        e.require(daily[f'IC_{arm}'].notna().eq(daily.scoreable).all(), 'IC scoreable mask mismatch')
    for name in e.CONTRASTS:
        a, b = name.split('-')
        np.testing.assert_array_equal(daily[name], daily[f'IC_{a}']-daily[f'IC_{b}'])

    accesses = [json.loads(line) for line in (sealed / 'access.jsonl').read_text().splitlines()]
    expected = []
    for source in contract['sources']:
        fold = source['fold']
        records = [(source, 'keys')] + [(r, 'prediction') for r in contract['predictions'] if r['fold'] == fold] + [(source, 'label')]
        part = daily.loc[daily.fold == fold]
        for record, kind in records:
            key = {'keys': 'keys', 'label': 'labels', 'prediction': 'path'}[kind]
            hash_key = {'keys': 'keys_sha256', 'label': 'label_sha256', 'prediction': 'prediction_sha256'}[kind]
            dates = contract['schedules'][fold]['evaluate' if kind == 'label' else 'predict']
            e.legal_request(contract, fold, kind, dates)
            event = dict(kind=kind, fold=fold, arm=record.get('arm'), path=record[key],
                         parent_sha256=record[hash_key], dates=dates,
                         columns=e.KEYS + {'keys': [], 'label': [e.LABEL, 'exit_date'], 'prediction': ['score', 'reason']}[kind])
            expected.append((event, int(part.loc[part.mature, 'canonical_count'].sum() if kind == 'label' else part.canonical_count.sum())))
    e.require(len(accesses) == 2*len(expected), 'unexpected access events')
    for i, (event, rows) in enumerate(expected):
        e.require(accesses[2*i] == dict(stage='request', **event), 'request differs from bound source/role/date/columns')
        complete = accesses[2*i+1]
        e.require({k: v for k, v in complete.items() if k not in {'rows', 'slice_hash'}} == dict(stage='complete', **event)
                  and complete['rows'] == rows and len(complete['slice_hash']) == 64, 'access completion mismatch')

    # Only small already-published daily aggregates are recalculated. No source scores/labels.
    contrasts, support = e.infer(daily)
    desc = e.descriptive(daily, contract)
    for name, frame in [('contrasts', contrasts), ('descriptive', desc)]:
        e.require(frame.to_csv(index=False, lineterminator='\n').encode() == (sealed / f'{name}.csv').read_bytes(), 'aggregate differs')
    e.require(support == e.read_json(sealed / 'bootstrap_support.json'), 'shared MBB sample hashes/support differ')
    e.require(e.report_text(daily, desc, contrasts, support, bound).encode() == (sealed / 'REPORT.md').read_bytes(), 'report differs')

    # Independently implement the HAC sandwich as a dense kernel on original session positions.
    finite = daily.scoreable.to_numpy()
    positions = np.flatnonzero(finite)
    delta = daily.loc[finite, list(e.CONTRASTS)].to_numpy()
    mu = delta.mean(axis=0)
    residual = delta-mu
    max_error = 0.0
    for lag in [20, 40]:
        kernel = np.maximum(0, 1-np.abs(positions[:, None]-positions[None, :])/(lag+1))
        se = np.sqrt(np.diag(residual.T @ kernel @ residual))/len(positions)
        p = 2*norm.sf(np.abs(mu/se))
        np.testing.assert_allclose(se, contrasts[f'hac{lag}_se'], rtol=1e-12, atol=1e-15)
        np.testing.assert_allclose(p, contrasts[f'hac{lag}_p'], rtol=1e-12, atol=1e-15)
        max_error = max(max_error, float(np.max(np.abs(se-contrasts[f'hac{lag}_se']))))
    ordered = sorted(enumerate(contrasts.hac20_p), key=lambda pair: pair[1])
    maximum, adjusted = 0.0, np.zeros(6)
    for rank, (index, p) in enumerate(ordered):
        maximum = max(maximum, (6-rank)*p)
        adjusted[index] = min(maximum, 1)
    np.testing.assert_array_equal(adjusted, contrasts.holm_p)
    e.require(not contrasts.reject.any(), 'unexpected formal decision; review required')
    e.exclusive_json(target, dict(status='D3A_COMPLETE_VERIFIED_STOP_FOR_REVIEW', contract_hash=bound,
        source_git_commit=marker['git_commit'], outcome_opened_utc=marker['time_utc'],
        opening_marker_sha256=e.sha(marker_path), sealed_receipt_sha256=e.sha(sealed / 'receipt.json'),
        scope='Source and export byte/receipt checks; access audit; daily aggregate recomputation and independent dense-kernel HAC/Holm. No fresh score/label pairing.',
        models=45, prediction_dates=len(daily), mature_scoreable_dates=int(daily.scoreable.sum()),
        unscored_boundary_dates=int((~daily.mature).sum()), common_pairs=int(daily.common_count.sum()),
        mature_canonical_keys=int(daily.loc[daily.mature, 'canonical_count'].sum()),
        completed_accesses=len(expected), source_receipts=len(contract['source_receipts']),
        hac_oracle_max_absolute_se_error=max_error, formal_rejections=int(contrasts.reject.sum()),
        bootstrap_full_support=True, missing_or_failed_stages=False, recent_access=False,
        reviewer_sha256_lf=e.d2.d1.sha(Path(__file__), lf=True)))
    print('D3-A completion, exact aggregate reconstruction and independent HAC/Holm verified.')


if __name__ == '__main__':
    main()
