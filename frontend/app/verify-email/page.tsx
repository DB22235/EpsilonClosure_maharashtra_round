'use client'

import Link from 'next/link'
import { ArrowRight, Mail, RefreshCw, ShieldCheck } from 'lucide-react'
import { DemoNotice, FairShell, IconBox } from '@/components/fair-shell'

export default function VerifyEmailPage() {
  return (
    <FairShell active="Verify Email">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] px-5 py-16 sm:px-12 lg:px-20">
        <div className="mx-auto max-w-2xl border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[10px_10px_0_var(--fd-ink)] sm:p-10">
          <div className="flex flex-col items-center text-center">
            <IconBox color="var(--fd-yellow)">
              <Mail className="size-8 text-[var(--fd-ink)]" />
            </IconBox>

            <span className="mt-6 border-[2px] border-[var(--fd-ink)] bg-[var(--fd-teal)] px-3 py-1 font-mono text-xs font-black uppercase">
              Verification Link Sent
            </span>

            <h1 className="font-display mt-4 text-4xl font-black tracking-tight sm:text-5xl">
              CHECK YOUR EMAIL
            </h1>

            <p className="mt-4 max-w-lg text-base font-medium leading-relaxed">
              We sent a verification link to <strong className="font-mono text-sm underline">alex.morgan@example.com</strong>.
              Verifying your email confirms your identity for Fair Drop registration rules.
            </p>

            <div className="mt-8 grid w-full gap-4 text-left font-mono text-xs font-bold sm:grid-cols-2">
              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4">
                <div className="text-[var(--fd-ink)]/70 uppercase">STATUS</div>
                <div className="mt-1 flex items-center gap-2 text-sm text-[var(--fd-teal)] font-black">
                  <ShieldCheck className="size-4" /> VERIFICATION PENDING
                </div>
              </div>
              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4">
                <div className="text-[var(--fd-ink)]/70 uppercase">RETRY COOLDOWN</div>
                <div className="mt-1 text-sm font-black">60 SECONDS</div>
              </div>
            </div>

            <div className="mt-8 flex flex-col gap-4 w-full">
              <Link href="/events" className="button-primary justify-center text-base">
                Continue to Events <ArrowRight className="size-5" />
              </Link>

              <button type="button" className="button-secondary justify-center text-sm">
                <RefreshCw className="size-4" /> Resend Verification Email
              </button>
            </div>

            <div className="mt-8 w-full text-left">
              <DemoNotice>
                In static demo mode, your account is simulated as email-verified. Click Continue to Events.
              </DemoNotice>
            </div>
          </div>
        </div>
      </div>
    </FairShell>
  )
}
