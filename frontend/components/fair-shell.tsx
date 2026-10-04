'use client'

import { ArrowRight, Menu, ShieldCheck, ShieldAlert, Ticket, User, X, LayoutDashboard, LogOut, Loader2 } from 'lucide-react'
import { useState } from 'react'
import Link from 'next/link'
import type { DemoEvent } from '@/lib/demo-events'
import { useAuth } from '@/lib/AuthContext'

export function DevPersonaSwitcher() {
  const { user, signIn } = useAuth()
  const [switching, setSwitching] = useState<string | null>(null)

  const handleSwitch = async (email: string, pass: string) => {
    setSwitching(email)
    try {
      await signIn(email, pass)
    } catch (err) {
      console.warn('[PersonaSwitcher] Switch failed:', err)
    } finally {
      setSwitching(null)
    }
  }

  return (
    <div className="hidden sm:flex items-center gap-1.5 border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-2 py-1 font-mono text-[10px] font-bold shadow-[2px_2px_0_var(--fd-ink)]">
      <span className="text-[var(--fd-ink)]/70 uppercase">PERSONA:</span>
      <button
        type="button"
        disabled={!!switching || user?.email === 'admin@fairdrop.com'}
        onClick={() => handleSwitch('admin@fairdrop.com', 'AdminPassword123!')}
        className={`px-1.5 py-0.5 border border-[var(--fd-ink)] cursor-pointer transition-all ${
          user?.email === 'admin@fairdrop.com'
            ? 'bg-[var(--fd-ink)] text-[var(--fd-yellow)] font-black'
            : 'bg-white text-[var(--fd-ink)] hover:bg-neutral-100'
        }`}
        title="Switch active session to Administrator Operator (admin@fairdrop.com)"
      >
        {switching === 'admin@fairdrop.com' ? <Loader2 className="inline size-3 animate-spin" /> : '🛡️ Admin'}
      </button>
      <button
        type="button"
        disabled={!!switching || user?.email === 'user@fairdrop.com'}
        onClick={() => handleSwitch('user@fairdrop.com', 'UserPassword123!')}
        className={`px-1.5 py-0.5 border border-[var(--fd-ink)] cursor-pointer transition-all ${
          user?.email === 'user@fairdrop.com'
            ? 'bg-[var(--fd-ink)] text-[var(--fd-teal)] font-black'
            : 'bg-white text-[var(--fd-ink)] hover:bg-neutral-100'
        }`}
        title="Switch active session to Standard Attendee (user@fairdrop.com)"
      >
        {switching === 'user@fairdrop.com' ? <Loader2 className="inline size-3 animate-spin" /> : '🎟️ Attendee'}
      </button>
      <button
        type="button"
        disabled={!!switching || user?.email === 'ntc3108@gmail.com'}
        onClick={() => handleSwitch('ntc3108@gmail.com', 'Password123!')}
        className={`px-1.5 py-0.5 border border-[var(--fd-ink)] cursor-pointer transition-all ${
          user?.email === 'ntc3108@gmail.com'
            ? 'bg-[var(--fd-ink)] text-[var(--fd-pink)] font-black'
            : 'bg-white text-[var(--fd-ink)] hover:bg-neutral-100'
        }`}
        title="Switch active session to Naman Attendee (ntc3108@gmail.com)"
      >
        {switching === 'ntc3108@gmail.com' ? <Loader2 className="inline size-3 animate-spin" /> : '🎟️ Naman'}
      </button>
    </div>
  )
}

export function FairShell({ children, active }: { children: React.ReactNode; active?: string }) {
  const [open, setOpen] = useState(false)
  const { user, signOut, isAdmin } = useAuth()
  const baseLinks = [
    ['Explore Drops', '/events'],
    ['How It Works', '/#how-it-works'],
    ['Public Audit', '/events/camp_demo_001/audit'],
    ['My Profile', '/profile'],
  ]
  const links = isAdmin ? [...baseLinks, ['Admin Console', '/admin']] : baseLinks

  return (
    <main className="min-h-screen bg-[var(--fd-cream)] text-[var(--fd-ink)]">
      <div className="mx-auto max-w-[1440px] px-4 py-4 sm:px-8 lg:px-12">
        <nav className="relative z-30 flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-4 shadow-[6px_6px_0_var(--fd-ink)] sm:px-8">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-3" aria-label="Fair Drop home">
              <span className="grid size-10 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] shadow-[3px_3px_0_var(--fd-ink)]">
                <Ticket className="size-5" strokeWidth={3} />
              </span>
              <span className="font-display text-xl font-black tracking-[-0.06em]">FAIR DROP</span>
            </Link>
            <DevPersonaSwitcher />
          </div>
          <div className="hidden items-center gap-6 text-sm font-bold lg:flex">
            {links.map(([label, href]) => (
              <Link
                key={label}
                href={href}
                className={`nav-link ${active === label ? 'border-[var(--fd-pink)] text-[var(--fd-pink)]' : ''}`}
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="hidden items-center gap-3 sm:flex">
            {user ? (
              <>
                <span
                  className={`font-mono text-[10px] font-black uppercase px-2 py-1 border-2 border-[var(--fd-ink)] shadow-[2px_2px_0_var(--fd-ink)] flex items-center gap-1 ${
                    isAdmin
                      ? 'bg-[var(--fd-yellow)] text-[var(--fd-ink)]'
                      : 'bg-[var(--fd-teal)] text-[var(--fd-ink)]'
                  }`}
                  title={isAdmin ? 'Active role: Platform Admin Operator' : 'Active role: Standard Event Participant'}
                >
                  {isAdmin ? '🛡️ OPERATOR' : '🎟️ ATTENDEE'}
                </span>
                <Link href="/profile" className="button-secondary p-2.5 flex items-center gap-2" title="User Profile">
                  <User className="size-4" />
                  <span className="max-w-[120px] truncate">{user.email?.split('@')[0]}</span>
                </Link>
                <button
                  type="button"
                  onClick={() => signOut()}
                  className="button-secondary text-xs px-3 py-2 flex items-center gap-1.5"
                  title="Sign out of account"
                >
                  <LogOut className="size-3.5" /> Sign Out
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="button-secondary">
                  Sign In
                </Link>
                <Link href="/signup" className="button-secondary">
                  Sign Up
                </Link>
              </>
            )}
            <Link href="/events" className="button-primary">
              Explore Events <ArrowRight className="size-4" />
            </Link>
          </div>
          <button
            className="grid size-11 place-items-center border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] shadow-[3px_3px_0_var(--fd-ink)] lg:hidden"
            onClick={() => setOpen(!open)}
            aria-label="Toggle navigation"
            aria-expanded={open}
          >
            {open ? <X /> : <Menu />}
          </button>
          {open && (
            <div className="absolute left-0 right-0 top-[calc(100%+12px)] z-40 flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-5 shadow-[6px_6px_0_var(--fd-ink)] lg:hidden">
              {links.map(([label, href]) => (
                <Link key={label} href={href} onClick={() => setOpen(false)} className="font-bold">
                  {label}
                </Link>
              ))}
              <hr className="border-t-2 border-[var(--fd-ink)]" />
              {user ? (
                <>
                  <div className="flex items-center justify-between px-2 font-mono text-xs font-bold text-[var(--fd-ink)]/70">
                    <span>Signed in:</span>
                    <span className="truncate max-w-[180px]">{user.email}</span>
                  </div>
                  <Link href="/profile" onClick={() => setOpen(false)} className="button-secondary text-center">
                    My Profile
                  </Link>
                  <button
                    type="button"
                    onClick={() => { setOpen(false); signOut(); }}
                    className="button-secondary text-center flex items-center justify-center gap-2"
                  >
                    <LogOut className="size-4" /> Sign Out
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" onClick={() => setOpen(false)} className="button-secondary text-center">
                    Sign In
                  </Link>
                  <Link href="/signup" onClick={() => setOpen(false)} className="button-secondary text-center">
                    Create Account
                  </Link>
                </>
              )}
              <Link href="/events" className="button-primary text-center">
                Explore Events <ArrowRight className="inline size-4" />
              </Link>
            </div>
          )}
        </nav>
        {children}
        <footer className="flex flex-col gap-5 border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-ink)] px-5 py-8 text-[var(--fd-cream)] sm:flex-row sm:items-center sm:justify-between sm:px-12">
          <div>
            <div className="font-display text-2xl font-black">FAIR DROP.</div>
            <p className="mt-1 text-sm text-[var(--fd-muted)]">Fair allocation for high-demand events. Zero bot speed race.</p>
          </div>
          <div className="flex flex-wrap gap-5 text-xs font-bold uppercase">
            <Link href="/events">Events</Link>
            <Link href="/profile">Profile</Link>
            <Link href="/admin">Admin Suite</Link>
            <Link href="/events/camp_demo_001/audit">Public Audit</Link>
          </div>
        </footer>
      </div>
    </main>
  )
}

export function AdminShell({ children, campaignId, activeTab }: { children: React.ReactNode; campaignId?: string; activeTab?: string }) {
  const { user, signOut, isAdmin, role, loading: authLoading } = useAuth()
  const targetId = campaignId || 'camp_demo_001'

  // Non-admin participant guard: block standard users from operator console
  if (user && !isAdmin && !authLoading) {
    return (
      <main className="min-h-screen bg-[var(--fd-cream)] text-[var(--fd-ink)] flex items-center justify-center p-6">
        <div className="w-full max-w-lg border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-8 shadow-[10px_10px_0_var(--fd-ink)] text-center">
          <div className="mx-auto grid size-16 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] shadow-[4px_4px_0_var(--fd-ink)]">
            <ShieldAlert className="size-8 text-[var(--fd-ink)]" />
          </div>
          <span className="mt-4 inline-block border-2 border-[var(--fd-ink)] bg-red-100 px-3 py-1 font-mono text-xs font-black uppercase text-red-900">
            ACCESS RESTRICTED
          </span>
          <h1 className="font-display mt-3 text-3xl font-black">OPERATOR ACCESS REQUIRED</h1>
          <p className="mt-3 text-sm font-medium text-neutral-700 leading-relaxed">
            Your account <strong className="font-mono bg-neutral-200 px-1 border border-neutral-400">{user.email}</strong> holds standard participant privileges (role: <span className="font-mono font-bold text-blue-800">{role || 'USER'}</span>). The Admin Suite is restricted to platform operators.
          </p>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/events" className="button-primary bg-[var(--fd-pink)] text-xs font-mono font-bold">
              Return to User Portal
            </Link>
            <button
              type="button"
              onClick={async () => {
                await signOut()
                window.location.href = '/admin/login'
              }}
              className="button-secondary text-xs font-mono font-bold cursor-pointer"
            >
              Sign In With Admin Account
            </button>
          </div>
        </div>
      </main>
    )
  }

  const adminTabs = [
    ['Dashboard', '/admin'],
    ['Campaigns', '/admin/campaigns'],
    ['+ New Campaign', '/admin/campaigns/new'],
  ]

  const campaignSubTabs = [
    ['Overview', `/admin/campaigns/${targetId}`],
    ['Edit', `/admin/campaigns/${targetId}/edit`],
    ['Monitor', `/admin/campaigns/${targetId}/monitor`],
    ['Draw', `/admin/campaigns/${targetId}/draw`],
    ['Claims', `/admin/campaigns/${targetId}/claims`],
    ['Audit', `/admin/campaigns/${targetId}/audit`],
    ['Simulations', `/admin/campaigns/${targetId}/simulations`],
  ]

  return (
    <main className="min-h-screen bg-[var(--fd-cream)] text-[var(--fd-ink)]">
      <div className="mx-auto max-w-[1440px] px-4 py-4 sm:px-8 lg:px-12">
        <header className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-ink)] p-5 text-[var(--fd-cream)] shadow-[6px_6px_0_var(--fd-ink)] sm:px-8">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-full border-[3px] border-[var(--fd-cream)] bg-[var(--fd-yellow)] text-[var(--fd-ink)]">
                <LayoutDashboard className="size-5" />
              </span>
              <div>
                <h1 className="font-display text-2xl font-black tracking-tight">FAIR DROP / ADMIN SUITE</h1>
                <p className="text-xs font-mono text-[var(--fd-muted)]">SYSTEM STATUS: ALL ENGINE NODES OPERATIONAL · 0 OVERSELL</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <DevPersonaSwitcher />
              {user ? (
                <span className="hidden sm:inline font-mono text-[11px] text-[var(--fd-teal)] border border-[var(--fd-teal)] px-2 py-1 bg-black/40">
                  OPERATOR: {user.email}
                </span>
              ) : (
                <span className="hidden sm:inline font-mono text-[11px] text-[var(--fd-yellow)] border border-[var(--fd-yellow)] px-2 py-1 bg-black/40">
                  DEMO / SHOWCASE
                </span>
              )}
              <Link href="/events" className="border-2 border-[var(--fd-cream)] bg-transparent px-3 py-1.5 font-mono text-xs font-bold uppercase text-[var(--fd-cream)] hover:bg-[var(--fd-cream)] hover:text-[var(--fd-ink)]">
                Exit Admin
              </Link>
              {user ? (
                <button
                  type="button"
                  onClick={async () => {
                    await signOut()
                    window.location.href = '/admin/login'
                  }}
                  className="border-2 border-[var(--fd-cream)] bg-[var(--fd-pink)] px-3 py-1.5 font-mono text-xs font-bold uppercase text-[var(--fd-ink)] shadow-[3px_3px_0_var(--fd-cream)] cursor-pointer"
                >
                  Admin Logout
                </button>
              ) : (
                <Link href="/admin/login" className="border-2 border-[var(--fd-cream)] bg-[var(--fd-pink)] px-3 py-1.5 font-mono text-xs font-bold uppercase text-[var(--fd-ink)] shadow-[3px_3px_0_var(--fd-cream)]">
                  Sign In
                </Link>
              )}
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2 border-t border-neutral-700 pt-4">
            {adminTabs.map(([label, href]) => (
              <Link
                key={label}
                href={href}
                className={`border-2 border-[var(--fd-cream)] px-4 py-1.5 font-mono text-xs font-black uppercase ${
                  activeTab === label ? 'bg-[var(--fd-teal)] text-[var(--fd-ink)] shadow-[2px_2px_0_var(--fd-cream)]' : 'bg-neutral-800 text-[var(--fd-cream)]'
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
        </header>

        {campaignId && (
          <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-5 py-3 font-mono text-xs font-bold shadow-[4px_4px_0_var(--fd-ink)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>CAMPAIGN CONSOLE: <strong className="font-mono text-sm underline">{targetId}</strong></span>
              <div className="flex flex-wrap gap-2">
                {campaignSubTabs.map(([label, href]) => (
                  <Link
                    key={label}
                    href={href}
                    className={`border-2 border-[var(--fd-ink)] px-2.5 py-1 text-[11px] font-black uppercase ${
                      activeTab === label ? 'bg-[var(--fd-pink)] shadow-[2px_2px_0_var(--fd-ink)]' : 'bg-[var(--fd-card)]'
                    }`}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}

        {children}

        <footer className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-ink)] p-5 text-center text-xs font-mono text-[var(--fd-muted)]">
          FAIR DROP ADMIN CONTROL v1.0.4 · PARALLEL SEAT ALLOCATION ENGINE · CONFIDENTIAL OPERATOR ACCESS
        </footer>
      </div>
    </main>
  )
}

export function EventCard({ event }: { event: DemoEvent }) {
  return (
    <article className="event-card flex min-h-[290px] flex-col justify-between">
      <div>
        <div className="flex items-start justify-between">
          <span className="category" style={{ backgroundColor: event.color }}>
            {event.category}
          </span>
          <span className="font-mono text-xs font-bold">{event.date}</span>
        </div>
        <div className="mt-8">
          <h3 className="font-display text-3xl font-black leading-none tracking-[-0.06em]">{event.name}</h3>
          <p className="mt-2 text-sm font-medium">{event.venue}</p>
          <p className="mt-1 text-xs font-mono font-bold text-[var(--fd-ink)]/70">{event.seats} SEATS AVAILABLE · UNIFORM LOTTERY</p>
        </div>
      </div>
      <div className="mt-6 flex items-center justify-between border-t-[3px] border-[var(--fd-ink)] pt-4 text-xs font-bold uppercase">
        <StatusPill>{event.status}</StatusPill>
        <Link href={`/events/${event.id}`} className="button-primary text-xs py-1.5 px-3">
          View Drop <ArrowRight className="inline size-4" />
        </Link>
      </div>
    </article>
  )
}

export function PageIntro({ eyebrow, title, copy }: { eyebrow: string; title: React.ReactNode; copy?: string }) {
  return (
    <header className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-12 sm:px-12 lg:px-20">
      <p className="eyebrow">{eyebrow}</p>
      <h1 className="section-title max-w-4xl">{title}</h1>
      {copy && <p className="mt-6 max-w-2xl text-lg font-medium leading-relaxed">{copy}</p>}
    </header>
  )
}

export function ProgressSteps({ current }: { current: number }) {
  const steps = [
    { label: 'Event Info', path: 'detail' },
    { label: 'Waiting Room', path: 'waiting-room' },
    { label: 'Identity Register', path: 'register' },
    { label: 'Status & Draw', path: 'status' },
    { label: 'Lottery Result', path: 'result' },
    { label: 'Seat Selection', path: 'claim' },
    { label: 'Confirmed', path: 'confirmed' },
  ]

  return (
    <div className="overflow-x-auto border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 sm:p-6">
      <div className="flex min-w-[700px] items-center justify-between gap-2">
        {steps.map((s, i) => (
          <div
            key={s.label}
            className={`flex flex-1 items-center justify-center gap-2 border-[3px] border-[var(--fd-ink)] p-2.5 font-mono text-[11px] font-black uppercase ${
              i === current
                ? 'bg-[var(--fd-pink)] shadow-[3px_3px_0_var(--fd-ink)]'
                : i < current
                ? 'bg-[var(--fd-teal)]'
                : 'bg-[var(--fd-cream)] opacity-60'
            }`}
          >
            <span>{String(i + 1).padStart(2, '0')}</span>
            <span className="hidden sm:inline">{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Field({ label, placeholder, type = 'text', defaultValue, disabled = false }: { label: string; placeholder: string; type?: string; defaultValue?: string; disabled?: boolean }) {
  return (
    <label className="flex flex-col gap-2 text-sm font-bold">
      <span>{label}</span>
      <input
        type={type}
        placeholder={placeholder}
        defaultValue={defaultValue}
        disabled={disabled}
        className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-4 py-3 outline-none placeholder:text-[var(--fd-ink)]/45 focus:shadow-[4px_4px_0_var(--fd-pink)] disabled:opacity-60"
      />
    </label>
  )
}

export function DemoNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-4 text-xs font-mono font-bold shadow-[4px_4px_0_var(--fd-ink)]">
      ⚡ STATIC PROTOTYPE MODE: {children}
    </div>
  )
}

export function Button({ children, secondary = false, onClick, className = '' }: { children: React.ReactNode; secondary?: boolean; onClick?: () => void; className?: string }) {
  return (
    <button onClick={onClick} className={`${secondary ? 'button-secondary' : 'button-primary'} ${className}`}>
      {children}
    </button>
  )
}

export function IconBox({ children, color = 'var(--fd-pink)' }: { children: React.ReactNode; color?: string }) {
  return (
    <div className="grid size-14 place-items-center border-[3px] border-[var(--fd-ink)] shadow-[4px_4px_0_var(--fd-ink)]" style={{ backgroundColor: color }}>
      {children}
    </div>
  )
}

export function StatusPill({ children }: { children: React.ReactNode }) {
  return (
    <span className="border-[2px] border-[var(--fd-ink)] bg-[var(--fd-teal)] px-2.5 py-1 font-mono text-[10px] font-black uppercase shadow-[2px_2px_0_var(--fd-ink)]">
      {children}
    </span>
  )
}

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
    </div>
  )
}

export function CheckRow({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="flex gap-3 border-b-2 border-[var(--fd-ink)] py-3">
      <span className="grid size-7 shrink-0 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] font-black">✓</span>
      <div>
        <div className="font-bold text-sm">{title}</div>
        <div className="text-xs font-medium opacity-75">{copy}</div>
      </div>
    </div>
  )
}

export function TicketStub({ name, seatLabel = 'Seat A-042', campaignId = 'camp_demo_001' }: { name: string; seatLabel?: string; campaignId?: string }) {
  return (
    <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
      <div className="flex justify-between border-b-[3px] border-[var(--fd-ink)] pb-4 font-mono text-xs font-black">
        <span>FAIR DROP OFFICIAL PASS</span>
        <Ticket className="size-5" />
      </div>
      <div className="py-6">
        <div className="font-display text-3xl sm:text-4xl font-black leading-none">{name}</div>
        <div className="mt-3 font-mono text-xs font-bold uppercase bg-[var(--fd-card)] border-2 border-[var(--fd-ink)] p-2 inline-block">
          CONFIRMED ACCESS · {seatLabel}
        </div>
      </div>
      <div className="flex justify-between border-t-[3px] border-[var(--fd-ink)] pt-4 font-mono text-[11px] font-black">
        <span>REF: FD-2026-CONF-042</span>
        <span>CAMPAIGN: {campaignId}</span>
      </div>
    </div>
  )
}
