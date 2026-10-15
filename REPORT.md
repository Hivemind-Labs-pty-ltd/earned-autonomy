# Trust Gym v0: results

Run 2026-10-15. Pre-registered in `PREREG.md` (tag `prereg`) before any code or data; every deviation is dated in
`DECISIONS.md`. All synthetic: no customer data. New spend: **$8.55** (cap $25).

**Question:** can AI agents earn autonomy the way employees do (start supervised, learn from corrections, get promoted
one task type at a time on evidence), under clear oversight and governance? And does the standard advice hold up?

## Data

| Tier | What | n |
|---|---|---|
| T1 Simulated | 2 agents × 4 task types × 4,000 actions; hidden true error rates with patterns (steady, learning, early errors, drift, bad update, defector); simulated reviewers with complacency | 200 worlds + 6 sweeps × 100 + 4 forced-pattern × 100 |
| T2 Generated | real `deepseek-v4-flash` agents with tools, 6 archetypes (customer service, workshop bookings, IT desk, accounts payable, outbound follow-up, data/ops), procedurally seeded truth and traps | 6,000 tasks × good/sloppy agent; 1,800 scoped; 3,600 learning-loop; 300 × 2 reviewer agents |
| T3 Public anchor | τ²-bench retail conversations from 2026-09-11 (flash + Haiku, prompt-only and gated) | 240 conversations |

## Verdicts

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| H1 | Promotions are right (true error ≤ ε after promotion in ≥ 80%) | T1 89% · T2 96% (good) / 92% (sloppy) | **PASS** |
| H2 | ≥ 40% of reviews removed at ≤ 1 escape per 100 auto actions | Safety half passes everywhere (0.19–0.62/100). Reviews removed: T1 23% · T2 34% / 14% · T3 0% | **FAIL** |
| H3 | ≤ half the escapes of checks-only at the same automation | T1 0.55 (≈0.51–0.60) · T2 0.34 / 0.31 | **MIXED** (passes on real agents, just misses in simulation) |
| H4 | Regression demoted within 20 actions | median 11; 137/137 demoted | **PASS** |
| H5 | Learning loop reaches L2 in ≤ half the reviews | no promotions: the per-version evidence discount resets trust every cycle | **INCONCLUSIVE** |
| H6 | Hidden-test pass rate tracks true error (ρ ≤ −0.6) | ρ = −0.81 (36 versions, p = 2e-9) | **PASS** |
| H7 | ≥ 50% of training gain carries to hidden tests | 1.17; true error fell in 6/6 archetypes | **PASS** |
| L1 | Least scope: ≥ 30% fewer wrong tool calls, success non-inferior | −73% wrong/unneeded calls; success −0.6 pts; serious errors 2.0% → 0.67% | **PASS** |
| L2 | Supervised start: ≥ 30% fewer escapes at ≤ 15% more reviews | T1 −14% at +6% · T2 −39% at +21% / −38% at +14% | **MIXED** |
| L3 | Per-type trust: ≥ 10 pts more automation, no more escapes | T1 +20 pts but slightly more escapes · T2 good agent: per-agent automated *more* | **FAIL** |
| L4 | Hard demotion (→ L1): ≥ 20% fewer escapes | −1% | **FAIL** |
| G1 | Review time −40% and regressions detected ≤ 50 actions | detection 100%; review time −23% | **FAIL** (workload half) |
| G2 | Every autonomous action explainable from the ledger | 100% (T1, T2) | **PASS** |
| G3 | No autonomous action after an incident | 0 | **PASS** (holds by construction) |
| G4 | Self-promotion / rule-loosening blocked and logged | 28/28 blocked; 8/8 legitimate requests allowed | **PASS** |
| G5 | Canaries keep reviewer catch ≥ 85%; without, < 85% | 94.1% vs 92.6%; escapes −15% | **FAIL** (assumed reviewer model only) |
| M1 | Reviewer agent removes ≥ 50% of human reviews, escapes ≤ A + 0.5/100 | good agent: −71% reviews, 0.36 vs 0.12 ✓ · sloppy: −63%, 2.56 vs 0.86 ✗ | **MIXED** |
| M2 | Different-model reviewer catches more | 82.9% vs 87.4% recall; 52% vs 28% false alarms | **FAIL** (opposite) |
| R1 | Per-skill peer trust: +5 pts accuracy over equal trust, ≤ 50% of verify-all's calls | 96.7% vs 67.1%, but 71% of calls | **FAIL** |
| R2 | Error rates differ ≥ 2× by counterparty type | good agent 4.5× (hostile) · sloppy 1.3× | **MIXED** (hostile has more traps by construction) |
| R3 | Defecting peer rerouted within 10 bad outputs | greedy routing never explores: rerouted in 2% of runs | **FAIL** |
| E-rank | Policies rank the same across tiers (τ ≥ 0.6) | T1–T2 τ = 0.60 · T3 degenerate (nothing promotes) | **MIXED** |

**Tally: 8 PASS · 8 FAIL · 5 MIXED · 1 INCONCLUSIVE.**

## What we learned

1. **Earned trust is a safety mechanism first.** On real agents it lets through 66–69% fewer serious errors than
   checks alone at the same automation (H3). 92–96% of promotions are deserved (H1), and regressions are caught in a
   median 11 actions (H4). On τ²-bench, where agents fail about 1 in 5 conversations, it correctly grants **no**
   autonomy; checks alone let through 13× more errors than full review.
2. **It frees less work than hoped at a strict bar.** At ε = 5% an agent needs ~73 clean reviews per task type before
   its first promotion, so savings were 14–34% (H2 fails). The bar is the dial: ε = 10% removes 41% of reviews in
   simulation. Set ε per task type by business risk.
3. **Least scope is the strongest method result.** Giving each task only the tools it needs cut wrong tool calls by
   73% and serious errors by two thirds, at no cost to success (L1).
4. **Agents learn from corrections, and tests are a valid trust signal.** Error rates fell to ~0% in 5 of 6
   archetypes within 2–3 cycles. Hidden-test scores track true error (ρ = −0.81), with no sign of test-gaming (H6,
   H7). Caveat: the sloppy agent was missing rules by design.
5. **But the version discount fights the learning loop.** Halving evidence on every update meant a fast-learning
   agent never got promoted (H5). Exploratory (no discount): loop agents earned promotion on 52% of task types vs 31%
   frozen, at the same 73-review floor. **Fix:** carry evidence across a version change when the new version passes
   the hidden tests (the spec's own rule 7 clause, now required).
6. **Standard advice that didn't hold:**
   - **Hard demotion to the bottom adds nothing** over stepping down one level (L4). Drop it.
   - **Per-type trust isn't a free win** (L3). It automates more for uneven agents, less for uniformly good ones.
     Use per-type evidence with an agent-level prior (pooling).
   - **A different-model reviewer is not better** (M2): lower recall and nearly double the false alarms. Drop the
     "same-model reviewers count for less" rule; measure each reviewer instead.
   - **Reviewer agents only help with good agents** (M1). They suit triage for a 2%-error agent, not a 14% one.
   - **Peer trust must explore** (R1, R3). Greedy "use the most trusted" keeps a defector; exploratory Thompson
     routing kept 95% accuracy with 43% of the verification and always caught the defector, but after ~37 bad
     answers, not 10.
   - **Supervised start is a trade, not a rule** (L2). It cuts escapes 14–39% for 6–21% more reviews.
7. **Governance works mechanically.** Every autonomous action was explainable, nothing acted after an incident, and
   every self-promotion attempt was blocked (G2–G4). Canaries cut escapes 15%, but proving reviewer complacency
   needs real people (G5).

## Limits

- **Synthetic only.** T2 tasks follow fixed patterns; real work has a longer tail. T3 is too small to promote
  anything.
- **The T2 grader was corrected after the pre-registered hand-check** (it over-counted allowed writes and harmless
  phrasing as promises). Strict-grader rates: good 5.4%, sloppy 18.0%, vs 2.0% / 14.4% final. Both are in the raw
  rows (`serious_strict`).
- **Reviewer behaviour in T1 is an assumed model** (Parasuraman & Manzey-style complacency), swept in sensitivity
  runs.
- **One agent model** (deepseek-v4-flash) in T2.
- Hidden test sets per archetype are small (1–14).

## Reproduce

```bash
python -m t1.run 200 && python -m t1.peer        # T1, free, ~2 min
python -m gym.test_governance                     # G4
python analyze.py && python analyze_t2.py         # verdicts (T2/T3 streams are committed)
```
