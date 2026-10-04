# Fair Drop — Routing & Guard Map

## Route categories

| Category     | Path pattern                        | Guard                            | Fallback if denied         |
|--------------|-------------------------------------|----------------------------------|----------------------------|
| Public       | `/`, `/events`, `/events/[id]`      | None                             | —                          |
| Auth         | `/login`, `/signup`, `/verify-email`| Redirect if already signed in    | `/events`                  |
| User         | `/events/[id]/waiting-room` → `/confirmed`, `/profile` | Requires session            | `/login?redirect=<path>`   |
| Admin        | `/admin/*`                          | Requires session + ADMIN role    | `/` or `/admin/login`      |

## Guard behavior

1. **`<AuthGuard>`** — wraps user-protected routes. Reads session from `AuthProvider`. If no session → redirect to `/login?redirect=<current path>`.
2. **`<AdminGuard>`** — wraps `/admin/*`. If no session → `/admin/login`. If session but role ≠ ADMIN → `/` with unauthorized toast.
3. **`<GuestGuard>`** — wraps `/login`, `/signup`. If already authenticated → redirect to `?redirect` param or `/events`.

## Redirect preservation

- Clicking **[Explore Events]** on landing while unauthenticated → `/login?redirect=/events`
- Clicking **[Join Fair Drop]** on event page while unauthenticated → `/login?redirect=/events/[id]`
- After successful login → navigate to `redirect` param or `/events` by default.

## Layout structure

- `app/layout.tsx` — root layout with `<AuthProvider>` and global nav shell.
- `app/(public)/layout.tsx` — public nav (Logo, Explore, Login/Signup).
- `app/(auth)/layout.tsx` — centered minimal auth layout.
- `app/(user)/layout.tsx` — authenticated user shell (Logo, Explore, Profile, Logout).
- `app/admin/layout.tsx` — admin sidebar + topbar.

## Nav state

- Nav must reflect auth state reactively.
- Unauthenticated: shows `[Login]` `[Sign up]`.
- Authenticated USER: shows `[Explore]` `[Profile]` `[Logout]`.
- Authenticated ADMIN: additionally shows `[Admin Console]`.