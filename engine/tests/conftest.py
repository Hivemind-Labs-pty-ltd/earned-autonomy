import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))


def pytest_configure(config):
    config.addinivalue_line("markers", "covers(*rule_ids): the spec rules (EA-x.y) this test checks")
