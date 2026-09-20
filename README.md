# Sol Advisor

**Sol / xhigh runs the show. It declares a risk-gated route before task tools, keeps
solo as the default, and uses a single auxiliary only when that improves delivery.**

Sol Advisor is a Codex-only workflow for capability-routed software delivery. You
bring the goal and constraints; Sol owns the plan, implementation or delegation,
verification, and acceptance.

## Go deeper

I write [**Attention Heads**](https://attentionheads.substack.com/?utm_source=github&utm_medium=readme&utm_campaign=sol-advisor) — deep, evidence-backed writing on AI, cognition, and agentic engineering. The **Agentic Engineering Field Notes** series is where I publish practical advice on the craft of using AI. [Subscribe](https://attentionheads.substack.com/subscribe?utm_source=github&utm_medium=readme&utm_campaign=sol-advisor) to get new posts to your inbox.

## Quick start

This fork preserves Daniel McAteer's [upstream project](https://github.com/DannyMac180/sol-advisor) and adds native Windows support.

You need a current Codex CLI with plugins and native custom-agent support; use the
same Codex home as Codex Desktop. Select GPT-5.6 Sol / xhigh in the primary session.
Luna / Max or Terra / Max access is needed only when the selected route delegates.

### Windows (native PowerShell)

Requires PowerShell 5.1+ and Python 3.11+; no Bash, WSL, or jq. From a reviewed clone
of this fork, run the following to register the plugin and install its companion roles:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1
~~~

See the [Windows installation and troubleshooting guide](plugins/sol-advisor/skills/orchestration/references/windows.md).
The execution-policy option applies only to this process. Do not change a managed policy.

### macOS / Linux (POSIX shell and jq)

~~~sh
codex plugin marketplace add joserey7/sol-advisor --ref main
codex plugin add sol-advisor@sol-advisor-joserey7
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "sol-advisor@sol-advisor-joserey7") | .source.path')" && test -n "$plugin_dir" && test "$plugin_dir" != null && test -d "$plugin_dir" && test -f "$plugin_dir/scripts/install-agents.sh" && sh "$plugin_dir/scripts/install-agents.sh"
~~~

The companion installer verifies all three exact role files after installation. It is
fail-closed: modified, unsafe, nonregular, symlinked, unknown, or differing files
are left untouched. It does not edit Codex configuration. Start a fresh Codex task
after installation so native roles are discovered.

Use this one prompt in the new task:

~~~text
Use $sol-advisor:orchestration to build this feature and verify it. Declare the selective route before task tools.
~~~

## What you do

Give Sol the outcome, constraints, and any important repository context. You do not
need to select or manage a lane; Sol records the route and owns verification and
acceptance.

## Routes

| Mode | Use it when | Delivery |
|---|---|---|
| `solo` | Default; risk is contained. | Root plans, implements, tests, and self-reviews. |
| `delegate` | A complete spec is better executed by one implementer. | Luna / Max for bounded work, or Terra / Max for judgment-heavy or high-risk work; root verifies. |
| `audit` | Independent final scrutiny matters more than delegation. | Root implements; a fresh read-only Sol / xhigh reviews. |
| `full` | Explicit broad or high-risk exception. | One selected implementer, root verification, and a fresh Sol / xhigh review. |

Solo is the default. One auxiliary is the default maximum; `full` is the explicit
exception. Sol emits a `SELECTIVE ROUTE` declaration with the mode and concise risk
rationale before the first task tool call. It can escalate only when newly observed
risk justifies it and never silently downgrades.

## What happens automatically

Sol / xhigh keeps architecture, decomposition, route selection, parent verification,
escalation decisions, and acceptance in the primary task. Auxiliary work substitutes
for root work; it does not duplicate it. The root inspects the complete diff and
reruns the requested checks. When the selected route includes a review, a fresh Sol /
xhigh reviewer returns ship, fix-first, or rethink; any fix requires a new review.

## Updating

On Windows, run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-plugin.ps1 -Update`.
On macOS/Linux, update the plugin and companion roles below. Then start a new task:

~~~sh
codex plugin marketplace upgrade sol-advisor-joserey7
codex plugin add sol-advisor@sol-advisor-joserey7
plugin_dir="$(codex plugin list --json | jq -r '.installed[] | select(.pluginId == "sol-advisor@sol-advisor-joserey7") | .source.path')" && test -n "$plugin_dir" && test "$plugin_dir" != null && test -d "$plugin_dir" && test -f "$plugin_dir/scripts/install-agents.sh" && sh "$plugin_dir/scripts/install-agents.sh"
~~~

For exact spawn, runtime-evidence, sandbox, installer, and maintainer verification
details, read [advanced native operations](plugins/sol-advisor/skills/orchestration/references/operations.md).
For local development, install this checkout as a marketplace:

~~~sh
cd /absolute/path/to/sol-advisor
codex plugin marketplace add /absolute/path/to/sol-advisor
codex plugin add sol-advisor@sol-advisor-joserey7
~~~
