# Research: the Trust Gym

*Informative. The evidence behind the Earned Autonomy specification.*

The Trust Gym is the test bench used to check whether the framework's rules actually work, and whether common advice
about deploying AI agents holds up. Every round was **pre-registered**: the hypotheses, metrics and pass thresholds were
written and committed before any code or data for that round existed. Results are reported whether they passed or
failed, and several recommendations were dropped because they failed.

## How pre-registration works here, and how to check it

1. **Before a round:** a `PREREG*.md` file states the hypotheses and pass thresholds. It is committed and tagged
   (`research/prereg`, `research/prereg-v1`, …).
2. **During a round:** every choice the pre-registration didn't settle is logged in [DECISIONS.md](DECISIONS.md)
   *before* the results it affects. Corrections found later are logged as dated entries; nothing earlier is edited.
3. **After a round:** a `REPORT*.md` gives every verdict (PASS, FAIL, MIXED or INCONCLUSIVE) against the pre-registered
   thresholds. Anything decided after seeing results is labelled *exploratory*.

To check a round yourself, list when its pre-registration, code and report first appeared:

```bash
git log --full-history --diff-filter=A --format='%h %ad %s' --date=iso -- PREREG-v1.md gym/engine_v1.py REPORT-v1.md
#  2408260 2026-10-15 18:35:44  v1: REPORT-v1.md
#  5dd32b4 2026-10-15 18:34:33  v1: carry-over, … (the code)
#  ee4b408 2026-10-15 18:31:52  v1: prereg (before any v1 code)
git show --stat research/prereg-v1      # the tagged commit holds only the pre-registration
```

The research was merged into this repository with its full history, so these commands work here. The files sat at
the top level before the merge, which is why the paths above have no `research/` prefix.

**Limit of this check:** commit dates are set by the machine that made the commit. Independent timestamping is on the
[launch checklist](../docs/launch-checklist.md).

## Data tiers

| Tier | What it is | Ground truth |
|---|---|---|
| **T1 Simulated** | Simulated organisations whose agents have a known, hidden error rate per task type that changes over time (steady, learning, drifting, a bad update, a defector) | Exact |
| **T2 Generated** | 6,000 tasks across six agent types (customer service, workshop bookings, IT service desk, accounts payable, outbound follow-up, data operations), done by real AI agents with tools. Each task's correct outcome was fixed in code before an AI wrote the customer's message | Seeded |
| **T3 Public anchor** | Conversations from τ²-bench, a public customer-service benchmark | Programmatic |

No customer data was used.

## Rounds

| Round | Date | Question | Pre-registration | Verdicts | Headline | Spend (USD) | Report |
|---|---|---|---|---|---|---|---|
| v0 | 15 Oct 2026 | Does earned trust work, and does the standard advice hold? | `research/prereg` | 8 pass · 8 fail · 5 mixed · 1 inconclusive | Earned trust let through 66–69% fewer serious mistakes than checks alone; narrow tools cut wrong actions 73%; several common recommendations failed | 8.55 | [REPORT.md](REPORT.md) · [PREREG.md](PREREG.md) |
| v1 | 15 Oct 2026 | Do the revisions fix v0's failures? | `research/prereg-v1` | 2 pass · 2 mixed · 2 fail; peer routing split (1 pass, 1 fail) | Keeping trust across tested versions works (0% → 36% of task types promoted); pooling and risk-label thresholds made things worse | 0 | [REPORT-v1.md](REPORT-v1.md) · [PREREG-v1.md](PREREG-v1.md) |
| v2 | 16 Oct 2026 | Do consequence levels, reviewer trust and knowledge-edit versions work? | `research/prereg-v2` | 1 pass · 1 mixed · 4 fail | Consequence levels work; evidence shouldn't fade; success is an alert, not a gate | 0 | [REPORT-v2.md](REPORT-v2.md) · [PREREG-v2.md](PREREG-v2.md) |
| v3 | 16 Oct 2026 | Confirmation of v2's fixes on fresh seeds | `research/prereg-v3` | 2 pass · 1 fail | Reviewer trust and the 60-day re-entry rule confirmed; carry-over safe but only as good as the hidden tests. Reference numbers for the framework | 0 | [REPORT-v3.md](REPORT-v3.md) · [PREREG-v3.md](PREREG-v3.md) |
| Platform | 18 Oct 2026 | Does a commercial agent platform's own safety layer add to it? | `research/prereg-10x` (+ `-d`, `-k`) | 1 pass · 2 mixed · 3 fail | The platform as-is did slightly worse than a minimal agent; adding narrow tools and the learning loop gave the safest agent measured (82–87% fewer serious mistakes) | 43.13 | [REPORT-10x.md](REPORT-10x.md) · [PREREG-10x.md](PREREG-10x.md) |
| v4 | 18 Oct 2026 | Statistics under continuous checking, mis-tagging attacks, agents that behave only when watched | `research/prereg-v4` | 1 mixed · 4 fail (failures traced to a mis-specified metric and an incident channel that defeats the criterion) | Hidden, random spot-checks are essential; a tool floor blocks mis-tagging; a strict promotion bound is optional | 0.004 | [REPORT-v4.md](REPORT-v4.md) · [PREREG-v4.md](PREREG-v4.md) |

Total new spend: about USD 51.7. Rounds marked 0 reused earlier data or ran in simulation only.

## Honest limits

- **Synthetic only.** No real customers or real reviewers yet. A pilot is the next step.
- **We built the bench.** We wrote the task generator, the agents' policies, the checks and the grader. Independent
  tasks and grading would make the evidence stronger.
- **Mostly one model** (DeepSeek v4 Flash), with a brief comparison to Claude Haiku 4.5 on τ²-bench.
- **The grader was corrected after the pre-registered hand-check** in v0. The original strict verdicts are kept beside
  the corrected ones, and the correction is logged in [DECISIONS.md](DECISIONS.md).
- **Simulated reviewers** follow an assumed model of attention and complacency.
- **Exploratory findings** (labelled in each report) need a pre-registered confirmation before they count as tested.

## Re-running

The code is plain Python 3.11. From this folder, the simulation tier runs for free in a few minutes:

```bash
python -m t1.run 200 && python -m t1.peer   # T1 simulation
python analyze.py && python analyze_t2.py     # v0 verdicts from the committed T2 and T3 data
python analyze_v3.py                          # v3 reference numbers
```

Re-running the generated-task tier (T2) needs an OpenRouter API key and a spending cap (see each runner's budget
guard).

## Notes

- [SPEC.md](SPEC.md) in this folder is a **historical snapshot** (v0.2) kept for the record. The current specification
  lives in [/spec](../spec/README.md).
- The platform round ([REPORT-10x.md](REPORT-10x.md)) describes a commercial agent platform's internals. Public copies
  will be sanitised; see the [launch checklist](../docs/launch-checklist.md).
- Pre-registrations and reports are never edited after the fact. Corrections are added as new, dated entries.
