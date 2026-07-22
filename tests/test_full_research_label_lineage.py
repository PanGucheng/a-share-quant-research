from research_validation.feature_matrix import canonical_hash
from scripts.run_full_research_labels_v1 import label_input_payload


def test_label_input_hash_changes_with_raw_or_key_provenance() -> None:
    base = label_input_payload(
        matrix_artifact_id="matrix:a",
        raw_artifact_id="raw:a",
        raw_sha256="b" * 64,
        key_partition_sha256="c" * 64,
        label_name="label_20d_t1",
        entry_lag=1,
        holding_days=20,
    )
    changed_raw = {**base, "raw_parquet_sha256": "d" * 64}
    changed_key = {**base, "key_partition_sha256": "e" * 64}

    assert canonical_hash(base) != canonical_hash(changed_raw)
    assert canonical_hash(base) != canonical_hash(changed_key)
