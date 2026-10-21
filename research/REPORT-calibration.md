# Round "calibration": measuring trust — results

Run 2026-10-21. Pre-registered in `PREREG-calibration.md` (tag `research/prereg-calibration`) before any code.
Operationalisations are logged in `DECISIONS.md` before any scored run. **New LLM spend: $0** (offline). Code:
`calibration/` (`run.py`, `analyze.py`, `explore.py`) → `report/verdicts-calibration.json`. Exploratory follow-ups are
labelled and live in `report/raw/calibration-explore*.json`.

**Question:** the MEASURE step gives every trust key a **trust score**, the probability that its true serious-error rate
is under its error bar. Does the score mean what it says, and what is evidence that isn't a live review worth?

## Verdicts

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| CAL1 | ECE ≤ 0.05 for live human evidence | T1 **0.146** · good agent **0.088** · sloppy agent **0.039** | **MIXED** |
| CAL2 | "Score ≥ 0.95" agrees with Wilson promotion ≥ 95% of the time | pooled **95.8%** (T1 96.2% · good 90.5% · sloppy 96.9%); best-matching threshold **0.976–0.979**, agreeing 99.9–100% | **PASS** |
| CAL3 | Shadow evidence cuts ramp-up human minutes ≥ 50%, undeserved promotions ≤ +1 pt | ramp-up minutes **+328%** (the person does the task by hand during shadow); undeserved +0.4 pts | **FAIL** |
| CAL3b | Replay pre-load cuts ramp-up human minutes ≥ 50%, undeserved ≤ +1 pt | ramp-up minutes **+3%**; undeserved **−1.5 pts** | **FAIL** |

**Tally:** 1 PASS · 1 MIXED · 2 FAIL.

## What happened

**The score is conservative where evidence is thin, and slightly over-confident at the top when agents change.**

| Score bin | T1: share truly under the bar | Good agent | Sloppy agent |
|---|--:|--:|--:|
| 0–0.5 (mean ~0.08–0.19) | 0.26 | 0.35 | 0.07 |
| 0.9–0.95 | 0.91 | 0.99 | 0.99 |
| 0.95–0.99 (mean ~0.97) | 0.94 | 1.00 | 0.99 |
| 0.99–1 | 0.96 | 1.00 | 0.99 |

- **Most of the calibration error is in the low-score bin.** With a flat prior, an agent with little evidence scores low
  even when it's actually fine. That's conservative: it delays trust, it doesn't grant it wrongly.
- **At high scores the simulated worlds are slightly over-confident** (0.97 scored, 0.94 actual). Those worlds include
  agents that get worse after promotion (drift, bad updates, defectors), which no score from past evidence can foresee.
  Step-down handles them. On the generated-task agents, which don't change, high scores were if anything
  under-confident.
- **The score reproduces the Wilson rule almost exactly at a threshold of about 0.975 instead of 0.95.** At 0.95 it
  promotes earlier than Wilson (for example about 58 clean reviews instead of 73 at the 5% bar).

**Evidence that isn't a live review (calibrated weights, 100 observations per key):**

| Source | ECE at weight 1.0 | Best weight on the grid | ECE at best |
|---|--:|--:|--:|
| Shadow comparison | 0.051 | 2.0 (grid maximum) | 0.043 |
| Historical replay | 0.080 | 2.0 (grid maximum) | 0.064 |
| Pre-deployment tests (easier than live work) | 0.033 | **0.75** | 0.024 |

The shadow and replay weights hit the top of the grid. That mostly reflects the flat prior's pessimism (more evidence
corrects an under-confident score), **not** that a shadow comparison is worth two reviews. Read it as: shadow and replay
are at least as informative as a live review. Tests need a discount even when graded perfectly, because they're easier
than real work.

**What each source saves (T1, 200 worlds):**

| Arm | Ramp-up human minutes / world | The multiple | Serious escapes / 100 | Undeserved promotions |
|---|--:|--:|--:|--:|
| Live supervised review (L) | 2,246 | 5.23× | 0.58 | 5.3% |
| Shadow ramp-up (SH, weight 2.0) | 9,613 (of which 9,326 is manual work that would happen anyway) | 1.49× | 0.30 (+ 62 human-made errors / world) | 5.7% |
| Replay pre-load (RP, weight 2.0) | 2,314 | 5.32× | 0.60 | 3.8% |

- **Shadow mode costs more human time, not less, because a person does the task by hand while the agent only drafts.**
  Reviewing a draft (1 minute) is quicker than doing the task (2–6 minutes), so supervised review is the cheaper ramp.
  Shadow's *extra* minutes beyond the status quo are small (adjudication only, −87% against L's ramp), and nothing the
  agent does reaches anyone. **Shadow buys zero exposure, not saved time.** It's the right mode where reviewing drafts
  isn't possible or the risk is unacceptable.
- **Replay didn't shorten the ramp-up either.** Exploratory, by pattern, minutes until first promotion for keys that
  promote live:

  | Pattern | Live | Replay | Change |
  |---|--:|--:|--:|
  | Defector | 82 | 22 | **−73%** |
  | Drift | 44 | 19 | **−56%** |
  | Bad update | 83 | 55 | **−34%** |
  | Steady | 96 | 93 | −3% |
  | Learning | 90 | 130 | +44% |
  | Early errors | 111 | 224 | +103% |

  Replay helps when the agent's starting behaviour is good, and hurts when the agent starts badly and improves (it
  measures the bad start, and the errors count). Even for steady agents it barely helps. **Replay disagreements are
  adjudicated at 95% accuracy, while live reviewers miss more** (complacency model), so replay finds *more* of an agent's
  real errors. Live evidence was flattering agents. Replay's promotions were more deserved (3.8% undeserved vs 5.3%),
  not faster.

## How this fits

- **Fits:** "no shortcuts to trust". Non-review evidence is real evidence, but it doesn't make trust cheaper on its own.
  Shadow costs the work itself; replay is honest and therefore slower.
- **New:** **live review flatters agents** when reviewers miss errors. A trust score built only from live reviews is
  optimistic by however many errors the reviewers miss. Canaries partly correct this (they're in Core); adjudicated
  replay corrects it further.
- **New:** the multiple is decided mostly by **how much work stays held and how long each review takes**, not by the
  source of the evidence (see also the dial round).

## Recommended values for the spec

- **Trust score:** `BetaCDF(bar; 1 + errors, 1 + judged − errors)`. **Promotion threshold 0.975** to match the tested
  Wilson rule (0.95 is more lenient: about 20% fewer clean reviews needed).
- **Evidence weights (Open, pending real data):**
  - live review 1.0;
  - shadow comparison 1.0;
  - historical replay 1.0;
  - pre-deployment tests **0.75**, and never the only evidence for promotion.
- **Evidence modes:**
  - **Supervised review** is the cheapest ramp when drafts can be reviewed.
  - **Shadow** is for zero-exposure ramp-up, where it costs the manual work.
  - **Replay** is for honest starting evidence: it measures real errors more completely.
- **Report the score with a "thin evidence" flag,** since low scores mostly mean "not enough evidence yet", not "bad".

## Limits

- **All synthetic,** with simple models of human error (3%), adjudication accuracy (95%) and reviewer complacency.
- **The weight calibration is confounded by the flat prior.** A follow-up should calibrate weights *relative to live
  evidence* rather than absolutely.
- **Replay assumes past cases look like live work.** In practice they may not.
- **The by-pattern replay analysis is exploratory** (post-hoc).
