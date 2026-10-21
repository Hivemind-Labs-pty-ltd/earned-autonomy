"""Training and hidden test suites (EA-4.3, EA-4.4, EA-4.10).

- Corrections become tests and are split at random: about 2/3 training, 1/3 hidden.
- Hidden suites can also be seeded when a version is created (authored scenarios), so carry-over can work for a
  fast learner whose corrections dry up (on the commercial-harness run, carry-over never fired without seeding).
- Hidden tests are unreadable by the agent and by whoever improves it (the builder). Reads go through governance.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from .governance import Actor, GovernanceGuard


@dataclass
class SuiteCase:
    test_id: str
    task_type: str
    scenario: dict                                  # scenario + expected result, opaque to the engine
    visibility: str                             # training | hidden
    source: str                                 # correction | authored
    created_at: str = ""


@dataclass
class SuiteStore:
    guard: GovernanceGuard
    _tests: dict[str, list[SuiteCase]] = field(default_factory=dict)
    _random: secrets.SystemRandom = field(default_factory=secrets.SystemRandom)

    def add_correction_test(self, test_id: str, task_type: str, scenario: dict, created_at: str = "") -> None:
        """A test drafted from a correction and approved by a person. Assigned hidden with probability 1/3."""
        visibility = "hidden" if self._random.random() < 1 / 3 else "training"
        self._tests.setdefault(task_type, []).append(SuiteCase(test_id, task_type, scenario, visibility, "correction", created_at))

    def seed_hidden(self, task_type: str, cases: list[tuple[str, dict]], created_at: str = "") -> None:
        """Authored hidden tests added at version creation (EA-4.10)."""
        for test_id, scenario in cases:
            self._tests.setdefault(task_type, []).append(
                SuiteCase(test_id, task_type, scenario, "hidden", "authored", created_at))

    def hidden_count(self, task_type: str) -> int:
        return sum(1 for test in self._tests.get(task_type, []) if test.visibility == "hidden")

    def training(self, task_type: str) -> list[SuiteCase]:
        """Training tests: anyone may read these, including the agent and its builder."""
        return [test for test in self._tests.get(task_type, []) if test.visibility == "training"]

    def hidden(self, actor: Actor, task_type: str, agent_id: str | None = None) -> list[SuiteCase]:
        """Hidden tests: policy owner and auditor only; never the agent or its builder (EA-4.4)."""
        if not self.guard.request(actor, "read_hidden_tests", agent_id, {"task_type": task_type}):
            raise PermissionError("hidden tests are not readable by this actor")
        return [test for test in self._tests.get(task_type, []) if test.visibility == "hidden"]

    def run_hidden(self, task_type: str, runner) -> tuple[float, int]:
        """Run the hidden suite with a test-runner callable `runner(spec) -> bool`. The runner is infrastructure
        (not the agent's improver) and returns only the pass rate and count."""
        cases = [test for test in self._tests.get(task_type, []) if test.visibility == "hidden"]
        if not cases:
            return 0.0, 0
        passed = sum(1 for test in cases if runner(test.scenario))
        return passed / len(cases), len(cases)
