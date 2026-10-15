# Trust Gym v2: results

Run 2026-10-16. Pre-registered in `PREREG-v2.md` (tag `prereg-v2`) before any v2 code. Base policy = the recommended
v1 policy. Tests the 2026-10-16 decisions in SPEC.md: consequence levels, success bar, evidence expiry, reviewer
trust, and knowledge edits as versions. **New LLM spend: $0** (T1 simulation + committed T2 streams). Code:
`gym/engine_v2.py`, `t1/world_v2.py`, `analyze_v2.py` → `report/verdicts-v2.json`; exploratory follow-ups in
`analyze_v2_explore.py` → `report/explore-v2.json`.

## Verdicts (pre-registered)

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| C1 | Consequence bars beat a flat 5% bar (cost-weighted escapes ≤ flat, reviews removed ≥ flat − 2 pts) | T1: cost 3.93 vs 3.91 per 100, removed 19% vs 23% · T2 good: 1.44 vs 1.46, 34% vs 35% ✓ · T2 sloppy: 6.99 vs 6.40, 20% vs 14% | **MIXED** |
| C2 | C1 floor: ≥ 40% of C1 reviews removed at ≤ 1.0 escapes/100 auto | T1 45% / 0.60 · T2 good 54% / 0.84 · T2 sloppy 63% / 0.71 | **PASS** |
| C3 | Success criterion cuts auto-executed non-serious failures ≥ 30% at ≤ 5 pts automation | T1 −47% but −11.8 pts · T2 good −9% / −0.2 · T2 sloppy −13% / −0.5 | **FAIL** |
| F1 | Evidence fading cuts rare-then-drift escapes ≥ 30% at ≤ 3 pts automation | half-life 90 d: −36%, −6.0 pts · 180 d: −31%, −3.9 pts | **FAIL** (adopt none) |
| R1 | Reviewer trust: escapes −25% at ≤ +15% review minutes; bad reviewer at R2 ≤ 60 reviews | escapes −20% (70.4 → 56.3), minutes +25%; no reviewer ever reached R2 (18–28 evidence per world, below n_min 30) | **FAIL** |
| K1 | Knowledge edits as versions: carry-over keeps ≥ 80% of always-keep automation, escapes ≤ 1.1 × always-discount | carry 4.2% vs keep 12.9% vs discount 1.6% automation; escapes 43.0 / 46.8 / 42.9 | **FAIL** |

**Tally: 1 PASS · 1 MIXED · 4 FAIL.** Every failure has a clear cause, and the exploratory runs below found a fix for
most.

## Exploratory follow-ups (post-hoc, labelled; not pre-registered)

| Failure | Candidate fix | Result |
|---|---|---|
| C1 MIXED | Where does the sloppy agent's extra cost come from? | The bars work: C3 auto-actions fall (good 624 → 147, sloppy 66 → 0) and C1 auto-actions rise (+400–480). The extra cost is C1 escapes (cost 1 each, ~10 per world) plus noise from reviewer misses on held C4 items (cost 30 each). Without the success criterion, consequence bars beat flat on T1: cost 3.84 vs 3.91, removed 30% vs 23%. |
| K1 FAIL | Carry over when hidden pass ≥ 0.8, **dropping "≥ previous version"** | T1: 11.3% automation (87% of always-keep), escapes 44.4 (1.04 × discount): would pass. T2 learning loop: same 142/400 promotions, 125/125 deserved, 0 escapes. A 0.05 tolerance instead: 66%, not enough. |
| R1 FAIL | Clean second checks count as evidence; canaries 5% | Reviewers sorted correctly: A (0.95) ends at R2 in 100% of worlds, B (0.85) 79%, C (0.60) 0%, D (degrading) 8%; median bad-reviewer reviews at R2 = 0. Escapes −18%, minutes +20%. At 2% canaries the bad reviewer stayed trusted for a median of 174 reviews. |
| F1 FAIL | Re-entry rule: step down one level when a task type returns after a gap > 60 days | Rare-then-drift escapes −17% (5.0 → 4.2) at zero automation cost. |

## Recommended SPEC changes

1. **Keep ε 10 / 5 / 2% and "C4 never promotes".** C2 passed: the C1 floor (35 judged actions) frees 45–63% of
   C1 reviews at under 1 escape per 100.
2. **Task success = the action achieved its goal.** Add the outcome label `incomplete`. "Approved as-is or
   cosmetic" equals "not serious", so it added nothing.
3. **Minimum task success becomes a monitored alert** (85 / 90 / 95%), not a promotion gate (C3 failed).
4. **No evidence fading** (F1 failed). Fading punishes Senior task types, because only 5% of their actions are
   judged. Optional **re-entry rule:** after a gap of more than 60 days in a task type, step down one level
   (exploratory).
5. **Carry-over: hidden pass ≥ 0.8. Drop "≥ the previous version"** (exploratory; confirmed on T2 loop data).
6. **Knowledge edits as versions:** sound with fix 5. Hidden suites must run automatically on every edit, and
   batching edits (e.g. a weekly release) is recommended (untested). Bad edits are expensive: with 20% of edits
   making the agent worse, automation stays at ~13% even if trust is always kept.
7. **Reviewer trust:**
   - Clean second checks count as evidence (ε_rev 10%, n_min 30).
   - Canaries at 5%.
   - Second checks: R1 25%, R2 5%.
   - Position it as **quality control** that finds bad reviewers (exploratory), not as the main escape reducer.

## Surprises

1. The success definition was redundant with "not serious".
2. Canaries and disagreements alone never reach n_min in a year, so no reviewer was trusted.
3. The "≥ previous" clause, not the 0.8 threshold, breaks carry-over under frequent versions.
4. Fading punishes high trust: the less you check, the faster evidence fades.
5. Bad edits are costly: autonomy stays low whatever the carry rule.

## Limits

- **Synthetic only;** no new agent runs.
- **K1's simulated hidden tests are more informative than real ones** (ρ = −0.98 vs T2's −0.81); fix 5 was
  confirmed on T2 real loop data.
- **Fixed reviewer catch rates** in R1 (no complacency).
- **F1 is T1 only.**
- **The exploratory fixes are post-hoc** and need a pre-registered confirmation before they become [tested].
