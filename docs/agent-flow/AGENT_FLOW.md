# Agent Flow: GitHub Copilot Coding Agent

This document defines how we use GitHub Copilot coding agent to implement small RFCs via issues and pull requests.

## Overview
- Create a small, well-scoped RFC issue.
- Assign the issue to Copilot via GraphQL (required for agent to start).
- Copilot opens a draft PR from `copilot/*` branch, writes PR description, and starts a workflow run in its sandbox.
- We review, leave `@copilot` comments to iterate, and merge when CI is green.

## GraphQL assignment (required)
Per GitHub docs, use GraphQL to locate Copilot assignee IDs and set the issue assignee. REST will not work for triggering the agent.

1) Find eligible assignees (bots may show as `Copilot`):

```
query {
  repository(owner: "<owner>", name: "<repo>") {
    suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
      nodes {
        login
        __typename
        ... on Bot { id }
        ... on User { id }
      }
    }
  }
}
```

Look for `login` values like `copilot` or `copilot-swe-agent` and capture the `id`.

2) Create an issue (GraphQL):

```
mutation($repoId: ID!, $title: String!, $body: String) {
  createIssue(input: {repositoryId: $repoId, title: $title, body: $body, labelIds: [], assigneeIds: []}) {
    issue { id number url }
  }
}
```

3) Assign Copilot to the issue (GraphQL):

```
mutation($issueId: ID!, $assigneeIds: [ID!]!) {
  addAssigneesToAssignable(input: {assignableId: $issueId, assigneeIds: $assigneeIds}) {
    assignable { ... on Issue { id number url assignees(first: 10){nodes{login}} } }
  }
}
```

Assign with the `id` from step 1. Copilot will create a draft PR shortly.

## Creation chain and removal chain
- Creation: Issue → PR → Workflow run
- Removal: Workflow (cancel/delete) → PR (close) → Issue (close)

We use removal then re-create to recover from failures quickly. Scripts under `scripts/agent/` provide helpers.

## Retry loop
1) Detect failure: Non-green workflow for Copilot PR branch; or PR blocked.
2) Cleanup:
   - Cancel any in-progress runs for the branch.
   - Close the PR.
   - Close the issue.
3) Re-create:
   - Create the issue again from the RFC template content.
   - Assign Copilot via GraphQL.
   - Monitor for new PR and workflow run.

## Small RFC guidance
- Keep scope minimal, time-box expected effort (agent minutes) and API calls.
- Include: problem, acceptance criteria, files to touch, minimal reproduction or smoke test steps.
- Avoid multi-repo or ambiguous tasks.

## Copilot development environment
- Preinstall tools via `.github/copilot-setup-steps.yml` to reduce flakiness and speed up.
- Ensure CI is deterministic; fail on warnings.

## References
- Changelog: Copilot agent supports `AGENTS.md` custom instructions
- Best practices: repository instructions, PR iteration with `@copilot`, MCP
- Pilot guide: evaluate, secure, pilot; branch protections; reviewer rules
- Concepts: limits, costs, security protections
- MCP: GitHub + Playwright servers enabled by default; extend later as needed
