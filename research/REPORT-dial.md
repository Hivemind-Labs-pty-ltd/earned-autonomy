# Round "dial": ladder vs oversight in proportion to uncertainty — results

Run 2026-10-21. Pre-registered in `PREREG-dial.md` (tag `research/prereg-dial`) before any code. Operationalisations are
logged in `DECISIONS.md` before any scored run. **New LLM spend: $0** (offline). Code: `dial/` (`run.py`, `analyze.py`) →
`report/verdicts-dial.json`.

**Question:** in the lifecycle's DECIDE step, does a continuous **dial** (spot-check rate from the trust score:
`clip(5 × (1 − score) + 0.02, 0.02, 1)`, pre-review while the score is under 0.95) raise **the multiple** against the
Core ladder, without more escapes or slower regression detection?

## Verdicts

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| DIAL1 | Dial's multiple ≥ 1.1 × ladder | T1 **1.008×** · good agent **1.067×** · sloppy agent **1.008×** | **FAIL** |
| DIAL2 | Dial's escapes ≤ ladder + 0.1 per 100 | +0.015 · +0.005 · +0.018 | **PASS** |
| DIAL3 | Regression demotion ≤ ladder + 5 actions (T1) | median **17 vs 17** | **PASS** |

**Tally:** 2 PASS · 1 FAIL.

## Numbers

| Data | Arm | The multiple | Last third | Escapes /100 | Done without a person | Promotions deserved | Mean spot-check rate |
|---|---|--:|--:|--:|--:|--:|--:|
| T1 (200 worlds) | ladder | 5.12× | 4.96× | 0.62 | 32.7% | 91.9% | 25% / 5% by level |
| | dial | 5.17× | 5.11× | 0.64 | 35.0% | 93.0% | 16.5% |
| Good agent (20 seeds) | ladder | 6.01× | 7.43× | 0.35 | 40.6% | 100% | 25% / 5% |
| | dial | 6.42× | 7.62× | 0.35 | 43.6% | 100% | 12.9% |
| Sloppy agent (20 seeds) | ladder | 5.02× | 5.47× | 0.91 | 25.1% | 98.9% | 25% / 5% |
| | dial | 5.06× | 5.20× | 0.92 | 26.2% | 100% | 18.6% |

## What happened

- **The dial is as safe as the ladder and catches regressions just as fast.** Escapes are within 0.02 per 100, demotion
  takes 17 actions in both arms, and promotions are as deserved or more.
- **It barely moves the multiple** (+1% to +7%). Spot-checks are a small share of human minutes. Most minutes go on work
  that's still held for pre-review: task types not yet trusted, high-consequence and critical work, and actions flagged
  by checks. Tuning how often trusted work is sampled can't reach those minutes.
- **The dial promotes a little earlier,** because a 0.95 score is more lenient than the Wilson rule. That's where most of
  its small gain comes from, not from the sampling curve.

## How this fits

- **Fits:** the core round's finding. Trust rules alone sit around 5–6× (up to about 7.6× in steady state), and **10×
  won't come from fine-tuning oversight.** It has to come from less held work (better agents, more task types that can
  earn trust) and cheaper reviews (faster review per item, batching).
- **The dial is a valid, equally safe way to set oversight,** so it can stay as an Advanced option for teams that want
  smooth control. It isn't a lever on the multiple.

## Recommended values for the spec

- **Core keeps the ladder:** it's simpler and costs almost nothing in multiple.
- **The dial is an Advanced option:** pre-review while score < 0.975 (to match Wilson promotion; this round used 0.95),
  spot-check rate `clip(5 × (1 − score) + 0.02, 0.02, 1)`, with the same step-down trigger and incident rule as Core.

## Limits

- **Synthetic,** with the same reviewer and manual-minutes assumptions as earlier rounds (1-minute reviews; manual C1 2 ·
  C2 4 · C3 6 · C4 6).
- **One dial curve (k = 5, floor 2%) was tested.** A steeper curve would sample less but risks slower detection; not
  tested.
- **The generated-task streams have no regressions,** so DIAL3 is graded on T1 only.
