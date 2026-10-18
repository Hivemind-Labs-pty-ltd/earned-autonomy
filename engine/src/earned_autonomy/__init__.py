"""Earned Autonomy: reference trust engine. AI agents earn autonomy over their actions the way employees do.

Implements SPEC v0.2. Start with `TrustEngine`; see README.md for the quickstart.
"""
from .engine import TrustEngine, reviewer_key
from .governance import Actor, GovernanceGuard
from .models import (CONSEQUENCE, COSMETIC_REASONS, L0, L1, L2, L3, LABELS, LEVEL_NAMES, REASON_CODES,
                     SERIOUS_REASONS, ChecksResult, Decision, OutcomeEvent, Policy, ProposedAction, TaskTypePolicy,
                     TrustState, is_serious, payload_hash)
from .record import MemoryBackend, SQLiteBackend, TrustRecord, VerifyResult
from .stats import BoundStrategy, WilsonBound
from .suites import SuiteCase, SuiteStore
from .tagging import RuleTagger, Tagger, TagResult

__version__ = "0.2.0"
__all__ = [
    "TrustEngine", "reviewer_key", "Actor", "GovernanceGuard", "CONSEQUENCE", "COSMETIC_REASONS", "L0", "L1", "L2",
    "L3", "LABELS", "LEVEL_NAMES", "REASON_CODES", "SERIOUS_REASONS", "ChecksResult", "Decision", "OutcomeEvent",
    "Policy", "ProposedAction", "TaskTypePolicy", "TrustState", "is_serious", "payload_hash", "MemoryBackend",
    "SQLiteBackend", "TrustRecord", "VerifyResult", "BoundStrategy", "WilsonBound", "SuiteCase", "SuiteStore",
    "RuleTagger", "Tagger", "TagResult",
]
