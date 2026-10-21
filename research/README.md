# Research: the Trust Gym

*Informative. The evidence behind the Earned Autonomy specification and guides.*

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

Each round is labelled **trust** (does the framework measure, decide and oversee correctly?) or **implementation** (how
to build agents that make fewer mistakes, outside the standard).

| Round | Kind | Date | Question | Pre-registration | Verdicts | Headline | Spend (USD) | Report |
|---|---|---|---|---|---|---|---|---|
| v0 | Trust | 15 Oct 2026 | Does earned trust work, and does the standard advice hold? | `research/prereg` | 8 pass · 8 fail · 5 mixed · 1 inconclusive | Earned trust let through 66–69% fewer serious mistakes than checks alone; narrow tools cut wrong actions 73%; several common recommendations failed | 8.55 | [REPORT.md](REPORT.md) · [PREREG.md](PREREG.md) |
| v1 | Trust | 15 Oct 2026 | Do the revisions fix v0's failures? | `research/prereg-v1` | 2 pass · 2 mixed · 2 fail; peer routing split (1 pass, 1 fail) | Keeping trust across tested versions works (0% → 36% of task types promoted); pooling and risk-label thresholds made things worse | 0 | [REPORT-v1.md](REPORT-v1.md) · [PREREG-v1.md](PREREG-v1.md) |
| v2 | Trust | 16 Oct 2026 | Do consequence levels, reviewer trust and knowledge-edit versions work? | `research/prereg-v2` | 1 pass · 1 mixed · 4 fail | Consequence levels work; evidence shouldn't fade; success is an alert, not a gate | 0 | [REPORT-v2.md](REPORT-v2.md) · [PREREG-v2.md](PREREG-v2.md) |
| v3 | Trust | 16 Oct 2026 | Confirmation of v2's fixes on fresh seeds | `research/prereg-v3` | 2 pass · 1 fail | Reviewer trust and the 60-day re-entry rule confirmed; carry-over safe but only as good as the hidden tests. Reference numbers for the framework | 0 | [REPORT-v3.md](REPORT-v3.md) · [PREREG-v3.md](PREREG-v3.md) |
| Production harness | Implementation | 18 Oct 2026 | Does a production agent harness's own safety layer add to the framework? | `research/prereg-10x` (+ `-d`, `-k`) | 1 pass · 2 mixed · 3 fail | The harness as-is did slightly worse than a minimal agent; adding narrow tools and the learning loop gave the safest agent measured (82–87% fewer serious mistakes) | 43.13 | [REPORT-10x.md](REPORT-10x.md) · [PREREG-10x.md](PREREG-10x.md) |
| v4 | Trust | 18 Oct 2026 | Statistics under continuous checking, mis-tagging attacks, agents that behave only when watched | `research/prereg-v4` | 1 mixed · 4 fail (failures traced to a mis-specified metric and an incident channel that defeats the criterion) | Hidden, random spot-checks are essential; a tool floor blocks mis-tagging; a strict promotion bound is optional | 0.004 | [REPORT-v4.md](REPORT-v4.md) · [PREREG-v4.md](PREREG-v4.md) |
| Contracts | Implementation | 21 Oct 2026 | Do rules learned from an agent's behaviour cut human minutes? | `research/prereg-contracts` | 1 pass · 1 mixed · 2 fail | Learned rules promoted on agreement alone locked in the agent's bad habits; gated by human-judged evidence they were safe but saved no review time | 0 | [REPORT-contracts.md](REPORT-contracts.md) · [PREREG-contracts.md](PREREG-contracts.md) |
| Core | Trust | 21 Oct 2026 | Can simple rules on lookup tables match the full framework? | `research/prereg-core` | 1 pass · 2 mixed · ablations reported | Eight simple rules (the seven Core rules plus planted test items for reviewers) matched the full framework on safety and on the multiple; the multiple was about 4.4–6.3 times; trust rules alone don't reach ten times | 0 | [REPORT-core.md](REPORT-core.md) · [PREREG-core.md](PREREG-core.md) |
| Playbooks | Implementation | 21 Oct 2026 | Are approved playbooks (the process as code, signed off once) safer and lighter on human time? | `research/prereg-playbooks` | 2 pass · 3 fail · 1 descriptive | Zero serious mistakes and zero actions triggered by hidden instructions on 1,800 tasks; human time fell 31% only when approval counted towards trust; model cost didn't fall | 0.67 | [REPORT-playbooks.md](REPORT-playbooks.md) · [PREREG-playbooks.md](PREREG-playbooks.md) |
| Calibration | Trust | 21 Oct 2026 | Do trust scores mean what they say, and what is non-review evidence worth? | `research/prereg-calibration` | 1 pass · 1 mixed · 2 fail | The trust score matches the promotion rule at a 0.975 threshold (99.9% agreement); it is cautious when evidence is thin; shadow comparison removes exposure but costs the manual work; replay gives more honest evidence, not faster trust | 0 | [REPORT-calibration.md](REPORT-calibration.md) · [PREREG-calibration.md](PREREG-calibration.md) |
| Dial | Trust | 21 Oct 2026 | Does oversight that follows the trust score raise the multiple over a fixed ladder? | `research/prereg-dial` | 2 pass · 1 fail | Equally safe and just as quick to catch regressions, but only +1–7% on the multiple: most human time goes on work still held for review, not on spot-checks | 0 | [REPORT-dial.md](REPORT-dial.md) · [PREREG-dial.md](PREREG-dial.md) |

Total new spend: about USD 52.4. Rounds marked 0 reused earlier data or ran in simulation only.

The production-harness round's files keep their original names (`REPORT-10x.md`, `PREREG-10x.md`, tag
`research/prereg-10x`), because pre-registrations and reports are never edited after the fact. They describe one
commercial agent platform's internals; see Notes.

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
- The production-harness round describes a commercial agent platform's internals. Its original files are kept exactly
  as written, to preserve the pre-registration record; public copies will be sanitised (see the
  [launch checklist](../docs/launch-checklist.md)).
- Implementation rounds inform the [implementation guide](../docs/implementation-guide.md), which is outside the
  standard. Trust rounds inform the [specification](../spec/README.md).
- Pre-registrations and reports are never edited after the fact. Corrections are added as new, dated entries.
