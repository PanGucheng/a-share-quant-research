"""Append-only D1 approval overlay; preserve the diagnostic recipe verbatim."""
from __future__ import annotations

import argparse
import contextlib
import io
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_literature_representation_d1 as d1
from factor_research.literature_representation import digest

FREEZE = Path('reports/literature_factor_representation_d1/freeze_v1')
SCAN = Path('outputs/literature_factor_representation_d1/d1_structure_20260910_v2/full')
BS = Path('outputs/research_protocol_v3_precompute/v3_precompute_broad494_strict332_20260909_v1')


def check(root=ROOT):
    recipe, inventory = d1.load_packet(root)
    packet = root / FREEZE
    bound = d1.read_json(packet / 'freeze.json')
    if digest({k: v for k, v in bound.items() if k != 'freeze_hash'}) != bound['freeze_hash']:
        raise ValueError('freeze digest mismatch')
    for name, expected in bound['files_lf'].items():
        if d1.sha(root / name, lf=True) != expected:
            raise ValueError(f'frozen dependency changed: {name}')
    if bound['recipe_hash'] != recipe['recipe_hash'] or bound['ordered_arms'] != recipe['arms']:
        raise ValueError('frozen recipe identity mismatch')
    if not bound['policy_finalized'] or not bound['d2_authorized']:
        raise ValueError('formal authorization required')
    return bound, recipe, inventory


def build():
    packet = ROOT / FREEZE
    if packet.exists():
        raise ValueError('freeze exists; never overwrite')
    recipe, _ = d1.load_packet()
    with contextlib.redirect_stdout(io.StringIO()):
        d1.scan(ROOT, 'd1_structure_20260910_v2', 'full', verify_only=True)
    review = ROOT / 'reports/literature_factor_representation_d1/full_review_v2'
    for name, expected in d1.read_json(review / 'file_hashes_lf.json').items():
        if d1.sha(review / name, lf=True) != expected:
            raise ValueError('full review changed')
    for arm in 'RCH':
        candidate = d1.read_json(ROOT / d1.PACKET / f'{arm}_candidate.json')
        if candidate['ordered_columns'] != recipe['arms'][arm] or candidate['feature_identity_hash'] != digest(recipe['arms'][arm]):
            raise ValueError('candidate arm mismatch')
    bs = d1.read_json(ROOT / BS / 'contract.json')
    authority = d1.read_json(ROOT / d1.V3 / 'contract.json')
    if bs['config'] != authority['config'] or bs['runtime'] != authority['runtime']:
        raise ValueError('B/S learner differs from V3')
    for pool in ['Broad494', 'Strict332']:
        result = d1.read_json(ROOT / BS / 'verification' / pool / 'result.json')
        if result['status'] != 'all_nine_exact' or len(result['folds']) != 9:
            raise ValueError('B/S replay incomplete')
    packet.mkdir()
    semantics = dict(
        dense_estimand='Within a frozen field x horizon bucket, equal-weight average rank over available eligible lag nodes, provided at least half of frozen nodes are available.',
        variable_node_composition=True, fixed_complete_lag_path=False,
        raw_U='Common raw carry-through is not proof of quality or resolved economic semantics; preserve all item caveats and canonical missingness.',
        recursive_status='quality_limited_raw_carry_through',
        recursive_factors=['ta_trend_adx_neg', 'ta_trend_adx_pos', 'ta_volatility_atr'],
        correctness_blocker='stop; never waive because a factor belongs to U',
        multifamily='all frozen families required; coverage loss accepted; no fallback',
        orientation='economic-axis; measurement_orientation, expected_return_direction and representation_sign remain separate',
        substitution='0.995 high-confidence same-semantic same-scale gate; same mechanism/units/operator/inputs/horizon, Full/Era evidence, compatible masks and all-pair complete linkage; zero new substitutions',
        rank='float64 full dated universe, average ties, no jitter/ID tie breaking; constant/all-missing/below-min => NaN; infinity => NaN; no label or survivor mask',
        fold_safety='Each output is a deterministic function only of the complete canonical PIT cross-section on its own date and frozen metadata. No fitted state, inter-date normalization or recursive restart. Chunking/reuse introduces no future observations. Design itself remains retrospective 2010-2023, not selection-past-only.',
    )
    d1.write_json(packet / 'semantics.json', semantics)
    paths = [*[(d1.PACKET / p.name) for p in (ROOT / d1.PACKET).iterdir()],
             *[p.relative_to(ROOT) for p in review.iterdir()],
             SCAN / 'summary.json', BS / 'contract.json',
             *[BS / 'verification' / p / 'result.json' for p in ['Broad494', 'Strict332']],
             FREEZE / 'semantics.json', Path('scripts/freeze_literature_representation.py')]
    # Bind each monthly receipt, which itself binds diagnostics and canonical slice evidence.
    paths += [p.relative_to(ROOT) for p in (ROOT / SCAN).glob('*/receipt.json')]
    bound = dict(schema_version=1, status='D1_CLOSED_REPRESENTATIONS_FROZEN_D2_NOT_YET_RUN',
        approval_date='2026-09-10', approval_status='accepted_user_requested_evaluation_and_implementation',
        approval_source='User request accompanying 完成 D1 Freeze 并推进 D2 预计算; evaluated against full review',
        source_git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        canonical_dataset_id=d1.CANONICAL_ID, source_candidate=d1.PACKET.as_posix(),
        recipe_hash=recipe['recipe_hash'], policy_finalized=True, d2_authorized=True,
        outcomes_authorized=False, recent_authorized=False, ordered_arms=recipe['arms'],
        u_identity_hash=digest(recipe['u']), composite_dag_hash=digest(recipe['composites']),
        frozen_policy=recipe['diagnostic_policy'], semantics=semantics,
        evaluation_contract=d1.read_json(ROOT / d1.PACKET / 'evaluation_contract.json'),
        files_lf={p.as_posix(): d1.sha(ROOT / p, lf=True) for p in paths})
    bound['freeze_hash'] = digest(bound)
    d1.write_json(packet / 'freeze.json', bound)
    check()
    print(bound['freeze_hash'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['build', 'check'])
    args = parser.parse_args()
    if args.mode == 'build':
        build()
    else:
        print(check()[0]['freeze_hash'])
