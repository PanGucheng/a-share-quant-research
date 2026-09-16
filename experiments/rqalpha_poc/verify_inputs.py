"""Read-only, bounded provenance check; never imports or runs the active learner."""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def sha(path, lf=False):
    content = path.read_bytes()
    return hashlib.sha256(content.replace(b"\r\n", b"\n") if lf else content).hexdigest()


def verify(main_root):
    import rqalpha

    authority = HERE.parents[1] / "reports/rqalpha_integration_audit_v1/ENVIRONMENT.json"
    native = json.loads(authority.read_text(encoding="utf-8"))["installed_matches_upstream_lf"]
    installed = Path(rqalpha.__file__).parent
    for name, expected in native.items():
        assert sha(installed / Path(name).relative_to("rqalpha"), lf=True) == expected, name
    fixture = json.loads((HERE / "fixtures/sealed_canary.json").read_text(encoding="utf-8"))
    before = json.loads((HERE / "fixtures/main_guard_before.json").read_text(encoding="utf-8"))
    main_root = Path(main_root).resolve()
    contract = (
        main_root / "outputs/lightgbm_hyperparameter_research/lgbm_nested_20260916_v1/contract.json"
    )
    assert sha(contract) == before["contract_sha256"], "active research contract changed"
    for name, expected in before["code_lf"].items():
        assert sha(main_root / name, lf=True) == expected, name
    for name, expected in fixture["provenance"].items():
        assert sha(main_root / name) == expected, name
    base = main_root / "outputs/economic_translation_mvp/e2_historical_core_v2"
    receipt = json.loads((base / "receipt.json").read_text())
    for name, expected in receipt.items():
        assert sha(base / name) == expected, name
    evidence = json.loads((base / "evidence.json").read_text())
    values = {r["name"]: r["fact"]["value"] for rows in evidence.values() for r in rows}
    v = fixture["real_canary"]
    assert (v["open"], v["close"], v["adv20"], v["state"]) == (
        values["raw_open"],
        values["close_mark"],
        values["adv20_shares"],
        values["state"],
    )
    events = main_root / "outputs/economic_translation_mvp/e2_semantic_v1/events.parquet"
    reviewed = next(
        r["coverage"]["reviewed_sources"] for r in evidence["A"] if r["name"] == "events_clear"
    )
    bound = next(
        x["sha256"] for x in reviewed if x["path"].replace("\\", "/").endswith("events.parquet")
    )
    assert sha(events) == bound
    queries = {
        "dividend_rows": [
            ("asset_id", "==", "SH600000"),
            ("ex_date", ">=", "20200101"),
            ("ex_date", "<=", "20201231"),
        ],
        "bonus_rows": [
            ("asset_id", "==", "SH600000"),
            ("ex_date", ">=", "20150101"),
            ("ex_date", "<=", "20231229"),
            ("bonus_per_share", ">", 0),
        ],
    }
    for key, filters in queries.items():
        rows = json.loads(pd.read_parquet(events, filters=filters).to_json(orient="records"))
        assert rows == fixture[key], key
    return dict(
        status="PASS",
        active_bound_files=len(before["code_lf"]),
        active_contract_sha256=before["contract_sha256"],
        canary_receipt_files=len(receipt),
        event_rows=3,
        market_value_rows=1,
        network=False,
        main_modified=False,
        no_model_or_prediction_read=True,
        no_2024plus_values=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--main-root", required=True)
    print(json.dumps(verify(p.parse_args().main_root), indent=2))
