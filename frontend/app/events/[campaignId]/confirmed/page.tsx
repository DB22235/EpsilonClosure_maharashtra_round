'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowRight, Check, ExternalLink, ShieldCheck, Ticket, Download, Share2 } from 'lucide-react'
import { DemoNotice, FairShell, ProgressSteps, TicketStub } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { useAuth } from '@/lib/AuthContext'

interface ConfirmedBookingData {
  booking_id?: string
  receipt_id?: string
  seat_id?: string
  seat_label?: string
  confirmed_at?: string
  campaign_id?: string
}

export default function ConfirmedPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)

  const { user } = useAuth()
  const [booking, setBooking] = useState<ConfirmedBookingData | null>(null)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const cached = sessionStorage.getItem(`fairdrop_confirmed_${campaignId}`)
        if (cached) {
          setBooking(JSON.parse(cached))
        }
      } catch (err) {
        console.warn('Failed to load confirmed booking pass:', err)
      }
    }
  }, [campaignId])

  const seatLabel = booking?.seat_label || 'Seat A-042'
  const receiptHash = booking?.receipt_id || '0x9482fa8941029482a0b12984920'
  const confirmedAtStr = booking?.confirmed_at
    ? new Date(booking.confirmed_at).toLocaleString('en-US', {
        month: 'short',
        day: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short',
      })
    : '2026-04-18 14:15:00 UTC'

  const passHolderName = (user?.email?.split('@')[0] || 'PASS HOLDER').toUpperCase()

  return (
    <FairShell active="Explore Drops">
      <ProgressSteps current={6} />

      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-12 sm:px-12 lg:px-20">
        <div className="mx-auto max-w-4xl border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[10px_10px_0_var(--fd-ink)] sm:p-10">
          
          <div className="flex flex-col items-center text-center">
            <div className="grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] shadow-[4px_4px_0_var(--fd-ink)]">
              <Check className="size-10 stroke-[3] text-[var(--fd-ink)]" />
            </div>

            <span className="mt-4 border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-3 py-1 font-mono text-xs font-black uppercase">
              BOOKING ATOMICALLY CONFIRMED
            </span>

            <h1 className="font-display mt-3 text-4xl font-black sm:text-5xl">
              ACCESS TICKET ISSUED
            </h1>

            <p className="mt-3 max-w-lg text-base font-medium">
              Your seat reservation for <strong>{event.name}</strong> is sealed into the system ledger.
            </p>
          </div>

          {/* Ticket Stub Card & Security Stamps Visual Stickers */}
          <div className="mt-8 relative">
            {/* Sticker Badge 1 */}
            <div className="absolute -top-4 -right-2 z-10 rotate-6 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-4 py-2 font-mono text-xs font-black shadow-[4px_4px_0_var(--fd-ink)]">
              STAMP: 0 OVERSELL
            </div>

            {/* Sticker Badge 2 */}
            <div className="absolute -bottom-4 -left-2 z-10 -rotate-6 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] px-4 py-2 font-mono text-xs font-black shadow-[4px_4px_0_var(--fd-ink)]">
              UNIFORM LOTTERY VERIFIED
            </div>

            <TicketStub name={event.name} seatLabel={seatLabel} campaignId={campaignId} />
          </div>

          {/* Receipt Details Card */}
          <div className="mt-10 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
            <h3 className="font-display text-xl font-black mb-4">CONFIRMATION RECEIPT DETAILS</h3>

            <div className="grid gap-4 sm:grid-cols-2 font-mono text-xs font-bold">
              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                <span className="text-[var(--fd-ink)]/70 uppercase">PASS HOLDER</span>
                <div className="mt-1 text-sm font-black truncate">{passHolderName}</div>
              </div>

              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                <span className="text-[var(--fd-ink)]/70 uppercase">CONFIRMED AT</span>
                <div className="mt-1 text-sm font-black">{confirmedAtStr}</div>
              </div>

              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                <span className="text-[var(--fd-ink)]/70 uppercase">VENUE &amp; SEAT</span>
                <div className="mt-1 text-sm font-black">{event.venue} ({seatLabel})</div>
              </div>

              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                <span className="text-[var(--fd-ink)]/70 uppercase">AUDIT RECEIPT HASH</span>
                <div className="mt-1 text-[11px] font-mono font-black break-all text-[var(--fd-pink)]">
                  {receiptHash}
                </div>
              </div>
            </div>
          </div>

          {/* Actions & Return Links */}
          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            <Link
              href={`/events/${campaignId}/audit`}
              className="button-primary flex-1 justify-center text-center text-base bg-[var(--fd-pink)] flex items-center gap-2"
            >
              <ShieldCheck className="size-5" /> View Fairness Audit <ExternalLink className="size-5" />
            </Link>

            <Link
              href="/events"
              className="button-secondary flex-1 justify-center text-center text-base flex items-center gap-2"
            >
              Explore More Events <ArrowRight className="size-5" />
            </Link>
          </div>

          <div className="mt-6">
            <DemoNotice>
              {booking
                ? 'Your seat reservation has been sealed into the database ledger.'
                : 'Ticket preview state. Win an allocation to redeem an authoritative booking pass.'}
            </DemoNotice>
          </div>
        </div>
      </div>
    </FairShell>
  )
}
