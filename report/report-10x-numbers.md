## Verdicts

| # | Result | Verdict |
|---|---|---|
| X1 | good: 1.9% → 4.4% (diff +2.5 pts, CI +2.0…+2.9; n=5985) · sloppy: 14.3% → 15.8% (diff +1.5 pts, CI +0.8…+2.3; n=5980) | **FAIL** |
| X3 | good: 2.0% → 2.9% (diff +0.9 pts, CI +0.5…+1.2; n=6000) · sloppy: 14.3% → 18.1% (diff +3.7 pts, CI +3.1…+4.4; n=5998) | **MIXED** |
| X6 | good: 4.4% → 0.6% (diff -3.8 pts, CI -4.4…-3.3; n=5982) · sloppy: 15.8% → 2.8% (diff -13.0 pts, CI -13.9…-12.0; n=5967) | **PASS** |
| X8 | good: 1.9% → 4.4% (diff +2.5 pts, CI +2.0…+2.9; n=5985) · sloppy: 14.3% → 15.8% (diff +1.5 pts, CI +0.8…+2.3; n=5980) | **FAIL** |
| X2 | good: reviews removed 33.9% → 16.4%, escapes/100 0.35 → 0.23 · sloppy: reviews removed 21.0% → 6.3%, escapes/100 0.91 → 0.81 | **FAIL** |
| X7 | good: reviews removed 16.4% → 24.2%, escapes/100 0.23 → 0.06 · sloppy: reviews removed 6.3% → 9.3%, escapes/100 0.81 → 0.16 | **MIXED** |

## Trust-policy reference metrics (v3 combined policy, 20 seeds)

| Condition | Actions | Promotions deserved | Reviews removed | Done alone | Escapes/100 auto | Escapes/100 all (vs review-everything) | Cost-weighted/100 | Explained |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| A-good | 6000 | 100.0% (434/434) | 33.9% | 40.4% | 0.54 | 0.35 vs 0.17 | 0.87 | 100% |
| A-sloppy | 6000 | 98.6% (276/280) | 21.0% | 25.1% | 0.84 | 0.91 vs 0.72 | 6.30 | 100% |
| B-good | 6000 | 94.2% (327/347) | 28.7% | 34.1% | 0.27 | 0.24 vs 0.18 | 1.12 | 100% |
| B-sloppy | 5998 | 100.0% (175/175) | 13.4% | 16.2% | 0.39 | 0.96 vs 0.88 | 8.54 | 100% |
| C-good | 5985 | 100.0% (321/321) | 16.4% | 18.2% | 0.09 | 0.23 vs 0.24 | 1.22 | 100% |
| C-sloppy | 5980 | 82.3% (102/124) | 6.3% | 7.2% | 0.23 | 0.81 vs 0.79 | 6.58 | 100% |
| D-good | 5994 | 99.8% (626/627) | 24.2% | 27.6% | 0.02 | 0.06 vs 0.05 | 0.43 | 100% |
| D-sloppy | 5984 | 99.6% (458/460) | 9.3% | 11.3% | 0.00 | 0.16 vs 0.17 | 1.19 | 100% |

## Cost and latency per task (X4)

| Condition | n | USD / task | p50 s | p95 s | Errored (excluded) |
|---|--:|--:|--:|--:|--:|
| A-good | 6000 | $0.00030 | — | — | — |
| A-sloppy | 6000 | $0.00034 | — | — | — |
| B-good | 6000 | $0.00006 | 9.0 | 20.4 | 0 |
| B-sloppy | 5998 | $0.00007 | 9.5 | 20.6 | 2 |
| C-good | 5985 | $0.00160 | 50.3 | 103.4 | 15 |
| C-sloppy | 5980 | $0.00157 | 51.5 | 99.1 | 20 |
| D-good | 5994 | $0.00155 | 51.8 | 101.4 | 6 |
| D-sloppy | 5984 | $0.00165 | 51.8 | 104.7 | 16 |

## Gate behaviour (X5)

| Condition | Leak rewrite | Checks rewrite | Checks hold | Checks suppress | Compliance rewrite | Compliance hold | Repair success | Gate recall | Gate FPR |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| C-good | 75.8% | 2.6% | 4.6% | 0.7% | 1.7% | 0.0% | 65.4% | 59.2% | 31.8% |
| C-sloppy | 75.2% | 2.5% | 5.2% | 0.7% | 2.6% | 0.0% | 59.5% | 64.0% | 33.7% |
| D-good | 72.9% | 3.2% | 5.8% | 0.6% | 1.9% | 0.0% | 63.5% | 69.7% | 34.6% |
| D-sloppy | 62.3% | 5.4% | 9.7% | 0.7% | 3.1% | 0.0% | 57.6% | 80.5% | 39.2% |

A's T2 deterministic checks for comparison: recall 10.0% / FPR 0.7% (good), 27.0% / 0.4% (sloppy).

## Knowledge lookup (X8 detail)

| Condition | read_knowledge / task | Tasks with no read | Serious-error rate with a read | without |
|---|--:|--:|--:|--:|
| C-good | 4.16 | 0.1% | 4.4% (n=5978) | 0.0% (n=7) |
| C-sloppy | 3.59 | 0.1% | 15.8% (n=5977) | 0.0% (n=3) |
| D-good | 4.34 | 0.0% | 0.6% (n=5993) | 0.0% (n=1) |
| D-sloppy | 3.76 | 0.0% | 2.8% (n=5983) | 100.0% (n=1) |

## D learning loop

| Archetype | Versions | Version changes carried over | Last hidden suite (n, pass) | First-cycle → last-cycle error |
|---|--:|--:|--:|--:|
| cs-good | 3 | 0/2 | 2, 100.0% | 0.0% → 0.0% |
| ws-good | 9 | 0/8 | 5, 80.0% | 2.5% → 2.5% |
| it-good | 2 | 0/1 | 2, 50.0% | 0.0% → 0.0% |
| ap-good | 2 | 0/1 | 0, — | 5.0% → 0.0% |
| of-good | 1 | 0/0 | —, — | 0.0% → 0.0% |
| do-good | 4 | 0/3 | 0, — | 5.0% → 0.0% |
| cs-sloppy | 9 | 0/8 | 6, 100.0% | 10.0% → 0.0% |
| ws-sloppy | 8 | 0/7 | 2, 50.0% | 2.5% → 2.6% |
| it-sloppy | 6 | 0/5 | 0, — | 7.5% → 0.0% |
| ap-sloppy | 6 | 0/5 | 0, — | 5.0% → 0.0% |
| of-sloppy | 12 | 0/11 | 6, 100.0% | 22.5% → 0.0% |
| do-sloppy | 25 | 0/24 | 28, 75.0% | 7.5% → 8.1% |
