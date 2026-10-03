# Fair Drop — Team Workflow and Merge-Conflict Playbook

## Repository ownership

```text
/apps/backend        Dhruv
/apps/frontend       Rohan
/apps/simulator      Dhanya
/apps/mediapipe      Naman
/packages/api-contract  Dhruv defines; all consume
/docs                 shared documents only
/tests/integration    Dhruv
/tests/simulation     Dhanya
```

## Branches

Use one branch per person:

```text
feature/naman-mediapipe
feature/rohan-frontend
feature/dhanya-simulator
feature/dhruv-fastapi
```

Do not commit directly to `main` except for agreed emergency fixes.

## Commit prefixes

```text
backend: ...
frontend: ...
mediapipe: ...
simulator: ...
docs: ...
contract: ...
test: ...
```

Keep commits small and single-purpose.

## Cross-team contract rule

The only normal cross-team dependency is the HTTP/OpenAPI contract and shared JSON schemas. No contributor should import another contributor’s internal modules.

If a contract changes:

1. Add or update the schema.
2. Add an example request/response.
3. Tell affected owners.
4. Update mocks/tests.
5. Merge contract change before dependent implementation where practical.

## Integration sequence

1. Dhruv publishes initial OpenAPI contract and mock server responses.
2. Rohan builds frontend against the contract.
3. Dhanya builds simulator against the contract.
4. Naman publishes challenge result contract and mock mode.
5. Dhruv integrates challenge adapter.
6. Dhanya tests challenge/replay behavior through HTTP.
7. Rohan integrates challenge states.
8. Whole team runs the demo sequence.

## Conflict avoidance

- Never move or rename another owner’s files without agreement.
- Never add shared helpers to another owner’s directory.
- Use an API adapter instead of direct imports.
- Avoid changing database schema casually; Dhruv owns migrations.
- Avoid changing response field names without versioning or notifying Rohan/Dhanya.
- Rebase before merge.
- Resolve conflicts with the file owner present.
- Never resolve by accepting “ours” or “theirs” blindly.

## Definition of team success

The four people can run independently, then integrate through documented boundaries without copying internal code, manually editing each other’s directories, or inventing incompatible assumptions.
