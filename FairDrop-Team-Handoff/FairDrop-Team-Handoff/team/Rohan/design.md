# Fair Drop — Visual Design System

## 1. Design direction

The visual language should feel trustworthy under pressure: dark event-console foundations, high-contrast status colors, clear typography, and a strong distinction between user-facing fairness evidence and operator metrics.

The design should communicate:

- Calm control rather than panic.
- Transparency rather than mystery.
- Secure progress rather than competitive speed.
- Evidence rather than marketing claims.

Use the team’s existing design template for layout and component structure. This document defines the shared visual language, not a replacement template.

## 2. Color theme

### Core palette

```text
Midnight Navy       #0B1020   main application background
Deep Violet         #17113B   panels and hero surfaces
Electric Indigo     #5B5CE2   primary action and active links
Fairness Cyan       #29D3D8   verified/audit/information accent
Soft Lavender       #B9B8FF   secondary text and chart highlight
Cloud White         #F7F8FC   primary text on dark surfaces
Slate               #98A2B3   secondary text
Border               #2C3150   cards, dividers, input borders
```

### Status palette

```text
Success Green       #22C55E   confirmed, valid, available
Warning Amber       #F59E0B   pending, challenge required, expiring soon
Danger Red          #EF4444   rejected, expired, replay, oversell alert
Info Blue           #38BDF8   neutral system information
Standby Purple      #A78BFA   standby status
```

Use status color with text and/or icon. Never communicate meaning through color alone.

## 3. Surface hierarchy

- `App background`: Midnight Navy.
- `Primary panel`: Deep Violet or a slightly lighter navy.
- `Elevated card`: `#20264A`.
- `Input background`: `#11172C`.
- `Primary button`: Electric Indigo.
- `Primary button hover`: lighter indigo.
- `Secondary button`: transparent with Border outline.
- `Audit highlights`: Fairness Cyan with dark text where contrast allows.

Avoid excessive gradients, glowing effects, or animated noise during the booking flow. The dashboard may use restrained gradients for grouping but must remain readable.

## 4. Typography

Use a clean sans-serif such as Inter, system UI, or the existing design template’s approved font. Use a monospace face only for:

- Entry IDs.
- Request IDs.
- Roster hashes.
- Audit references.
- Technical metrics.

Suggested scale:

```text
Display       40–48 px
Page heading  28–36 px
Section       20–24 px
Body          15–17 px
Caption       12–14 px
Metric        24–32 px
```

Keep body line-height comfortable. Avoid dense walls of small text during the event flow.

## 5. User-facing status language

Use direct text:

- `Registration is open`.
- `Your entry is accepted`.
- `Your entry is already recorded`.
- `Registration is closed`.
- `You were selected`.
- `You are on standby: position 42`.
- `Your hold expires in 01:32`.
- `This entitlement has expired`.
- `We are checking your saved status`.
- `Repeated attempts triggered a temporary cooldown`.

Never say “You won because you were fastest” or imply that a queue number is a guaranteed seat.

## 6. Main screens

### Public event page

Hero section with event title, capacity policy, registration window, and a compact “How fairness works” explanation. The primary action should be obvious without making the user believe that early milliseconds decide the result.

### Waiting room

Show campaign state, server-synchronized countdown, connection status, and admission explanation. Use a calm progress surface rather than a casino-like race display.

### Registration receipt

Show accepted status, entry ID, policy version, and what happens next. Provide a refresh-safe status link.

### Challenge surface

Use one instruction, one timer, visible progress, camera permission state, and an accessible fallback. Avoid shaming language for failure.

### Result page

Use large status treatment: winner/standby/not selected/pending. Show only the information the participant should see. Explain next action and expiry clearly.

### Redemption page

Show server-reconciled hold timer, validation progress, selected event/seat details, confirm button, and expiry warnings.

### Operator dashboard

Use grouped cards for Participation, Allocation, Inventory, Reliability/Security. Include charts comparing valid entries and selection rates across simulator classes.

## 7. Accessibility

- Keyboard navigable controls.
- Visible focus states.
- Semantic headings and labels.
- Screen-reader status announcements for state changes.
- No camera-only path.
- No color-only status.
- Reduced-motion support.
- Clear timeout warnings.
- Adequate touch targets.
- Responsive layout.
- High contrast for text and controls.

## 8. Charts and evidence

Recommended chart colors:

```text
Normal human       Soft Lavender
Fast bot           Warning Amber
Burst bot          Danger Red
Retry bot          Fairness Cyan
Shared-network     Info Blue
Slow/accessibility Success Green
```

Always label the denominator. A chart must distinguish:

```text
raw requests
valid entries
winners
selection rate
```

## 9. Component rules

- Buttons must show disabled/loading state during mutations.
- Mutation retries preserve idempotency keys.
- Toasts are supplemental; important state appears in the page.
- Errors use a stable code plus human-readable message.
- Hashes and IDs use copy controls and monospace styling.
- Do not render fake inventory numbers.
- Do not hide critical expiry information.
