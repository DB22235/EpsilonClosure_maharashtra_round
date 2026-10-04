'use client'

import {
  ArrowRight,
  Check,
  ChevronRight,
  CircleDot,
  Fingerprint,
  LogOut,
  Menu,
  ShieldCheck,
  Sparkles,
  Ticket,
  Trophy,
  User,
  X,
  Zap,
} from 'lucide-react'
import { useState } from 'react'
import Link from 'next/link'
import { demoEvents } from '@/lib/demo-events'
import { useAuth } from '@/lib/AuthContext'

const principles = [
  {
    number: '01',
    title: 'REMOVE THE RACE',
    copy: 'Speed, refreshes, and request volume do not create extra chances.',
    icon: Zap,
    color: 'var(--fd-yellow)',
  },
  {
    number: '02',
    title: 'PROTECT INVENTORY',
    copy: 'Atomic seat holds mean one seat can never belong to two people.',
    icon: ShieldCheck,
    color: 'var(--fd-teal)',
  },
  {
    number: '03',
    title: 'SHOW THE EVIDENCE',
    copy: 'Every draw produces an auditable receipt with frozen roster hash.',
    icon: Fingerprint,
    color: 'var(--fd-pink)',
  },
]

const steps = [
  ['01', 'ENTER THE DROP', 'A calm waiting room protects the system.'],
  ['02', 'ONE VERIFIED ENTRY', 'Your identity creates one eligible chance.'],
  ['03', 'FAIR DRAW', 'A frozen roster is shuffled uniformly.'],
  ['04', 'CLAIM YOUR SEAT', 'Human confirmation completes the booking.'],
]

export default function Page() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { user, signOut } = useAuth()

  return (
    <main className="min-h-screen overflow-hidden bg-[var(--fd-cream)] text-[var(--fd-ink)]">
      <div className="mx-auto max-w-[1440px] px-4 py-4 sm:px-8 lg:px-12">
        <nav className="relative z-20 flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-4 shadow-[6px_6px_0_var(--fd-ink)] sm:px-8">
          <Link href="/" className="flex items-center gap-3" aria-label="Fair Drop home">
            <span className="grid size-10 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] shadow-[3px_3px_0_var(--fd-ink)]">
              <Ticket aria-hidden="true" className="size-5" strokeWidth={3} />
            </span>
            <span className="font-display text-xl font-black tracking-[-0.06em]">FAIR DROP</span>
          </Link>

          <div className="hidden items-center gap-8 text-sm font-bold lg:flex">
            <a className="nav-link" href="#how-it-works">How it works</a>
            <a className="nav-link" href="#events">Active drops</a>
            <a className="nav-link" href="#evidence">Evidence</a>
            <Link className="nav-link" href="/admin">Admin Console</Link>
          </div>

          <div className="hidden items-center gap-3 sm:flex">
            {user ? (
              <>
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
                  Login
                </Link>
                <Link href="/signup" className="button-secondary">
                  Sign Up
                </Link>
              </>
            )}
            <Link href="/events" className="button-primary">
              Explore Events <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </div>
          <button
            className="grid size-11 place-items-center border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] shadow-[3px_3px_0_var(--fd-ink)] lg:hidden"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          </button>
          {menuOpen && (
            <div className="absolute left-0 right-0 top-[calc(100%+12px)] flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-5 shadow-[6px_6px_0_var(--fd-ink)] lg:hidden">
              {user ? (
                <>
                  <div className="flex items-center justify-between px-2 font-mono text-xs font-bold text-[var(--fd-ink)]/70">
                    <span>Signed in:</span>
                    <span className="truncate max-w-[180px]">{user.email}</span>
                  </div>
                  <Link href="/profile" onClick={() => setMenuOpen(false)} className="button-secondary text-center">
                    My Profile
                  </Link>
                  <button
                    type="button"
                    onClick={() => { setMenuOpen(false); signOut(); }}
                    className="button-secondary text-center flex items-center justify-center gap-2"
                  >
                    <LogOut className="size-4" /> Sign Out
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" onClick={() => setMenuOpen(false)} className="button-secondary text-center">Login</Link>
                  <Link href="/signup" onClick={() => setMenuOpen(false)} className="button-secondary text-center">Sign Up</Link>
                </>
              )}
              <Link href="/events" onClick={() => setMenuOpen(false)} className="button-primary text-center">Explore Events</Link>
              <Link href="/admin" onClick={() => setMenuOpen(false)}>Admin Console</Link>
            </div>
          )}
        </nav>

        <section id="top" className="relative grid min-h-[650px] items-center gap-12 border-x-[3px] border-b-[3px] border-[var(--fd-ink)] px-5 py-16 sm:px-12 lg:grid-cols-[1fr_0.9fr] lg:px-20 lg:py-24">
          <div className="relative z-10 max-w-2xl">
            <div className="mb-7 inline-flex -rotate-2 items-center gap-2 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] px-4 py-2 text-xs font-black uppercase shadow-[4px_4px_0_var(--fd-ink)]">
              <CircleDot className="size-4" aria-hidden="true" /> Built for high-demand events
            </div>
            <p className="mb-5 font-mono text-sm font-bold uppercase tracking-[0.16em]">A better way to get in</p>
            <h1 className="font-display max-w-[700px] text-[clamp(4rem,9vw,8.2rem)] font-black leading-[0.84] tracking-[-0.09em]">
              FAIR ACCESS.<br />
              <span className="text-[var(--fd-pink)] [text-shadow:4px_4px_0_var(--fd-ink)]">NO BOT RACE.</span>
            </h1>
            <p className="mt-8 max-w-xl text-lg font-medium leading-relaxed sm:text-xl">
              A transparent registration and allocation platform for high-demand events. One verified entry. A fair draw. Atomic seat protection.
            </p>
            <div className="mt-9 flex flex-wrap gap-4">
              <Link href="/events" className="button-primary">
                Explore Events <ArrowRight aria-hidden="true" className="size-5" />
              </Link>
              <a href="#how-it-works" className="button-secondary">
                How It Works
              </a>
            </div>
            <div className="mt-10 flex flex-wrap gap-3 text-xs font-bold uppercase tracking-wide">
              <span className="sticker bg-[var(--fd-card)]">
                <Check aria-hidden="true" className="size-4 text-[var(--fd-teal)]" /> 0 overselling
              </span>
              <span className="sticker bg-[var(--fd-card)]">
                <Check aria-hidden="true" className="size-4 text-[var(--fd-teal)]" /> Auditable draw
              </span>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-[520px] lg:rotate-2">
            <div className="absolute -right-2 -top-10 z-10 rotate-6 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-5 py-3 font-display text-xl font-black shadow-[5px_5px_0_var(--fd-ink)] sm:-right-8">
              <span className="font-mono text-sm">UP TO</span><br />50,000 PEOPLE
            </div>
            <div className="relative border-[3px] border-[var(--fd-ink)] bg-[var(--fd-blue)] p-5 shadow-[10px_10px_0_var(--fd-ink)] sm:p-8">
              <div className="flex items-start justify-between">
                <span className="font-mono text-xs font-bold uppercase">Fair drop / 2026</span>
                <Trophy aria-hidden="true" className="size-8" />
              </div>
              <div className="mt-14 grid place-items-center">
                <div className="relative grid aspect-square w-[72%] place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] shadow-[7px_7px_0_var(--fd-ink)]">
                  <div className="grid aspect-square w-[67%] place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)]">
                    <Ticket aria-hidden="true" className="size-24 -rotate-12 sm:size-32" strokeWidth={1.7} />
                  </div>
                  <span className="absolute -bottom-4 -left-8 rotate-[-8deg] border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] px-3 py-2 font-mono text-xs font-bold shadow-[4px_4px_0_var(--fd-ink)]">
                    ONE ENTRY<br />PER PERSON
                  </span>
                </div>
              </div>
              <div className="mt-14 flex items-end justify-between border-t-[3px] border-[var(--fd-ink)] pt-4">
                <div>
                  <div className="font-mono text-xs font-bold uppercase">Available seats</div>
                  <div className="font-display text-5xl font-black tracking-[-0.08em]">500</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-xs font-bold uppercase">Allocation</div>
                  <div className="font-display text-2xl font-black">LOTTERY</div>
                </div>
              </div>
            </div>
            <div className="absolute -bottom-7 -right-3 rotate-[-7deg] border-[3px] border-[var(--fd-ink)] bg-[var(--fd-red)] px-4 py-3 font-display text-lg font-black text-white shadow-[4px_4px_0_var(--fd-ink)]">
              SPEED ≠ CHANCE
            </div>
          </div>
        </section>

        <section id="events" className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-16 sm:px-12 lg:px-20">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <p className="eyebrow">Open now</p>
              <h2 className="section-title">
                FIND YOUR<br />
                <span className="text-[var(--fd-teal)]">FAIR DROP.</span>
              </h2>
            </div>
            <Link href="/events" className="button-secondary self-start sm:self-auto">
              View All Drops <ChevronRight aria-hidden="true" className="size-4" />
            </Link>
          </div>
          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            {demoEvents.map((event) => (
              <article key={event.id} className="event-card flex flex-col justify-between">
                <div>
                  <div className="flex items-start justify-between">
                    <span className="category" style={{ backgroundColor: event.color }}>
                      {event.category}
                    </span>
                    <span className="font-mono text-xs font-bold">{event.date}</span>
                  </div>
                  <div className="mt-14">
                    <h3 className="font-display text-3xl font-black leading-none tracking-[-0.06em]">{event.name}</h3>
                    <p className="mt-2 text-sm font-medium">{event.venue} · {event.seats} seats</p>
                  </div>
                </div>
                <div className="mt-8 flex items-center justify-between border-t-[3px] border-[var(--fd-ink)] pt-4 text-xs font-bold uppercase">
                  <span>Uniform lottery</span>
                  <Link href="/login" className="underline underline-offset-4">
                    View Drop <ArrowRight aria-hidden="true" className="inline size-4" />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] px-5 py-16 sm:px-12 lg:px-20">
          <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
            <div>
              <p className="eyebrow">The fairness model</p>
              <h2 className="section-title">
                THE SYSTEM<br />STAYS <span className="text-[var(--fd-pink)]">CALM.</span>
              </h2>
              <p className="mt-6 max-w-md text-lg font-medium leading-relaxed">
                We remove the race instead of asking legitimate people to race bots. The waiting room protects infrastructure; the draw decides winners.
              </p>
            </div>
            <div className="grid gap-4">
              {steps.map(([number, title, copy]) => (
                <div key={number} className="flex gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
                  <span className="font-mono text-sm font-bold">{number}</span>
                  <div>
                    <h3 className="font-display text-xl font-black">{title}</h3>
                    <p className="mt-1 text-sm font-medium">{copy}</p>
                  </div>
                  <ArrowRight aria-hidden="true" className="ml-auto hidden size-5 shrink-0 sm:block" />
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="evidence" className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-purple)] px-5 py-16 sm:px-12 lg:px-20">
          <div className="grid gap-10 lg:grid-cols-[1fr_1fr] lg:items-center">
            <div>
              <p className="eyebrow">Proof over promises</p>
              <h2 className="section-title">
                EVERY DROP<br />LEAVES A <span className="text-[var(--fd-yellow)] [text-shadow:3px_3px_0_var(--fd-ink)]">TRAIL.</span>
              </h2>
              <p className="mt-6 max-w-lg text-lg font-medium leading-relaxed">
                A public fairness receipt shows the policy version, roster hash, lottery method, and zero-oversell result. No hidden queue advantage. No mystery winners.
              </p>
              <Link href="/events/camp_demo_001/audit" className="button-primary mt-8 bg-[var(--fd-yellow)] text-[var(--fd-ink)]">
                See Sample Audit <ArrowRight aria-hidden="true" className="size-5" />
              </Link>
            </div>
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-5 shadow-[8px_8px_0_var(--fd-ink)] sm:p-7">
              <div className="flex items-center justify-between border-b-[3px] border-[var(--fd-ink)] pb-4">
                <span className="font-mono text-xs font-bold uppercase">Fairness receipt / #FD-2026</span>
                <Sparkles aria-hidden="true" className="size-5" />
              </div>
              <div className="grid grid-cols-2 gap-5 py-6 sm:grid-cols-3">
                <div>
                  <span className="metric-label">Eligible</span>
                  <strong className="metric-value">41,205</strong>
                </div>
                <div>
                  <span className="metric-label">Winners</span>
                  <strong className="metric-value">500</strong>
                </div>
                <div>
                  <span className="metric-label">Oversell</span>
                  <strong className="metric-value text-[var(--fd-teal)]">0</strong>
                </div>
              </div>
              <div className="flex items-center gap-3 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] p-3 font-mono text-xs font-bold">
                <Check aria-hidden="true" className="size-5" /> DRAW VERIFIED · UNIFORM LOTTERY
              </div>
            </div>
          </div>
        </section>

        <section className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-5 py-16 text-center sm:px-12 lg:px-20">
          <p className="eyebrow justify-center">Your next fair chance</p>
          <h2 className="font-display text-5xl font-black leading-none tracking-[-0.08em] sm:text-7xl">
            READY WHEN<br />THE DROP IS.
          </h2>
          <Link href="/events" className="button-primary mt-8">
            Explore Open Events <ArrowRight aria-hidden="true" className="size-5" />
          </Link>
        </section>

        <footer id="about" className="flex flex-col gap-5 border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-ink)] px-5 py-8 text-[var(--fd-cream)] sm:flex-row sm:items-center sm:justify-between sm:px-12">
          <div>
            <div className="font-display text-2xl font-black tracking-[-0.06em]">FAIR DROP.</div>
            <p className="mt-1 text-sm text-[var(--fd-muted)]">Fair access for high-demand events.</p>
          </div>
          <div className="flex flex-wrap gap-5 text-xs font-bold uppercase">
            <Link href="/events">Events</Link>
            <Link href="/profile">Profile</Link>
            <Link href="/admin">Admin Console</Link>
            <Link href="/events/camp_demo_001/audit">Audit</Link>
          </div>
        </footer>
      </div>
    </main>
  )
}
