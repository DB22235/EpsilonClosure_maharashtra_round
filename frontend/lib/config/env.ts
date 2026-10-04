/**
 * Fair Drop — Environment Configuration
 *
 * Single module that reads and validates all NEXT_PUBLIC_* env vars.
 * Import from here — never use process.env directly in page components.
 *
 * Safe fallbacks prevent crashes during local dev without a .env file.
 */

function bool(value: string | undefined, fallback = false): boolean {
  if (value === undefined) return fallback
  return value === '1' || value.toLowerCase() === 'true'
}

function str(value: string | undefined, fallback: string): string {
  if (!value || value.trim() === '') return fallback
  return value.trim()
}

export const env = {
  /** Base URL of the FastAPI backend, without trailing slash */
  NEXT_PUBLIC_API_BASE_URL: str(
    process.env.NEXT_PUBLIC_API_BASE_URL,
    'http://localhost:8000/api/v1',
  ),

  /**
   * When true the app runs entirely in demo/mock mode:
   * - No real API calls are made.
   * - MockFairDropApi is used.
   * - No Supabase credentials are required.
   */
  NEXT_PUBLIC_DEMO_MODE: bool(process.env.NEXT_PUBLIC_DEMO_MODE, true),

  /** Supabase project URL — required when DEMO_MODE=false */
  NEXT_PUBLIC_SUPABASE_URL: str(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    '',
  ),

  /** Supabase anon/public key — required when DEMO_MODE=false */
  NEXT_PUBLIC_SUPABASE_ANON_KEY: str(
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    '',
  ),

  /** Cloudflare Turnstile site key — empty disables the widget */
  NEXT_PUBLIC_TURNSTILE_SITE_KEY: str(
    process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY,
    '',
  ),
} as const

export type Env = typeof env
