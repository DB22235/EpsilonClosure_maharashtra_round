'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowRight, Lock, ShieldAlert, LayoutDashboard, RefreshCw, AlertCircle } from 'lucide-react'
import { DemoNotice } from '@/components/fair-shell'
import { useAuth } from '@/lib/AuthContext'
import { api, FairDropApiError } from '@/lib/api'

export default function AdminLoginPage() {
  const router = useRouter()
  const { signIn, signOut } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setErrorCode(null)
    setLoading(true)

    try {
      // 1. Authenticate with Supabase
      const { error: authError } = await signIn(email, password)
      if (authError) {
        throw new Error(authError.message || 'Authentication failed. Please verify credentials.')
      }

      // 2. Verify ADMIN role against backend
      try {
        const adminProfile = await api.adminMe()
        if (adminProfile?.role?.toUpperCase() !== 'ADMIN') {
          throw new Error('Access Denied: Your account does not hold operator privileges (profiles.role = "ADMIN").')
        }
        router.push('/admin')
      } catch (roleErr: any) {
        if (roleErr instanceof FairDropApiError) {
          if (roleErr.status === 403) {
            setErrorCode(roleErr.code)
            throw new Error('Access Denied: Your account does not hold operator privileges (profiles.role = "ADMIN").')
          }
          setErrorCode(roleErr.code)
          throw new Error(roleErr.message)
        }
        throw roleErr
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred during admin sign in.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[var(--fd-cream)] text-[var(--fd-ink)] flex items-center justify-center p-4">
      <div className="w-full max-w-md border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[10px_10px_0_var(--fd-ink)] sm:p-8">
        <div className="flex flex-col items-center text-center border-b-[3px] border-[var(--fd-ink)] pb-6">
          <div className="grid size-14 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] shadow-[4px_4px_0_var(--fd-ink)]">
            <LayoutDashboard className="size-7 text-[var(--fd-ink)]" />
          </div>
          <h1 className="font-display mt-4 text-3xl font-black">ADMIN SUITE LOGIN</h1>
          <p className="mt-1 font-mono text-xs font-bold text-[var(--fd-ink)]/70 uppercase">
            OPERATOR CONTROL CONSOLE
          </p>
        </div>

        {error && (
          <div className="mt-6 border-[3px] border-[var(--fd-ink)] bg-red-100 p-4 shadow-[4px_4px_0_var(--fd-ink)]">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="size-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <strong className="font-display text-sm font-black text-red-700 block">
                  {errorCode ? `ERROR: ${errorCode}` : 'AUTHENTICATION FAILED'}
                </strong>
                <p className="font-mono text-xs font-bold text-red-900 mt-1 leading-snug">
                  {error}
                </p>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-xs font-mono font-bold uppercase">
            <span>Operator Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@yourdomain.com"
              required
              className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-mono font-bold uppercase">
            <span>Security Passcode</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            className="button-primary justify-center text-center mt-2 bg-[var(--fd-pink)] cursor-pointer disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="size-4 animate-spin" /> Verifying Operator Credentials...
              </>
            ) : (
              <>
                Sign In to Admin Dashboard <ArrowRight className="size-5" />
              </>
            )}
          </button>

          <Link
            href="/admin"
            className="button-secondary justify-center text-center text-xs font-mono py-2"
          >
            Continue in Demo / Showcase Mode →
          </Link>
        </form>

        <div className="mt-6">
          <DemoNotice>
            Role-Based Access: Accounts must have profiles.role = &apos;ADMIN&apos; to access live operator controls. Or click Showcase Mode to inspect offline.
          </DemoNotice>
        </div>
      </div>
    </main>
  )
}

