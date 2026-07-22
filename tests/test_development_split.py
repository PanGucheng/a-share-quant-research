import pandas as pd

from research_validation.development_split import DevelopmentSplitConfig, build_development_robustness_splits
from research_validation.purged_split import label_intervals


def test_development_windows_never_use_outer_test() -> None:
    calendar = pd.bdate_range("2020-01-01", periods=1000)
    outer = pd.DataFrame([{"split_id": "split_001", "test_start": calendar[850], "test_end": calendar[949]}])
    assignments = pd.DataFrame(
        [{"split_id": "split_001", "datetime": date, "fold": "train" if index < 760 else "validation"} for index, date in enumerate(calendar[:820])]
        + [{"split_id": "split_001", "datetime": date, "fold": "test"} for date in calendar[850:950]]
    )
    outputs = build_development_robustness_splits(
        outer,
        assignments,
        label_intervals(calendar, 20, 1),
        DevelopmentSplitConfig(),
    )

    assert len(outputs["inner_split_manifest"]) == 3
    assert outputs["leakage_audit"]["status"].eq("pass").all()
    assert not set(outputs["development_date_assignments"]["datetime"]) & set(calendar[850:950])
