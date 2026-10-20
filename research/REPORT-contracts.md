# Shadow contracts (narrow round): results

Run 2026-10-21. Pre-registered in `PREREG-contracts.md` (tag `research/prereg-contracts`) before any code. Run-time choices
are logged in `DECISIONS.md` before any arm ran. **New LLM spend: $0.** All runs are offline, on the committed T2 streams
(6,000 tasks each for the good and sloppy agent) over 20 seeds. Code: `contracts/` (`induce.py`, `run.py`, `analyze.py`)
→ `report/verdicts-contracts.json`.

**Question:** does adding shadow contracts to the current framework (v3 combined policy) do more work without a person
and cut human minutes, without more serious mistakes?

## Verdicts

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| K1 | No more mistakes: C escapes ≤ A + 0.1 per 100 | good A 0.35 · B 0.29 · C 0.34 · sloppy A 0.91 · B **1.08** · C 0.86 | **PASS** |
| K2 | Fewer human minutes: C ≤ 0.7 × A | good A 0.694 · B 0.697 · C 0.725 (C/A **1.04**) · sloppy A 0.830 · B 0.811 · C 0.854 (C/A **1.03**) | **FAIL** |
| K3 | Circularity: C locked-in < 5% AND B ≥ 2× C | sloppy: B **4.1%** locked-in (0.4 of 9.8 scored episodes per seed), C 0% ✓ · good: B and C both 0%, so the contrast is not shown | **MIXED** |
| K4 | More work without a person: C ≥ A + 10 pts | good A 40.4% · B 40.3% · C 41.0% · sloppy A 25.1% · B 27.2% · C 25.9% | **FAIL** |

**Tally:** 1 PASS · 1 MIXED · 2 FAIL.

## What happened

| Stream | Arm | Promotions/seed | Tasks run by contract/seed | Held (disagreement)/seed | Extra judged reviews/seed | Demotions/seed |
|---|---|--:|--:|--:|--:|--:|
| good | B | 13.0 | 713 | 38 | — | 0 |
| good | C | 2.5 | 176 | 0 | 230 | 0 |
| sloppy | B | 13.4 | 733 | 33 | — | 4.3 |
| sloppy | C | 2.8 | 195 | 8 | 201 | 0 |

- **Contracts formed easily but covered work the statistics already automated.** Arm C's coverage sat mostly in
  low-consequence information replies: workshop status 58–61% of post-training tasks, IT how-to 7–21%, plus 17% of
  accounts-payable coding on the sloppy agent. The v3 policy already lets these act alone at Trusted or Senior, so moving
  them to contracts saved almost nothing.
- **The judged-sample bar costs more minutes than it saves at this coverage.** C spent about 200–230 extra judged
  reviews and about 12 minutes of sign-offs per seed to promote 2–3 clauses. Those clauses then removed few reviews the
  base policy wasn't already skipping. Net: +3–4% minutes.
- **Circularity is real, and the judged sample stops it.** On the sloppy agent, agreement-only promotion (B) locked in
  4.1% of clause episodes: it hardened the agent's own consistent mistakes into code. The clearest case was
  customer-service returns opened outside policy, wrong on 7–11 of 13–20 tasks. B's escapes rose from 0.91 to 1.08 per
  100. C, which needs human-judged evidence, locked in none and was safer than A (0.86 per 100).
- **Every arm uses far fewer human minutes than doing the work by hand:** about 0.7–0.85 minutes per task against an
  estimated 4.2 minutes manually (the pre-registered estimates). That's the existing framework's gain; contracts didn't
  add to it here.

## How this fits with earlier findings

- **Fits:** "agreement isn't correctness". Consistency alone hardens bad habits (v4 found the same with watch-aware
  agents: measured behaviour ≠ true behaviour). The fix is the same principle as v0.6: promote only on human-judged
  evidence, against the consequence bar.
- **Fits:** deterministic rules are safe when gated. Arm C was the safest arm on the sloppy agent, consistent with the
  checks results (v0, gates bench).
- **Doesn't fit the hoped-for uplift:** on these streams, contracts promote where trust is already earned. The
  bottleneck the design targets is **review time on work the statistics can't yet trust**: medium and high consequence,
  judgement-heavy work. That's exactly where clauses formed least: customer complaints, refunds, quotes, supplier
  queries, and IT access and password changes had few or no pure, fully-sourced leaves.

## Limits

- **Frozen streams:** the agent never changes, so contracts can't show their cost advantage (no model call needed), their
  speed, or their behaviour under world change. Those were deliberately out of scope.
- **Short streams:** about 230–330 tasks per type, with the first 30% used for training. Clauses had little time to
  promote, especially under C's judged bar (≥ 30 judged runs at the consequence bar).
- **Simple contracts:** a depth-3 tree over the target record's fields, with exact argument provenance. A richer inducer
  could cover more of the judgement-heavy types; untested.
- **Minutes only:** the round measured human minutes, not compute cost. A contract replaces a model call, a saving this
  round didn't measure.
- **The good agent made too few consistent mistakes for B to lock any in,** so the circularity contrast shows only on
  the sloppy agent.

## Recommended next step

Keep contracts **only with the judged-evidence gate** (arm C's rule), and point them where they can pay off:

- **Measure compute cost per task,** not just human minutes. Contracts mainly replace model calls on routine work.
- **Test them on volume, not variety:** high-frequency, low-to-moderate consequence task types, over longer streams,
  where hardening can also cut cost and latency.
- **Don't expect contracts to reduce review on judgement-heavy work.** On this evidence, that remains the job of the
  learning loop and the trust statistics.
