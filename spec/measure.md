# Measure: the trust score and the trust profile

How much can an agent be trusted with a task type, right now? This page explains how the Measure rules
([requirements/01-measure.md](requirements/01-measure.md)) answer that. **Sections marked _Normative_ restate rules;
the rule files are authoritative. Everything else is informative.**

## Evidence

_Normative (EA-1.2 to EA-1.4, EA-1.17, EA-1.18, EA-1.21)._

- Evidence is **judged actions**: an action a person approved, edited or rejected before it happened (pre-review),
  judged afterwards (spot-check), or reported as an incident. Each one is either a **serious error** or not.
- **Live human judgement counts at weight 1.0.** Every other source has a stated weight relative to it.
- Other sources MAY count in the trust score, at a policy-set weight:

  | Source | What it is | Default weight | Status |
  |---|---|--:|---|
  | `human` | Live pre-review, spot-check and incident | 1.0 | Tested |
  | `shadow` | The agent's output compared with what a person actually did on the same case | 1.0 | Open |
  | `replay` | The agent graded on past cases people already handled | 1.0 | Open |
  | `test` | Pre-deployment tests | 0.75 | Open |

  The defaults come from a calibration round in simulation; they are provisional until confirmed against human
  judgement in production (EA-1.19). Test results are never the only evidence for an implied autonomy above
  supervised. A version discount (EA-4.7) applies to every source.
- **Only live human evidence moves the Core ladder** (EA-1.21). Other sources change the trust score and the profile,
  not the decision.

**Effective evidence** is the weighted count: `n = Σ weight × judged` and `e = Σ weight × serious`, over sources.

## The trust score

_Normative (EA-1.14)._

The trust score is the probability that the task type's true serious-error rate `p` is below its error bar `ε`, given
the evidence:

```
trust score = P(p < ε | evidence) = I_ε(a₀ + e, b₀ + n − e)
```

`I_x(a, b)` is the regularised incomplete beta function (the Beta distribution's cumulative probability). The prior is
Beta(a₀, b₀), default **Beta(1, 1)**: every error rate equally likely before any evidence. A capped task type scores 0.

**Reading it.** 0.98 means "98% sure this task type is under its bar". A low score with **thin evidence** (less than
the clean floor: 35, 73 or 189 judged actions at C1, C2, C3) mostly means "not enough evidence yet", not "a bad
agent". The trust profile flags this.

### How it relates to the Wilson rule

Core promotes when the 95% Wilson upper bound is at or below the error bar (EA-2.14, EA-2.15). A two-sided 95%
interval leaves 2.5% above its upper end, so the matching score threshold is **0.975**, not 0.95.

The equivalence is not exact, and this is exactly how close it is (flat prior, threshold 0.975; checked for all 33
published cells, `engine/tests/test_measure.py::test_trust_score_matches_wilson_at_every_promotion_point`):

- **Wherever Wilson promotes, the score is at least 0.975:** between 0.975 and 0.979 in all 33 cells.
- **The score reaches 0.975 a little earlier:** 0–1 judged actions earlier at C1, up to 2 at C2 and up to 7 at C3 (182
  instead of 189 with no errors). The gap is largest with no errors and shrinks as errors accumulate.
- In simulation, "score ≥ 0.975" agreed with Wilson promotion 99.9–100% of the time (best thresholds 0.976–0.979).
  At 0.95 the score promotes about 20% earlier (about 58 instead of 73 clean judged actions at C2) and does not match.

So the Core ladder's decisions stay on the bound or the table; the score is how the same evidence is *reported*. An
implementation that promotes on the score instead (the dial, EA-2.22) uses 0.975.

### Calibration (informative)

From [research/REPORT-calibration.md](../research/REPORT-calibration.md):

- **Mixed overall** (expected calibration error 0.146 on the simulated organisations, 0.088 on a good generated-task
  agent, 0.039 on a sloppy one).
- **Conservative at low scores.** With the flat prior, an agent with little evidence scores low even when it's fine.
  That delays trust; it never grants it wrongly.
- **Slightly over-confident at the top** in worlds where agents get worse after promotion (scored about 0.97, actual
  0.94). No score from past evidence can foresee a later regression; step-down (EA-2.17) and incidents (EA-2.18)
  handle it.

## The trust profile

_Normative (EA-1.15). Field names are those of the reference engine's `trust_report()`._

| Field | Meaning |
|---|---|
| `estimated_error_rate`, `error_rate_interval` | Posterior mean `(a₀ + e) / (a₀ + b₀ + n)` and the 2.5–97.5% posterior interval |
| `trust_score` | As above |
| `thin_evidence` | Effective evidence below the clean floor |
| `effective_evidence` | `n`, the weighted judged actions |
| `evidence_by_source` | Judged, serious and weight for each source |
| `freshness` | The agent version and when the last evidence arrived |
| `trend` | `slipping`, `improving`, `stable` or `insufficient`, from the recent window against the overall rate |
| `autonomy_setting` | Where the task type actually is: supervised, trusted, senior, capped, paused or retired |
| `implied_autonomy` | What the evidence alone supports: `supervised`, `trusted_or_above` or `capped` |

The autonomy setting and the implied autonomy can differ: the setting needs at least 30 judged actions since the last
change, moves one level at a time, and uses live human evidence only.

## The agent's trust summary

_Normative (EA-1.16)._ For each agent: the share of its actions at each autonomy setting, its incidents (all and last
30 days), and how many of its task types are slipping, improving or stable. Owners make the decisions in
[EA-2.21](requirements/02-decide.md) from this view.

## Evidence modes (informative)

Each source has a different cost. From the calibration round:

- **Supervised review is the cheapest ramp** when drafts can be reviewed before they go out.
- **Shadow** has zero exposure but costs the manual work: a person still does every task while the agent shadows.
  It is not a time saver. Use it where reviewing drafts isn't possible or the risk is unacceptable.
- **Replay** gives more honest evidence: it found more real errors, with fewer undeserved promotions (3.8% vs 5.3%),
  but it didn't make ramp-up faster.
- **Live review flatters agents** when reviewers miss errors. Canaries (EA-3.11) and reviewer trust (EA-3.12) partly
  correct this.
