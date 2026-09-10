"""Review completed D1 diagnostics only. Never loads canonical feature values."""
from __future__ import annotations

from collections import Counter
import contextlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from scripts.run_literature_representation_d1 import (
    PACKET, ROOT, load_packet, read_json, scan, scheduled_dates, sha, write_json,
)


def main():
    run_id = 'd1_structure_20260910_v2'
    base = ROOT / 'outputs/literature_factor_representation_d1' / run_id / 'full'
    target = ROOT / 'reports/literature_factor_representation_d1/full_review_v2'
    if target.exists():
        raise ValueError('review already exists; preserve it')
    with contextlib.redirect_stdout(io.StringIO()):
        summary = scan(ROOT, run_id, 'full', verify_only=True)
    recipe, inventory = load_packet()
    approved = {r['factor'] for r in inventory}
    dates = scheduled_dates(ROOT, 'full')
    family_totals = Counter()
    raw_zero = Counter()
    completed = 0
    nodes = {n['id']: n for n in recipe['composites']}
    for month in dates.to_period('M').unique():
        folder = base / str(month)
        days = dates[dates.to_period('M') == month].strftime('%Y-%m-%d').tolist()
        receipt = read_json(folder / 'receipt.json')
        assert receipt['exact_alias_pairs'] == 5
        assert [r['datetime'] for r in receipt['output_hashes']] == days
        assert all(set(r['hashes']) == {'R','C','H'} for r in receipt['output_hashes'])
        requests = Counter()
        for line in (folder / 'access.jsonl').read_text(encoding='utf-8').splitlines():
            event = json.loads(line)
            assert event['kind'] == 'canonical_feature_slice'
            assert set(event['columns']) <= approved
            assert days[0] <= event['start'] <= event['end'] <= days[-1]
            identity = (event['path'], event['start'], event['end'], tuple(event['columns']))
            if event['stage'] == 'request':
                requests[identity] += 1
            else:
                assert event['stage'] == 'complete' and requests[identity] > 0
                requests[identity] -= 1
                completed += 1
        assert not any(requests.values())
        leaves = pd.read_parquet(folder / 'leaves.parquet')
        assert set(leaves.datetime) == set(days) and not leaves.duplicated(['datetime','factor']).any()
        assert len(leaves) == len(days)*len(recipe['parents']) and set(leaves.factor) == set(recipe['parents'])
        for row in leaves.loc[leaves.finite_n.eq(0)].itertuples():
            raw_zero[(month.year,row.factor)] += 1
        out = pd.read_parquet(folder / 'outputs.parquet')
        assert set(out.datetime) == set(days) and not out.duplicated(['datetime','output']).any()
        assert len(out) == len(days)*len(nodes) and set(out.output) == set(nodes)
        for row in out.itertuples():
            hist = {int(k):v for k,v in json.loads(row.family_count_histogram).items()}
            assert sum(hist.values()) == row.universe_n
            assert hist.get(row.frozen_families,0) == row.valid_rows
            assert row.frozen_families == len(nodes[row.output]['families'])
        families = pd.read_parquet(folder / 'families.parquet')
        assert not families.duplicated(['datetime','output','family']).any()
        assert len(families) == len(days)*sum(len(n['families']) for n in nodes.values())
        for row in families.itertuples():
            hist = {int(k):v for k,v in json.loads(row.node_count_histogram).items()}
            assert sum(hist.values()) == row.universe_n
            assert sum(v for k,v in hist.items() if k >= row.needed_nodes) == row.valid_rows
            if row.frozen_nodes > 1:
                key = (month.year,row.output,row.family,row.frozen_nodes)
                for metric,value in [('rows',row.universe_n),('valid',row.valid_rows),
                    ('partial',sum(v for k,v in hist.items() if row.needed_nodes <= k < row.frozen_nodes))]:
                    family_totals[key+(metric,)] += value
    rows = []
    for year,output,family,count in sorted({k[:4] for k in family_totals}):
        values = {m:family_totals[(year,output,family,count,m)] for m in ['rows','valid','partial']}
        rows.append(dict(year=year,output=output,semantic_id=nodes[output]['semantic_id'],family=family,
                         frozen_nodes=count,**values,partial_share_valid=values['partial']/values['valid']))
    target.mkdir(parents=True)
    for name in summary['aggregate_hashes']:
        with (target / name).open('xb') as stream:
            stream.write((base / name).read_bytes())
    pd.DataFrame(rows).to_csv(target/'year_family_composition.csv',index=False,lineterminator='\n')
    pd.DataFrame([dict(year=y,factor=f,all_missing_dates=n) for (y,f),n in sorted(raw_zero.items())]).to_csv(
        target/'all_missing_leaf_dates.csv',index=False,lineterminator='\n')
    write_json(target/'run_summary.json',summary)
    review = dict(status='FULL_SCAN_VERIFIED_HUMAN_REVIEW_REQUIRED',d2_authorized=False,policy_finalized=False,
        run_id=run_id,recipe_hash=recipe['recipe_hash'],source_summary_sha256=sha(base/'summary.json'),
        source_packet=PACKET.as_posix(),review_code_sha256_lf=sha(Path(__file__),lf=True),
        verified_dates=len(dates),verified_months=168,feature_slice_requests_completed=completed,
        checks=['source/code/packet/chunk/aggregate hashes','calendar and leaf/output identity counts',
                'logged requests within approved development dates and feature columns',
                'all registered aliases checked in every month','family/node histogram denominator checks'],
        verification_scope='diagnostic/receipt verification; independent numeric oracle ran in user full scan; no fresh canonical reload')
    write_json(target/'verification.json',review)
    write_json(target/'file_hashes_lf.json',{p.name:sha(p,lf=True) for p in sorted(target.iterdir())})
    print(json.dumps(review,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
