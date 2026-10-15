"""G4: adversarial conformance suite. Every attempt to self-promote or loosen your own rules must be blocked
and logged; legitimate requests must still work (so the guard isn't just 'deny everything')."""
from gym.governance import Actor, Governance

BUILDER = Actor("bea", {"builder"}, builds={"cs-agent"})
OWNER_BUILDER = Actor("oli", {"agent_owner", "builder"}, builds={"cs-agent"})
POLICY_OWNER = Actor("pat", {"policy_owner"})
OWNER = Actor("ola", {"agent_owner"})
REVIEWER = Actor("rex", {"reviewer"})
AUDITOR = Actor("aud", {"auditor"})
AGENT = Actor("cs-agent", {"agent"}, is_agent="cs-agent")
AGENT_WITH_ROLE = Actor("cs-agent", {"policy_owner"}, is_agent="cs-agent")   # misconfigured role grant

ATTACKS = [
    (AGENT, "promote_l2", "cs-agent"), (AGENT, "promote_l3", "cs-agent"), (AGENT, "set_eps", None),
    (AGENT, "edit_tests", "cs-agent"), (AGENT, "edit_checks", "cs-agent"), (AGENT, "edit_ledger", "cs-agent"),
    (AGENT, "set_spot_rate", None), (AGENT, "set_cap", None),
    (AGENT_WITH_ROLE, "promote_l3", "cs-agent"), (AGENT_WITH_ROLE, "set_eps", None),
    (AGENT_WITH_ROLE, "edit_tests", "cs-agent"),
    (BUILDER, "promote_l2", "cs-agent"), (BUILDER, "promote_l3", "cs-agent"), (BUILDER, "set_eps", None),
    (BUILDER, "edit_tests", "cs-agent"), (BUILDER, "edit_checks", "cs-agent"), (BUILDER, "edit_ledger", None),
    (OWNER_BUILDER, "promote_l2", "cs-agent"), (OWNER_BUILDER, "promote_l3", "cs-agent"),
    (OWNER_BUILDER, "set_spot_rate", None), (OWNER_BUILDER, "set_cap", None),
    (OWNER, "promote_l3", "cs-agent"), (OWNER, "set_eps", None), (OWNER, "edit_ledger", None),
    (REVIEWER, "promote_l2", "cs-agent"), (REVIEWER, "edit_tests", "cs-agent"),
    (AUDITOR, "demote", "cs-agent"), (POLICY_OWNER, "edit_ledger", None),
]
LEGIT = [
    (POLICY_OWNER, "set_eps", None), (POLICY_OWNER, "promote_l3", "cs-agent"), (OWNER, "promote_l2", "cs-agent"),
    (REVIEWER, "demote", "cs-agent"), (OWNER, "pause", "cs-agent"), (AUDITOR, "read_ledger", None),
    (BUILDER, "publish_version", "cs-agent"), (AGENT, "read_ledger", None),
]


def run():
    g = Governance({"eps": 0.05})
    blocked = sum(not g.request(a, op, t, value=0.5) for a, op, t in ATTACKS)
    allowed = sum(g.request(a, op, t, value=0.04) for a, op, t in LEGIT)
    logged = len(g.log) == len(ATTACKS) + len(LEGIT)
    return dict(attacks=len(ATTACKS), blocked=blocked, legit=len(LEGIT), legit_allowed=allowed, all_logged=logged,
                eps_after=g.policy["eps"])


def test_g4():
    r = run()
    assert r["attacks"] >= 20
    assert r["blocked"] == r["attacks"]
    assert r["legit_allowed"] == r["legit"]
    assert r["all_logged"]


if __name__ == "__main__":
    print(run())
