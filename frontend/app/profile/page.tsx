'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowRight, CheckCircle2, ShieldCheck, Ticket, User, Mail, Phone, ExternalLink, RefreshCw, LogIn, AlertCircle } from 'lucide-react'
import { DemoNotice, FairShell, PageIntro, StatusPill } from '@/components/fair-shell'
import { useAuth } from '@/lib/AuthContext'
import { api, FairDropApiError } from '@/lib/api'

interface BackendMeData {
  profile?: {
    id: string
    user_id: string
    email: string
    role: string
    created_at: string
  }
  participant?: {
    id: string
    profile_id: string
    device_fingerprint_id?: string
    verification_status: string
    risk_level: string
    created_at: string
  }
  server_time?: string
}

export default function ProfilePage() {
  const { user, loading: authLoading, signOut } = useAuth()
  const [backendData, setBackendData] = useState<BackendMeData | null>(null)
  const [loadingBackend, setLoadingBackend] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchProfile = async () => {
    if (!user) return
    setLoadingBackend(true)
    setError(null)
    try {
      const data = await api.me()
      setBackendData(data)
    } catch (err: any) {
      console.error('[Profile] Failed to fetch /auth/me:', err)
      if (err instanceof FairDropApiError) {
        setError(`[${err.code}] ${err.message}`)
      } else {
        setError(err.message || 'Failed to connect to Fair Drop backend')
      }
    } finally {
      setLoadingBackend(false)
    }
  }

  useEffect(() => {
    if (user) {
      fetchProfile()
    } else {
      setBackendData(null)
    }
  }, [user])

  const userInitials = (user?.email?.substring(0, 2) || 'FD').toUpperCase()
  const memberDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
    : '2026'

  // Registrations placeholder for demo / active user
  const activeRegistrations = [
    {
      campaignId: 'camp_demo_001',
      eventName: 'Future / Forward 2026',
      status: 'SELECTED (WINNER)',
      date: 'APR 18, 2026',
      seat: 'Seat A-042',
      claimLink: '/events/camp_demo_001/confirmed',
    },
    {
      campaignId: 'camp_demo_002',
      eventName: 'Sunset Sessions Brooklyn',
      status: 'REGISTERED',
      date: 'MAY 02, 2026',
      seat: 'Pending Draw',
      claimLink: '/events/camp_demo_002/status',
    },
  ]

  return (
    <FairShell active="My Profile">
      <PageIntro
        eyebrow="Participant Profile"
        title={
          <>
            MY FAIR DROP<br />
            <span className="text-[var(--fd-pink)]">ACCOUNT & PASSES.</span>
          </>
        }
        copy="Manage your verified identity credentials, track active registrations, and retrieve confirmed event seat passes."
      />

      <section className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-12 sm:px-12 lg:px-20">
        {!user && !authLoading ? (
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-8 shadow-[8px_8px_0_var(--fd-ink)] mb-10 text-center max-w-xl mx-auto">
            <h2 className="font-display text-2xl font-black mb-3">NOT SIGNED IN</h2>
            <p className="text-sm font-medium mb-6">
              You are currently browsing as a guest. Sign in or create an account to verify your identity and enter fair drops.
            </p>
            <div className="flex justify-center gap-4">
              <Link href="/login" className="button-primary">
                <LogIn className="size-4" /> Sign In
              </Link>
              <Link href="/signup" className="button-secondary">
                Create Account
              </Link>
            </div>
          </div>
        ) : null}

        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          {/* User Account Info */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[8px_8px_0_var(--fd-ink)]">
            <div className="flex items-center gap-4 border-b-[3px] border-[var(--fd-ink)] pb-4">
              <div className="grid size-14 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] font-display text-2xl font-black">
                {userInitials}
              </div>
              <div className="min-w-0">
                <h2 className="font-display text-2xl font-black truncate">
                  {user ? user.email?.split('@')[0] : 'Guest User'}
                </h2>
                <div className="flex items-center gap-2 mt-1">
                  <StatusPill>
                    {backendData?.participant?.verification_status || (user ? 'AUTHENTICATED' : 'ANONYMOUS')}
                  </StatusPill>
                  {backendData?.profile?.role && (
                    <span className="border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] px-2 py-0.5 font-mono text-[10px] font-black uppercase">
                      {backendData.profile.role}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {error && (
              <div className="mt-4 border-2 border-red-600 bg-red-100 p-3 text-xs font-mono font-bold text-red-900 flex items-start gap-2">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p>{error}</p>
                  <button
                    onClick={fetchProfile}
                    className="mt-2 flex items-center gap-1 underline text-[11px]"
                  >
                    <RefreshCw className="size-3" /> Retry Sync
                  </button>
                </div>
              </div>
            )}

            <div className="mt-6 flex flex-col gap-4 font-mono text-xs font-bold">
              <div className="flex items-center gap-3 border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-3">
                <Mail className="size-4 shrink-0 text-[var(--fd-pink)]" />
                <span className="truncate">{user ? user.email : 'Not logged in'}</span>
              </div>

              {backendData?.participant && (
                <>
                  <div className="flex items-center justify-between border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-3">
                    <span className="text-[var(--fd-ink)]/70">RISK LEVEL:</span>
                    <span className={`px-2 py-0.5 border border-[var(--fd-ink)] ${
                      backendData.participant.risk_level === 'LOW' ? 'bg-green-200' : 'bg-yellow-200'
                    }`}>
                      {backendData.participant.risk_level}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1 border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-3">
                    <span className="text-[10px] text-[var(--fd-ink)]/70">PARTICIPANT ID:</span>
                    <span className="truncate font-mono text-[11px] select-all">
                      {backendData.participant.id}
                    </span>
                  </div>
                </>
              )}

              <div className="flex items-center gap-3 border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-3">
                <ShieldCheck className="size-4 shrink-0 text-[var(--fd-pink)]" />
                <span>1 VERIFIED ENTRY PER CAMPAIGN</span>
              </div>
            </div>

            <div className="mt-6 border-t-2 border-[var(--fd-ink)] pt-4 text-xs font-mono font-bold flex items-center justify-between">
              <span>MEMBER SINCE {memberDate.toUpperCase()}</span>
              {user && (
                <button
                  onClick={() => signOut()}
                  className="underline hover:text-[var(--fd-pink)] cursor-pointer"
                >
                  Sign Out
                </button>
              )}
            </div>
          </div>

          {/* Active Registrations & Tickets */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[8px_8px_0_var(--fd-ink)]">
            <h2 className="font-display text-2xl font-black mb-4">
              MY CAMPAIGN REGISTRATIONS ({activeRegistrations.length})
            </h2>

            <div className="flex flex-col gap-4">
              {activeRegistrations.map((reg) => (
                <div
                  key={reg.campaignId}
                  className="flex flex-col gap-3 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-5 shadow-[4px_4px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <span className="font-mono text-xs font-black uppercase text-[var(--fd-ink)]/70">
                      {reg.date} · {reg.seat}
                    </span>
                    <h3 className="font-display text-xl font-black">{reg.eventName}</h3>
                    <div className="mt-2">
                      <StatusPill>{reg.status}</StatusPill>
                    </div>
                  </div>

                  <Link href={reg.claimLink} className="button-primary text-xs py-2 px-3 self-start sm:self-auto">
                    View Status <ArrowRight className="size-4" />
                  </Link>
                </div>
              ))}
            </div>

            <div className="mt-8 border-t-2 border-[var(--fd-ink)] pt-6">
              <h3 className="font-display text-xl font-black mb-3">ADMIN ACCESS</h3>
              <p className="text-xs font-medium mb-4">
                Have administrative privileges? Access the Fair Drop campaign manager suite.
              </p>
              <Link href="/admin" className="button-secondary text-sm">
                Open Admin Suite <ExternalLink className="size-4" />
              </Link>
            </div>

            <div className="mt-6">
              <DemoNotice>
                {user ? 'Connected to live Supabase Authentication session.' : 'Static preview. Sign in to link live entries.'}
              </DemoNotice>
            </div>
          </div>
        </div>
      </section>
    </FairShell>
  )
}
