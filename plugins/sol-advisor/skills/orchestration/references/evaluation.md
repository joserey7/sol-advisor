# GPT-6 release validation and measurement

## Scope and source checks

v0.8.0 was published on 2026-09-22 after the release checklist. Its initial
pins are Sol xhigh (primary, demanding implementation, review), Luna max (bounded
implementation), and optional Astra high (decision advice). These settings preserve
the previous reasoning policy where practical; they are not a measured optimum.

Official references checked on 2026-09-22:
- [GPT-6 Sol model and supported effort](https://developers.openai.com/api/docs/models/gpt-6-sol)
- [GPT-6 Luna model and supported effort](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [GPT-6 Astra model and supported effort](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Native Codex subagents and configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Public documentation does not establish account access or observed runtime configuration.
No benchmark here proves Luna equals old Terra or that a lower effort costs less overall.

## v0.8.0 release verification

On 2026-09-22, the portable suite passed 54 tests locally (five Windows skips for
unavailable symlink privileges or the POSIX-only wrapper). The PR's POSIX verifier
and four Windows CI combinations of PowerShell 5.1/7 and Python 3.11/3.13 passed.
`git diff --check` was clean.

A native Windows smoke run covered a clean core install, exact released v0.7.0
upgrade, Terra archival, preservation of customized Terra, refusal of a conflicting
Luna profile before writes, and optional Astra installation in a disposable target.
The normal installation left Astra absent.

A disposable native Codex task observed Sol/xhigh as primary and exercised `solo`,
Luna/max `delegate`, Sol/xhigh `delegate`, `audit`, and `full`. Selected-role checks
and declared-plan validation passed. Fresh Sol/xhigh reviews in `full` returned
`fix-first` for fixture defects; after Luna corrections and primary verification,
a new review returned `ship` for the fixture's explicit bounded contract. All
reviewers received fresh context. Astra was not consulted.

The reviewers requested read-only access, but this Windows host applied
`workspace-write` / `managed`. Before/after manifests of tracked and untracked
files were identical during each review, so behavioral read-only was observed;
enforced read-only isolation was not. Check the effective host policy on each run
and require hard isolation when the task needs it. Cost and quality comparisons
for later routing changes remain unmeasured.

## Release checklist

1. Run the portable suite, shell syntax/whitespace checks, and all native Windows CI jobs.
   Test clean install, released v0.7.0 upgrade, historical CRLF migration, customized
   profile refusals, preserved custom Terra, optional Astra absence, and repeated install.
2. On a disposable native Codex task, confirm primary Sol/xhigh and each selected role's
   observed model/effort. Exercise solo, Luna delegate, Sol delegate, audit, and full.
   Check fresh contexts, primary verification, fix-first re-review, and actual isolation.
3. Verify no Astra use or required installation on ordinary routes. Test absent/declined
   authorization. Run a LIVE Astra consultation only with separate explicit user approval;
   schema fixtures do not constitute consent to spend. Verify repeats require renewed consent.
4. Record remaining gaps and results before publishing. Do not mark a release validated
   solely because static tests passed. Do not alter the published v0.7.0 tag.

## Compare delivery cost, not agent counts

Use the same starting commit and acceptance criteria in separate worktrees/tasks. Include
small fixes, repetitive bounded edits, a cross-module feature, a concurrency bug, and a
permissions/data migration change. Compare Sol-only versus selective Luna/Sol; compare
Sol high versus xhigh in a separate experiment so variables are not conflated. Include
Astra only for qualifying decisions, never to inflate the common path.

Record task/category, base commit, selected route, actual model/effort, context supplied,
observed token/credit usage if exposed, time to accepted result, primary verification,
review findings, retry/correction counts, user interventions, and later regressions.
Use repeated trials when practical. Label unavailable usage as unavailable; do not derive
subscription quota or dollar cost from the number of agents. Include discovery, handoff,
verification, review, and rework in total cost per ACCEPTED change. Preserve hard quality
criteria; a cheaper failed delivery is not a saving.

Astra may improve a decision without making the whole task cheaper. Record what changed
and which evidence supports that attribution, distinguishing inference from observation.

## Rollback

Keep a reviewed v0.7.0 checkout and backups of personalized profiles. Rolling back the
plugin alone does not downgrade GPT-6 agent files automatically: v0.7.0 correctly treats
new profiles as conflicts. Move reviewed v0.8.0 profiles outside discovery, restore the
matching released v0.7.0 profiles (including archived Terra), reinstall that version,
and start a fresh task. Never overwrite custom profiles merely to make a check green.
