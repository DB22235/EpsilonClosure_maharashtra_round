'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowRight, Save, Settings } from 'lucide-react'
import { AdminShell, DemoNotice, Field } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'

export default function AdminCampaignEditPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)

  return (
    <AdminShell campaignId={campaignId} activeTab="Edit">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase">CAMPAIGN CONSOLE / EDIT</span>
            <h1 className="font-display text-3xl font-black">EDIT CONFIGURATION: {event.name}</h1>
          </div>
          <Link href={`/admin/campaigns/${campaignId}`} className="button-primary bg-[var(--fd-pink)]">
            <Save className="size-5" /> Save Changes
          </Link>
        </div>

        <form className="mt-8 grid gap-6 sm:grid-cols-2">
          <Field label="Event Title" placeholder="Event Title" defaultValue={event.name} />
          <Field label="Venue Location" placeholder="Venue" defaultValue={event.venue} />
          <Field label="Capacity Limit" placeholder="Seats" defaultValue={event.seats.toString()} type="number" />
          <Field label="Policy Version Tag" placeholder="Policy Tag" defaultValue={event.policyVersion} />
          <Field label="Registration Start" placeholder="Start Date" defaultValue={event.registrationStart} />
          <Field label="Registration End" placeholder="End Date" defaultValue={event.registrationEnd} />

          <div className="sm:col-span-2 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[4px_4px_0_var(--fd-ink)]">
            <h3 className="font-display text-xl font-black mb-3">PAUSE SCOPE CONTROL</h3>
            <div className="grid gap-4 sm:grid-cols-3 font-mono text-xs font-bold">
              <label className="flex items-center gap-2 border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-3">
                <input type="checkbox" className="size-4 accent-[var(--fd-pink)]" /> PAUSE ADMISSION QUEUE
              </label>
              <label className="flex items-center gap-2 border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-3">
                <input type="checkbox" className="size-4 accent-[var(--fd-pink)]" /> PAUSE REGISTRATION
              </label>
              <label className="flex items-center gap-2 border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-3">
                <input type="checkbox" className="size-4 accent-[var(--fd-pink)]" /> PAUSE REDEMPTION / CLAIMS
              </label>
            </div>
          </div>
        </form>

        <div className="mt-8">
          <DemoNotice>
            Static Edit Form interface for operator settings management.
          </DemoNotice>
        </div>
      </div>
    </AdminShell>
  )
}
