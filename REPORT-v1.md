# Trust Gym v1: results

Run 2026-10-15. Pre-registered in `PREREG-v1.md` (tag `prereg-v1`) before any v1 code. Same data and seeds as v0
(T1 worlds, committed T2/T3 streams). New LLM spend: **$0**. v0 is untouched and reproducible (`gym/engine.py`);
v1 lives in `gym/engine_v1.py`, `analyze_v1.py`, `report/verdicts-v1.json`.

## Verdicts

| # | Revision | Result | Verdict |
|---|---|---|---|
| V1 | Carry trust across versions that pass hidden tests | learning-loop key-runs promoted 0/400 (v0) → 142/400; 0.00 escapes/100 auto; promotions deserved 102/102; 18/30 version changes passed | **PASS** |
| V2 | One-level demotion | T1 escapes/100 0.595 → 0.603 (inside +5%), automation 27.1% → 27.7%; T2 unchanged | **PASS** (non-inferior) |
| V3 | Pooled trust (agent prior, k = 20) | T1 passes; T2 automation 46% vs 56% (good agent), 9% vs 17% (sloppy) | **MIXED** |
| V4 | ε by risk label (10/5/3%/never) | reviews removed T1 23 → 29%, T2 good 34 → 36%; escapes ≤ 0.62/100 auto | **FAIL** (< 40%) |
| V5 | Thompson peer routing | R1: 95.4% accuracy vs 67.1%, 433 vs 1,000 calls · R3: rerouted 100%, median 37.5 bad outputs | **R1 PASS · R3 FAIL** |
| V5b | Thompson + forgetting 0.98 | R1: 96.5%, 501 calls (just over the bar) · R3: median 21; unverified bad outputs 18.4 → 10.0 | **R1 FAIL · R3 FAIL** |
| V6 | All revisions combined | automation T1 27 → 34%, T2 good 42 → 47%, sloppy 17 → 22%; escapes/100 T1 +4.7% (ok), T2 good 0.33 → 0.52, sloppy 0.77 → 0.87 | **MIXED** |

v1 combined on T1 under the v0 definitions: H1 93.4% PASS · H2 29.7% removed FAIL · H3 ratio 0.503 FAIL by a hair ·
H4 median 14 PASS · G1 −30% review time, 98% detected FAIL · G2 100% PASS · G3 0 PASS (by design an L3 incident now
leaves the type at L2, ~1.26 per world).

## Recommended v1 policy

- **Trust unit:** agent × task type, no pooling.
- **Start:** L1, checks always on; a failed check is held at every level.
- **Promote:** ≥ 30 own observations since the last level change AND 95% Wilson upper bound of serious-error rate
  ≤ ε. Default ε = 0.05. The policy owner overrides per task type **from measured error and consequence, not a risk
  label**. Capped types (money, deletes, irreversible) never promote.
- **Spot-checks:** 25% at L2, 5% at L3; canaries 2% of reviews.
- **Demote one level** when the 95% Wilson lower bound of the last 50 observations > ε, or on an incident.
- **Agent updates:** evidence carries over in full if the new version's hidden-test pass rate ≥ 0.8 and ≥ the
  previous version's; otherwise discount to ½ and drop to L1 if the bound no longer holds.
- **Peer routing:** Thompson sampling on Beta posteriors per (agent, skill), forgetting 0.98; verify when the lower
  bound < 0.85, plus a 10% audit.
- **Governance:** unchanged from v0 (roles, separation of duties, versioned policy-as-code, append-only ledger).

## Surprises

1. **Risk labels ran opposite to error rates.** In T2, "low-risk" task types had the *highest* error rate (3.8% vs
   1.3% med, 1.9% high), so a looser ε on low-risk work promoted the most error-prone work. That drove V6's T2 escape
   rise. Set ε from measured error and consequence, never from a label.
2. **Pooling hurts.** An agent prior penalises an agent's good task types for its bad ones.
3. **Carry-over is the biggest win.** It turns "a fast learner never gets promoted" into 36% of key-runs promoted,
   all deserved.
4. **Workload savings top out around 30–40%.** The binding constraint is the evidence floor (~73 clean reviews per
   task type before the first promotion). Next lever to test: a smaller floor for low-consequence types, or
   transferring evidence from a validated test suite.
5. **Forgetting halves a defector's damage** but doesn't get detection under 10 bad outputs; that needs a stronger
   signal than 10% audits.
6. **Limitation:** frozen T2 streams give carry-over nothing to act on, so there the recommended policy equals V2.
