"""EXPLORATORY (post-hoc, not pre-registered) follow-ups to PREREG-v4. Writes report/explore-v4.json."""
import json
import statistics as st
from collections import Counter

from analyze_v2 import rev
from analyze_v3 import COMBINED
from analyze_v4 import ARMS, SCENARIOS
from gym.engine_v2 import CONS
from gym.engine_v4 import RANK, ConfigV4, run_v4
from t1.attacks import mistag_world
from t1.world_v2 import world

out = {}
# 1. S2a: split downgrade escapes into autonomous vs missed in review
s2 = {}
for name, kw in SCENARIOS:
    row = {}
    for d in (False, True):
        au = rv = 0
        for s in range(310_000, 310_200):
            acts, _ = mistag_world(s, **kw)
            e = run_v4(acts, ConfigV4(**COMBINED, tag_defence=d), seed=s * 17 + 3, reviewer=rev(s))
            for k, g, tc, cons, auto in e.events:
                if RANK[tc] > RANK[cons]:
                    au += auto
                    rv += not auto
        row["on" if d else "off"] = dict(autonomous=au / 200, missed_in_review=rv / 200)
    row["autonomous_cut"] = 1 - row["on"]["autonomous"] / row["off"]["autonomous"] if row["off"]["autonomous"] else 1.0
    s2[name] = row
out["s2a_split"] = s2
# 2. S1 T1: undeserved promotions by key pattern
s1 = {}
for arm in ("W95", "CS-mix"):
    c, tot = Counter(), Counter()
    for s in range(300_000, 300_200):
        acts, keys = world(s)
        e = run_v4(acts, ConfigV4(**COMBINED, bound=arm), seed=s * 17 + 3, reviewer=rev(s))
        for p in e.promotions:
            if p["to"] < 2:
                continue
            r = keys[p["key"]]["rates"][p["type_i"]: p["type_i"] + 200]
            if len(r) < 50:
                continue
            cons = next(a.meta["cons"] for a in acts if (a.agent, a.task_type) == p["key"])
            pat = keys[p["key"]]["pattern"]
            tot[pat] += 1
            c[pat] += st.fmean(r) > CONS[cons]["eps"]
    s1[arm] = {pat: dict(undeserved=c[pat], promotions=tot[pat]) for pat in tot}
out["s1_t1_by_pattern"] = s1
json.dump(out, open("report/explore-v4.json", "w"), indent=1)
print(json.dumps(out, indent=1))
