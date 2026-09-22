---
name: orchestration
description: "Codex-native selective delivery with GPT-6 Sol and Luna; explicitly authorized Astra decision advice is optional."
---

# Sol Advisor Orchestration

Own intent, architecture, route selection, verification, and acceptance in the primary
GPT-6 Sol / xhigh session. Default to `solo`; normally use at most one auxiliary.
Keep the four delivery modes `solo`, `delegate`, `audit`, and exceptional `full`.
Astra is an optional decision consultation, not a fifth mode or a routine pipeline step.

## Discover, then confirm

Before task tools, emit a provisional declaration, or a confirmed one when sufficient
evidence is already available:

~~~text
SELECTIVE ROUTE
phase: provisional | confirmed
mode: solo | delegate | audit | full
difficulty: bounded | judgment-heavy
risk: contained | material
worker: none | luna | sol-implementer
reason: <task-specific evidence and expected benefit>
~~~

Provisional discovery is bounded and read-only: locate the affected behavior,
interfaces, tests, and consequence risks. Do not implement, spawn agents, or expand
into an unbounded repository survey. Confirm the route before the first edit or spawn.
A provisional route can change in either direction as evidence improves. After
confirmation, record new evidence before changing the plan; do not silently remove a
required review. A material-risk review can be removed only with explicit user approval
and evidence that the risk was eliminated, not merely to save credits.

Verify primary model and effort through available runtime metadata. The required pin
is `gpt-6-sol` / `xhigh`. If unavailable, ask for user confirmation; if conflicting,
request the correct session and stop before implementation or delegation. A skill
cannot change the primary model. Never pretend metadata or access was observed.

## Separate capability, consequence risk, and delegation benefit

Use Luna / max for fully specified bounded work. Use Sol / xhigh for judgment-heavy
implementation within settled architecture. Volume alone does not require Sol;
small changes can still have material consequences. Terra is retired, never a fallback.

- `solo`: primary plans, implements, tests, and self-reviews; no delivery auxiliary.
- `delegate`: one Luna or Sol implementer executes; primary verifies. Use only when
  delegating replaces meaningful work or context, and consequence risk is contained.
- `audit`: primary implements and verifies, then a fresh read-only Sol reviews.
- `full`: explicitly justified broad or material-risk exception: one implementer,
  primary verification, then fresh read-only Sol review.

Material consequence risk requires `audit` or `full`, regardless of diff size or worker
model. Consider data loss, permissions, irreversible migrations, cross-cutting
invariants, reversibility, and verification strength. Delegation is not obligatory:
when the primary already has the context, direct Sol implementation may be cheaper.
Do not create permanent explorer/tester/planner chains or duplicate worker execution.

## Delegate with a complete contract

Read [role-contracts.md](references/role-contracts.md) before the first delegation.
Use [operations.md](references/operations.md) for selected-role checks, the confirmed
plan validator, exact spawn syntax, runtime evidence, and observed isolation. On native
Windows use [windows.md](references/windows.md); never fall back to WSL or another home.
Resolve helpers from the installed skill, not the working repository.

Before any auxiliary spawn, validate the declared confirmed plan with `check-plan` and
preflight only its selected roles. Normal solo needs no companion checks. The validator
checks declarations, not their truth; verify actual user authorization and evidence.
Missing, conflicting, unsafe, unavailable, or unobservable selected model/effort/role
stops that lane. Never silently substitute. Installation is not proof of model access.

Every worker packet contains OBJECTIVE, FILES AND OWNERSHIP, INTERFACES, CONSTRAINTS,
VERIFICATION, and the structured implementation return. Preserve concurrent edits and
exact ownership. The primary inspects the actual accumulated diff, scope, and artifacts,
and reruns requested verification. Worker reports are claims, not acceptance evidence.

New complexity can justify moving from Luna to Sol immediately; do not force failed
retries. Correct a specification error with a precise amended contract. Do not repeatedly
retry an unchanged plan. A separate Sol implementer is not the final Sol reviewer.

## Review without duplication

For `audit` and `full`, after primary verification, spawn a new Sol / xhigh reviewer
with fresh context. It inspects the complete accumulated diff and remains read-only.
Use observed permissions, not requested permissions. Return `ship`, `fix-first`, or
`rethink`. A reviewer never implements its own findings. A Sol review is context-clean,
not cross-model-family independence.

`fix-first`: primary fixes in audit, selected implementer fixes in full. Re-verify and
obtain a new fresh review. Any implementation correction invalidates the prior verdict.
`rethink`: revise the design; do not claim completion. Solo/delegate receive no fresh
review unless a declared route change requires one. Never report unrun checks as passed.

## Consult Astra only by explicit exception

Astra / high is off by default and not installed with the core roles. Read
[astra-advice.md](references/astra-advice.md) before proposing its use. Require explicit
user authorization for one bounded consequential decision and consultation. Installation,
model availability, full mode, task size, or ordinary failed tests are not authorization.

Qualifying triggers: consequential irreversible uncertainty, a structural disagreement,
or an evidence-backed diagnostic blocker. Do not force Luna/Sol failures first when the
risk is already clear. Provide alternatives, constraints, evidence and counterevidence,
and required checks; no undirected whole-repository review.

Astra remains read-only, never implements, never spawns agents, and never replaces a
required Sol review. Sol retains the decision and acceptance. A repeat consultation
requires renewed explicit authorization. Its additional auxiliary is a recorded exception
to the normal limit. One consultation can contain multiple model calls: this is a
workflow authorization policy, not a hard token/credit cap or an enforced sandbox.
If Astra is declined or unavailable, continue safely with Sol only where the uncertainty
permits; otherwise report the unresolved decision without claiming completion.
