# 🤖 Copilot Agent Flow (Dungeon Project)

This repository is designed to pilot GitHub Copilot coding agent for a C# console TUI dungeon game. Implementation work will be delivered by Copilot via PRs; local agents (Claude/GPT) curate issues, instructions, and reviews.

## Principles
- One small RFC per issue/PR. Keep tasks narrowly scoped with explicit acceptance criteria.
- Assign issues to Copilot via GraphQL only (required to trigger the agent).
- Copilot works on branches named `copilot/*` and opens exactly one draft PR per task.
- PRs must build and pass CI; no warnings. Human review required before merge.
- If a run fails, apply removal chain then retry: workflow → PR → issue; re-create the issue and re-assign Copilot.

## Files that guide Copilot
- `.github/copilot-instructions.md` – build/test steps, PR/branch rules.
- `.github/instructions/**/*.instructions.md` – path-scoped rules (add as needed).
- `**/AGENTS.md` – these instructions; may be nested per subproject.
- `docs/agent-flow/AGENT_FLOW.md` – detailed flow with GraphQL queries and scripts.

## Issue & PR rules
- Title: `Game-RFC-XXX: Short title` (or Flow-RFC for workflow work)
- Labels: `rfc`, `agent`
- PR title: `Implement Game-RFC-XXX: Short title`
- PR body: include acceptance checklist and `Closes #<issue-number>`

## CI
- Minimal CI validates build/tests on PRs. Copilot should fix issues until green.

## Retry policy
- If the Copilot Actions run fails or stalls, use cleanup scripts to:
  1) cancel/delete latest workflow runs for the PR branch,
  2) close the PR,
  3) close the issue (cannot delete via API),
  4) re-create the issue and re-assign Copilot.

See `docs/agent-flow/AGENT_FLOW.md` and `scripts/agent/*.ps1`.# 🤖 Copilot Agent Flow (Dungeon Project)

This repository is designed to pilot GitHub Copilot coding agent for a C# console TUI dungeon game. Implementation work will be delivered by Copilot via PRs; local agents (Claude/GPT) curate issues, instructions, and reviews.

## Principles
- One small RFC per issue/PR. Keep tasks narrowly scoped with explicit acceptance criteria.
- Copilot-assigned issues are created and assigned via GraphQL only.
- Copilot works on branches named `copilot/*` and opens exactly one draft PR per task.
- PRs must build and pass CI; no warnings. Human review required before merge.
- If a run fails, apply removal chain then retry: workflow → PR → issue; re-create the issue and re-assign Copilot.

## Files that guide Copilot
- `.github/copilot-instructions.md` – build/test steps, coding conventions, PR/branch rules.
- `.github/instructions/**/*.instructions.md` – path-scoped rules (add as needed).
- `**/AGENTS.md` – these instructions; may be nested per subproject.
- `docs/agent-flow/AGENT_FLOW.md` – detailed flow with GraphQL queries and scripts.

## Issue & PR rules
- Title: `Game-RFC-XXX: Short title` (or Flow-RFC for workflow work)
- Labels: `rfc`, `agent`, optional component labels
- PR title: `Implement Game-RFC-XXX: Short title`
- PR body: include acceptance checklist and `Closes #<issue-number>`

## CI
- Minimal CI validates build/tests on PRs. Copilot should fix issues until green.

## Retry policy
- If the Copilot Actions run fails or stalls, use cleanup scripts to:
  1) cancel/delete latest workflow runs for the PR branch,
  2) close the PR,
  3) close the issue (cannot delete via API),
  4) re-create the issue and re-assign Copilot.

See `docs/agent-flow/AGENT_FLOW.md` and `scripts/agent/*.ps1`.