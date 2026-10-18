"""Data model (SPEC §5). Plain dataclasses, stdlib only."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---- levels (SPEC §2) -------------------------------------------------------------------------------------
L0, L1, L2, L3 = 0, 1, 2, 3
LEVEL_NAMES = {L0: "Observe", L1: "Supervised", L2: "Trusted", L3: "Senior"}

# ---- outcome labels and reason codes (SPEC §5) ---------------------------------------------------------------
LABELS = ("approved", "cosmetic_edit", "material_edit", "rejected", "incomplete")
SOURCES = ("pre_review", "spot_check", "incident", "canary")
SERIOUS_REASONS = ("wrong_fact", "wrong_amount", "wrong_record", "wrong_recipient", "unauthorised_action",
                   "promise_beyond_policy", "missing_info_not_asked", "followed_injected_instruction",
                   "policy_breach", "other_serious")
COSMETIC_REASONS = ("tone", "wording", "formatting", "other_cosmetic")
REASON_CODES = SERIOUS_REASONS + COSMETIC_REASONS

# ---- consequence levels (SPEC §7, decided 2026-10-16, [tested v2]) --------------------------------------------
CONSEQUENCE = {
    "C1": {"eps": 0.10, "success_min": 0.85},
    "C2": {"eps": 0.05, "success_min": 0.90},
    "C3": {"eps": 0.02, "success_min": 0.95},
    "C4": {"eps": 0.0, "success_min": None},     # never promotes
}
RANK = {"C1": 1, "C2": 2, "C3": 3, "C4": 4}


def max_consequence(*levels: str | None) -> str | None:
    vals = [c for c in levels if c]
    return max(vals, key=RANK.__getitem__) if vals else None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


def payload_hash(payload: Any) -> str:
    """The record keeps a hash of the payload, never its content (SPEC §10 privacy)."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()


def is_serious(label: str, reason_code: str | None) -> bool:
    """SPEC §2: material_edit or rejected with a non-cosmetic reason code. Incidents are serious by definition."""
    return label in ("material_edit", "rejected") and reason_code not in COSMETIC_REASONS


TrustKey = tuple[str, str, str]      # (org_id, agent_id, task_type)


@dataclass
class ProposedAction:
    """SPEC §5. `payload` stays with the caller; only its hash enters the trust record."""
    action_id: str
    org_id: str
    agent_id: str
    agent_version: str
    kind: str                                   # message.send | tool.call | delegate | ...
    payload: Any = None
    task_type: str | None = None                # set by the tagger (or by the caller)
    tag_confidence: float | None = None
    counterparty_id: str | None = None
    parent_action_id: str | None = None         # delegation provenance (SPEC §11)
    created_at: datetime = field(default_factory=utcnow)
    # write tools this action will call (SPEC §4 tool floor). Names only enter the record; args never do.
    write_tools: list[str] = field(default_factory=list)
    write_tool_args: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> TrustKey:
        return (self.org_id, self.agent_id, self.task_type or "")


@dataclass
class ChecksResult:
    """Pre-send checks are run by the caller; the engine only reads the result (SPEC §6 step 3)."""
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


@dataclass
class Decision:
    """SPEC §5. `mode` is hold | act. A spot-check is drawn only after execution and is never shown to the agent,
    so the agent-visible mode never says act_spot (SPEC §6 step 6, see engine.mark_executed)."""
    decision_id: str
    action_id: str
    trust_key: TrustKey
    mode: str                                   # hold | act
    why: str
    level: int
    evidence_n: float
    evidence_err: float
    upper_bound: float
    eps: float
    consequence: str | None
    checks: dict
    policy_version: int
    agent_version: str
    payload_hash: str
    created_at: str
    tool_floor: str | None = None               # highest floor of the action's write tools (SPEC §4)

    @property
    def allowed(self) -> bool:
        return self.mode == "act"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["trust_key"] = list(self.trust_key)
        return d


@dataclass
class OutcomeEvent:
    event_id: str
    action_id: str
    decision_id: str | None
    trust_key: TrustKey
    agent_version: str
    source: str
    label: str
    reason_code: str | None
    serious: bool
    actor_id: str
    diff_ref: str | None
    created_at: str


@dataclass
class TrustState:
    """SPEC §5. Derived; rebuilt exactly by replaying the trust record."""
    trust_key: TrustKey
    level: int = L1
    n: float = 0.0
    err: float = 0.0
    fail: float = 0.0                           # incomplete outcomes (task success alert only)
    since_change: float = 0.0
    recent: list = field(default_factory=list)  # last rolling_n serious flags, cleared on level change
    agent_version: str | None = None
    paused: bool = False
    state_version: int = 0
    last_activity_at: str | None = None
    updated_at: str | None = None

    def snapshot(self) -> dict:
        d = asdict(self)
        d["trust_key"] = list(self.trust_key)
        return d


@dataclass
class TaskTypePolicy:
    consequence: str = "C2"
    eps: float | None = None                    # optional override; may only tighten the consequence bar
    capped: bool = False
    tools: list[str] = field(default_factory=list)


@dataclass
class Policy:
    """Policy-as-code (SPEC §5, §10). Immutable in use: every change produces a new version via governance."""
    policy_version: int = 1
    eps: float = 0.05                           # fallback when a type has no consequence level
    n_min: int = 30
    confidence: float = 0.95
    rolling_n: int = 50
    rolling_min: int = 10
    reentry_gap_days: float = 60.0
    spot_rate: dict = field(default_factory=lambda: {2: 0.25, 3: 0.05})
    canary_rate: float = 0.02
    version_discount: float = 0.5
    carry_hidden_min: float = 0.8
    min_hidden_tests: int = 10
    tag_confidence_min: float = 0.8
    alert_fraction: float = 0.8                 # alert when the rolling upper bound passes 80% of ε (SPEC §9)
    require_checks: bool = True
    # reviewer trust (SPEC §9, [tested v3])
    reviewer_eps: float = 0.10
    reviewer_n_min: int = 30
    reviewer_canary_rate: float = 0.05
    second_check_rate: dict = field(default_factory=lambda: {1: 0.25, 2: 0.05})
    task_types: dict[str, TaskTypePolicy] = field(default_factory=dict)
    # SPEC §4 tool floor: explicit per-tool overrides (tool -> C1..C4). Otherwise a tool's floor is derived.
    tool_floors: dict[str, str] = field(default_factory=dict)
    # Tools known to write (for the shared-tool lint). Floors apply to whatever an action declares in write_tools.
    write_tools: list[str] = field(default_factory=list)
    # SPEC §7 strict promotion: consequence levels ("C3") and/or task type names that use the anytime-valid bound.
    strict_promotion: list[str] = field(default_factory=list)

    def tool_floor(self, tool: str) -> str:
        """SPEC §4: explicit override, else the highest consequence of any task type listing the tool,
        else C4 (a write tool no task type lists)."""
        if tool in self.tool_floors:
            return self.tool_floors[tool]
        levels = [tp.consequence for tp in self.task_types.values() if tool in tp.tools]
        return max_consequence(*levels) or "C4"

    def is_strict(self, task_type: str) -> bool:
        if task_type in self.strict_promotion:
            return True
        tp = self.type_policy(task_type)
        return tp is not None and tp.consequence in self.strict_promotion

    def type_policy(self, task_type: str) -> TaskTypePolicy | None:
        return self.task_types.get(task_type)

    def eps_for(self, task_type: str) -> float:
        tp = self.type_policy(task_type)
        if tp is None:
            return self.eps
        if tp.consequence == "C4" or tp.capped:
            return 0.0
        base = CONSEQUENCE[tp.consequence]["eps"]
        return min(base, tp.eps) if tp.eps is not None else base

    def is_capped(self, task_type: str) -> bool:
        tp = self.type_policy(task_type)
        return tp is not None and (tp.capped or tp.consequence == "C4")

    def success_min(self, task_type: str) -> float | None:
        tp = self.type_policy(task_type)
        return CONSEQUENCE[tp.consequence]["success_min"] if tp else None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["spot_rate"] = {str(k): v for k, v in self.spot_rate.items()}
        d["second_check_rate"] = {str(k): v for k, v in self.second_check_rate.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Policy":
        d = copy.deepcopy(d)
        d["spot_rate"] = {int(k): v for k, v in d.get("spot_rate", {}).items()}
        d["second_check_rate"] = {int(k): v for k, v in d.get("second_check_rate", {}).items()}
        d["task_types"] = {k: TaskTypePolicy(**v) for k, v in d.get("task_types", {}).items()}
        return cls(**d)

    def evolve(self, **changes) -> "Policy":
        """A new policy version with the given fields changed."""
        d = self.to_dict()
        d.update(changes)
        d["policy_version"] = self.policy_version + 1
        if "task_types" in changes:
            d["task_types"] = {k: (asdict(v) if isinstance(v, TaskTypePolicy) else v)
                               for k, v in changes["task_types"].items()}
        return Policy.from_dict(d)


def lint_shared_write_tools(policy: Policy, write_tools: list[str] | None = None) -> list[str]:
    """SPEC §4 design rule: warn when a write tool is listed by task types of different consequence levels.
    Its derived floor then pushes the lower-consequence types up, so they can never earn autonomy.
    Checks `write_tools` (or policy.write_tools); with neither, checks every listed tool. Explicit floors are noted."""
    tools = write_tools if write_tools is not None else (policy.write_tools or
                                                         sorted({t for tp in policy.task_types.values()
                                                                 for t in tp.tools}))
    out = []
    for tool in tools:
        users = {tt: tp.consequence for tt, tp in policy.task_types.items() if tool in tp.tools}
        if len(set(users.values())) > 1:
            lo = min(users.values(), key=RANK.__getitem__)
            pushed = sorted(tt for tt, c in users.items() if RANK[c] < RANK[policy.tool_floor(tool)])
            note = f" (explicit floor {policy.tool_floors[tool]})" if tool in policy.tool_floors else ""
            out.append(f"write tool '{tool}' is shared across {sorted(set(users.values()))}{note}: "
                       f"floor {policy.tool_floor(tool)} holds {pushed or [lo]} on every use. Split the tool or give "
                       f"it an argument-dependent floor.")
    return out
