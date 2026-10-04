'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowRight, Check, Ticket, Loader2, AlertCircle, Clock } from 'lucide-react'
import { FairShell } from '@/components/fair-shell'
import { useAuth } from '@/lib/AuthContext'

export default function SignupPage() {
  const router = useRouter()
  const { signUp } = useAuth()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [cooldown, setCooldown] = useState<number>(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 1 ? prev - 1 : 0))
    }, 1000)
    return () => clearInterval(timer)
  }, [cooldown])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (cooldown > 0) return
    setErrorMsg(null)
    setSuccessMsg(null)
    setLoading(true)

    try {
      const { error } = await signUp(email, password)
      if (error) {
        const msg = error.message || ''
        const isRateLimit =
          msg.toLowerCase().includes('rate limit') ||
          msg.toLowerCase().includes('over_email_send_rate_limit') ||
          msg.toLowerCase().includes('security purposes')

        if (isRateLimit) {
          setErrorMsg(
            'Supabase Security Cooldown: Supabase cloud limits rapid account registrations to 1 request per 60 seconds per IP. Please wait for the cooldown timer below before creating another account.'
          )
          setCooldown(60)
        } else {
          setErrorMsg(msg)
        }
      } else {
        setSuccessMsg('Account created and verified successfully! Entering Fair Drop...')
        setTimeout(() => {
          router.push('/events')
        }, 1200)
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Signup failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <FairShell active="Sign up">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] px-5 py-12 sm:px-12 lg:grid lg:grid-cols-[0.8fr_1.2fr] lg:gap-16 lg:px-20 lg:py-20">
        <div>
          <p className="eyebrow">Join Fair Drop</p>
          <h1 className="section-title">
            CREATE YOUR<br />
            <span className="text-[var(--fd-pink)]">FAIR ACCESS.</span>
          </h1>
          <p className="mt-6 max-w-md text-lg font-medium leading-relaxed">
            Create one verified account for every fair drop. Your account helps us protect one-entry-per-person registration.
          </p>
          <div className="mt-8 flex flex-col gap-4">
            {['One verified entry per event', 'Recover your registration if you reconnect', 'Clear status updates from draw to seat'].map((item) => (
              <div key={item} className="flex items-center gap-3 text-sm font-bold">
                <span className="grid size-7 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)]">
                  <Check className="size-4" />
                </span>
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-5 shadow-[8px_8px_0_var(--fd-ink)] sm:p-8 lg:mt-0">
          <div className="flex items-center gap-3 border-b-[3px] border-[var(--fd-ink)] pb-5">
            <span className="grid size-10 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)]">
              <Ticket className="size-5" />
            </span>
            <div>
              <h2 className="font-display text-2xl font-black">Create Account</h2>
              <p className="text-sm font-medium opacity-70">Join 50,000+ fair drop participants</p>
            </div>
          </div>

          {errorMsg && (
            <div className="mt-5 flex items-center gap-3 border-[3px] border-[var(--fd-ink)] bg-[#FFEBEA] p-4 text-sm font-bold text-[var(--fd-red)] shadow-[4px_4px_0_var(--fd-ink)]">
              <AlertCircle className="size-5 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mt-5 flex items-center gap-3 border-[3px] border-[var(--fd-ink)] bg-[#E6F8F3] p-4 text-sm font-bold text-[var(--fd-teal)] shadow-[4px_4px_0_var(--fd-ink)]">
              <Check className="size-5 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
            <label className="flex flex-col gap-2 text-sm font-bold">
              Display name
              <input
                className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-4 py-3 outline-none focus:shadow-[4px_4px_0_var(--fd-pink)]"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Jane Doe"
              />
            </label>
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
                minLength={8}
                className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-4 py-3 outline-none focus:shadow-[4px_4px_0_var(--fd-pink)]"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
              />
            </label>
            <label className="flex items-start gap-3 text-sm font-medium">
              <input type="checkbox" defaultChecked className="mt-1 size-4 accent-[var(--fd-pink)]" />
              I agree to the Fair Drop terms and policy rules.
            </label>
            
            <button
              type="submit"
              disabled={loading || cooldown > 0}
              className="button-primary justify-center cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="size-5 animate-spin" /> Creating Account...
                </>
              ) : cooldown > 0 ? (
                <>
                  <Clock className="size-5 animate-pulse" /> Security Cooldown ({cooldown}s)
                </>
              ) : (
                <>
                  Create Account <ArrowRight className="size-5" />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm font-medium">
            Already have an account?{' '}
            <Link className="font-black underline text-[var(--fd-pink)]" href="/login">
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </FairShell>
  )
}

