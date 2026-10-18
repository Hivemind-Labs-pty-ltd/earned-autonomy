# Trust Gym T2-10x: results (does the 10x harness add a bump?)

Run 2026-10-18. Pre-registered in `PREREG-10x.md`: tag `prereg-10x`, plus addendum D (`prereg-10x-d`) and amendment K
(`prereg-10x-k`), all before the scored runs. Run-time fixes are logged in `DECISIONS.md`.

**Setup:** the same 6,000 generated tasks, the same model (DeepSeek v4 Flash via OpenRouter) and the same grader in
every condition. All local; no staging. **New spend: $43.13** (cap $60). Excluded as errors (timeouts and failed
turns): 59 of 24,000 new task runs (B 2, C 35, D 22).

| | What it is |
|---|---|
| **A** | the minimal T2 agent (already run) |
| **B** | the 10x runtime loop only (`run_turn`, production step bounds), with A's prompt and tools |
| **C** | the full 10x harness: a lean prompt plus policy in knowledge files read with the platform's `read_knowledge`; the pre-send chain (leak gate → checks, including `DEFAULT_CHECKS` and translated archetype rules → compliance judge) with the 2-retry rewrite loop; the context card |
| **D** | C + tool scope per task type + the learning loop (rules learned from corrections into `learned-rules.md`, a new version on each change, carry-over gated by hidden tests) |

## Verdicts

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| X1 | C has ≥ 25% fewer serious errors than A | good 1.9% → **4.4%** · sloppy 14.3% → **15.8%** (higher; paired CIs +2.0…+2.9 and +0.8…+2.3 pts) | **FAIL** |
| X2 | C earns more trust than A (+5 pts reviews removed, no more escapes) | reviews removed good 33.9% → 16.4%, sloppy 21.0% → 6.3% | **FAIL** |
| X3 | The runtime loop alone ≈ A | good +0.9 pts (CI +0.5…+1.2, inside ±1.5) · sloppy +3.7 pts (CI +3.1…+4.4, outside ±3) | **MIXED** |
| X6 | D has ≥ 25% fewer serious errors than C | good 4.4% → **0.6%** (−87%) · sloppy 15.8% → **2.8%** (−82%); CIs exclude 0 | **PASS** |
| X7 | D earns more trust than C | good: removed 16.4% → 24.2%, escapes/100 0.23 → 0.06 ✓ · sloppy: 6.3% → 9.3% (+3.0 pts, under +5), escapes 0.81 → 0.16 | **MIXED** |
| X8 | C's errors aren't higher than A's despite the lean prompt | upper CI +2.9 pts good (margin +1.0), +2.3 sloppy (margin +2.0) | **FAIL** |
| X4/X5 | Cost, latency, gate behaviour | see below | reported |

## Trust-policy reference metrics (v3 combined policy, 20 seeds)

| Condition | Promotions deserved | Reviews removed | Done alone | Escapes/100 auto | Escapes/100 all (vs review-everything) | Cost-weighted/100 |
|---|--:|--:|--:|--:|--:|--:|
| A-good | 100% (434/434) | 33.9% | 40.4% | 0.54 | 0.35 vs 0.17 | 0.87 |
| A-sloppy | 98.6% (276/280) | 21.0% | 25.1% | 0.84 | 0.91 vs 0.72 | 6.30 |
| B-good | 94.2% (327/347) | 28.7% | 34.1% | 0.27 | 0.24 vs 0.18 | 1.12 |
| B-sloppy | 100% (175/175) | 13.4% | 16.2% | 0.39 | 0.96 vs 0.88 | 8.54 |
| C-good | 100% (321/321) | 16.4% | 18.2% | 0.09 | 0.23 vs 0.24 | 1.22 |
| C-sloppy | 82.3% (102/124) | 6.3% | 7.2% | 0.23 | 0.81 vs 0.79 | 6.58 |
| **D-good** | **99.8% (626/627)** | **24.2%** | 27.6% | **0.02** | **0.06 vs 0.05** | 0.43 |
| **D-sloppy** | **99.6% (458/460)** | 9.3% | 11.3% | **0.00** | **0.16 vs 0.17** | 1.19 |

Every condition: 100% of autonomous actions explainable from the ledger.

## Cost, latency (X4) and gate behaviour (X5)

| Condition | USD/task | p50 / p95 s | Leak rewrite (1st draft) | Checks hold (1st) | Any rewrite | Repair success | Gate recall | Gate FPR | Held overall |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| A | $0.0003 | — | — | — | — | — | 10% / 27% (T2 checks) | 0.7% / 0.4% | — |
| B | $0.0001 | 9 / 20 | — | — | — | — | — | — | — |
| C-good | $0.0016 | 50 / 103 | 75.8% | 4.6% | 80.1% | 65.4% | 59.2% | 31.8% | 33.0% |
| C-sloppy | $0.0016 | 52 / 99 | 75.2% | 5.2% | 80.3% | 59.5% | 64.0% | 33.7% | 38.5% |
| D-good | $0.0016 | 52 / 101 | 72.9% | 5.8% | 77.9% | 63.5% | 69.7% | 34.6% | 34.8% |
| D-sloppy | $0.0017 | 52 / 105 | 62.3% | 9.7% | 70.9% | 57.6% | 80.5% | 39.2% | 40.4% |

Holds end mostly at the checks stage (27–36% of tasks), after the leak-gate rewrite. The top failing rows are the
default "no commitment" rubric (about 11% of tasks) and the dollar-amount rubric (about 6%). In C-good only 115 of
the roughly 1,600 actions held at the checks stage contained a real serious error.

## Knowledge lookup (X8 detail)

`read_knowledge` calls per task: C-good 4.16, C-sloppy 3.59, D-good 4.34, D-sloppy 3.76. Tasks with no read: ≤ 0.1%,
too few to compare error rates with and without a read.

## D learning loop

- **Versions** per archetype (good / sloppy):

  | | cs | ws | it | ap | of | do |
  |---|--:|--:|--:|--:|--:|--:|
  | good | 3 | 9 | 2 | 2 | 1 | 4 |
  | sloppy | 9 | 8 | 6 | 6 | 12 | 25 |

  Data ops (sloppy) ended with 72 learned rules.
- **Carry-over fired 0 of 66 times.** Hidden suites stayed under the 10-test minimum once errors became rare.
- **Error rate by 5-cycle block:** good 1.0 → 0.5 → 0.2 → 0.5 → 0.6%; sloppy 5.1 → 2.0 → 2.9 → 2.4 → 1.8%.
- **Decomposition (exploratory):**
  - **D before any learned rule** (C + scope only): −46% (good) and −47% (sloppy) vs C on the same tasks.
  - **D after ≥ 1 rule:** −92% and −84%.

## What we learned

1. **The full 10x setup (D) is the best agent measured.** Serious errors are 0.6% (good) and 2.8% (sloppy), against
   A's 1.9% and 14.3%. Under the trust framework, D-good is as safe as reviewing everything (0.06 vs 0.05 escapes per
   100 actions) while removing 24% of reviews. Scoped tools halve errors; learned rules take it to −84–92%.
2. **The harness without scope and learning (C) is not a bump; it's slightly worse than the minimal agent.** Most of
   the gap comes from the runtime loop itself (B): it follows injected instructions more often (good 1.7% → 2.6%,
   sloppy 1.2% → 3.2%) and makes more wrong reschedules. Likely causes, not isolated: the 10-step bound (A stops at
   6), reasoning settings, and how tool results are framed.
3. **Knowledge lookup works mechanically:** about 4 reads per task, almost never skipped. X8's failure is mostly the
   runtime effect, not unread policy.
4. **The gate detects far better than the T2 checks (59–80% vs 10–27%), but it's too noisy for autonomy:**
   - 32–39% false alarms.
   - The leak gate rewrites 62–76% of first drafts, mostly for em dashes.
   - About 40% of rewrites never reach a sendable draft.
   - The default commitment rubric is the largest source of holds.

   About a third of actions are held, which is why C earns less autonomy than A.
5. **Carry-over never fired.** The hidden-suite minimum penalises fast learners: once errors are rare, few
   corrections arrive to fill the suite.
6. **Cost:** the full harness costs about $0.0016 per task (5–25× A and B) and takes about 50 s median per task.

## Recommendations

1. **Ship tool scope per task type** (enforce `ToolGrant.when`).
2. **Turn on the learning loop** (corrections → learned-rules knowledge, versioned).
3. **Tune the gate before relying on it for autonomy:**
   - Auto-fix em dashes rather than rewriting the whole reply.
   - Measure the default commitment rubric's false-positive rate and re-grade it.
   - Reconsider turning a rewrite-cap hit into a hold.
4. **Investigate the runtime's injection susceptibility** vs a minimal loop.
5. **SPEC §8:** seed hidden suites at version creation (from authored scenarios) so carry-over can work for fast
   learners.

## Limits

- **Synthetic tasks and one model** (Flash), with same-model rubric and compliance grading.
- **The knowledge split** is our own split of each archetype's policy.
- **B/C/D set `thinking: true`** to match A's default reasoning.
- **D's catch draws use hashed seeds;** T2's original loop used string seeds.
- **The smoke runs aren't scored.**
