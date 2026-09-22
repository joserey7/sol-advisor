# Native role contracts

The source of pin metadata is `scripts/role-registry.json`; shipped TOMLs must match.
The primary is GPT-6 Sol / xhigh. All auxiliary spawns use fresh context and no per-spawn
model or effort overrides. Use `fork_turns: none` with the exact `agent_type` below.

| Companion check key | Native agent type | Model / effort | Responsibility |
|---|---|---|---|
| `luna` | `sol_advisor_luna_implementer` | gpt-6-luna / max | Bounded implementation |
| `sol-implementer` | `sol_advisor_sol_implementer` | gpt-6-sol / xhigh | Judgment-heavy implementation |
| `sol` | `sol_advisor_sol_reviewer` | gpt-6-sol / xhigh | Fresh audit/full review |
| `astra` | `sol_advisor_astra_advisor` | gpt-6-astra / high | Optional authorized decision advice |

The `sol` check alias remains the reviewer for compatibility. It never means the Sol
implementer. No Terra role is selectable. Selected-role preflight and runtime evidence
are mandatory; see [operations.md](operations.md). Custom profiles do not launch nested
Codex CLIs or change global default-agent settings.

## Shared implementation packet

Read the affected source before deciding ownership. Replace every placeholder:

~~~text
OBJECTIVE
<Observable outcome and why it matters.>

FILES AND OWNERSHIP
You own only: <exact files or modules>.
Other agents or the user may be editing concurrently. Preserve their edits; do not
revert unrelated work. Stop and report any need to expand ownership.

INTERFACES
<Signatures, types, schemas, commands, and behavior that must remain compatible.>

CONSTRAINTS
<Settled architecture, conventions, safety boundaries, and excluded scope.>
Do not spawn agents or perform the primary's architecture work again.

VERIFICATION
Run: <exact command>; success: <concrete expected output>.
Inspect: <diff/artifact>; success: <concrete expected evidence>.

RETURN
IMPLEMENTATION REPORT
STATUS: complete | partial | blocked
OBJECTIVE: <one line>
CHANGES: <file-by-file actual diff>
VERIFIED: <commands and actual evidence; list checks not run>
JUDGMENT CALLS: <decisions left open by the specification, or none>
GAPS: <ambiguity, failed checks, incomplete work, or none>
~~~

Luna follows a bounded specification and surfaces complexity. Sol resolves difficult
implementation details within the settled architecture. Either may stop on missing
requirements; neither silently broadens scope. Sol is selected up front for known
judgment-heavy work; no mandatory Luna retry. For specification errors, amend the
contract rather than retrying unchanged instructions.

The primary inspects the complete diff, preserves concurrent work, and reruns checks.
Delegation substitutes for primary execution; it does not duplicate it. In `solo` and
`audit`, the primary implements directly. In `delegate` and `full`, one selected worker
implements. Only `audit` and `full` add a final fresh reviewer.

## Fresh review packet

After primary verification, spawn exactly:

~~~text
agent_type: sol_advisor_sol_reviewer
fork_turns: none
~~~

~~~text
ROLE
Fresh final reviewer. Strictly read-only: no edits, fixes, formatting, new files, or
scope expansion. Do not run commands that mutate caches/artifacts; use parent evidence.

STATED GOAL
<User's requested outcome and acceptance criteria.>

ACCUMULATED CHANGE SET
<Exact allowed files and explicit base/head revisions, or the complete working-tree
diff including untracked/new files. Inspect the actual files, not just a summary.>

INTERFACES AND CONSTRAINTS
<Compatibility, invariants, safety boundaries, and excluded scope.>

VERIFICATION EVIDENCE
<Commands and actual primary-session output; artifacts inspected; checks not run.>

REVIEW
Assess correctness, completeness, regressions, ownership, tests, and material risk.

SOL REVIEW
VERDICT: ship | fix-first | rethink
REASON: <decisive evidence-based reason>
FINDINGS: <precise file references and required fixes, or none>
RESIDUAL RISK: <remaining risk and verification gaps, or none>
~~~

Every correction after a verdict invalidates it. In audit the primary fixes; in full
the selected implementer fixes. The primary re-verifies, then obtains a new fresh
review of the accumulated change set. The reviewer never fixes its own findings.
Sol reviewing Sol is context-clean, not cross-model-family independence.

## Exceptional advice

Use `sol_advisor_astra_advisor` with `fork_turns: none` only after the authorization,
packet, and isolation checks in [astra-advice.md](astra-advice.md). It is advisory, not
a substitute reviewer. A decision consultation happens when needed before committing
to the affected implementation, not automatically at the end of every delivery.
