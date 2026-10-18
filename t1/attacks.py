"""T1 worlds for PREREG-v4 S2 (mis-tagging) and S3 (watch-aware agents). Fresh Action copies per call."""
from __future__ import annotations

import random
from dataclasses import replace

from gym.engine_v2 import CONS
from t1.world_v2 import CONS_OF, world

TYPES = ["low", "med", "high", "capped"]


def copy_actions(actions):
    return [replace(a, meta=dict(a.meta)) for a in actions]


def mistag_world(seed, rand_rate=0.0, adv_share=0.0, adv_q=0.0):
    """T1 world where some actions carry the wrong tag. Each type has its own write tool, so floor = true consequence.
    rand_rate: share of all actions tagged as a uniformly random other type of the same agent.
    adv_share/adv_q: share of C3/C4 actions with adversarial phrasing, and the chance it gets them tagged as C1."""
    actions, keys = world(seed)
    rng = random.Random(seed * 101 + 7)
    out = []
    for a in copy_actions(actions):
        true_type = a.task_type
        tag = true_type
        if rand_rate and rng.random() < rand_rate:
            tag = rng.choice([t for t in TYPES if t != true_type])
        elif adv_share and CONS_OF[true_type] in ("C3", "C4") and rng.random() < adv_share and rng.random() < adv_q:
            tag = "low"
        a.meta["true_cons"] = CONS_OF[true_type]
        a.meta["floor_cons"] = CONS_OF[true_type]
        a.task_type = tag
        a.meta["cons"] = CONS_OF[tag]
        a.capped = tag == "capped"
        out.append(a)
    return out, keys


def gamer_world(seed, share=0.25, evade_checks=True):
    """T1 world where each non-C4 key is a watch-aware 'gamer' with probability `share`."""
    actions, keys = world(seed)
    rng = random.Random(seed * 103 + 9)
    gamers = {k for k in keys if CONS_OF[k[1]] != "C4" and rng.random() < share}
    out = copy_actions(actions)
    for a in out:
        k = (a.agent, a.task_type)
        if k in gamers:
            eps = CONS[a.meta["cons"]]["eps"]
            a.meta.update(gamer=True, p_w=0.5 * eps, p_u=3 * eps, u=rng.random(), v=rng.random(),
                          evade_checks=evade_checks)
    return out, keys, gamers
