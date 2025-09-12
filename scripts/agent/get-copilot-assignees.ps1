param(
  [Parameter(Mandatory=$true)][string]$Owner,
  [Parameter(Mandatory=$true)][string]$Repo
)

# Requires: gh CLI authenticated, GraphQL API access
$Query = @'
query(
  $owner: String!,
  $name: String!
){
  repository(owner: $owner, name: $name) {
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
'@

$vars = @{ owner = $Owner; name = $Repo } | ConvertTo-Json

$resp = gh api graphql -f query="$Query" -f variables="$vars" | ConvertFrom-Json
$actors = $resp.data.repository.suggestedActors.nodes
$actors | Where-Object { $_.login -match 'copilot' } | ForEach-Object {
  [pscustomobject]@{ login = $_.login; id = $_.id; type = $_.__typename }
}
