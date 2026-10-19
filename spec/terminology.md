# Terminology

The defined terms used throughout the specification. Field names in the data model match these terms in
`snake_case`. Abbreviations aren't used, except the level labels below and standard acronyms (AI, API, ID, UTC).

| Term | Definition |
|---|---|
| **Action** | Anything an agent does that changes something outside itself: sending a message, calling a write tool, updating a record, booking, paying, deleting, or delegating to another agent. Reading is not an action. A reply is one kind of action. |
| **Proposed action** | An action the agent wants to take, captured before it happens. The framework governs proposed actions only. |
| **Agent** | An AI system that proposes actions on behalf of an organisation. |
| **Agent version** | An immutable snapshot of everything that determines an agent's behaviour: instructions, model, tools and tool scope, rules, checks and knowledge. Any change to any of these is a new version. |
| **Organisation** | The business an agent works for. Trust is never shared between organisations. |
| **Task type** | A catalogue entry describing one kind of action, with a name, a description, example requests, allowed tools and a consequence level. Trust is tracked per task type. |
| **Task catalogue** | The set of task types an organisation's agents may perform. Part of the policy. |
| **Trust key** | The triple (organisation, agent, task type). All trust state belongs to one trust key. |
| **Trust level** | A trust key's position on the ladder: L1 Supervised, L2 Trusted or L3 Senior. See [levels](levels.md). |
| **L0 Observe** | A deployment choice, not a level the engine assigns: the agent may tag and suggest but not propose actions. |
| **Consequence level** | How costly a mistake in a task type would be: C1 Low, C2 Moderate, C3 High or C4 Critical. It sets the error bar. See [levels](levels.md). |
| **Error bar (ε)** | The highest serious-error rate a task type may have and still be trusted, e.g. 0.05. Set by the consequence level. The field name is `error_bar`; ε is its symbol in formulas. |
| **Checks** | Deterministic rules run on every proposed action before it happens, e.g. "the refund equals the order total". The caller runs them; the engine reads the result. |
| **Decision** | The engine's answer for one proposed action: hold (a person reviews it first) or act (it goes ahead), with the reasons. |
| **Hold** | The action waits for a person to approve, edit or reject it. |
| **Act** | The action goes ahead without a person approving it first. |
| **Judged action** | An action a person (or an authorised verifier) has judged: before it happened (pre-review), afterwards (spot-check) or through an incident. Only judged actions are evidence. |
| **Outcome** | The judgement of one action: `approved`, `cosmetic_edit`, `material_edit`, `rejected` or `incomplete`, with a reason code for edits and rejections. |
| **Serious error** | An outcome labelled `material_edit` or `rejected` with a non-cosmetic reason code, or any incident. Only serious errors count against trust. |
| **Incomplete** | A harmless outcome that didn't achieve the action's goal. Tracked for alerts; not a serious error. |
| **Task success** | The share of judged actions that achieved their goal. Monitored, not a promotion gate. |
| **Incident** | A serious problem with an executed action, found after the fact by anyone. |
| **Challenge** | A request by an affected customer or staff member for a person to review an executed action. |
| **Spot-check** | A review, after the fact, of an action the agent took on its own, selected at random. |
| **Canary** | A known-bad item placed in a review queue to check that reviewers catch it. |
| **Second check** | A second reviewer's judgement of a first reviewer's decision, used to measure reviewers. |
| **Upper bound** | The highest error rate that still plausibly explains the evidence (95% confidence by default). Promotion needs it to be under the error bar. |
| **Lower bound** | The lowest error rate that still plausibly explains recent evidence. A step-down happens when it is over the error bar. |
| **Promotion** | Moving a trust key up one level. |
| **Step-down** | Moving a trust key down one level. |
| **Carry-over** | Keeping a trust key's evidence when the agent's new version passes its hidden tests. |
| **Version discount** | Halving a trust key's evidence when a new version doesn't pass its hidden tests. |
| **Training test** | A test the agent, and whoever improves it, may see. |
| **Hidden test** | A test the agent and whoever improves it can never see, used to judge new versions. |
| **Seeded hidden test** | A hidden test written for a version from a realistic request, not from a correction. |
| **Correction** | A person's fix to an agent's action; it becomes a draft rule and a draft test. |
| **Tool floor** | The lowest consequence level an action can have if it calls a given write tool. |
| **Write tool** | A tool that changes something outside the agent. Tools that only read are not write tools. |
| **Trust record** | The permanent, append-only, tamper-evident log of every proposed action, decision, outcome, incident, version, policy change and governance request. It holds references and labels, not customer content. |
| **Sequence number** | An entry's position in the trust record's hash chain: the record's order of truth. |
| **Policy** | The versioned rules an organisation applies: task catalogue, error bars, caps, sample rates and roles. |
| **AI owner** | The business person accountable for the agents in an area, such as a team lead or department head. Owns the task catalogue and the consequence levels. |
| **Policy owner** | Sets error bars, caps, tool scope and sample rates. |
| **Reviewer** | Judges agents' actions. |
| **Auditor** | Reads everything; changes nothing. |
| **Builder** | Creates and changes agent versions. |
| **Governance guard** | The component that allows or blocks every change to policy, trust or tests, and logs every request. |
| **Delegation** | One agent handing an action to another agent. |
