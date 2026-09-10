"""Independent naive reference. Does not import the production transform module."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def naive_day(frame, recipe):
    ranks = {}
    for name in recipe['parents']:
        if name in recipe['u']:
            continue
        values = frame[name].tolist()
        ordered = sorted(x for x in values if math.isfinite(x))
        n = len(ordered)
        mapping = {}
        if n >= recipe['diagnostic_policy']['rank_min'] and len(set(ordered)) > 1:
            start = 0
            while start < n:
                end = start + 1
                while end < n and ordered[end] == ordered[start]:
                    end += 1
                # Zero-based interval [start,end): average one-based ranks.
                mapping[ordered[start]] = ((start + 1 + end) / 2 - .5) / n - .5
                start = end
        ranks[name] = [mapping.get(x, float('nan')) for x in values]
    outputs = {name: [x if math.isfinite(x) else float('nan') for x in frame[name]]
               for name in recipe['parents']}
    q = recipe['diagnostic_policy']['child_fraction']
    for node in recipe['composites']:
        generated = []
        for i in range(len(frame)):
            available_families = []
            for family in node['families']:
                leaves = [ranks[m['factor']][i] * m['sign'] for m in family['members']]
                finite = [v for v in leaves if math.isfinite(v)]
                if len(finite) >= math.ceil(q * len(leaves)):
                    available_families.append(sum(finite) / len(finite))
            generated.append(sum(available_families) / len(available_families)
                if len(available_families) >= math.ceil(recipe['diagnostic_policy']['family_fraction'] * len(node['families'])) else float('nan'))
        outputs[node['id']] = generated
    return {arm: pd.concat([frame[['datetime', 'instrument']].reset_index(drop=True),
             pd.DataFrame({k: np.asarray(outputs[k], dtype=np.float64) for k in names})], axis=1)
            for arm, names in recipe['arms'].items()}
