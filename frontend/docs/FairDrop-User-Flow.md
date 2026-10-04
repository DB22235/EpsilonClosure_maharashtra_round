# Fair Drop — Complete User Flow (UI Phase)

> This document defines the exact navigation flow for the frontend.
> Backend integration is pending. Build the UI with mock adapters.
> Preventive measures (risk, cooldown, replay) are handled in another track — leave extension points.

## 1. Public (unauthenticated) flow
Landing page (/)
│
├── [Explore Events] clicked
│ │
│ ▼
│ Auth gate check
│ │
│ ├── Not signed in → /login
│ │ │
│ │ ├── [Sign up] → /signup → /verify-email → /login
│ │ └── [Sign in] → /events (preserve redirect URL)
│ │
│ └── Signed in → /events
│
├── [How Fair Drop works] → scroll section or /#how-it-works
└── [Login] / [Sign up] in nav → /login or /signup

text


## 2. Authenticated user flow (event booking)
/events (event discovery grid)
│
▼
/events/[campaignId] (event detail page)
│
├── Campaign status = OPEN
│ │
│ ▼
│ [Join Fair Drop] button
│ │
│ ▼
│ /events/[campaignId]/waiting-room
│ │
│ ├── admission state = WAITING → stay, poll status
│ ├── admission state = ADMITTED → /events/[campaignId]/register
│ ├── admission state = CHALLENGE_REQUIRED → /events/[campaignId]/challenge (modal or page)
│ └── admission state = COOLDOWN → show cooldown screen
│
├── Campaign status = CLOSED/FROZEN/DRAWING → /events/[campaignId]/status
├── Campaign status = CLAIMING → /events/[campaignId]/result
└── Campaign status = COMPLETED → /events/[campaignId]/audit

text


## 3. Registration → Result → Claim flow
/events/[campaignId]/register
│
├── Submit registration (idempotent)
│ │
│ ├── ACCEPTED → /events/[campaignId]/status
│ ├── DUPLICATE → /events/[campaignId]/status (with "already registered")
│ ├── CHALLENGE_REQUIRED → open challenge host
│ └── REJECTED/QUARANTINED → show reason
│
▼
/events/[campaignId]/status (timeline: verified → recorded → window → freeze → draw → result)
│
▼ (when campaign reaches CLAIMING)
/events/[campaignId]/result
│
├── result = SELECTED → [Claim a seat] → /events/[campaignId]/claim
├── result = STANDBY → show standby position
├── result = NOT_SELECTED → show audit link
└── result = PENDING → show "lottery not run yet"

text


## 4. Claim flow (winner path)
/events/[campaignId]/claim
│
├── Step 1: Human validation (challenge host)
│ │
│ ├── Turnstile / MediaPipe / Visual / Mock
│ └── On PASS → proceed to seat selection
│
├── Step 2: Seat selection (seat map)
│ │
│ └── On seat chosen → POST /entitlements/{id}/hold
│ │
│ ▼
│ /events/[campaignId]/claim (hold view with countdown)
│
├── Step 3: Confirm exact event/seat
│ │
│ └── POST /entitlements/{id}/redeem
│ │
│ ▼
│ /events/[campaignId]/confirmed
│
└── Hold expired? → return to seat selection step

text


## 5. Confirmation & receipt
/events/[campaignId]/confirmed
│
├── Show booking ID, event, seat, timestamp
├── [View fairness receipt] → /events/[campaignId]/audit
└── [Download receipt] → (future)

text


## 6. User account routes
/profile — profile summary, verification state, past bookings
/verify-email — email verification landing

text


## 7. Admin flow (parallel universe)
/admin/login
│
▼
/admin (dashboard: metrics overview)
│
├── /admin/campaigns (list all campaigns)
│ │
│ ├── [New campaign] → /admin/campaigns/new
│ │ │
│ │ ▼
│ │ Multi-step form → save DRAFT
│ │
│ └── Click campaign row → /admin/campaigns/[campaignId]
│ │
│ ├── /edit (edit draft fields)
│ ├── /monitor (live metrics)
│ ├── /draw (run lottery)
│ ├── /claims (hold/confirm status)
│ ├── /audit (admin audit view)
│ └── /simulations (adversarial testing shell)




## 8. Flow rules

- **Auth gate** triggers on any protected route if session missing. Preserve `?redirect=` param.
- **Mock mode** (`NEXT_PUBLIC_DEMO_MODE=true`) must allow full flow traversal without a backend.
- **State recovery**: every protected page calls `getCampaignStatus()` on mount to recover from refresh/reconnect.
- **Role-based routing**: `/admin/*` routes require `role === "ADMIN"`. Non-admin redirects to `/`.
- **No backend decisions in UI**: every state transition driven by API response, not local booleans.
- **Challenge host** is a reusable component. The claim flow and the admission flow both use it with different `operation` scope.