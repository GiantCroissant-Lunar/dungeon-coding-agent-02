#!/usr/bin/env python3
"""
Create micro-issues from an RFC and (optionally) assign the first one to Copilot via GraphQL.
Environment:
- GH_TOKEN: token with repo scope
- GITHUB_REPOSITORY: owner/name (optional if --repo is passed)
- GAME_RFC: e.g., Game-RFC-001 (used to locate RFC file by pattern RFC-001-*.md)
"""
import os
import re
import glob
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from rfc_parser import parse_any_rfc

class GitHubAPI:
    def __init__(self, token: str):
        self.token = token

    def gql(self, query: str, variables: Dict = None) -> Optional[Dict]:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            p = f.name
        try:
            env = {**os.environ, 'GH_TOKEN': self.token}
            res = subprocess.run(['gh','api','graphql','--input',p], capture_output=True, text=True, env=env, check=True)
            return json.loads(res.stdout)
        finally:
            os.unlink(p)

    def get_repo_id(self, owner: str, name: str) -> Optional[str]:
        q = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) { id }
        }
        """
        d = self.gql(q, {'owner': owner, 'name': name})
        return d['data']['repository']['id'] if d and d.get('data') else None

    def get_copilot_id(self, owner: str, name: str) -> Optional[str]:
        q = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
              nodes {
                login
                __typename
                ... on Bot { id }
              }
            }
          }
        }
        """
        d = self.gql(q, {'owner': owner, 'name': name})
        if not d or 'data' not in d:
            return None
        for n in d['data']['repository']['suggestedActors']['nodes']:
            if n.get('__typename') == 'Bot' and 'copilot' in (n.get('login') or '').lower():
                # Prefer copilot-swe-agent if present
                if n.get('login') == 'copilot-swe-agent':
                    return n['id']
        # fallback to first bot containing copilot
        for n in d['data']['repository']['suggestedActors']['nodes']:
            if n.get('__typename') == 'Bot' and 'copilot' in (n.get('login') or '').lower():
                return n['id']
        return None

    def create_issue(self, repo_id: str, title: str, body: str, assignee_ids: List[str]) -> Optional[int]:
        m = """
        mutation($repositoryId: ID!, $title: String!, $body: String!, $assigneeIds: [ID!]) {
          createIssue(input: { repositoryId: $repositoryId, title: $title, body: $body, assigneeIds: $assigneeIds }) {
            issue { number }
          }
        }
        """
        v = { 'repositoryId': repo_id, 'title': title, 'body': body, 'assigneeIds': assignee_ids }
        d = self.gql(m, v)
        if d and d.get('data') and d['data']['createIssue']:
            return int(d['data']['createIssue']['issue']['number'])
        return None


def locate_rfc_file(repo_root: Path, game_rfc: str) -> Optional[Path]:
    m = re.match(r'Game-RFC-(\d+)', game_rfc)
    if not m:
        return None
    num = m.group(1)
    pattern = repo_root / 'docs' / 'game-rfcs' / f'RFC-{int(num):03d}-*.md'
    files = glob.glob(str(pattern))
    return Path(files[0]) if files else None


def main():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    repo_env = os.environ.get('GITHUB_REPOSITORY', '')
    game_rfc = os.environ.get('GAME_RFC')
    if not token or not repo_env or not game_rfc:
        print('Missing GH_TOKEN/GITHUB_TOKEN, GITHUB_REPOSITORY, or GAME_RFC')
        return 1

    owner, name = repo_env.split('/')
    repo_root = Path(__file__).resolve().parents[2]

    rfc_file = locate_rfc_file(repo_root, game_rfc)
    if not rfc_file:
        print(f'RFC file not found for {game_rfc}')
        return 1

    templates = parse_any_rfc(str(rfc_file), game_rfc)
    if not templates:
        print('No micro-issues derived from RFC')
        return 1

    api = GitHubAPI(token)
    repo_id = api.get_repo_id(owner, name)
    bot_id = api.get_copilot_id(owner, name)

    created = []
    for i, t in enumerate(templates):
        assignees = [bot_id] if (i == 0 and bot_id) else []
        num = api.create_issue(repo_id, t.title, t.body, assignees)
        if num:
            created.append(num)
            print(f'Created issue #{num}: {t.title}')
        else:
            print(f'Failed to create issue: {t.title}')

    print(f'Created {len(created)} micro-issues for {game_rfc}')
    return 0 if created else 1

if __name__ == '__main__':
    raise SystemExit(main())
