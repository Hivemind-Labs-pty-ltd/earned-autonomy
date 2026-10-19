"""Governance guard (SPEC §10). Roles, separation of duties, every request logged (allowed or not).

Roles: ai_owner, policy_owner, reviewer, auditor, builder, agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ROLES = frozenset({"ai_owner", "policy_owner", "reviewer", "auditor", "builder", "agent"})

# operation -> roles allowed to perform it
ALLOWED: dict[str, set] = {
    # policy (SPEC §10: the policy owner sets ε, caps, tools per type and sample rates)
    "set_policy": {"policy_owner"},
    "set_error_bar": {"policy_owner"},
    "set_cap": {"policy_owner"},
    "set_spot_rate": {"policy_owner"},
    "set_tools": {"policy_owner"},
    # catalogue (SPEC §4: the AI owner maintains task types and assigns consequence levels)
    "add_task_type": {"ai_owner"},
    "set_consequence": {"ai_owner"},
    # levels
    "promote": {"policy_owner"},                    # manual promotion; the normal path is evidence
    "demote": {"policy_owner", "ai_owner", "reviewer"},
    "pause": {"policy_owner", "ai_owner", "reviewer"},
    "resume": {"policy_owner", "ai_owner"},
    # tests and checks (SPEC §8: the agent and any improver never edit these)
    "edit_tests": {"policy_owner"},
    "edit_checks": {"policy_owner"},
    "read_hidden_tests": {"policy_owner", "auditor"},
    # versions
    "publish_version": {"builder", "ai_owner"},
    # the record
    "read_record": {"policy_owner", "ai_owner", "reviewer", "auditor", "agent"},
    "edit_record": set(),                           # append-only for everyone
}

# Ops that loosen or bypass the rules for a specific agent: its builder may never do these (separation of duties).
SEPARATION_OF_DUTIES_OPERATIONS = frozenset({"promote", "set_error_bar", "set_cap", "set_spot_rate", "set_tools", "edit_tests", "edit_checks",
                     "read_hidden_tests", "set_consequence", "set_policy", "resume"})


@dataclass
class Actor:
    actor_id: str
    roles: set
    builds: set = field(default_factory=set)        # agent ids this actor builds or changes
    agent_id: str | None = None                     # set when the actor IS an agent

    def __post_init__(self):
        unknown = set(self.roles) - ROLES
        if unknown:
            raise ValueError(f"unknown roles {sorted(unknown)}")


@dataclass
class GovernanceResult:
    allowed: bool
    reason: str


class GovernanceGuard:
    def __init__(self, log):
        """`log(type, body)` appends to the trust record."""
        self._log = log

    def check(self, actor: Actor, operation: str, target_agent: str | None = None) -> GovernanceResult:
        if operation not in ALLOWED:
            return GovernanceResult(False, "unknown_op")
        if actor.agent_id is not None or "agent" in actor.roles:
            # an agent may read its own record and nothing else (SPEC §10)
            if operation == "read_record" and (target_agent is None or target_agent == actor.agent_id):
                return GovernanceResult(True, "ok")
            return GovernanceResult(False, "agent_cannot_govern")
        if not (set(actor.roles) & ALLOWED[operation]):
            return GovernanceResult(False, "role_not_allowed")
        if operation in SEPARATION_OF_DUTIES_OPERATIONS:
            if target_agent and target_agent in actor.builds:
                return GovernanceResult(False, "separation_of_duties")
            if target_agent is None and actor.builds:
                # organisation-wide rule changes: anyone who builds an agent can't move them
                return GovernanceResult(False, "separation_of_duties")
        return GovernanceResult(True, "ok")

    def request(self, actor: Actor, operation: str, target_agent: str | None = None, arguments: dict | None = None) -> bool:
        result = self.check(actor, operation, target_agent)
        self._log("governance", {"actor_id": actor.actor_id, "roles": sorted(actor.roles), "operation": operation,
                                 "target_agent": target_agent, "arguments": arguments or {}, "allowed": result.allowed,
                                 "reason": result.reason})
        return result.allowed
