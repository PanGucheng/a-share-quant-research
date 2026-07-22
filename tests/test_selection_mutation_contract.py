import pandas as pd

from research_validation.mutation_contract import canonical_frame_hash, frame_content_hash, mutate_test_rows


def test_outer_test_value_and_order_mutations_do_not_change_development_hash() -> None:
    dates = pd.bdate_range("2024-01-01", periods=6)
    frame = pd.DataFrame({"datetime": dates, "factor": ["a"] * 6, "rank_ic": [float(value) for value in range(6)]})
    development = dates[:3]
    test = dates[3:]
    baseline = canonical_frame_hash(frame.loc[frame["datetime"].isin(development)], sort_keys=["datetime", "factor"])

    for mutation in ("test_ic", "extreme_missing", "row_order"):
        changed = mutate_test_rows(frame, test_dates=test, mutation=mutation, value_columns=["rank_ic"])
        projected = changed.loc[changed["datetime"].isin(development)]
        assert canonical_frame_hash(projected, sort_keys=["datetime", "factor"]) == baseline
        if mutation == "row_order":
            assert canonical_frame_hash(changed, sort_keys=["datetime", "factor"]) == canonical_frame_hash(
                frame, sort_keys=["datetime", "factor"]
            )
            assert frame_content_hash(changed) != frame_content_hash(frame)
        else:
            assert canonical_frame_hash(changed, sort_keys=["datetime", "factor"]) != canonical_frame_hash(
                frame, sort_keys=["datetime", "factor"]
            )
