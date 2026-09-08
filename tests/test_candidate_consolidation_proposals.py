import numpy as np
import pandas as pd

from factor_research.candidate_consolidation_proposals import propose_groups


def test_representative_no_labels_retains_horizon_and_defers_masks():
    names = list("abcd")
    membership = pd.DataFrame({"factor": names, "cluster_id": "same"})
    semantic = pd.DataFrame(
        {
            "factor": names,
            "mechanism": "ratio",
            "horizon": ["5", "5", "20", "5"],
            "representative_eligible": [True, True, True, False],
            "formula_token_count": [3, 2, 1, 0],
        }
    )
    quality = pd.DataFrame(
        {
            "factor": names,
            "worst_era_coverage": [0.9, 0.95, 1.0, 1.0],
            "full_coverage": 1.0,
            "infinite_fraction": 0.0,
        }
    )
    distance = pd.DataFrame(np.zeros((4, 4)), index=names, columns=names)
    first = propose_groups(membership, semantic, quality, distance)
    assert first.set_index("factor").loc["a", "proposed_representative"] == "b"
    assert (
        first.set_index("factor").loc["c", "proposal_role"] == "retain_horizon_or_semantic_variant"
    )
    assert first.set_index("factor").loc["d", "proposal_role"] == "deferred"
    quality["IC"] = [100, -100, 0, 999]
    pd.testing.assert_frame_equal(
        first, propose_groups(membership.iloc[::-1], semantic, quality, distance)
    )
