"""Conformance suite for the Earned Autonomy spec (spec/README.md).

Every test declares the rules it checks with `@pytest.mark.covers("EA-x.y", ...)`. `scripts/build_requirements.py`
reads those markers to build `conformance/compliance-matrix.md`. A build is compliant when every MUST rule is met.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
for path in (HERE, ENGINE / "tests", ENGINE / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pytest_configure(config):
    config.addinivalue_line("markers", "covers(*rule_ids): the spec rules (EA-x.y) this test checks")
