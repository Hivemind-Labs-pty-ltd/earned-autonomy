# Decisions log

Append-only. Newest at the bottom.

## 2026-10-15 — prereg
- PREREG.md written before any code or data. Budget hard stop US$25 new spend.

## 2026-10-15 — operationalisations fixed before any T1 result (engine written, smoke run only)
- **Rolling demotion** = Wilson *lower* bound of the last 50 observed outcomes > ε (needs ≥ 10 observations). An upper bound would demote on noise.
- **Promotion** needs ≥ n_min observations since the last level change AND the cumulative Wilson upper bound ≤ ε. With ε = 0.05 that means ~73 clean reviews before the first promotion.
- **H1** "next 200 actions of that type" = the mean of the *true* error rate over the key's next 200 own actions (T1 knows the rate function).
- **H3 / B-matched** = per world, hold_p = 1 − a_D / (1 − flag rate), so B-matched's automation equals D's exactly. "Escapes" = all executed serious errors per 100 actions (auto + reviewer misses).
- **H4 / G1** latency = the key's own actions from the regression point to its first demotion. G1 counts only keys at L2+ when the regression hits.
- **R1** operationalised: the trust arm passes if its accuracy is ≥ equal-trust + 5 points AND it uses ≤ 50% of verify-all's verification calls ("accuracy per verification call" is undefined when equal trust makes 0 calls).
- **T1 world**: 2 agents × 4 task types (low / med / high / capped), 4000 actions, type mix 40/30/20/10; base rates low U(0.5–2%), med U(2–5%), high U(5–12%), capped U(2–6%); pattern per key drawn from steady 40% · learning 15% · early 15% · drift 10% · bad update 12% · defector 8%.

## 2026-10-15 — R3 measurement bug fixed (after first peer run)
- First run defined "caught" as the defector's lower bound < threshold on both skills; once the host stops routing to it, its record never updates, so it never counted as caught (6.5%). Fixed to "the host no longer routes either skill to the defector", which is what down-weighting below the decision threshold means in PREREG R3. THRESH (0.85) and AUDIT (10%) were set in code before the first run and are unchanged.
- **Post-hoc (labelled exploratory, not a prereg test):** the prereg trust arm routes greedily on the lower bound and never explores, so untried consultants keep no record and a defector stays first choice (cold start). Added `trust-ts` (Thompson-sampling routing). Reported beside the prereg arm; the R1/R3 verdicts use the prereg arm.

## 2026-10-15 — G4 suite first run: 28/28 attacks blocked, 7/8 legit allowed
- The refused legit request was an agent reading its own ledger (role map omitted `agent` for `read_ledger`). Fixed; rerun 28/28 blocked, 8/8 legit allowed. Guard rules for attacks unchanged.
