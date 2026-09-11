"""D3-A: preflight is metadata-only; run opens all five arms once."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model_research import frozen_prediction_evaluation as job  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'preflight', 'run'])
    parser.add_argument('--run-id', default='d3a_five_arm_20260911_v1')
    args = parser.parse_args()
    if not re.fullmatch(r'd3a_[A-Za-z0-9_-]+', args.run_id):
        raise ValueError('invalid run-id')
    if args.action == 'prepare':
        contract = job.prepare()
    elif args.action == 'preflight':
        contract = job.checked_contract()
    else:
        subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_frozen_prediction_d3a.py'], cwd=ROOT, check=True)
        contract = job.checked_contract()
        paths = [*job.CODE, (job.PACKET / 'contract.json').as_posix()]
        for name in paths:
            subprocess.run(['git', 'ls-files', '--error-unmatch', name], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', *paths], cwd=ROOT, check=True)
        print(job.run_once(ROOT, contract, args.run_id, job.git_head()), flush=True)
    print(f'D3-A contract verified: {job.d2.digest(contract)}', flush=True)
    if args.action != 'run':
        print('Metadata and byte integrity only; no outcome pairing or numerical score/label access.', flush=True)


if __name__ == '__main__':
    main()
