# Fair Drop — Team Handoff Package

This package is the shared project handoff for the four-person hackathon team.

## Structure

- `shared/` — canonical universal context, workflow rules, PRD, architecture, engineering rules, phases, design system, and living memory.
- `team/Naman/` — complete shared packet plus Naman’s MediaPipe role context.
- `team/Rohan/` — complete shared packet plus Rohan’s frontend role context.
- `team/Dhanya/` — complete shared packet plus Dhanya’s simulator/testing role context.
- `team/Dhruv/` — complete shared packet plus Dhruv’s FastAPI/backend role context.
- `existing/` — previously created system design, original implementation context, source image, project links, and Coldplay research extracts.

## Reading order

1. Read `shared/FairDrop-Universal-Context.md`.
2. Read `shared/prd.md`, `shared/architecture.md`, `shared/rules.md`, `shared/phases.md`, `shared/design.md`, and `shared/memory.md`.
3. Read the role-specific context inside your `team/<Name>/` folder.
4. Read `shared/FairDrop-Team-Workflow.md` before creating branches or changing shared contracts.

## Important implementation facts

- Dhruv and Naman use Python 3.11.9 virtual environments.
- Dhruv owns `/apps/backend` and the API contract.
- Rohan owns `/apps/frontend`.
- Dhanya owns `/apps/simulator`.
- Naman owns `/apps/mediapipe`.
- Cross-team integration happens through HTTP/OpenAPI and shared schemas, not internal imports.
