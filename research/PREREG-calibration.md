# Pre-registration: round "calibration" (measuring trust)

Written 2026-10-21, before any code for this round. Tagged `research/prereg-calibration`. Nothing here changes after the
tag; corrections go in `DECISIONS.md` as dated entries. New LLM spend: **$0** (offline: T1 simulation and committed T2
streams).

## Question

The framework is now a lifecycle whose MEASURE step gives every trust key (organisation × agent × task type) a **trust
score**: the probability that the key's true serious-error rate is below its task type's error bar, given the evidence.
Two questions:

1. **Does the trust score mean what it says?** Among keys scored *s*, does about *s* of them truly sit under the bar?
2. **What should evidence that isn't a live human review count for?** Shadow comparison, historical replay and
   pre-deployment tests. And how much human time would each save at that weight?

## Trust score

`score = P(p < bar | evidence) = BetaCDF(bar; 1 + errors, 1 + judged − errors)`, a Beta(1, 1) prior updated with the
(possibly weighted) evidence counts. Error bars as in the spec: C1 0.10 · C2 0.05 · C3 0.02. C4 is excluded (its bar is
zero; it never acts alone). A Jeffreys prior, Beta(0.5, 0.5), is reported as a sensitivity check only and is not graded.

## Part A: calibration of live human evidence

- **Evidence process:** the recommended Core (Core + canaries, `core.policy_core.core_config(canaries=True)`), unchanged.
  After every judged outcome on a C1–C3 key, record the key's evidence counts (judged, errors), its own action index and
  whether it is eligible to promote (≥ 30 judged since its last level change).
- **Data:** T1 main worlds, seeds 140 000–140 199 (new). T2 good-full and sloppy-full streams, seeds 500–519.
- **Target ("truly under the bar"):** T1: the mean **true** rate over the key's next 200 own actions ≤ bar. T2: the
  **realised** serious-error rate over the key's next 200 own actions ≤ bar. Points with fewer than 50 future actions are
  dropped.
- **Thinning:** every 5th recorded point per key, to limit correlation between neighbouring points.
- **Bins:** [0, 0.5) · [0.5, 0.6) · [0.6, 0.7) · [0.7, 0.8) · [0.8, 0.9) · [0.9, 0.95) · [0.95, 0.99) · [0.99, 1].
  **ECE** = Σ bin share × |mean score − share truly under the bar|. A reliability table is reported per data set.
- **Known bias, stated now:** live evidence comes from reviewers who miss some errors (the reviewer model), so counts can
  understate the true error rate. Scores may therefore run over-confident. That is part of what is being measured.

## Part B: weights for other evidence

On T1 worlds only (true rates are known). Seeds 140 000–140 199. Each source produces observations that are added to a
key's counts multiplied by a weight *w* (judged += w, errors += w × error).

- **Shadow comparison:** a person does the task as normal while the agent's draft is compared automatically. Per action:
  the agent is wrong with the key's true rate; the person is wrong independently with probability **0.03**; when both are
  wrong they give the *same* wrong answer with probability **0.3** (a false agreement). Agreement → a clean observation.
  Disagreement → a person adjudicates (1 minute) and identifies whether the agent was wrong with accuracy **0.95**; a
  correct agent wrongly marked wrong 5% of the time. Wording differences are excluded by definition (decision and facts
  only).
- **Historical replay:** the agent is run on past cases a person handled, before deployment. The agent's error rate on
  them is its rate at the start of live work. Past human decisions are wrong with probability 0.03, with the same
  agreement and adjudication model as shadow.
- **Pre-deployment tests:** written scenarios, graded perfectly with no human, but the agent's error rate on them is its
  live starting rate × a per-key shift drawn from U(0.3, 1.0) (tests are easier than live work).
- **Weight calibration:** for each source alone, give each C1–C3 key 100 observations and compute its score with
  w ∈ {0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0}. The target is the mean true rate over the key's first 200 live actions ≤ bar.
  The **calibrated weight** is the w with the lowest ECE. Ties go to the smaller w.

## Part C: what each source saves

On T1 seeds 140 000–140 199, against the Core + canaries baseline (**L**, live supervised ramp-up):

- **SH (shadow ramp-up):** while a key is Supervised, the agent doesn't act. A person does the task by hand (manual
  minutes C1 2 · C2 4 · C3 6 · C4 6) and the shadow observation is recorded at the calibrated shadow weight (plus 1 minute
  per adjudicated disagreement). Promotion uses the same Core lookup table on the weighted counts. Once promoted, the
  key runs as in L. Errors the person makes during shadow are reported separately as *human-made errors*, not agent
  escapes.
- **RP (replay pre-load):** before live work, every C1–C3 key gets 100 replay observations at the calibrated replay weight
  (plus 1 minute per adjudicated disagreement). Then live as L.
- **Ramp-up human minutes** = all human minutes spent on a key while it is Supervised, including manual work done during
  shadow and adjudication. Also reported: *extra* minutes beyond the status quo (that is, excluding manual work that
  would have been done anyway).
- **Undeserved promotion** = a promotion where the mean true rate over the key's next 200 own actions exceeds the bar.

## Hypotheses (pass marks fixed now)

- **CAL1:** ECE ≤ 0.05 for live human evidence. PASS if it holds on T1 and both T2 streams; MIXED if on some.
- **CAL2:** at every recorded point where the key is eligible to promote, the decision "score ≥ 0.95" agrees with the
  Wilson promotion decision (95% Wilson upper bound ≤ bar) at least 95% of the time. The best-matching score threshold is
  reported.
- **CAL3:** at its calibrated weight, shadow evidence (SH) cuts ramp-up human minutes by ≥ 50% against L, and increases
  undeserved promotions by no more than 1 percentage point.
- **CAL3b (added for replay, same marks):** RP cuts ramp-up human minutes by ≥ 50% against L, with undeserved promotions
  ≤ L + 1 pt.

Every result is reported, including failures.
