"""Short E2 quote-unit audit, fixed date/column slices; never joins B scores."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qlib_integration.economic_data_readiness import (
    QuoteSliceReader,
    inspect_quotes,
    synthetic_feasibility,
)


def main():
    # Existing canonical provider identity, no new downloads and no Qlib D.features.
    provider = (ROOT / "../qlib_data/cn_data_community_20260609_derived").resolve()
    out = ROOT / "outputs/economic_translation_mvp/e2_data_canary_v1"
    out.mkdir(parents=True, exist_ok=False)
    reader = QuoteSliceReader(provider)
    try:
        result = inspect_quotes(reader)
        result.to_csv(out / "quote_unit_canary.csv", index=False, lineterminator="\n")
        synthetic_feasibility().to_csv(
            out / "synthetic_aum_feasibility.csv", index=False, lineterminator="\n"
        )
        (out / "access.json").write_text(
            json.dumps(reader.audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(result.to_string(index=False))
    except Exception as exc:
        (out / "failure.json").write_text(
            json.dumps(dict(error=repr(exc), access=reader.audit), indent=2) + "\n",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()
