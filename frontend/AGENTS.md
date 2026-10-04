# Fair Drop Frontend Agent Instructions

## Project

This is the frontend for Fair Drop, a fair high-demand event allocation platform.

Fair Drop is designed for events such as:

- Concerts
- Movies
- Sports events
- Conferences
- University events
- Other limited-capacity events

The frontend is built with:

- Next.js App Router
- TypeScript
- Tailwind CSS
- Supabase Auth
- FastAPI backend integration
- Vercel deployment

## Required context files

Before making changes, read:

1. `docs/FairDrop-Universal-Context.md`
2. `docs/FairDrop-Master-Backend-Integration-Guide.md`
3. `docs/FairDrop-Frontend-Integration-Guide.md`

These documents are the source of truth.

If any current code conflicts with those documents, follow the documents unless the user explicitly changes the requirements.

## Core product principle

Fair Drop removes the speed race.

The system uses:

```text
Authentication
→ Admission/waiting room
→ Identity and risk checks
→ One idempotent registration
→ Registration cutoff
→ Frozen eligible roster
→ Deterministic uniform lottery
→ Winner or standby result
→ Human validation when required
→ Temporary seat hold
→ Exact seat confirmation
→ Confirmed booking
