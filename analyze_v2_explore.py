"""EXPLORATORY (post-hoc, not pre-registered): candidate fixes for the v2 failures. Writes report/explore-v2.json."""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

from analyze_v2 import rev, t2_actions
from gym.engine_v2 import CONS, ConfigV2, EngineV2, PoolReviewer, run_v2
from gym.engine import wilson_upper
from t1.world_v2 import fading_world, version_world, world

ROOT = Path(__file__).resolve().parent
out = {}


# (a) gap-triggered staleness instead of continuous fading
class GapEngine(EngineV2):
    GAP = 60.0

    def _fade(self, k, s, day, cons):
        if day is None:
            return
        if s.last_day is not None and day - s.last_day > self.GAP and s.level >= 2:
            self._set(k, s, s.level - 1, "stale_gap")
        s.last_day = day


rows = []
for s in range(100):
    acts, _ = fading_world(30_000 + s)
    main = [a for a in acts if a.agent != "agX"]
    r = {}
    for name, cls in (("none", EngineV2), ("gap60", GapEngine)):
        e = cls(ConfigV2(), seed=s * 17 + 3, reviewer=rev(30_000 + s), n_total=len(acts))
        for a in acts:
            e.step(a)
        e2 = cls(ConfigV2(), seed=s * 17 + 3, reviewer=rev(30_000 + s), n_total=len(main))
        for a in main:
            e2.step(a)
        r[name] = (e.by_key_escapes.get(("agX", "rare_drift"), 0), e2.summary()["automation"])
    rows.append(r)
out["F1_gap60"] = {n: dict(drift_escapes=st.fmean(x[n][0] for x in rows), main_automation=st.fmean(x[n][1] for x in rows))
                   for n in ("none", "gap60")}


# (b) reviewer trust counting clean second checks as evidence, canaries 5%
class RevEngine(EngineV2):
    def _review(self, a, cons, executed):
        progress = self.t / self.n_total
        r = self.rng.choice(self.pool)
        r.reviews += 1
        self.m["minutes"] += 1
        if r.st.level >= 2 and r.catch_p(progress) < 0.80:
            r.bad_reviews_at_r2 += 1
        caught = a.true_err and self.rng.random() < r.catch_p(progress)
        if self.rng.random() < self.cfg.canary_rate:
            self.m["canary"] += 1
            self.m["minutes"] += 1
            self._rev_observe(r, not (self.rng.random() < r.catch_p(progress)))
        if not caught and self.rng.random() < self.cfg.second_check[min(2, r.st.level)]:
            others = [x for x in self.pool if x is not r]
            r2 = self.rng.choice([x for x in others if x.st.level >= 2] or others)
            self.m["second"] += 1
            self.m["minutes"] += 1
            found = a.true_err and self.rng.random() < r2.catch_p(progress)
            if found:
                caught = True
            self._rev_observe(r, found)          # clean second check counts as clean evidence
        a.meta["_reviewer"] = r
        saw_fail = caught or (a.meta.get("nsf", False) and self.rng.random() < 0.95)
        return caught, saw_fail


def pool(seed):
    rng = random.Random(seed * 101 + 9)
    return [PoolReviewer("A", lambda p: 0.95, rng), PoolReviewer("B", lambda p: 0.85, rng),
            PoolReviewer("C", lambda p: 0.60, rng), PoolReviewer("D", lambda p: 0.95 - 0.45 * p, rng)]


rr = []
for s in range(100):
    acts, _ = world(40_000 + s)
    res = {}
    p = pool(40_000 + s)
    e = run_v2(acts, ConfigV2(reviewer_trust=False), seed=s * 17 + 3, pool=p)
    res["no-trust"] = (e.summary()["escapes"], e.summary()["minutes"], 0, 0, [1] * 4)
    for cr in (0.02, 0.05):
        p = pool(40_000 + s)
        e = RevEngine(ConfigV2(reviewer_trust=True, canary_rate=cr), seed=s * 17 + 3, pool=p, n_total=len(acts))
        for a in acts:
            e.step(a)
        sm = e.summary()
        res[f"clean-evidence canary {cr}"] = (sm["escapes"], sm["minutes"], p[2].bad_reviews_at_r2,
                                             p[3].bad_reviews_at_r2, [x.st.level for x in p])
    rr.append(res)
out["R1_clean_evidence"] = {}
for k in rr[0]:
    out["R1_clean_evidence"][k] = dict(
        escapes=st.fmean(x[k][0] for x in rr), minutes=st.fmean(x[k][1] for x in rr),
        median_bad_at_r2=st.median([x[k][2] for x in rr] + [x[k][3] for x in rr]),
        end_share_r2=[st.fmean(x[k][4][i] >= 2 for x in rr) for i in range(4)])


# (c) carry-over without the ">= previous" clause, and with a 0.05 tolerance
class CarryEngine(EngineV2):
    TOL = None   # None = drop the clause

    def st(self, a):
        k = (a.agent, a.task_type)
        if k in self.state and self.state[k].version != a.version and self.cfg.version_mode == "carry":
            s = self.state[k]
            hp = self.cfg.version_pass.get((a.agent, a.version, a.task_type))
            ok = hp is not None and hp >= self.cfg.carry_min and (
                self.TOL is None or s.last_hidden is None or hp >= s.last_hidden - self.TOL)
            if ok:
                s.version = a.version
                s.last_hidden = hp
        return super().st(a)


class CarryTol(CarryEngine):
    TOL = 0.05


kr = []
for s in range(100):
    acts, vpass, _ = version_world(50_000 + s)
    res = {}
    for name, cls, mode in (("carry-prereg", EngineV2, "carry"), ("carry-no-prev", CarryEngine, "carry"),
                            ("carry-tol05", CarryTol, "carry"), ("keep", EngineV2, "keep"),
                            ("discount", EngineV2, "discount")):
        e = cls(ConfigV2(version_mode=mode, version_pass=vpass), seed=s * 17 + 3, reviewer=rev(50_000 + s),
                n_total=len(acts))
        for a in acts:
            e.step(a)
        sm = e.summary()
        res[name] = (sm["automation"], sm["escapes"])
    kr.append(res)
out["K1_carry_variants"] = {k: dict(automation=st.fmean(x[k][0] for x in kr), escapes=st.fmean(x[k][1] for x in kr))
                            for k in kr[0]}

# (d) C1 breakdown: auto-escape cost by consequence, consequence bars without the success criterion vs flat
br = {}
for name in ("good-full", "sloppy-full"):
    acts = t2_actions(name)
    res = {}
    for arm, cfg in (("flat", ConfigV2(bars="flat")), ("cons-nosucc", ConfigV2(success_criterion=False))):
        rows = []
        for s in range(20):
            e = run_v2(acts, cfg, seed=s * 17 + 3, reviewer=rev(s))
            b = e.summary()["by_cons"]
            rows.append({c: dict(auto=b[c]["auto"], esc_auto=b[c]["escapes_auto"], esc=b[c]["escapes"],
                                 cost=b[c]["cost"]) for c in CONS})
        res[arm] = {c: {f: st.fmean(r[c][f] for r in rows) for f in ("auto", "esc_auto", "esc", "cost")} for c in CONS}
    br[name] = res
out["C1_breakdown_T2"] = br

(ROOT / "report/explore-v2.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))


# (e) the K1 fix on real T2 learning-loop data: carry if hidden >= 0.8 (no ">= previous")
def t2_loop_check():
    import analyze_v1 as v1
    from analyze import load_stream as ls
    from gym.engine import Reviewer as R
    from gym.engine_v1 import PolicyConfigV1, run_stream_v1
    acts = ls(v1.RAW / "t2-stream-loop.jsonl")
    seq = {}
    for a in acts:
        seq.setdefault((a.agent, a.task_type), []).append(a.true_err)
    variants = {}
    for label, rule in (("prereg (>=0.8 and >= previous)", lambda prev, cur: cur >= .8 and cur >= prev),
                        ("no-previous (>=0.8)", lambda prev, cur: cur >= .8)):
        vp = {}
        for arch in ("ap", "cs", "do", "it", "of", "ws"):
            rows = [json.loads(l) for l in open(v1.RAW / f"t2-loop-{arch}.jsonl")]
            for p, c in zip(rows, rows[1:]):
                vp[(f"{arch}-loop", c["version"])] = rule(p["hidden_pass"], c["hidden_pass"])
        promoted = auto = esc = good = total = 0
        for s in range(20):
            e = run_stream_v1(acts, PolicyConfigV1(kind="D", hard_demotion=False, version_pass=vp), seed=s,
                              reviewer=R(random.Random(s + 101)))
            promoted += len({p["key"] for p in e.promotions if p["to"] >= 2})
            m = e.summary()
            auto += m["auto"]
            esc += m["escapes_auto"]
            for p in e.promotions:
                if p["to"] >= 2:
                    nxt = seq[p["key"]][p["type_i"]: p["type_i"] + 200]
                    if len(nxt) >= 30:
                        total += 1
                        good += st.fmean(nxt) <= 0.05
        variants[label] = dict(promoted_keyruns=promoted, keyruns=20 * len(seq), esc_per100_auto=100 * esc / max(1, auto),
                               h1=f"{good}/{total}", versions_passed=f"{sum(vp.values())}/{len(vp)}")
    return variants


out["K1_fix_on_T2_loop"] = t2_loop_check()
(ROOT / "report/explore-v2.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out["K1_fix_on_T2_loop"], indent=1))
