import pandas as pd

from scripts.run_split_specific_allowlist_v1 import allowlist_payload_hash


def test_allowlist_hash_is_order_invariant_but_direction_sensitive() -> None:
    frame = pd.DataFrame({"factor": ["b", "a"], "frozen_direction": [1, -1], "cluster_id": ["c2", "c1"]})
    reordered = frame.iloc[::-1].reset_index(drop=True)
    changed = frame.copy()
    changed.loc[0, "frozen_direction"] = -1

    assert allowlist_payload_hash(frame) == allowlist_payload_hash(reordered)
    assert allowlist_payload_hash(frame) != allowlist_payload_hash(changed)
