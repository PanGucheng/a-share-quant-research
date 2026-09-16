import json
import os
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def no_runtime_network():
    from .harness import offline

    with offline():
        yield


def pytest_sessionfinish(session, exitstatus):
    dest = os.environ.get("RQALPHA_POC_RESULT")
    if dest:
        from .test_canaries import RESULTS

        with Path(dest).open("x", encoding="utf-8") as f:
            json.dump(
                dict(exitstatus=int(exitstatus), tests=session.testscollected, cases=RESULTS),
                f,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
