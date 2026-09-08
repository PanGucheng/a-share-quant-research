import json
from pathlib import Path

import pandas as pd
import yaml

from factor_research.long_history_candidates import apply_rules
from factor_research.long_history_screening import sha256_file
from research_validation.canonical_dataset import canonical_hash


def test_frozen_v0_exports_replay_without_runtime_or_recent_data():
    root = Path(__file__).resolve().parents[1]
    report = root / "reports/long_history_multi_evaluator_screening_v1"
    evidence_receipt = json.loads((report / "EVIDENCE_V0_RECEIPT.json").read_text(encoding="utf-8"))
    candidate_receipt = json.loads((report / "CANDIDATE_V0_RECEIPT.json").read_text(encoding="utf-8"))
    rule_dir = root / "artifacts/long_history_multi_evaluator_screening_v1" / candidate_receipt["rule_id"]
    freeze = json.loads((rule_dir / "candidate_rule_freeze.json").read_text(encoding="utf-8"))
    assert canonical_hash({k: v for k, v in freeze.items() if k != "rule_id"}) == freeze["rule_id"]
    assert freeze["evidence_content_id"] == evidence_receipt["content_id"]
    assert sha256_file(root / "factor_research/long_history_candidates.py") == freeze["candidate_code_sha256"]
    assert sha256_file(root / "factor_research/long_history_boards.py") == evidence_receipt["board_code_sha256"]
    for name, digest in freeze["file_hashes"].items():
        assert sha256_file(rule_dir / name) == digest
    for name, receipt in (("factor_evidence_board.csv", evidence_receipt), ("candidate_board.csv", candidate_receipt)):
        assert sha256_file(report / name) == receipt["file_hashes"][name]
    evidence = pd.read_csv(report / "factor_evidence_board.csv", float_precision="round_trip")
    expected = pd.read_csv(report / "candidate_board.csv", float_precision="round_trip")
    rules = yaml.safe_load((rule_dir / "candidate_rules.yaml").read_text(encoding="utf-8"))
    actual, _ = apply_rules(evidence, rules, freeze["rule_id"])
    columns = ["factor", "analysis_direction", "agreement", "pass_count", "backend_available_count",
               *[f"{backend}_{field}" for backend in ("alphalens", "jqfactor", "qlib")
                 for field in ("candidate_status", "reasons")]]
    assert len(actual) == 765
    pd.testing.assert_frame_equal(actual[columns], expected[columns], check_exact=True)
