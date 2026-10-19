"""T1 simulated worlds: agents whose true serious-error rate per task type we set."""
from __future__ import annotations

import math
import random

from gym.engine import Action

TYPES = [("low", 0.40, (0.005, 0.02), False),
         ("med", 0.30, (0.02, 0.05), False),
         ("high", 0.20, (0.05, 0.12), False),
         ("capped", 0.10, (0.02, 0.06), True)]
PATTERNS = [("steady", .40), ("learning", .15), ("early", .15), ("drift", .10), ("bad_update", .12),
            ("defector", .08)]
REGRESSIONS = {"bad_update", "defector"}


def pick(rng, items):
    r, acc = rng.random(), 0.0
    for name, w in items:
        acc += w
        if r < acc:
            return name
    return items[-1][0]


def rate_fn(pattern: str, base: float, n_exp: int, rng: random.Random):
    """Returns (f(i) -> true rate at the key's i-th action, regression index or None)."""
    if pattern == "steady":
        return (lambda i: base), None
    if pattern == "learning":
        return (lambda i: base + 2 * base * math.exp(-i / 100)), None
    if pattern == "early":
        return (lambda i: 4 * base if i < 50 else base), None
    if pattern == "drift":
        return (lambda i: min(0.5, base * (1 + 3 * i / max(1, n_exp)))), None
    i0 = int(rng.uniform(0.3, 0.7) * n_exp)
    if pattern == "bad_update":
        return (lambda i: base if i < i0 else max(0.25, 5 * base)), i0
    if pattern == "defector":
        return (lambda i: 0.5 * base if i < i0 else 0.4), i0
    raise ValueError(pattern)


def make_world(seed: int, n_actions=4000, n_agents=2, check_recall=0.70, check_fpr=0.05,
               force_pattern: str | None = None):
    rng = random.Random(seed)
    keys = {}
    for a in range(n_agents):
        for name, w, (lo, hi), capped in TYPES:
            base = rng.uniform(lo, hi)
            pat = force_pattern or pick(rng, PATTERNS)
            n_exp = int(n_actions * w / n_agents)
            f, i0 = rate_fn(pat, base, n_exp, rng)
            keys[(f"ag{a}", name)] = dict(f=f, i0=i0, pattern=pat, base=base, capped=capped, i=0,
                                          version="v1", rates=[])
    weights = [(k, w / n_agents) for (k, (name, w, _, _)) in
               [((f"ag{a}", t[0]), t) for a in range(n_agents) for t in TYPES]]
    actions = []
    for _ in range(n_actions):
        k = pick(rng, weights)
        ks = keys[k]
        p = ks["f"](ks["i"])
        ks["rates"].append(p)
        # regressions are silent in T1 (the version string never changes), so the policy has to find them
        # from evidence alone; the version-change discount is exercised in T2's learning loop
        ver = "v1"
        ks["i"] += 1
        err = rng.random() < p
        flag = rng.random() < (check_recall if err else check_fpr)
        actions.append(Action(agent=k[0], task_type=k[1], true_err=err, check_flag=flag, version=ver,
                              capped=ks["capped"], meta={"p": p}))
    return actions, keys
