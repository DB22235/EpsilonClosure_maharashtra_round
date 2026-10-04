'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowRight, Loader2, AlertCircle } from 'lucide-react'
import { FairShell } from '@/components/fair-shell'
import { useAuth } from '@/lib/AuthContext'

export default function LoginPage() {
  const router = useRouter()
  const { signIn } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setLoading(true)

    try {
      const { error } = await signIn(email, password)
      if (error) {
        setErrorMsg(error.message)
      } else {
        router.push('/events')
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <FairShell active="Sign In">
      <section className="grid min-h-[680px] items-center gap-12 border-x-[3px] border-b-[3px] border-[var(--fd-ink)] px-5 py-14 sm:px-12 lg:grid-cols-2 lg:px-20">
        <div className="max-w-xl">
          <p className="eyebrow">Your fair access pass</p>
          <h1 className="section-title">
            WELCOME<br />
            <span className="text-[var(--fd-pink)]">BACK.</span>
          </h1>
          <p className="mt-7 text-lg font-medium leading-relaxed">
            One verified account. One eligible entry per event. Your dashboard keeps every registration, result, and claim in one place.
          </p>
          <div className="mt-8 grid gap-4 text-sm font-bold">
            <div className="flex items-center gap-3">
              <span className="grid size-7 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] font-black">✓</span>
              No speed advantage or request racing
            </div>
            <div className="flex items-center gap-3">
              <span className="grid size-7 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] font-black">✓</span>
              Auditable uniform lottery allocation
            </div>
          </div>
        </div>

        <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[8px_8px_0_var(--fd-ink)] sm:p-8">
          <div className="mb-7 flex border-[3px] border-[var(--fd-ink)] p-1 bg-[var(--fd-cream)]">
            <Link href="/login" className="flex-1 p-3 text-center text-sm font-black uppercase bg-[var(--fd-pink)] border-r-2 border-[var(--fd-ink)]">
              Sign In
            </Link>
            <Link href="/signup" className="flex-1 p-3 text-center text-sm font-black uppercase hover:bg-[var(--fd-muted)]">
              Create Account
            </Link>
          </div>

          {errorMsg && (
            <div className="mb-5 flex items-center gap-3 border-[3px] border-[var(--fd-ink)] bg-[#FFEBEA] p-4 text-sm font-bold text-[var(--fd-red)] shadow-[4px_4px_0_var(--fd-ink)]">
              <AlertCircle className="size-5 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <label className="flex flex-col gap-2 text-sm font-bold">
              Email address
              <input
                type="email"
                required
                className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-4 py-3 outline-none focus:shadow-[4px_4px_0_var(--fd-pink)]"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-bold">
              Password
              <input
                type="password"
                required
                className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-4 py-3 outline-none focus:shadow-[4px_4px_0_var(--fd-pink)]"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </label>

            <div className="flex items-center justify-between text-xs font-bold">
              <label className="flex items-center gap-2">
                <input type="checkbox" defaultChecked className="size-4 accent-[var(--fd-pink)]" /> Remember me
              </label>
              <a href="#" className="underline">Forgot password?</a>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="button-primary justify-center cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="size-5 animate-spin" /> Signing In...
                </>
              ) : (
                <>
                  Sign In <ArrowRight className="size-5" />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm font-medium">
            Don't have an account?{' '}
            <Link href="/signup" className="font-black underline text-[var(--fd-pink)]">
              Sign Up
            </Link>
          </p>
        </div>
      </section>
    </FairShell>
  )
}

