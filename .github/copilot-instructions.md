# Copilot Instructions (Dungeon Project)

Use these instructions when creating PRs or working on issues.

## Build and test
- Environment: .NET 8 SDK
- Build: `dotnet build --nologo -warnaserror`
- Test: `dotnet test --nologo --verbosity minimal`
- Formatting: `dotnet format --verify-no-changes`

## Branch and PR rules
- Branches must start with `copilot/`.
- One small RFC per PR. Do not mix scopes.
- PR title: `Implement Game-RFC-XXX: <Title>`; body includes acceptance checklist and `Closes #<issue>`.
- Ensure CI is green and there are no warnings.

## Code conventions
- Namespaces: `Dungeon.Game.{Models,Systems,Utilities}`
- Keep rendering simple: `Console.SetCursorPosition`, ASCII/Unicode blocks.
- Prefer small, composable classes; unit test critical logic.

## Limits and scope
- No external game engines or graphics libs.
- No networking or persistence unless specified in an RFC.

## Notes for PR iteration
- Respond to PR comments tagged with `@copilot`.
- If CI fails, address failures or propose minimal scope reduction.
