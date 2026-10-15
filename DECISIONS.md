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
