# Fair Drop Frontend — Complete Handover & Integration Guide

> **For:** Dhruv (Backend Lead)
> **From:** Rohan (Frontend Lead)
> **Status:** Frontend UI 100% complete. Supabase Auth integrated. Ready to wire your backend endpoints.
> **Goal:** You take this entire frontend as-is, run it on your machine, and connect it to your already-running FastAPI backend. Zero merge conflicts. Zero rewrites needed.

---

## 1. WHY YOU'RE RECEIVING THIS

Rohan's frontend is complete and ready. Instead of sending you Python chunks or asking you to merge code, we're flipping the model:

**You take the entire frontend ZIP → run `npm install` → connect it to your backend → ship.**

This is faster because:
- Setting up Next.js on your machine takes 2 minutes.
- Zero merge pain — the frontend is self-contained.
- You already have the backend running, so you only need to make small changes to point the frontend to your API.
- Both frontend and backend can live in the same monorepo under your control.

---

## 2. QUICK START (5 MINUTES)

### 2.1 Prerequisites on your machine
```bash
node --version    # Should be v18+ or v20+
npm --version     # Should be v9+
If missing, install Node.js LTS from https://nodejs.org

2.2 Install and run
Bash

# Unzip the project
cd fair-drop-ui-design/frontend

# Install dependencies (first time only)
npm install

# Run dev server
npm run dev
Open http://localhost:3000 — you should see the Fair Drop landing page.

2.3 Environment variables
Create a file called .env.local in the frontend/ folder with:

env

# Supabase (SAME project you use for backend JWT validation)
NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR-SUPABASE-ANON-KEY

# Your FastAPI backend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# Toggle this to false when you're ready to use the live backend
NEXT_PUBLIC_DEMO_MODE=true
Critical: The Supabase project MUST be the same one your backend validates JWTs against. Otherwise auth will fail.

2.4 Make sure your backend is running
Bash

cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Confirm it's accessible: visit http://localhost:8000/health in your browser.

3. RECOMMENDED MONOREPO STRUCTURE
Put everything together like this:

text

fair-drop/
├── frontend/           ← This ZIP (Next.js + TypeScript + Tailwind)
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── types/
│   ├── docs/
│   ├── package.json
│   └── .env.local      ← You create this
│
└── backend/            ← Your existing FastAPI code
    ├── app/
    ├── migrations/
    ├── pyproject.toml
    └── .env            ← Your existing backend env
Each folder is independent. They never share code. They only talk over HTTP.

4. WHAT'S INSIDE THE FRONTEND
4.1 Tech stack
Layer	Tech
Framework	Next.js 14 (App Router)
Language	TypeScript 5
Styling	Tailwind CSS + Neo-brutalist design system
Auth	Supabase (@supabase/supabase-js)
State	React Context + hooks (no Redux/Zustand)
Icons	Lucide React
Charts	Recharts
4.2 Design system
Neo-brutalist UI with:

Warm cream background (#F7F1E8)
Thick black borders (2-3px)
Hard offset shadows (6px 6px 0 #111)
Accent colors: Pink, Yellow, Teal, Blue, Purple, Red, Green
Bold display typography
Sticker-style status pills
Color tokens live in Tailwind config and CSS variables.

4.3 Folder structure
text

frontend/
├── app/                        ← Next.js App Router pages
│   ├── layout.tsx              ← Root layout + AuthProvider wrapper
│   ├── page.tsx                ← Landing page
│   ├── login/page.tsx          ← Supabase login
│   ├── signup/page.tsx         ← Supabase signup
│   ├── verify-email/page.tsx   ← Email verification notice
│   ├── profile/page.tsx        ← User profile
│   ├── events/
│   │   ├── page.tsx            ← Event discovery grid
│   │   └── [campaignId]/
│   │       ├── page.tsx                  ← Event detail
│   │       ├── waiting-room/page.tsx     ← Admission waiting room
│   │       ├── register/page.tsx         ← Registration form
│   │       ├── status/page.tsx           ← Registration status timeline
│   │       ├── result/page.tsx           ← Lottery result (won/standby/not selected)
│   │       ├── claim/page.tsx            ← Seat selection + hold + confirm
│   │       ├── confirmed/page.tsx        ← Booking confirmation
│   │       └── audit/page.tsx            ← Public fairness audit
│   └── admin/
│       ├── login/page.tsx
│       ├── page.tsx                      ← Admin dashboard
│       └── campaigns/
│           ├── page.tsx                  ← Campaign list
│           ├── new/page.tsx              ← Create campaign form
│           └── [campaignId]/
│               ├── page.tsx              ← Campaign overview
│               ├── edit/page.tsx
│               ├── monitor/page.tsx
│               ├── draw/page.tsx         ← Run lottery
│               ├── claims/page.tsx
│               ├── audit/page.tsx
│               └── simulations/page.tsx
│
├── components/                 ← Reusable UI components
│   ├── nav/                    ← Navigation bars
│   ├── events/                 ← Event cards, filters
│   ├── waiting-room/           ← Waiting room UI
│   ├── seats/                  ← Seat map component
│   ├── challenges/             ← Challenge host + adapters (Turnstile/MediaPipe/Mock)
│   ├── admin/                  ← Admin dashboard components
│   ├── metrics/                ← Chart components
│   ├── feedback/               ← Loading, error, empty states
│   └── ui/                     ← Base UI primitives (buttons, cards, inputs)
│
├── lib/                        ← Business logic + API client
│   ├── supabase.ts             ← Supabase browser client
│   ├── AuthContext.tsx         ← React auth provider (session management)
│   ├── api.ts                  ← Typed API client for backend
│   └── utils.ts                ← Shared utilities
│
├── types/
│   └── domain.ts               ← All domain types (CampaignStatus, RegistrationStatus, etc.)
│
├── docs/                       ← Context documents (read if you want deep context)
│   ├── FairDrop-Universal-Context.md
│   ├── FairDrop-Master-Backend-Integration-Guide.md
│   ├── FairDrop-Frontend-Integration-Guide.md
│   ├── FairDrop-User-Flow.md
│   └── FairDrop-Routing-Map.md
│
├── public/                     ← Static assets
├── .env.local                  ← YOU CREATE THIS
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs
└── README.md
5. COMPLETE USER FLOW
The frontend implements this exact navigation flow:

text

Landing (/)
   │
   ├── [Explore Events] → /events (public, no auth needed to browse)
   ├── [Login] → /login
   └── [Sign Up] → /signup

Login/Signup → Supabase handles auth → redirects to /events

/events (grid of campaigns)
   │
   └── Click card → /events/[campaignId]
                      │
                      └── [Join Fair Drop] (requires auth; redirects to login if needed)
                            │
                            ▼
                      /events/[campaignId]/waiting-room
                            │
                            ├── Calls POST /campaigns/{id}/join
                            ├── Receives admission_token + nonce
                            ├── Stores permit in sessionStorage
                            └── [Continue to Registration]
                                  │
                                  ▼
                            /events/[campaignId]/register
                                  │
                                  ├── Calls POST /campaigns/{id}/register
                                  │   with admission_token + Idempotency-Key header
                                  └── Redirects to /status
                                        │
                                        ▼
                                  /events/[campaignId]/status
                                        │
                                        ├── Polls GET /campaigns/{id}/status every 8s
                                        └── Shows timeline (verified → registered → window → freeze → draw → result)
                                              │
                                              ▼
                                        /events/[campaignId]/result
                                              │
                                              ├── Calls GET /campaigns/{id}/result
                                              │
                                              ├── SELECTED (winner) → [Claim] → /claim
                                              ├── STANDBY → shows position
                                              └── NOT_SELECTED → shows audit link

/events/[campaignId]/claim (3 steps)
   │
   ├── Step 1: Challenge host (Turnstile/MediaPipe/Mock) — currently uses mock adapter
   ├── Step 2: Seat map — currently mocked (will call POST /entitlements/{id}/hold when backend ready)
   └── Step 3: Confirm → POST /entitlements/{id}/redeem → /confirmed

/events/[campaignId]/confirmed
   │
   └── Shows booking receipt + link to /audit

/events/[campaignId]/audit → GET /campaigns/{id}/audit (public fairness receipt)
Admin flow (parallel)
text

/admin/login → Supabase + role check → /admin
   │
   ├── /admin → dashboard with metric cards
   └── /admin/campaigns → list
         │
         ├── [New] → /admin/campaigns/new → create draft
         └── Click row → /admin/campaigns/[id]
                           │
                           ├── /edit     → edit draft fields
                           ├── /monitor  → live metrics
                           ├── /draw     → run lottery (requires FROZEN state)
                           ├── /claims   → selected/held/confirmed tabs
                           ├── /audit    → admin audit log
                           └── /simulations → shell for adversarial testing
6. AUTH ARCHITECTURE
How it works
text

┌─────────────┐                   ┌──────────┐
│   Browser   │                   │ Supabase │
│  (Next.js)  │ ───signup/login──▶│   Auth   │
└──────┬──────┘                   └────┬─────┘
       │                                │
       │       ◀───JWT access_token─────┘
       │
       │  Every API request:
       │  Authorization: Bearer <JWT>
       │  X-Request-ID: <uuid>
       │  Idempotency-Key: <key>  (for state-changing calls)
       │
       ▼
┌─────────────┐
│   FastAPI   │ ← Validates JWT with Supabase public key
│   Backend   │ ← Does JIT user provisioning (your existing code)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PostgreSQL  │
└─────────────┘
Files involved on frontend
lib/supabase.ts — initializes Supabase client with env vars
lib/AuthContext.tsx — React provider exposing { user, session, loading, signIn, signUp, signOut }
app/layout.tsx — wraps the app with <AuthProvider>
app/login/page.tsx — calls supabase.auth.signInWithPassword()
app/signup/page.tsx — calls supabase.auth.signUp()
What you need to do
Make sure your .env.local uses the same Supabase project URL and anon key that your backend validates JWTs against.
The frontend will automatically attach Authorization: Bearer <token> to every API call via lib/api.ts.
On your backend's first API call from a new user, your existing JIT provisioning code will create the profile and participant rows. No frontend changes needed.
7. API CLIENT — HOW THE FRONTEND CALLS YOUR BACKEND
File: lib/api.ts

Every API call automatically:

Reads the current Supabase JWT from the session
Attaches Authorization: Bearer <JWT> header
Attaches a unique X-Request-ID header for tracing
For state-changing calls, attaches Idempotency-Key header
Parses errors in your standard format: { error: { code, message, request_id } }
Mapped endpoints
TypeScript

api.me()                                              → GET  /auth/me
api.listCampaigns(page, pageSize)                     → GET  /campaigns
api.getCampaign(id)                                   → GET  /campaigns/{id}
api.getCampaignStatus(id)                             → GET  /campaigns/{id}/status
api.joinCampaign(id)                                  → POST /campaigns/{id}/join
api.register(id, token, nonce, idempKey)              → POST /campaigns/{id}/register
api.getResult(id)                                     → GET  /campaigns/{id}/result

// Admin
api.admin.createCampaign(body)                        → POST  /admin/campaigns
api.admin.listCampaigns()                             → GET   /admin/campaigns
api.admin.prepareCampaign(id)                         → POST  /admin/campaigns/{id}/prepare
api.admin.publishCampaign(id)                         → POST  /admin/campaigns/{id}/publish
api.admin.closeCampaign(id)                           → POST  /admin/campaigns/{id}/close
api.admin.freezeCampaign(id)                          → POST  /admin/campaigns/{id}/freeze
api.admin.drawLottery(id, seed)                       → POST  /admin/campaigns/{id}/draw

// Not wired yet (waiting for your Step 8)
api.holdSeat(entitlementId, seatId, idempKey)         → POST /entitlements/{id}/hold
api.redeemSeat(entitlementId, seatId, idempKey)       → POST /entitlements/{id}/redeem
If you add new endpoints, add a corresponding method to lib/api.ts and the frontend will use it instantly.

8. CURRENT INTEGRATION STATUS
✅ Wired to real backend (ready to test)
Page	Endpoint	Status
/events	GET /campaigns	✅ Live
/events/[id]	GET /campaigns/{id}	✅ Live
/events/[id]/waiting-room	POST /campaigns/{id}/join	✅ Live
/events/[id]/register	POST /campaigns/{id}/register	✅ Live
/events/[id]/status	GET /campaigns/{id}/status	✅ Live
/events/[id]/result	GET /campaigns/{id}/result	✅ Live
/login, /signup	Supabase direct	✅ Live
/admin/*	POST/GET /admin/campaigns/*	✅ Live
🚧 Still using mock data (waiting on your Step 8 and defense layers)
Page	Needs	What to do
/events/[id]/claim seat selection	POST /entitlements/{id}/hold	When ready, uncomment the api.holdSeat() call in app/events/[campaignId]/claim/page.tsx
/events/[id]/claim confirm	POST /entitlements/{id}/redeem	Same — uncomment api.redeemSeat()
/events/[id]/confirmed	Reads from redeem response	Already structured; just needs the real response
/events/[id]/audit	GET /campaigns/{id}/audit	Add endpoint to api.getAudit()
Challenge adapters	Turnstile verification + MediaPipe nonce	Currently uses MockAdapter — see section 10
Admin monitor charts	GET /admin/campaigns/{id}/metrics	Currently uses hardcoded demo data
📋 Toggle demo mode
In .env.local:

NEXT_PUBLIC_DEMO_MODE=true → Falls back to mock data where backend endpoints aren't ready
NEXT_PUBLIC_DEMO_MODE=false → All API calls go to your backend
Set to false once you've confirmed each endpoint works.

9. DEFENSE LAYERS — WHERE THEY LIVE IN THE UI
The UI has placeholder shells for all three defense layers. When your defense code is ready, we just pass extra fields in existing API calls.

Layer 1: Turnstile + JA3 (Waiting Room)
Location: app/events/[campaignId]/waiting-room/page.tsx
Current state: Static placeholder div
To integrate:
Add Cloudflare Turnstile widget using @marsidev/react-turnstile (or vanilla script)
Capture the turnstile_token on verification callback
Pass it in the POST /register body (add field to your schema)
JA3: Entirely backend concern. Your Cloudflare proxy adds the header cf-ja3-hash. You validate it server-side. No frontend change needed.
Layer 2: MediaPipe Gesture (Registration)
Location: app/events/[campaignId]/register/page.tsx (above the Register button)
Current state: Shows a placeholder "Liveness Check" box with a dev button to simulate success
To integrate:
Naman provides a React component or vanilla JS adapter that exposes a webcam feed and gesture detection
On successful gesture detection, enable the Register button and store a challenge_id + nonce
Pass challenge_id in POST /register body
Adapter interface already exists in components/challenges/ChallengeHost.tsx. Naman just implements the MediapipeAdapter using the shared ChallengeAdapterProps.
Layer 3: Atomic Seat Lock (Claim Page)
Location: app/events/[campaignId]/claim/page.tsx (seat selection step)
Current state: Click a seat → mock lock
To integrate:
Your POST /entitlements/{id}/hold already does the atomic DB SELECT ... FOR UPDATE
Frontend just calls api.holdSeat() with the clicked seat_id
If 409 Conflict, refresh seat map and show toast "Seat taken, pick another"
Server-sent hold_expires_at drives the countdown timer
The UI is already built for all three layers. You just need the backend endpoints to accept the extra fields.

10. IDEMPOTENCY HANDLING
The frontend generates stable idempotency keys for state-changing operations:

TypeScript

// Example from register page
let idempKey = sessionStorage.getItem(`idemp_${campaignId}`)
if (!idempKey) {
  idempKey = `reg_${campaignId}_${Date.now()}`
  sessionStorage.setItem(`idemp_${campaignId}`, idempKey)
}
await api.register(campaignId, token, nonce, idempKey)
Rules the frontend follows:

Same operation + same user + same campaign = same key (reused on retry)
Key stored in sessionStorage per campaign
On network timeout, the frontend retries with the same key (never generates a new one)
Your backend's existing idempotency logic handles the rest
11. TIMERS
The frontend never claims timer expiry on its own. It only displays countdowns based on server-sent timestamps.

Example response from your POST /join:

JSON

{
  "admission_token": "...",
  "nonce": "...",
  "expires_at": "2026-10-04T19:57:08Z",
  "expires_in_seconds": 120,
  "server_time": "2026-10-04T19:55:08Z"
}
Frontend calculates:

TypeScript

const remaining = (new Date(expires_at).getTime() - estimated_server_now) / 1000
When the display countdown hits zero, the frontend calls GET /campaigns/{id}/status and lets your backend decide if the permit is actually expired. This prevents clock-drift bugs.

Same pattern for:

Admission permits (expires_at)
Challenge nonces (expires_at)
Entitlements (expires_at)
Seat holds (hold_expires_at)
12. ERROR HANDLING
The frontend expects your standard error format:

JSON

{
  "error": {
    "code": "REGISTRATION_CLOSED",
    "message": "Registration has ended",
    "request_id": "req_abc123"
  }
}
Mapped error codes the frontend handles:

Code	UI behavior
AUTH_REQUIRED	Redirect to /login?redirect=<current>
CAMPAIGN_NOT_OPEN	Show campaign status page
REGISTRATION_CLOSED	Disable form, show cutoff time
DUPLICATE_ENTRY	Show "already registered" state
CHALLENGE_REQUIRED	Open challenge host modal
COOLDOWN_ACTIVE	Show 5-min countdown toast
ADMISSION_PERMIT_EXPIRED	Call joinCampaign() again
SEAT_NOT_AVAILABLE	Refresh seat map, show toast
HOLD_EXPIRED	Return to seat selection step
IDEMPOTENCY_CONFLICT	Stop retry, show request_id for support
503	Show retry-after state (no duplicate writes)
If you add new error codes, they'll show the generic error message by default. Add a mapping in lib/api.ts for custom handling.

13. CORS CONFIGURATION
Your backend already has CORS set to http://localhost:3000. ✅

If you deploy the frontend to a different URL (e.g., Vercel), add that URL to your backend's CORS_ORIGINS env var.

14. SUPABASE PROJECT ALIGNMENT
Critical: Both frontend and backend must use the same Supabase project.

Check:

Open Supabase dashboard
Settings → API
Copy Project URL and anon public key into frontend's .env.local
Copy JWT Secret (or JWKS URL) into backend's .env (your existing config)
If project IDs don't match, JWTs will fail validation and every protected call will 401.

15. TESTING THE FULL FLOW
Once frontend is running and backend is live, test this exact sequence:

A. User flow (should take 2 min to test)
Open http://localhost:3000
Click [Sign Up] → create account test@test.com / password test1234
Check Supabase dashboard → user appears
You're auto-redirected to /events
If list is empty, create a campaign via admin (step B below)
Click a campaign card → see detail page
Click [Join Fair Drop] → waiting room → receives permit (check Network tab)
Click [Continue to Registration] → register (check Network tab for Idempotency-Key)
Status page shows timeline
If you've already run the draw, result page shows WON / STANDBY / NOT_SELECTED
B. Admin flow
In Supabase dashboard, change your test user's role to ADMIN in the profiles table
Go to /admin/login → log in with same account
Dashboard loads with metric cards
[New Campaign] → fill form → save draft
[Prepare] → [Publish]
Open a second browser window as a user → register for the campaign
Back in admin: [Close] → [Freeze] → [Run Lottery]
User's result page now shows the outcome
C. Common gotchas to check
 Supabase URL/key in .env.local matches backend's Supabase config
 Backend bound to 0.0.0.0 not 127.0.0.1 (so frontend from browser can reach it)
 CORS allows http://localhost:3000
 JWT isn't expired (default 1 hour; refresh by signing in again)
 First-time user call creates profile row via your JIT provisioning
 Idempotency-Key header is being sent on POST /register (check Network tab)
16. BUILD & DEPLOY
Development
Bash

npm run dev          # Start dev server on :3000
npm run lint         # Run ESLint
npm run typecheck    # Run TypeScript compiler
npm run build        # Production build
npm start            # Start production server
Deploying to Vercel
Push the frontend folder to GitHub
Import the repo in Vercel
Set env vars in Vercel dashboard:
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_BASE_URL (point to your deployed backend)
NEXT_PUBLIC_DEMO_MODE=false
Deploy
Vercel auto-detects Next.js. Zero config needed.

17. WHAT I RECOMMEND YOU DO NEXT
Phase 1: Verify integration (30 min)
Install the frontend, run npm install + npm run dev
Create .env.local with matching Supabase keys
Test signup → login → see events list from your backend
Fix any CORS or JWT mismatches
Phase 2: Finish Step 8 (seat hold + redeem) (2-3 hours)
Add endpoints to your FastAPI
Add corresponding methods to lib/api.ts:
TypeScript

holdSeat: (entitlementId, seatId, idempKey) =>
  request(`/entitlements/${entitlementId}/hold`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempKey },
    body: JSON.stringify({ seat_id: seatId })
  }),
Uncomment the mock in app/events/[campaignId]/claim/page.tsx
Phase 3: Wire defense layers (parallel work)
Turnstile: get site key, add widget in waiting room
MediaPipe: Naman delivers adapter, slot into ChallengeHost
Both just pass extra fields in existing API calls
Phase 4: Demo prep (1 hour)
Create a demo campaign with realistic data
Pre-register a few test users
Rehearse the full flow
18. HOW TO ASK FOR CHANGES
If you need the frontend to send a new field or hit a new endpoint:

Tell me the endpoint shape (URL, method, request/response JSON)
I'll add it to lib/api.ts
I'll wire it into the right page
We test together
Frontend changes are usually 10-20 min each. Don't rewrite — just extend.

19. CONTACT & COORDINATION
Frontend owner: Rohan
Backend owner: Dhruv (you)
MediaPipe owner: Naman — he delivers an adapter conforming to components/challenges/types.ts
Simulator owner: Dhanya — she hits your /api/v1/* endpoints, no frontend dependency
Commit convention
text

frontend: <description>
backend:  <description>
docs:     <description>
If you edit the frontend
Don't touch app/, components/, lib/, types/ without telling me — merge conflicts
Safe to edit: README.md, .env.local, docs/
If you need UI changes, request them (see section 18)
20. QUICK REFERENCE CARD
Bash

# Setup (first time)
cd frontend
npm install
cp .env.example .env.local    # Then edit with your Supabase keys

# Daily use
npm run dev                   # Start frontend
# (In another terminal, your backend)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Before committing
npm run lint
npm run typecheck
npm run build

# Reset session (if testing auth)
# Browser DevTools → Application → Local Storage → clear all
21. KNOWN LIMITATIONS / TODO
 Seat selection calls mock (replace when Step 8 lands)
 Challenge host uses MockAdapter (replace with real Turnstile + MediaPipe adapters)
 Admin metrics charts use hardcoded demo data (replace with /metrics endpoint)
 No real-time updates (uses 8-second polling; can upgrade to Supabase Realtime later)
 No service worker for offline support (not needed for hackathon)
 No analytics (not needed for hackathon)
22. FINAL CHECKLIST BEFORE DEMO
 Frontend installs cleanly on your machine
 .env.local configured with correct Supabase + backend URLs
 Backend running on http://localhost:8000
 Can sign up and sign in
 Can see list of events
 Can register for an event (waiting room → register → status)
 Admin can create → prepare → publish → freeze → draw a campaign
 Winner sees "YOU'RE IN!" on result page
 Mobile layout works at 375px width
 No console errors in browser DevTools
 Backend logs show successful JWT validation + JIT provisioning
23. ONE-LINE SUMMARY
This frontend is complete, Supabase-authenticated, and ready to consume your FastAPI backend. Run npm install && npm run dev, point .env.local at your backend and Supabase, and 80% of the flow works end-to-end immediately. The remaining 20% (seat hold, defense layers) just needs their backend endpoints — the UI is already built.