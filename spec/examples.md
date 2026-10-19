# Examples and the maths

**Informative.** How the numbers in the rules work, in plain language. Every figure is computed by the reference
engine (`engine/src/earned_autonomy/stats.py`).

## The idea in one line

Promote when even the worst case looks good, step down when even the best case looks bad, and keep checking in
between.

## 1. What is counted

Each time a person judges one of the agent's actions in a task type, the trust key records one result: fine, or a
serious error (EA-3.3). So every trust key has two numbers: **judged actions** and **serious errors**.

## 2. Why the average isn't enough

An agent that got 5 refunds out of 5 right has a 0% error rate. Five is too few to know anything, though. It might
really get one in three wrong and have been lucky. So the question isn't "what is its error rate?" but **"what is the
highest error rate that could still plausibly explain what we've seen?"** That's the **upper bound**, at 95%
confidence (the Wilson score interval, EA-3.4).

## 3. The worst case shrinks as clean work builds up

With no serious errors:

| Clean judged actions | Worst plausible error rate |
|--:|--:|
| 5 | 43.4% |
| 10 | 27.8% |
| 20 | 16.1% |
| 35 | 9.9%: under the C1 bar (10%) |
| 50 | 7.1% |
| 73 | 5.0%: under the C2 bar (5%) |
| 100 | 3.7% |
| 189 | 2.0%: under the C3 bar (2%) |

A rule of thumb: with no errors, the worst case is roughly **4 ÷ the number judged**.

## 4. Mistakes push the finish line out

Judged actions needed before the upper bound is under the error bar:

| Error bar | 0 errors | 1 error | 2 errors | 3 errors |
|---|--:|--:|--:|--:|
| 10% (C1) | 35 | 53 | 69 | 84 |
| 5% (C2) | 73 | 110 | 142 | 173 |
| 2% (C3) | 189 | 280 | 361 | 437 |

At C2, 73 judged actions with one error gives a worst case of 7.4%: not good enough yet. One early mistake costs
about 37 more clean actions. It raises the bar; it doesn't reset to zero.

## 5. The promotion rule (EA-3.4)

A trust key moves up one level when both are true:

1. At least **30 judged actions since its last level change**, so a lucky streak right after a change isn't enough.
2. Its **upper bound is at or under its error bar.**

After promotion, a random 25% (L2) or 5% (L3) of actions are spot-checked (EA-2.8). Those judgements add to the same
two counts, so the record keeps growing, more slowly, which is why L3 takes longer.

## 6. Stepping down uses the opposite question (EA-3.5)

For a step-down, the engine looks only at the **last 50 judged actions** and asks the reverse: **"giving the agent
every benefit of the doubt, is its error rate still over the bar?"** That's the **lower bound**. At a 5% bar:

| Serious errors in the last 50 | Best plausible error rate | Step down? |
|--:|--:|---|
| 3 | 2.1% | No |
| 4 | 3.2% | No |
| 5 | 4.3% | No |
| **6** | **5.6%** | **Yes: over 5% even at best** |
| 7 | 7.0% | Yes |

So it is **slow to promote** (the worst case must be good) and **quick to step down** (only clear evidence of a
problem is needed). An incident steps down at once, without the maths (EA-3.7).

## 7. When the agent changes (EA-4.6, EA-4.7)

A new version that passes at least 80% of at least 10 hidden tests **keeps its record**. Otherwise both counts are
**halved**, and the key drops to L1 if the halved record no longer clears its bar. At C2, with no errors:

| Clean judged actions before | After halving | Upper bound after | Result |
|--:|--:|--:|---|
| 100 (just promoted) | 50 | 7.1% | Drops to L1 |
| 146 | 73 | 5.0% | Keeps its level |
| 400 (long record) | 200 | 1.9% | Keeps its level comfortably |

## 8. Strict promotion (EA-3.14, optional)

The engine re-checks the bound after every outcome. Strict promotion uses a bound that stays valid under that
continuous checking, at the cost of more evidence. Clean judged actions needed:

| Consequence | Wilson (default) | Strict |
|---|--:|--:|
| C1 | 35 | 46 |
| C2 | 73 | 93 |
| C3 | 189 | 236 |

## 9. Worked example: a refund

A customer service agent proposes a $49 refund. Task type `customer_service.refund.issue`, consequence C3 (error bar
2%), trust level L1.

1. **Tag** (EA-1.8): `customer_service.refund.issue`, confidence 0.95.
2. **Tool floor** (EA-1.14): the action calls `issue_refund`, whose floor is C3, the same as the tag. No mismatch.
3. **Checks** (EA-2.3): the amount equals the order total, and the order is inside the 30-day window. Pass.
4. **Decide** (EA-2.6): level L1, so **hold**. The decision is written to the record with the reason `level_L1`.
5. **Review** (EA-5.2): the reviewer approves it unchanged. Outcome `approved`, not serious. The key now has 112
   judged actions and 1 serious error. Upper bound 4.9%, over 2%: it stays at L1.
6. **Later** (EA-3.4): at 280 judged refunds with still only 1 serious error, the upper bound falls to 2.0%, and the
   key is **promoted to L2**.
7. **At L2** (EA-2.8): the next refund passes its checks and **goes ahead**. After it executes, a 25% random draw
   selects it for a spot-check. The agent never knows.
8. **A slip** (EA-3.5): a carrier changes its process, and 4 of the next 20 spot-checked refunds are wrong. The
   lower bound of 4 in 20 is 8.1%, over 2%, so the key **steps down to L1** automatically.
9. **Recovery** (EA-4.2, EA-4.6): the corrections become a new rule and new tests. The new version passes 90% of its
   hidden refund tests, so it keeps its evidence, and climbs back once the bound holds again.
