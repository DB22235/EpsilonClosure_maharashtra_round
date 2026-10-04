# Fair Drop — Final v0 Frontend Build Prompt

Copy everything inside the prompt section into **v0.dev**.

---

## Prompt for v0.dev

Build a complete, clean, production-structured **Next.js App Router frontend** for a hackathon project called **Fair Drop**.

This is a frontend-only project for now. The backend will be integrated later through a documented FastAPI HTTP API. Build the UI with a clean adapter boundary so the mock/demo data can be replaced by the real backend without rewriting the pages or components.

The generated project must be downloadable as a complete ZIP/repository and must run locally after installation with a standard command such as:

```bash
npm install
npm run dev
```

Use TypeScript throughout. Use clean, descriptive names. Do not generate random placeholder files, unnecessary initialization code, fake backend business logic, or unrelated demo components.

---

# 1. Product context

Fair Drop is a high-demand event registration and limited-seat allocation system for situations such as concerts, movies, conferences, sports events, university events, and other limited-capacity bookings.

The simulated scenario is:

```text
500 seats
up to 50,000 competing participants
```

The product does not claim to detect every bot. Its actual promise is:

> **An automated client must not gain a meaningful allocation advantage merely by being faster, sending more requests, repeating attempts, replaying tokens, creating extra traffic, or manipulating the queue.**

The core fairness model is:

```text
Published event
  → authenticated user
  → waiting room/admission gate
  → identity and risk checks
  → one idempotent registration per verified participant
  → registration closes
  → eligible roster freezes
  → deterministic uniform lottery
  → winner or standby result
  → short-lived entitlement
  → human validation when required
  → temporary seat hold
  → exact event/seat confirmation
  → confirmed booking and receipt
```

The waiting room protects infrastructure. It does not secretly select winners. Registration speed and repeated request volume must not create extra lottery entries.

---

# 2. Visual direction: Neo-brutalist event-security platform

Use a polished **Neo-brutalist editorial event platform** visual style inspired by the supplied reference image.

The reference image has:

- Warm off-white background.
- Thick black borders.
- Strong black typography.
- Bright pink, yellow, teal, blue, purple, and red accents.
- Large playful typography.
- Offset hard shadows.
- Sticker-like labels.
- Hand-drawn arrows and graphic shapes.
- Slightly irregular, energetic composition.
- Clear sections and strong visual hierarchy.

Do not copy the reference image literally. Adapt its design language to Fair Drop.

The UI must feel:

- Trustworthy.
- Friendly.
- Clear.
- Energetic.
- Secure.
- Modern.
- Appropriate for a serious high-demand booking platform.

Do not make the product look like a childish game. Use playful Neo-brutalism for visual identity, but preserve clarity for timers, booking states, security messages, and dashboards.

## Recommended visual tokens

```text
Canvas background: #F7F1E8
Primary ink:       #111111
Card background:   #FFFDF8
Pink:              #FF62B0
Yellow:            #FFD447
Teal:              #24C7B5
Blue:              #86A8FF
Purple:            #A98BFF
Red:               #F04444
Green:             #39D98A
Muted ink:         #5F5A52
Soft cream:        #EFE6D8
```

Use CSS variables for all colors. Do not hard-code colors throughout components.

## Neo-brutalist component rules

- Use thick 2px or 3px black borders.
- Use hard offset shadows such as `6px 6px 0 #111111`.
- Avoid blurry glassmorphism and excessive gradients.
- Use rounded corners sparingly, mostly between 10px and 18px.
- Use sticker, badge, label, and tape-like elements for status.
- Use strong contrast and readable text.
- Use visible focus rings.
- Never communicate state through color alone.
- Do not use animations that distract from countdowns or security states.
- Make the UI responsive from mobile width to large desktop.

## Typography

Use a bold display font for headings and a highly readable sans-serif for body text.

Preferred options:

```text
Headings: Space Grotesk, Archivo Black, or equivalent bold display font
Body: Inter or equivalent readable sans-serif
Numbers/timers: JetBrains Mono or equivalent monospace font
```

Use typography hierarchy:

- Very large display heading for the landing page.
- Bold but compact headings for dashboards.
- Monospace for countdowns, seat counts, latency, and request IDs.
- Do not use excessive all-caps for long sentences.

---

# 3. Technical requirements

Use:

- Next.js App Router.
- TypeScript.
- Tailwind CSS or a clean CSS-variable design-token system.
- Reusable component architecture.
- Accessible semantic HTML.
- Responsive layout.
- Lucide icons or another consistent icon library.
- Recharts or an equivalent chart library for dashboard visualizations.
- A lightweight client-side state solution only if needed.

Do not add a heavy state library unless necessary.

Do not connect to a real backend yet. Build a typed mock API adapter with the same interface that the FastAPI backend will later implement.

Do not place Supabase service-role keys in frontend code.

Create frontend environment variable examples only:

```text
NEXT_PUBLIC_API_BASE_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_TURNSTILE_SITE_KEY=
```

Use safe mock fallbacks when these variables are empty. Clearly mark all mock behavior as replaceable.

---

# 4. Required project structure

Create a clean, extensible structure similar to:

```text
app/
  layout.tsx
  page.tsx
  globals.css
  (public)/
    events/page.tsx
    events/[campaignId]/page.tsx
    events/[campaignId]/waiting-room/page.tsx
    events/[campaignId]/register/page.tsx
    events/[campaignId]/status/page.tsx
    events/[campaignId]/result/page.tsx
    events/[campaignId]/claim/page.tsx
    events/[campaignId]/confirmed/page.tsx
    events/[campaignId]/audit/page.tsx
  (auth)/
    login/page.tsx
    signup/page.tsx
    verify-email/page.tsx
  (user)/
    profile/page.tsx
  admin/
    login/page.tsx
    page.tsx
    campaigns/page.tsx
    campaigns/new/page.tsx
    campaigns/[campaignId]/page.tsx
    campaigns/[campaignId]/edit/page.tsx
    campaigns/[campaignId]/monitor/page.tsx
    campaigns/[campaignId]/draw/page.tsx
    campaigns/[campaignId]/claims/page.tsx
    campaigns/[campaignId]/audit/page.tsx
    campaigns/[campaignId]/simulations/page.tsx

components/
  brand/
  layout/
  navigation/
  events/
  waiting-room/
  registration/
  challenges/
  seats/
  claims/
  results/
  audit/
  admin/
  metrics/
  feedback/
  ui/

lib/
  api/
    client.ts
    types.ts
    errors.ts
    campaigns.ts
    registration.ts
    challenges.ts
    entitlements.ts
    admin.ts
    metrics.ts
  auth/
    auth-provider.tsx
    route-guards.ts
    supabase-browser.ts
  config/
    env.ts
  mocks/
    mock-api.ts
    mock-data.ts
    mock-session.ts
  state/
  timers/
    server-clock.ts
    use-countdown.ts
  utils/

public/
  illustrations/
  patterns/

hooks/
  use-campaign-status.ts
  use-registration-status.ts
  use-entitlement.ts
  use-server-countdown.ts

schemas/
  api.ts
  forms.ts

types/
  domain.ts

README.md
.env.example
package.json
```

If v0 uses a slightly different Next.js structure, preserve the same separation of concerns and naming principles.

---

# 5. Domain types and states

Create centralized TypeScript types. Do not repeat string literals across pages.

## Roles

```ts
type UserRole = "USER" | "ADMIN"
```

## Campaign states

```ts
type CampaignStatus =
  | "DRAFT"
  | "PREPARING"
  | "OPEN"
  | "CLOSED"
  | "FROZEN"
  | "DRAWING"
  | "CLAIMING"
  | "COMPLETED"
```

## Registration states

```ts
type RegistrationStatus =
  | "RECEIVED"
  | "VALIDATING"
  | "ACCEPTED"
  | "DUPLICATE"
  | "REJECTED"
  | "QUARANTINED"
```

## Entitlement states

```ts
type EntitlementStatus =
  | "SELECTED"
  | "CLAIM_PENDING"
  | "HELD"
  | "CONFIRMED"
  | "EXPIRED"
```

## Seat states

```ts
type SeatStatus = "AVAILABLE" | "HELD" | "CONFIRMED"
```

## User result states

```ts
type AllocationResult = "PENDING" | "SELECTED" | "STANDBY" | "NOT_SELECTED"
```

## Admission states

```ts
type AdmissionState =
  | "WAITING"
  | "ADMITTED"
  | "CHALLENGE_REQUIRED"
  | "COOLDOWN"
  | "EXPIRED"
```

## Risk levels

```ts
type RiskLevel = "LOW" | "MEDIUM" | "HIGH"
```

## Challenge types

```ts
type ChallengeType = "TURNSTILE" | "MEDIAPIPE" | "VISUAL" | "MOCK"
```

Use explicit states instead of multiple conflicting booleans.

---

# 6. Flexible event model

The frontend must support different event types without hard-coding the entire UI to concerts.

Create a generic event model:

```ts
interface CampaignSummary {
  id: string
  name: string
  description: string
  category: "GENERAL" | "CONCERT" | "MOVIE" | "SPORTS" | "CONFERENCE" | "OTHER"
  venue?: string
  city?: string
  eventStart?: string
  imageUrl?: string
  capacity: number
  registrationStart: string
  registrationEnd: string
  redemptionDeadline: string
  maxTicketsPerParticipant: number
  allocationMethod: "UNIFORM_LOTTERY"
  standbyPolicy: "FIXED_ORDER"
  status: CampaignStatus
  policyVersion: string
  tags: string[]
}
```

Create extensible optional details without forcing them into the current UI:

```ts
interface EventDetails {
  category: CampaignSummary["category"]
  organizerName?: string
  ageRestriction?: string
  durationMinutes?: number
  language?: string
  accessibilityNotes?: string[]
  customFields?: Record<string, string | number | boolean>
}
```

For now, use a general event presentation that works for:

- Concerts.
- Movies.
- Sports events.
- Conferences.
- University events.
- General limited-seat events.

Do not build separate concert/movie booking logic yet. Create an extension point for future event-specific detail modules.

---

# 7. Public and user pages

## 7.1 Landing page `/`

Create a visually strong Neo-brutalist landing page.

Hero copy:

```text
FAIR ACCESS.
NO BOT RACE.
```

Supporting copy:

```text
A transparent registration and allocation platform for high-demand events.
One verified entry. A fair draw. Atomic seat protection.
```

Hero actions:

```text
[Explore events]
[How Fair Drop works]
```

Hero visual should include:

- A stylized ticket/seat illustration.
- A bright “500 seats” sticker.
- A “50,000 participants” label.
- A small “0 overselling” badge.
- A large simple visual explaining that speed does not decide winners.

Sections:

1. Active event preview.
2. Three principles:
   - Remove the race.
   - Protect the inventory.
   - Show the evidence.
3. Simple process timeline.
4. Security/friction explanation.
5. Auditability section.
6. CTA to explore events.

Do not use fake real-time metrics on the public landing page. If mock metrics are shown, label them as demo data.

## 7.2 Events page `/events`

Create an event discovery page with:

- Page heading: “Open Fair Drops”.
- Search input.
- Category filter.
- Status filter.
- Sort control.
- Responsive event cards.

Event cards should show:

- Event category sticker.
- Event name.
- General image or color block.
- Date/time.
- Venue.
- Capacity.
- Registration status.
- Registration deadline.
- Allocation type.
- Button: `View event` or `Join registration`.

Keep the card generic enough for future event types.

## 7.3 Event detail page `/events/[campaignId]`

Show:

- Generic event hero.
- Category badge.
- Name.
- Description.
- Date and venue.
- Capacity.
- Registration countdown.
- Registration start/end.
- Maximum tickets per participant.
- “Uniform lottery” explanation.
- “One verified participant = one entry” explanation.
- Privacy and terms links.
- Policy version.
- Event-specific custom fields when present.

Primary button changes by backend state:

```text
Registration not started → Notify me
Registration open       → Join Fair Drop
Registration closed     → Registration closed
Lottery pending         → View status
Claiming                → View result
Completed               → View audit
```

If unauthenticated, preserve the return URL and send the user to login.

## 7.4 Login `/login`

Build a friendly Supabase-ready login form:

- Email.
- Password or magic-link mode.
- Continue button.
- Forgot password.
- Link to signup.
- Clear verification/error messages.
- Preserve redirect URL.

The actual Supabase calls may be represented by an auth adapter/mock in the generated frontend, but structure the code so a real Supabase client can replace it.

## 7.5 Signup `/signup`

Fields:

- Display name.
- Email.
- Password.
- Confirm password.
- Terms checkbox.

Show that email verification is required before registration.

## 7.6 Verify email `/verify-email`

Show:

- Email destination.
- Resend button.
- Verification status.
- Return-to-event action.

## 7.7 Waiting room `/events/[campaignId]/waiting-room`

This page must feel reassuring, not stressful.

Show:

- Event name.
- “You are safely in the waiting room.”
- Status indicator.
- Registration countdown.
- Optional estimated admission time.
- “Do not refresh” guidance.
- “Your valid registration will be recovered if you reconnect.”
- Small explanation that the waiting room protects the system, while the lottery decides allocation.
- Current risk/challenge state only in user-friendly language.

Do not imply that being first in the waiting room guarantees winning.

Use a sticker:

```text
SPEED DOES NOT BUY EXTRA CHANCES
```

## 7.8 Registration page `/events/[campaignId]/register`

Show:

- Authenticated user identity summary.
- Email verification state.
- Optional phone verification state.
- Event summary.
- One-entry policy.
- Human-validation explanation.
- Consent checkbox.
- Register button.
- Loading state.
- Idempotent retry-safe message.

Possible results:

```text
Registration accepted
Already registered
Challenge required
Cooldown active
Registration closed
Quarantined for review
```

Do not show technical risk-score internals to normal users.

## 7.9 Registration status `/events/[campaignId]/status`

Create a visual timeline:

```text
Account verified
Registration recorded
Registration window
Roster freeze
Lottery draw
Result available
```

Show:

- Registration ID.
- Policy version.
- Registration timestamp.
- Deadline.
- Current state.
- Server-synchronized last updated time.
- Refresh/reconnect reassurance.

## 7.10 Result page `/events/[campaignId]/result`

### Selected state

Use celebratory but not excessive styling:

```text
YOU’RE IN THE DRAW WINNER CIRCLE
```

Show:

- Event name.
- Selected result.
- Claim deadline.
- Entitlement status.
- `Claim a seat` button.
- Audit references.

### Standby state

Show:

- Standby position.
- Fixed-order explanation.
- Promotion rule.
- Current standby state.
- No misleading guarantee.

### Not selected state

Show:

- Clear result.
- Appreciation message.
- Public audit link.
- Future events CTA.

### Pending state

Show:

- “The lottery has not run yet.”
- Frozen roster/policy status.
- Expected result timing if available.

## 7.11 Claim page `/events/[campaignId]/claim`

Flow:

```text
Selected entitlement
  → Human validation if required
  → Seat selection
  → Temporary hold
  → Exact confirmation
```

Do not make the page look like a payment page because the MVP has no real payment.

## 7.12 Challenge host

Create a reusable challenge shell:

```text
ChallengeHeader
ChallengeInstruction
ChallengeViewport
ChallengeTimer
ChallengeProgress
ChallengeFallback
ChallengeResult
```

Supported visual modes:

1. Cloudflare Turnstile placeholder/adapter.
2. MediaPipe gesture game placeholder/adapter.
3. Confusing-image challenge.
4. Mock challenge for demo mode.

Show a short explanation:

```text
This quick interaction helps protect the drop from repeated automated requests.
It is one security signal, not a judgment about your identity.
```

For MediaPipe, include UI states for:

- Show open palm.
- Thumbs up.
- Thumbs down.
- Two fingers.
- Hold hand in target.

Each game should have:

- Instruction.
- 5–10 second timer.
- Progress indicator.
- Success state.
- Retry state.
- Failure state.
- Accessible alternative.

Do not implement the CV model in the frontend prompt. Create a clean adapter interface for Naman’s implementation.

## 7.13 Seat selection

Create a reusable generic seat-map component.

Use simple numbered seats in sections/rows. Do not hard-code a cinema-only layout.

Seat states:

```text
Available → cream/green treatment
Held      → yellow treatment
Confirmed → pink/purple treatment
Disabled  → muted gray treatment
Selected  → bold blue outline and thick shadow
```

The frontend must treat the backend response as authoritative. If a seat becomes unavailable, show a clear recovery state and refresh the seat map.

## 7.14 Seat hold and confirmation

Show:

- Event name.
- Selected seat.
- Participant identity.
- Server-synchronized countdown.
- `Confirm booking` button.
- `Release seat` option only if policy allows it.
- Expiry warning.

Timer states:

```text
Over 60 seconds → green
30–60 seconds   → yellow
Under 30 seconds → red
Expired          → blocked and refreshed
```

The timer is a visual display only. The backend decides expiry.

## 7.15 Confirmation page `/events/[campaignId]/confirmed`

Show:

- Large confirmed badge.
- Booking ID.
- Event name.
- Date/time.
- Venue.
- Seat.
- Participant name/email.
- Confirmation timestamp.
- Fairness receipt reference.
- Audit page link.
- Download/print receipt button if feasible.

## 7.16 Audit page `/events/[campaignId]/audit`

Show public aggregate evidence:

- Policy version.
- Registration cutoff.
- Registered count.
- Eligible count.
- Duplicate count.
- Roster hash shortened with copy button.
- Randomness reference.
- Lottery algorithm version.
- Winner count.
- Standby rule.
- Oversell count.
- Duplicate allocation count.
- Aggregate selection metrics.

Do not display private participant identities.

---

# 8. Admin pages

## 8.1 Admin login `/admin/login`

Same Supabase-ready auth structure, but after login verify admin role through the backend.

Show a clear unauthorized state if the authenticated account is not an admin.

## 8.2 Admin dashboard `/admin`

Neo-brutalist operations console.

Show metric cards:

```text
Active campaigns
Registered participants
Eligible entries
Confirmed seats
Suspicious attempts
Bot advantage
Overselling incidents
p95 latency
```

Use strong labels and short explanations.

## 8.3 Campaign list `/admin/campaigns`

Show table/cards with:

- Event name.
- Status.
- Capacity.
- Registered count.
- Eligible count.
- Confirmed count.
- Registration deadline.
- Policy version.
- Actions.

## 8.4 Create campaign `/admin/campaigns/new`

Build a clean multi-section form:

### Basic event information

- Event name.
- Description.
- Category.
- Venue.
- City.
- Event date/time.
- Optional image.

### Capacity and allocation

- Capacity.
- Numbered seats toggle.
- Maximum tickets per participant.
- Allocation method, currently fixed to uniform lottery.
- Standby policy, currently fixed to fixed order.

### Registration timing

- Registration start.
- Registration end.
- Redemption deadline.

### Eligibility and verification

- Verified email required.
- Phone verification optional.
- Human validation mode.
- Accessible alternative enabled.

### Published policy

- Policy version.
- Terms.
- Privacy notice.
- Event notes.

Display a live “policy preview” before save.

## 8.5 Campaign detail/monitor

Show:

- Campaign state timeline.
- Registered and eligible counts.
- Waiting/admission information.
- Risk distribution.
- Challenge activity.
- Duplicate requests.
- Cooldowns.
- Inventory state.
- p95/p99 latency.
- Error/retry rates.
- Pause/resume controls.

## 8.6 Draw page

Show pre-draw confirmation:

```text
Capacity: 500
Eligible entries: 46,890
Allocation: Uniform lottery
Policy version: v1.0
Roster hash: 8f4c...a21
```

Require explicit confirmation before running the draw.

After draw, show:

- Winner count.
- Standby count.
- Randomness reference.
- Algorithm version.
- Audit record.

## 8.7 Claims page

Show tabs:

```text
Selected
Claim pending
Held
Confirmed
Expired
Standby
```

Show seat and entitlement state clearly.

## 8.8 Simulations page

Create a frontend shell for future simulator integration.

Show configurable client profiles:

- Normal human.
- Fast bot.
- Burst bot.
- Retry bot.
- Account farm.
- Direct API bot.
- Token replay attacker.
- Race-condition attacker.
- Shared-network user.
- Slow/accessibility user.

Controls:

- Number of clients.
- Request rate.
- Account count.
- IP diversity.
- Timing jitter.
- Retry behavior.
- Challenge behavior.
- Defence layers enabled.

Use mock data only for the UI shell and label it clearly until Dhanya’s simulator is connected.

---

# 9. Dashboard metrics and charts

Use actual API-ready data structures, not hard-coded chart-only arrays hidden inside visual components.

Required charts:

1. Registration attempts over time.
2. Human versus automated client selection rate.
3. Bot advantage ratio.
4. Risk-level distribution.
5. Challenge success/failure/abandonment.
6. Available/held/confirmed inventory.
7. Hold expiry rate.
8. p95 and p99 latency.
9. Error and retry rate.
10. Duplicate attempts and cooldowns.

Most important chart title:

```text
Does more automation create more allocation chances?
```

The chart should compare:

- Normal users.
- Fast bots.
- Burst bots.
- Retry bots.

Use consistent legend labels. Do not present mock numbers as real results.

---

# 10. Auth and integration boundaries

Create a clean `AuthProvider` abstraction.

Example interface:

```ts
interface AuthSession {
  userId: string
  email?: string
  role?: "USER" | "ADMIN"
  accessToken?: string
}

interface AuthClient {
  getSession(): Promise<AuthSession | null>
  signIn(input: SignInInput): Promise<AuthSession>
  signUp(input: SignUpInput): Promise<void>
  signOut(): Promise<void>
  refreshSession(): Promise<AuthSession | null>
}
```

Implement a mock version for local UI preview and leave a clear adapter point for Supabase.

Create a clean `FairDropApi` interface:

```ts
interface FairDropApi {
  listCampaigns(): Promise<CampaignSummary[]>
  getCampaign(id: string): Promise<CampaignSummary>
  joinCampaign(id: string): Promise<AdmissionResponse>
  getCampaignStatus(id: string): Promise<CampaignUserStatus>
  register(id: string, input: RegisterInput, idempotencyKey: string): Promise<RegistrationResponse>
  createChallenge(input: CreateChallengeInput): Promise<ChallengeResponse>
  verifyChallenge(id: string, input: VerifyChallengeInput, idempotencyKey: string): Promise<ChallengeVerificationResponse>
  getResult(id: string): Promise<AllocationResultResponse>
  holdSeat(entitlementId: string, input: HoldSeatInput, idempotencyKey: string): Promise<SeatHoldResponse>
  redeemEntitlement(entitlementId: string, input: RedeemInput, idempotencyKey: string): Promise<BookingConfirmation>
  releaseEntitlement(entitlementId: string, idempotencyKey: string): Promise<void>
  getAudit(id: string): Promise<PublicAudit>
  getMetrics(id: string): Promise<MetricsSnapshot>
}
```

Create:

```text
MockFairDropApi
HttpFairDropApi
```

The page components must depend on `FairDropApi`, not directly on fetch calls or mock arrays.

---

# 11. Mock/demo behavior

The generated UI must be runnable without a backend.

Create a clearly isolated demo mode:

```text
NEXT_PUBLIC_DEMO_MODE=true
```

Mock behavior should support navigating through:

- Unauthenticated user.
- Authenticated normal user.
- Authenticated admin.
- Waiting state.
- Registration accepted.
- Challenge required.
- Cooldown state.
- Selected winner.
- Standby user.
- Not selected user.
- Seat selection.
- Seat hold countdown.
- Confirmed booking.
- Expired hold.
- Campaign paused.

Provide a small developer/demo state switcher only in development mode. Do not expose it in production UI.

Use stable deterministic mock IDs such as:

```text
camp_demo_001
user_demo_001
reg_demo_001
ent_demo_001
seat_demo_A18
```

Do not generate random IDs during every render. Avoid hydration mismatches.

---

# 12. Error, loading, and recovery states

Every page that communicates with the API needs:

- Loading skeleton.
- Empty state.
- Error state.
- Retry action.
- Unauthorized state where applicable.
- Paused state where applicable.
- Request ID display for support/debugging.

Important UI states:

```text
Registration not started
Registration closed
Campaign paused
Waiting for admission
Admission permit expired
Challenge required
Challenge failed
Cooldown active
Already registered
Roster frozen
Lottery pending
Selected
Standby
Not selected
Entitlement expired
Seat unavailable
Hold expired
Booking confirmed
Session expired
Reconnecting
Backend temporarily unavailable
Admin unauthorized
```

Use friendly language. Do not expose raw stack traces.

Example cooldown message:

```text
Repeated attempts detected

This operation is temporarily paused for your session.
Please try again in 05:00.
Your valid registration has not been deleted.
```

Example error footer:

```text
Request ID: req_demo_123
```

---

# 13. Accessibility requirements

The frontend must support:

- Keyboard navigation.
- Visible focus states.
- Semantic headings.
- Proper labels for inputs.
- `aria-live` for countdown/status updates where appropriate.
- Reduced-motion preference.
- High color contrast.
- Non-color status indicators.
- No camera-only requirement.
- Accessible alternative to MediaPipe interaction.
- Mobile viewport support.
- Screen-reader-friendly error text.

Do not use flashing animations for the timer.

Do not make confusing visual challenges the only path.

---

# 14. Responsive behavior

Mobile must be a first-class layout, not a shrunk desktop version.

On mobile:

- Convert navigation into a compact menu.
- Stack event details and CTA.
- Keep timers prominent.
- Make seat map horizontally scrollable or section-based.
- Keep buttons large enough to tap.
- Make admin dashboard cards stack cleanly.
- Avoid excessive decorative shapes covering content.

On desktop:

- Use editorial two-column hero layouts.
- Use dashboard side navigation.
- Use large metric cards and charts.
- Keep content width readable.

---

# 15. Naming and code quality requirements

Use:

- `PascalCase` for React components.
- `camelCase` for variables/functions.
- `UPPER_SNAKE_CASE` for fixed constants.
- Descriptive route and domain names.
- Small focused components.
- Typed props.
- Centralized domain types.
- Centralized API errors.
- Centralized design tokens.

Avoid:

- `Thing`, `Box`, `Stuff`, `Data`, `Temp`, or unexplained abbreviations.
- Duplicate types in multiple files.
- Random initialization during render.
- API calls directly inside large JSX blocks.
- Backend rules hidden inside UI components.
- Hard-coded seat counts scattered across the project.
- Fake metrics mixed with API types.
- Unused imports.
- Dead components.
- Excessive comments explaining obvious code.
- Unrelated packages.
- Placeholder lorem ipsum.

Use realistic copy for Fair Drop.

---

# 16. Security boundaries in the UI

The frontend must not:

- Decide whether a user is a winner.
- Decide whether a seat is available.
- Trust a browser timer for expiry.
- Store service-role credentials.
- Treat a queue number as authorization.
- Treat a challenge result as final human proof.
- Allow a user to set their own admin role.
- Display private participant lists.
- Retry state-changing requests with new idempotency keys.

The frontend may:

- Display backend states.
- Request a challenge.
- Host the MediaPipe/visual challenge.
- Display server-supplied timestamps.
- Submit user intent and confirmations.
- Recover state through the status endpoint.

---

# 17. Required README

Create a high-quality README containing:

1. Project overview.
2. Fair Drop fairness principle.
3. Screenshot or route overview.
4. Tech stack.
5. Local setup.
6. Environment variables.
7. Demo mode instructions.
8. Supabase integration instructions.
9. FastAPI API integration instructions.
10. Route map.
11. Domain state map.
12. Mock API replacement instructions.
13. Challenge adapter integration instructions.
14. Accessibility notes.
15. Known backend-pending integrations.
16. Deployment instructions for Vercel.
17. Code organization.
18. How to run lint/typecheck/build.

Include commands:

```bash
npm install
npm run dev
npm run lint
npm run typecheck
npm run build
```

If the generated project does not include scripts for `typecheck`, add them.

---

# 18. Definition of done for the v0 frontend

The generated frontend is complete when:

- It runs cleanly with `npm install` and `npm run dev`.
- It builds cleanly with `npm run build`.
- It has no intentional TypeScript errors.
- Public event discovery works in demo mode.
- Login/signup screens exist with an auth adapter boundary.
- User and admin route structures exist.
- Admin can create/configure a mock campaign through the UI.
- User can view a generic event of any category.
- Waiting room exists.
- Registration flow exists.
- Challenge host exists with Turnstile, MediaPipe, visual, and mock extension points.
- Registration status page exists.
- Result page supports selected, standby, not-selected, and pending states.
- Seat map exists.
- Seat hold timer exists and uses server-time-shaped data.
- Booking confirmation exists.
- Public audit page exists.
- Admin monitoring dashboard exists.
- Metrics cards and charts are API-ready.
- Cooldown, pause, expiry, and recovery states exist.
- Refresh/reconnect recovery is represented through a status adapter.
- API and auth logic are not scattered through components.
- Mock data is deterministic and isolated.
- The project is easy to replace with FastAPI and Supabase later.
- The UI is accessible and responsive.
- The interface follows the Neo-brutalist Fair Drop design system.

---

# 19. Final build instruction

Build the complete frontend now according to this specification.

Prioritize:

1. Clean architecture.
2. Flexible backend integration.
3. Complete user and admin flow.
4. Clear event-type extensibility.
5. Realistic loading/error/recovery states.
6. Accessibility.
7. Responsive behavior.
8. High-quality Neo-brutalist visual design.
9. Deterministic mock behavior.
10. No unnecessary backend assumptions.

Do not implement a fake backend inside the UI. Implement a replaceable mock adapter and clear API contracts.

Do not omit screens simply because their backend integration is pending. Build the UI state and adapter boundary now, and mark only the data source/integration as pending.

Do not invent unrelated features.

Do not use random initialization, random IDs per render, placeholder lorem ipsum, or unclear naming.

The final result should look like a strong hackathon-ready product that can later connect to:

```text
Next.js on Vercel
Supabase Auth
FastAPI modular monolith
PostgreSQL
Optional Redis
Cloudflare Turnstile
MediaPipe challenge adapter
Adversarial simulator
```

The product tagline is:

> **Fair access. Verifiable allocation. Zero bot advantage.**
