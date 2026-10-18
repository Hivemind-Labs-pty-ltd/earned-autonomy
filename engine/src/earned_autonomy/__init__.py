"""Earned Autonomy: reference trust engine. AI agents earn autonomy over their actions the way employees do.

Implements SPEC v0.4. Start with `TrustEngine`; see README.md for the quickstart.
"""
from .engine import TrustEngine, reviewer_key
from .governance import Actor, GovernanceGuard
from .models import (CONSEQUENCE, RANK, COSMETIC_REASONS, L0, L1, L2, L3, LABELS, LEVEL_NAMES, REASON_CODES,
                     SERIOUS_REASONS, ChecksResult, Decision, OutcomeEvent, Policy, ProposedAction, TaskTypePolicy,
                     TrustState, is_serious, lint_shared_write_tools, max_consequence, payload_hash)
from .record import MemoryBackend, SQLiteBackend, TrustRecord, VerifyResult
from .stats import BoundStrategy, ConfidenceSequenceBound, WilsonBound, clean_floor
from .suites import SuiteCase, SuiteStore
from .tagging import RuleTagger, Tagger, TagResult

__version__ = "0.4.0"
__all__ = [
    "TrustEngine", "reviewer_key", "Actor", "GovernanceGuard", "CONSEQUENCE", "COSMETIC_REASONS", "L0", "L1", "L2",
    "L3", "LABELS", "LEVEL_NAMES", "REASON_CODES", "SERIOUS_REASONS", "ChecksResult", "Decision", "OutcomeEvent",
    "Policy", "ProposedAction", "TaskTypePolicy", "TrustState", "is_serious", "payload_hash", "RANK", "lint_shared_write_tools", "max_consequence", "MemoryBackend",
    "SQLiteBackend", "TrustRecord", "VerifyResult", "BoundStrategy", "ConfidenceSequenceBound", "WilsonBound", "clean_floor", "SuiteCase", "SuiteStore",
    "RuleTagger", "Tagger", "TagResult",
]
