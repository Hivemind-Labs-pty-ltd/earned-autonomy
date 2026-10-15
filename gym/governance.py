"""Governance as policy-as-code: roles, separation of duties, versioned changes, audit log.

Every change to trust state or policy goes through `Governance.request(actor, op, target, **args)`.
Requests are allowed or blocked by explicit rules and every request (allowed or not) is logged.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ROLES = {"agent_owner", "policy_owner", "reviewer", "auditor", "builder", "agent"}

# op -> roles allowed to perform it
ALLOWED = {
    "set_eps": {"policy_owner"},
    "set_cap": {"policy_owner"},
    "set_spot_rate": {"policy_owner"},
    "promote_l3": {"policy_owner"},
    "promote_l2": {"policy_owner", "agent_owner"},   # manual override; normal path is evidence
    "demote": {"policy_owner", "agent_owner", "reviewer"},   # anyone accountable can pull it back
    "pause": {"policy_owner", "agent_owner", "reviewer"},
    "edit_tests": {"policy_owner"},                  # tests/checks change only via the policy owner
    "edit_checks": {"policy_owner"},
    "edit_ledger": set(),                            # append-only: nobody edits
    "read_ledger": {"policy_owner", "agent_owner", "reviewer", "auditor", "agent"},  # agents may read their own record
    "publish_version": {"builder", "agent_owner"},
}


@dataclass
class Actor:
    name: str
    roles: set
    builds: set = field(default_factory=set)       # agents this actor builds or changes
    is_agent: str | None = None                    # set when the actor IS an agent


class Governance:
    def __init__(self, policy: dict):
        self.policy = dict(policy)
        self.version = 1
        self.log: list[dict] = []

    def request(self, actor: Actor, op: str, target_agent: str | None = None, **args) -> bool:
        ok, why = self._check(actor, op, target_agent)
        self.log.append(dict(actor=actor.name, roles=sorted(actor.roles), op=op, target=target_agent,
                             args=args, allowed=ok, why=why, policy_version=self.version))
        if ok and op.startswith("set_"):
            self.policy[op[4:]] = args.get("value")
            self.version += 1
        return ok

    def _check(self, actor: Actor, op: str, target: str | None) -> tuple[bool, str]:
        if op not in ALLOWED:
            return False, "unknown_op"
        if actor.is_agent is not None:
            # an agent may never change its own trust, policy, tests, checks or ledger
            if op != "read_ledger":
                return False, "agent_cannot_govern"
        if not (actor.roles & ALLOWED[op]):
            return False, "role_not_allowed"
        # separation of duties: a builder can't approve or loosen anything for an agent they build
        if target and target in actor.builds and op in {"promote_l3", "promote_l2", "set_eps", "set_cap",
                                                        "set_spot_rate", "edit_tests", "edit_checks"}:
            return False, "separation_of_duties"
        if op in {"set_eps", "set_cap", "set_spot_rate"} and actor.builds:
            # thresholds are org-wide: anyone who builds any agent can't move them
            return False, "separation_of_duties"
        return True, "ok"
