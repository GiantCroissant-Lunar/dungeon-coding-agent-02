param(
  [Parameter(Mandatory=$true)][string]$Owner,
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter(Mandatory=$true)][string]$Body,
  [Parameter(Mandatory=$true)][string]$CopilotActorId
)

# Requires gh CLI; returns created issue number and url

# Get repo ID
$repoQuery = @'
query($owner: String!, $name: String!){ repository(owner: $owner, name: $name){ id } }
'@
$vars = @{ owner = $Owner; name = $Repo } | ConvertTo-Json
$repoResp = gh api graphql -f query="$repoQuery" -f variables="$vars" | ConvertFrom-Json
$repoId = $repoResp.data.repository.id

# Create issue
$createIssue = @'
mutation($repoId: ID!, $title: String!, $body: String){
  createIssue(input: {repositoryId: $repoId, title: $title, body: $body}){
    issue { id number url }
  }
}
'@
$vars2 = @{ repoId = $repoId; title = $Title; body = $Body } | ConvertTo-Json
$issueResp = gh api graphql -f query="$createIssue" -f variables="$vars2" | ConvertFrom-Json
$issueId = $issueResp.data.createIssue.issue.id
$issueNumber = $issueResp.data.createIssue.issue.number
$issueUrl = $issueResp.data.createIssue.issue.url

# Assign Copilot
$assign = @'
mutation($issueId: ID!, $assignees: [ID!]!){
  addAssigneesToAssignable(input: {assignableId: $issueId, assigneeIds: $assignees}){
    assignable { ... on Issue { id number url } }
  }
}
'@
$vars3 = @{ issueId = $issueId; assignees = @($CopilotActorId) } | ConvertTo-Json
$assignResp = gh api graphql -f query="$assign" -f variables="$vars3" | ConvertFrom-Json | Out-Null

[pscustomobject]@{ number = $issueNumber; url = $issueUrl }
