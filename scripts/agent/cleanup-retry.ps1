param(
  [Parameter(Mandatory=$true)][string]$Owner,
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$IssueNumber
)

# Removal chain: workflow -> PR -> issue (close). Then caller can recreate and reassign.
# Requires gh CLI with repo and actions scope.

# Find PR for issue
$pr = gh pr list --repo "$Owner/$Repo" --search "linked:$IssueNumber" --json number,headRefName,state | ConvertFrom-Json | Select-Object -First 1
if ($null -ne $pr) {
  $branch = $pr.headRefName
  # Cancel running workflows for branch
  $runs = gh run list --repo "$Owner/$Repo" --branch "$branch" --json databaseId,status,conclusion | ConvertFrom-Json
  foreach ($r in $runs) {
    if ($r.status -eq 'in_progress' -or $r.status -eq 'queued') {
      gh run cancel $r.databaseId --repo "$Owner/$Repo" | Out-Null
    }
  }
  # Close PR
  gh pr close $pr.number --repo "$Owner/$Repo" --delete-branch=false | Out-Null
}

# Close issue
gh issue close $IssueNumber --repo "$Owner/$Repo" | Out-Null
