'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Award, CheckCircle2, Clock, Search, Filter } from 'lucide-react'
import { AdminShell, DemoNotice, StatusPill } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'

export default function AdminCampaignClaimsPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)

  const mockClaims = [
    { winnerId: 'WIN-001', name: 'Alex Morgan', email: 'alex.morgan@example.com', seat: 'Seat A-042', status: 'CONFIRMED', heldUntil: 'COMPLETED' },
    { winnerId: 'WIN-002', name: 'Jordan Lee', email: 'jordan.l@example.com', seat: 'Seat B-012', status: 'HELD', heldUntil: '12m 40s' },
    { winnerId: 'WIN-003', name: 'Taylor Swift', email: 'taylor.s@example.com', seat: 'Seat C-008', status: 'CLAIM_PENDING', heldUntil: '14m 10s' },
    { winnerId: 'WIN-004', name: 'Chris Evans', email: 'chris.e@example.com', seat: 'Unselected', status: 'SELECTED', heldUntil: '14m 55s' },
    { winnerId: 'WIN-005', name: 'Sam Altman', email: 'sam.a@example.com', seat: 'Seat A-001', status: 'CONFIRMED', heldUntil: 'COMPLETED' },
  ]

  return (
    <AdminShell campaignId={campaignId} activeTab="Claims">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase">CAMPAIGN CONSOLE / CLAIMS & SEAT HOLDS</span>
            <h1 className="font-display text-3xl font-black">WINNER CLAIMS & SEAT HOLD STATUS</h1>
            <p className="text-xs font-mono font-bold mt-1">ATOMIC SEAT RESERVATIONS · 500 TOTAL WINNERS</p>
          </div>
          <span className="border-2 border-[var(--fd-ink)] bg-[var(--fd-pink)] px-3 py-1 font-mono text-xs font-black uppercase">
            384 CONFIRMED / 116 PENDING
          </span>
        </div>

        {/* Claims Table */}
        <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left font-mono text-xs font-bold">
              <thead>
                <tr className="border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)]">
                  <th className="p-3">WINNER ID</th>
                  <th className="p-3">PARTICIPANT</th>
                  <th className="p-3">EMAIL</th>
                  <th className="p-3">ASSIGNED SEAT</th>
                  <th className="p-3">CLAIM TIMER</th>
                  <th className="p-3">STATUS</th>
                </tr>
              </thead>
              <tbody>
                {mockClaims.map((c) => (
                  <tr key={c.winnerId} className="border-b-2 border-[var(--fd-ink)] bg-[var(--fd-card)]">
                    <td className="p-3 font-black text-[var(--fd-pink)]">{c.winnerId}</td>
                    <td className="p-3 font-display text-sm font-black">{c.name}</td>
                    <td className="p-3">{c.email}</td>
                    <td className="p-3 font-mono font-black">{c.seat}</td>
                    <td className="p-3">{c.heldUntil}</td>
                    <td className="p-3"><StatusPill>{c.status}</StatusPill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8">
          <DemoNotice>
            Static Claims & Seat Hold tracking table showing winner redemption status.
          </DemoNotice>
        </div>
      </div>
    </AdminShell>
  )
}
