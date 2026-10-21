"""Earned Autonomy: reference trust engine. AI agents earn autonomy over their actions the way employees do.

Implements spec v0.7 (lifecycle: measure, decide, oversee, learn, retire, govern) (spec/README.md). Docstrings cite rule IDs (EA-x.y) from spec/requirements/. Start with `TrustEngine`; see README.md for the quickstart.
"""
from .engine import TrustEngine, reviewer_key
from .governance import Actor, GovernanceGuard
from .models import (CONSEQUENCE, EVIDENCE_SOURCES, RANK, COSMETIC_REASONS, L0, L1, L2, L3, LABELS, LEVEL_NAMES, REASON_CODES,
                     SERIOUS_REASONS, ChecksResult, Decision, OutcomeEvent, Policy, ProposedAction, TaskTypePolicy,
                     TrustState, format_timestamp, is_serious, lint_shared_write_tools, max_consequence,
                     normalise_timestamp, parse_timestamp, payload_hash)
from .record import MemoryBackend, SQLiteBackend, TrustRecord, VerifyResult
from .stats import (BoundStrategy, ConfidenceSequenceBound, WilsonBound, beta_quantile, dial_spot_rate, clean_floor, posterior_interval,
                    promotion_table, regularized_incomplete_beta, step_down_threshold, trust_score)
from .suites import SuiteCase, SuiteStore
from .tagging import RuleTagger, Tagger, TagResult

__version__ = "0.7.0"
__all__ = [
    "TrustEngine", "reviewer_key", "Actor", "GovernanceGuard", "CONSEQUENCE", "COSMETIC_REASONS", "L0", "L1", "L2",
    "L3", "LABELS", "LEVEL_NAMES", "REASON_CODES", "SERIOUS_REASONS", "ChecksResult", "Decision", "OutcomeEvent",
    "Policy", "ProposedAction", "TaskTypePolicy", "TrustState", "format_timestamp", "normalise_timestamp", "parse_timestamp", "is_serious", "payload_hash", "RANK", "lint_shared_write_tools", "max_consequence", "MemoryBackend",
    "SQLiteBackend", "TrustRecord", "VerifyResult", "BoundStrategy", "ConfidenceSequenceBound", "WilsonBound", "clean_floor", "EVIDENCE_SOURCES", "beta_quantile", "dial_spot_rate",
    "posterior_interval", "promotion_table", "regularized_incomplete_beta", "step_down_threshold", "trust_score", "SuiteCase", "SuiteStore",
    "RuleTagger", "Tagger", "TagResult",
]
