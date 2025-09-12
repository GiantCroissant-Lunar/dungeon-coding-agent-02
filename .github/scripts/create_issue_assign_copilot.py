#!/usr/bin/env python3
"""
Create a GitHub Issue and assign it to a Copilot coding agent using GraphQL.

Features
- Finds repository ID via owner/name
- Locates a Copilot assignee via suggestedActors (filter by login match; default: contains "copilot")
- Creates the issue (title/body)
- Assigns the issue to the chosen Copilot actor
- Prints a compact JSON result and writes step outputs when GITHUB_OUTPUT is set

Auth
- Uses token from env: GITHUB_TOKEN or GH_TOKEN (bearer)

Usage (CLI)
python .github/scripts/create_issue_assign_copilot.py \
  --owner GiantCroissant-Lunar \
  --repo dungeon-coding-agent-02 \
  --title "MCP Test: Create Notion subpage" \
  --body "Goal: Use MCP Notion server to create a sub-page."

Optional flags:
  --assignee-pattern "copilot"   # substring or regex depending on --assignee-regex
  --assignee-regex               # treat pattern as regex (case-insensitive)
  --body-file path.md            # read body from a file instead of --body
  --dry-run                      # print what would be done without creating/assigning

Outputs
- stdout JSON: { "issue_number": int, "issue_url": str }
- If env GITHUB_OUTPUT is set, appends:
    issue_number=...
    issue_url=...

Exit codes
- 0 on success; non-zero on error with a concise message to stderr
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
import urllib.request

API_URL = "https://api.github.com/graphql"


def _load_dotenv_if_present() -> None:
    """Load simple KEY=VALUE lines from a .env file into process env.

    - Supports optional quotes around values
    - Ignores comments and blank lines
    - Later sources win; only sets if key not already set
    """
    candidates: list[Path] = []
    try:
        here = Path(__file__).resolve()
        repo_root = here.parents[2]  # .../.github/scripts -> repo root
        candidates.append(repo_root / ".env")
    except Exception:
        pass
    # Also consider current working directory
    try:
        candidates.append(Path.cwd() / ".env")
    except Exception:
        pass

    for p in candidates:
        try:
            if not p.exists():
                continue
            for raw in p.read_text(encoding="utf-8").splitlines():
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("export "):
                    s = s[len("export "):]
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and os.environ.get(k) is None:
                    os.environ[k] = v
        except Exception:
            # Non-fatal; continue
            continue


def _token_from_env() -> str:
    _load_dotenv_if_present()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.stderr.write("Missing GITHUB_TOKEN or GH_TOKEN in environment.\n")
        sys.exit(2)
    return token


def _graphql(token: str, query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "create-issue-assign-copilot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            obj = json.loads(data.decode("utf-8"))
    except Exception as e:
        sys.stderr.write(f"GraphQL request failed: {e}\n")
        sys.exit(3)
    if "errors" in obj and obj["errors"]:
        sys.stderr.write("GraphQL errors: " + json.dumps(obj["errors"]) + "\n")
        sys.exit(4)
    return obj.get("data", {})


REPO_Q = (
    "query($owner: String!, $name: String!){ repository(owner: $owner, name: $name){ id } }"
)

SUGGESTED_ACTORS_Q = (
    "query($owner: String!, $name: String!){\n"
    "  repository(owner: $owner, name: $name){\n"
    "    suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100){\n"
    "      nodes{ login __typename ... on Bot{ id } ... on User{ id } }\n"
    "    }\n"
    "  }\n"
    "}"
)

CREATE_ISSUE_M = (
    "mutation($repoId: ID!, $title: String!, $body: String){\n"
    "  createIssue(input: {repositoryId: $repoId, title: $title, body: $body}){\n"
    "    issue{ id number url }\n"
    "  }\n"
    "}"
)

ASSIGN_M = (
    "mutation($issueId: ID!, $assignees: [ID!]!){\n"
    "  addAssigneesToAssignable(input: {assignableId: $issueId, assigneeIds: $assignees}){\n"
    "    assignable{ ... on Issue{ id number url } }\n"
    "  }\n"
    "}"
)

# Alternative: replace actors (bot or user) per docs when assigning existing issues
REPLACE_ACTORS_M = (
    "mutation($assignableId: ID!, $actorIds: [ID!]!){\n"
    "  replaceActorsForAssignable(input: {assignableId: $assignableId, actorIds: $actorIds}){\n"
    "    assignable{ ... on Issue{ id number url } }\n"
    "  }\n"
    "}"
)


def find_repo_id(token: str, owner: str, repo: str) -> str:
    data = _graphql(token, REPO_Q, {"owner": owner, "name": repo})
    rid = data.get("repository", {}).get("id")
    if not rid:
        sys.stderr.write("Repository not found or missing id.\n")
        sys.exit(5)
    return rid


def find_copilot_assignee_id(
    token: str,
    owner: str,
    repo: str,
    pattern: str,
    use_regex: bool,
    exact_login: str | None = None,
    assign_mode: str = "auto",  # auto|user|bot
) -> tuple[str, str, str]:
    data = _graphql(token, SUGGESTED_ACTORS_Q, {"owner": owner, "name": repo})
    nodes = (
        data.get("repository", {})
        .get("suggestedActors", {})
        .get("nodes", [])
    )
    if not nodes:
        sys.stderr.write("No suggested actors returned.\n")
        sys.exit(6)

    # Normalize node shape
    norm = [
        {
            "login": n.get("login", ""),
            "id": n.get("id"),
            "type": n.get("__typename", ""),
        }
        for n in nodes
    ]

    def match(login: str) -> bool:
        if exact_login is not None:
            return login.lower() == exact_login.lower()
        if use_regex:
            return re.search(pattern, login, re.IGNORECASE) is not None
        return pattern.lower() in login.lower()

    # Prefer User actors; GitHub only allows assigning issues to Users, not Bots
    user_matches = [n for n in norm if n["type"] == "User" and match(n["login"])]
    bot_matches = [n for n in norm if n["type"] == "Bot" and match(n["login"])]

    # Selection preference
    if assign_mode == "user" and user_matches:
        chosen = user_matches[0]
        return chosen["id"], chosen["login"], "User"
    if assign_mode == "bot" and bot_matches:
        chosen = bot_matches[0]
        return chosen["id"], chosen["login"], "Bot"
    # auto: prefer user, else bot
    if user_matches:
        chosen = user_matches[0]
        return chosen["id"], chosen["login"], "User"
    if bot_matches:
        chosen = bot_matches[0]
        return chosen["id"], chosen["login"], "Bot"

    # Nothing matched at all
    sys.stderr.write(
        (
            f"No User actor matched pattern '{exact_login or pattern}'. Candidates: "
            + ", ".join(f"{x['login']}[{x['type']}]" for x in norm)
            + "\n"
        )
    )
    sys.exit(7)


def create_issue(token: str, repo_id: str, title: str, body: str | None) -> tuple[str, int, str]:
    data = _graphql(token, CREATE_ISSUE_M, {"repoId": repo_id, "title": title, "body": body})
    issue = data.get("createIssue", {}).get("issue") or {}
    iid = issue.get("id")
    num = issue.get("number")
    url = issue.get("url")
    if not (iid and num and url):
        sys.stderr.write("Failed to create issue (missing fields).\n")
        sys.exit(8)
    return iid, int(num), str(url)


def assign_issue(token: str, issue_id: str, assignee_ids: list[str]) -> None:
    _ = _graphql(token, ASSIGN_M, {"issueId": issue_id, "assignees": assignee_ids})


def write_github_outputs(issue_number: int, issue_url: str) -> None:
    out_path = os.environ.get("GITHUB_OUTPUT")
    if not out_path:
        return
    try:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(f"issue_number={issue_number}\n")
            f.write(f"issue_url={issue_url}\n")
    except Exception as e:
        sys.stderr.write(f"Failed to write GITHUB_OUTPUT: {e}\n")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Create an issue and assign Copilot via GraphQL")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--title", required=True)
    gbody = p.add_mutually_exclusive_group(required=False)
    gbody.add_argument("--body")
    gbody.add_argument("--body-file")
    p.add_argument("--assignee-pattern", default="copilot")
    p.add_argument("--assignee-regex", action="store_true")
    p.add_argument("--assignee-login")
    p.add_argument("--list-actors", action="store_true", help="List suggested assignable actors and exit")
    p.add_argument("--assign-mode", choices=["auto","user","bot"], default="auto", help="Prefer selecting a user or bot when both match")
    p.add_argument("--replace-mode", action="store_true", help="Assign using replaceActorsForAssignable instead of addAssigneesToAssignable/createIssue assigneeIds")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    token = _token_from_env()

    if args.list_actors:
        data = _graphql(token, SUGGESTED_ACTORS_Q, {"owner": args.owner, "name": args.repo})
        nodes = (
            data.get("repository", {})
            .get("suggestedActors", {})
            .get("nodes", [])
        )
        out = [
            {"login": n.get("login"), "id": n.get("id"), "type": n.get("__typename")}
            for n in nodes
        ]
        sys.stdout.write(json.dumps(out) + "\n")
        return 0

    body = args.body
    if args.body_file:
        try:
            with open(args.body_file, "r", encoding="utf-8") as f:
                body = f.read()
        except Exception as e:
            sys.stderr.write(f"Failed to read body file: {e}\n")
            return 9

    if args.dry_run:
        # Probe suggested actors early for fast fail
        _ = find_copilot_assignee_id(
            token, args.owner, args.repo, args.assignee_pattern, args.assignee_regex, args.assignee_login, args.assign_mode
        )
        rid = find_repo_id(token, args.owner, args.repo)
        sys.stdout.write(json.dumps({"dry_run": True, "repo_id": rid}) + "\n")
        return 0

    rid = find_repo_id(token, args.owner, args.repo)
    assignee_id, assignee_login, actor_type = find_copilot_assignee_id(
        token, args.owner, args.repo, args.assignee_pattern, args.assignee_regex, args.assignee_login, args.assign_mode
    )
    # Assignment path:
    # - If actor is User and not replace-mode: create issue then addAssignees
    # - If actor is Bot and not replace-mode: use createIssue with assigneeIds in one call (per docs)
    # - If replace-mode: create issue then replaceActorsForAssignable with the actor id
    iid, num, url = create_issue(token, rid, args.title, body) if args.replace_mode else (None, None, None)
    if args.replace_mode:
        # Need issue id; if not created yet, create first
        if iid is None:
            iid, num, url = create_issue(token, rid, args.title, body)
        _ = _graphql(token, REPLACE_ACTORS_M, {"assignableId": iid, "actorIds": [assignee_id]})
    else:
        if actor_type == "Bot":
            # Create with assigneeIds
            data = _graphql(
                token,
                "mutation($repoId: ID!, $title: String!, $body: String, $aids: [ID!]!){\n  createIssue(input: {repositoryId: $repoId, title: $title, body: $body, assigneeIds: $aids}){ issue{ id number url } }\n}",
                {"repoId": rid, "title": args.title, "body": body, "aids": [assignee_id]},
            )
            issue = data.get("createIssue", {}).get("issue") or {}
            iid = issue.get("id"); num = issue.get("number"); url = issue.get("url")
            if not (iid and num and url):
                sys.stderr.write("Failed to create issue with bot assignee.\n"); return 10
        else:
            # User path: create then add
            iid, num, url = create_issue(token, rid, args.title, body)
            assign_issue(token, iid, [assignee_id])

    result = {"issue_number": int(num), "issue_url": str(url), "assignee_login": assignee_login, "assignee_type": actor_type}
    sys.stdout.write(json.dumps(result) + "\n")
    write_github_outputs(num, url)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
