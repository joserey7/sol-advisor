# Native operations

Use this for installation, selected-role checks, runtime evidence, and maintenance.
For native PowerShell equivalents see [windows.md](windows.md). Python 3.11+ is now
required on ALL platforms. POSIX and Windows wrappers share `native-support.py`; no
third-party Python packages, nested Codex sessions, or configuration edits are needed.

## Install or check the bundle

From a reviewed repository checkout:

~~~sh
sh plugins/sol-advisor/scripts/install-agents.sh
sh plugins/sol-advisor/scripts/install-agents.sh --check
# Optional profile installation; NOT authorization to use Astra:
sh plugins/sol-advisor/scripts/install-agents.sh --with-astra
~~~

From an installed skill resolve its helpers, not the working repository:

~~~sh
skill_dir=<directory-containing-this-SKILL.md>
helper="$skill_dir/../../scripts/native-support.py"
installer="$skill_dir/../../scripts/install-agents.sh"
~~~

The default target is `$CODEX_HOME/agents`, or `$HOME/.codex/agents` on POSIX and
`$USERPROFILE/.codex/agents` on Windows. `--target-dir` overrides it. Do not change homes
or fall back to WSL when preflight fails. Restart the task so native roles are discovered.

Default install and `--check` cover `luna`, `sol-implementer`, and `sol` (reviewer).
`--with-astra` includes the optional profile. An absent or conflicting unselected Astra
source/destination cannot block the core installation. Updating core roles leaves a
previously opted-in Astra file untouched; use `--with-astra` to update/check that bundle.
Availability in the host must still be verified at runtime.

## Migration safety

`scripts/role-registry.json` is the single metadata registry. Active role names, model
IDs, effort, optional status, and read-only requests must match shipped TOMLs.

Only byte-exact recognized historical Luna/Sol files are migrated. v0.2.0/v0.5.0/v0.6.0
fingerprints and the released v0.6.0 CRLF variants are retained; v0.7.0 LF profiles are
added. Modified or unsafe active selected files fail before any installation changes.
New/current CRLF files are not silently normalized. Keep historical fixture bytes intact.

Known exact Terra profiles are archived as
`<agents-parent>/sol-advisor-retired/sol-advisor-terra-implementer.toml.<sha256>.bak`,
outside native agent discovery. An existing identical archive is reusable; conflicting
or linked archives fail preflight. Customized, unreadable, or unsafe Terra files are
preserved with a warning and never selected by this workflow. Move those files outside
agent discovery manually after reviewing them; preserving them does not disable them
for other Codex workflows. Checks never retire or write files.

All selected destinations and the retirement archive are preflighted before writes.
The installer rejects links/junctions in destination directory chains, stages complete
bytes on the same filesystem, rechecks destinations, and verifies the result. It does
not edit `config.toml`, erase custom profiles, or rewrite legacy fingerprint history.
Do not run concurrent installs or edits to the agent directory: multi-file installation
is not transactional. An I/O failure after publication may leave a partial update;
rerun checks and the installer, never overwrite a reported customization blindly.

## Confirmed plan validation

Before an auxiliary spawn, validate the confirmed plan from stdin. Normal solo needs
no helper calls. The validator makes no model calls and changes no files:

~~~sh
printf '%s\n' '{"mode":"delegate","difficulty":"bounded","risk":"contained","worker":"luna","delegation_benefit":"Execute repetitive edits without duplicating primary work"}' |
  python3 "$helper" check-plan
~~~

The output contains `companion_checks`, a checklist, NOT spawn order. In full, review
happens after implementation and primary verification. Authorized Astra advice happens
at the decision point, not automatically after the other roles.

`difficulty` is `bounded` or `judgment-heavy`. `risk` is `contained` or `material`.
Material risk requires audit/full. Delegate/full requires a worker and a concrete
`delegation_benefit`. Full also requires `full_justification`. Solo/audit has no worker.
Judgment-heavy delegated implementation requires `sol-implementer`, not forced Luna
retries. See role-contracts.md for the packets.

To select Astra, add an `astra` object with `decision`, `trigger`, `user_authorization`,
`evidence`, `counterevidence`, `alternatives`, `required_checks`, and integer
`consultation_number`. All text fields must be nonempty. A number greater than one
requires `renewed_authorization: true`. The helper checks declared fields, not whether
approval actually exists; verify the user's instruction. See astra-advice.md.

## Selected-role preflight and spawn

| Route | Required companion checks |
|---|---|
| solo | None |
| delegate, Luna | `--check-role luna` |
| delegate, Sol | `--check-role sol-implementer` |
| audit | `--check-role sol` |
| full, Luna | `--check-role luna --check-role sol` |
| full, Sol | `--check-role sol-implementer --check-role sol` |
| Authorized decision advice | Add `--check-role astra` |

`--check-role` is repeatable and implies non-mutating `--check`. Do not combine it with
`--with-astra`. Unknown roles fail, including the retired `terra` selector. Cache checks
only within the task; invalidate after install/update, role/config changes, or route
changes affecting selected roles. Do not preflight unavailable, unselected models.

~~~sh
sh "$installer" --check-role luna
~~~

Spawn exact native types from role-contracts.md using `fork_turns: none`, with no model
or effort overrides. Primary Sol cannot delegate its architecture/acceptance authority.

## Runtime evidence and observed isolation

Public spawn/details metadata is authoritative. For model or effort fields it omits,
inspect only the exact thread ID using the local helper; never replace visible public
evidence. If both sources exist they must agree. The inspector is not a model fallback.

~~~sh
python3 "$helper" inspect --expect-role luna <native-thread-uuid>
# Explicit hard-isolation check when required:
python3 "$helper" inspect --expect-role sol --require-read-only <review-thread-uuid>
~~~

`--sessions-dir` supports disposable fixtures. The inspector searches exact rollout
filename suffixes, reads only the matched session, prints allowlisted routing fields,
and rejects ambiguous/missing/conflicting evidence. It does not print messages, tokens,
environment variables, full configuration, or arbitrary rollout text.

The `sol` reviewer and `astra` advisor request read-only isolation. Record actual sandbox
and permission profile types. Observed read-only permits an enforced-isolation claim.
A broader host policy permits proceeding only when hard isolation is not required,
behavioral read-only is explicit, and the primary captures and verifies exact before/
after repository AND artifact state including new/untracked files. Avoid concurrent
edits during that snapshot interval. Report broader policy as residual risk. Unobservable
isolation, required-but-absent hard isolation, or any mutation stops the lane; do not
silently repair a mutation and keep the verdict. Parent verification is mandatory.

## Maintenance

~~~sh
sh plugins/sol-advisor/scripts/verify.sh
python3 -m unittest discover -s tests -v
git diff --check
~~~

The portable suite replaces duplicated shell fixtures while retaining historical bytes,
install safety, role-scoped checks, runtime privacy, and CLI coverage. Windows CI also
runs `tests/verify-windows.ps1` under PowerShell 5.1/7 and Python 3.11/3.13. Passing these
tests does not prove native model access, actual sandbox inheritance, agent obedience,
or cost savings. Complete [evaluation.md](evaluation.md) before publishing the next release.
