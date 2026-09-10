"""D2 metadata preflight, feature cache, fixed fits, independent replay, seal."""
from pathlib import Path
import argparse
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model_research import literature_precompute as job  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'cache', 'fit', 'replay', 'seal'])
    parser.add_argument('--run-id', default='d2_rch_20260910_v1')
    parser.add_argument('--arm', choices=job.POOLS, default='H')
    parser.add_argument('--fold', choices=job.FOLDS)
    args = parser.parse_args()
    if not re.fullmatch(r'd2_rch_[A-Za-z0-9_-]{1,64}', args.run_id):
        raise ValueError('invalid run id')
    ctx = job.context()
    if args.mode == 'preflight':
        print(json.dumps(dict(status='metadata_preflight_pass', freeze_hash=ctx['approval']['freeze_hash'],
            columns={arm: len(cols) for arm, cols in ctx['recipe']['arms'].items()},
            free_gib=shutil.disk_usage(ROOT).free / 2**30, code_contract=job.digest(job.contract(ctx)),
            real_model_resource_qualification='user-run H annual_2023 required'), indent=2))
        return
    out = ROOT / 'outputs/literature_factor_representation_d2' / args.run_id
    with job.v3.run_lock(out / 'run.lock'):
        bound = job.bind(out, ctx)
        folds = [args.fold] if args.fold else job.FOLDS
        if args.mode == 'cache':
            job.create_cache(out, ctx, bound)
        elif args.mode == 'fit':
            # H2023 is one of the authorized 27, not an extra trial model.
            if not (args.arm == 'H' and folds == ['annual_2023']):
                gate = out / 'replay/H/annual_2023'
                if not job.complete(gate, bound):
                    raise ValueError('H2023 saved-model replay must qualify resources first')
                resource = job.d1.read_json(out / 'H/annual_2023/resource.json')
                if resource['peak_rss_mib'] > 12 * 1024:
                    raise ValueError('H2023 exceeds frozen 12 GiB resource qualification budget')
            job.run_models(out, ctx, bound, args.arm, folds)
        else:
            from research_validation import literature_prediction_replay as replay
            if args.mode == 'replay':
                replay.run(out, ctx, bound, args.arm, folds)
            else:
                replay.summary(out, ctx, bound)


if __name__ == '__main__':
    main()
