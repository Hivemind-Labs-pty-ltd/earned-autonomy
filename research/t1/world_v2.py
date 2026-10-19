"""T1 worlds for v2: consequence + success annotations, calendar time, fading patterns, frequent versions."""
from __future__ import annotations

import random

from gym.engine import Action
from t1.world import TYPES, make_world

CONS_OF = {"low": "C1", "med": "C2", "high": "C3", "capped": "C4"}


def annotate(actions, seed, days=365.0):
    """Adds meta: cons, nsf (non-serious failure), day. One non-serious failure rate per key, U(0.02, 0.15)."""
    rng = random.Random(seed * 7 + 11)
    q = {}
    n = len(actions)
    for i, a in enumerate(actions):
        k = (a.agent, a.task_type)
        if k not in q:
            q[k] = rng.uniform(0.02, 0.15)
        a.meta["cons"] = CONS_OF[a.task_type]
        a.meta["nsf"] = (not a.true_err) and rng.random() < q[k]
        a.meta["day"] = days * i / n
    return actions


def world(seed, **kw):
    actions, keys = make_world(seed, **kw)
    return annotate(actions, seed), keys


def _flags(rng, err, recall=0.70, fpr=0.05):
    return rng.random() < (recall if err else fpr)


def fading_world(seed):
    """Main T1 world plus one extra agent with a rare-then-drift key and a steady-rare key (both C2)."""
    actions, keys = world(seed)
    rng = random.Random(seed * 13 + 5)
    extra = []
    # rare-then-drift: 300 actions days 0-60 at 1%, nothing days 60-240, 200 actions days 240-365 at 25%
    for i in range(300):
        d = 60 * i / 300
        e = rng.random() < 0.01
        extra.append(Action("agX", "rare_drift", e, _flags(rng, e),
                            meta={"cons": "C2", "nsf": False, "day": d, "pattern": "rare-then-drift"}))
    for i in range(200):
        d = 240 + 125 * i / 200
        e = rng.random() < 0.25
        extra.append(Action("agX", "rare_drift", e, _flags(rng, e),
                            meta={"cons": "C2", "nsf": False, "day": d, "pattern": "rare-then-drift"}))
    # steady-rare: 150 actions over the year at 1%
    for i in range(150):
        d = 365 * (i + 0.5) / 150
        e = rng.random() < 0.01
        extra.append(Action("agX", "steady_rare", e, _flags(rng, e),
                            meta={"cons": "C2", "nsf": False, "day": d, "pattern": "steady-rare"}))
    merged = sorted(actions + extra, key=lambda a: a.meta["day"])
    return merged, keys


def version_world(seed, n_actions=4000, n_agents=2, mean_gap=50, noise=0.04):
    """Steady base rates; each agent publishes a new version every ~mean_gap of its actions.
    80% of versions multiply its true rates by U(0.7, 1.0), 20% by U(2, 5) (cap 0.5).
    Hidden pass per (agent, version, type) = clip(1 - 3*rate + N(0, noise), 0, 1)."""
    rng = random.Random(seed * 17 + 3)
    base = {}
    for a in range(n_agents):
        for name, w, (lo, hi), capped in TYPES:
            base[(f"ag{a}", name)] = rng.uniform(lo, hi)
    mult = {f"ag{a}": 1.0 for a in range(n_agents)}
    ver = {f"ag{a}": 1 for a in range(n_agents)}
    left = {f"ag{a}": _geom(rng, mean_gap) for a in range(n_agents)}
    vpass, vrows = {}, []

    def record(ag):
        for name, *_ in TYPES:
            r = min(0.5, base[(ag, name)] * mult[ag])
            hp = min(1.0, max(0.0, 1 - 3 * r + rng.gauss(0, noise)))
            vpass[(ag, f"v{ver[ag]}", name)] = hp
            vrows.append((hp, r))

    for ag in mult:
        record(ag)
    weights = [((f"ag{a}", t[0]), t[1] / n_agents) for a in range(n_agents) for t in TYPES]
    actions = []
    for i in range(n_actions):
        r_, acc = rng.random(), 0.0
        for k, w in weights:
            acc += w
            if r_ < acc:
                break
        ag, name = k
        left[ag] -= 1
        if left[ag] <= 0:
            ver[ag] += 1
            mult[ag] *= rng.uniform(0.7, 1.0) if rng.random() < 0.8 else rng.uniform(2, 5)
            mult[ag] = min(mult[ag], 0.5 / min(base[(ag, t[0])] for t in TYPES))
            left[ag] = _geom(rng, mean_gap)
            record(ag)
        p = min(0.5, base[k] * mult[ag])
        e = rng.random() < p
        actions.append(Action(ag, name, e, _flags(rng, e), version=f"v{ver[ag]}", capped=(name == "capped"),
                              meta={"p": p}))
    return annotate(actions, seed), vpass, vrows


def _geom(rng, mean):
    n = 1
    while rng.random() > 1 / mean:
        n += 1
    return n
