"""R1 / R3: a drafting agent relies on 3 consultant agents with per-skill reliability.

Arms:
  equal   - ask one consultant at random, trust the answer
  verify  - ask, then verify every answer (1 verification call each; verification is always right)
  trust   - host-computed per-(consultant, skill) Beta posterior; ask the best-ranked consultant; verify
            only when its lower bound < THRESH, plus a 10% audit. Verified/audited outcomes update the record.
Consultant 0 defects at question DEFECT_AT (its reliability drops to 0.2 on every skill).
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL = [{"s0": 0.95, "s1": 0.80}, {"s0": 0.80, "s1": 0.95}, {"s0": 0.60, "s1": 0.60}]
THRESH, AUDIT, N_Q, DEFECT_AT = 0.85, 0.10, 1000, 500


def beta_lower(a, b):
    m = a / (a + b)
    v = a * b / ((a + b) ** 2 * (a + b + 1))
    return m - 1.96 * v ** 0.5


def run(arm: str, seed: int):
    rng = random.Random(seed)
    post = {(c, s): [1.0, 1.0] for c in range(3) for s in ("s0", "s1")}
    correct = calls = 0
    defect_bad_outputs = 0
    leaked = 0
    caught_after = None
    for q in range(N_Q):
        skill = rng.choice(["s0", "s1"])

        def rel(c):
            return 0.2 if (c == 0 and q >= DEFECT_AT) else REL[c][skill]

        if arm == "trust":
            c = max(range(3), key=lambda c: beta_lower(*post[(c, skill)]))
        elif arm == "trust-ts":   # POST-HOC (2026-10-15): Thompson-sampling routing, explores
            c = max(range(3), key=lambda c: rng.betavariate(*post[(c, skill)]))
        else:
            c = rng.randrange(3)
        ok = rng.random() < rel(c)
        if c == 0 and q >= DEFECT_AT and not ok:
            defect_bad_outputs += 1
        if arm == "equal":
            correct += ok
            continue
        unverified_bad = False
        if arm == "verify":
            calls += 1
            correct += 1
            continue
        verify = beta_lower(*post[(c, skill)]) < THRESH or rng.random() < AUDIT
        if verify:
            calls += 1
            post[(c, skill)][0 if ok else 1] += 1
            correct += 1
        else:
            correct += ok
            unverified_bad = (c == 0 and q >= DEFECT_AT and not ok)
        leaked += unverified_bad
        if q >= DEFECT_AT and caught_after is None:
            # caught = the host no longer routes either skill to the defector
            if all(max(range(3), key=lambda c, s=s: beta_lower(*post[(c, s)])) != 0 for s in ("s0", "s1")):
                caught_after = defect_bad_outputs
    return dict(acc=correct / N_Q, calls=calls, caught_after=caught_after, leaked=leaked)


def main(n=200):
    res = {}
    for arm in ("equal", "verify", "trust", "trust-ts"):
        rows = [run(arm, s) for s in range(n)]
        res[arm] = dict(acc=st.fmean(r["acc"] for r in rows), calls=st.fmean(r["calls"] for r in rows))
        if arm.startswith("trust"):
            res[arm]["defector_bad_unverified"] = st.fmean(r["leaked"] for r in rows)
            ca = [r["caught_after"] for r in rows if r["caught_after"] is not None]
            res[arm]["r3_median_bad_outputs"] = st.median(ca) if ca else None
            res[arm]["r3_caught_share"] = len(ca) / n
    (ROOT / "report/raw/t1-peer.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
