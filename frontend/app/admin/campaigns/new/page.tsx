'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowRight, CheckCircle2, ShieldCheck, Ticket, Plus, RefreshCw, AlertCircle } from 'lucide-react'
import { AdminShell, DemoNotice } from '@/components/fair-shell'
import { api, FairDropApiError } from '@/lib/api'

export default function NewCampaignPage() {
  const router = useRouter()

  const [name, setName] = useState('')
  const [venue, setVenue] = useState('')
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [capacity, setCapacity] = useState<number | ''>('')
  const [policyVersion, setPolicyVersion] = useState('v1.0')

  // Timeline dynamic defaults relative to now
  const now = new Date()
  const defaultStart = new Date(now.getTime() - 5 * 60000).toISOString().slice(0, 16)
  const defaultEnd = new Date(now.getTime() + 7 * 86400000).toISOString().slice(0, 16)
  const defaultRedemption = new Date(now.getTime() + 8 * 86400000).toISOString().slice(0, 16)

  const [registrationStart, setRegistrationStart] = useState(defaultStart)
  const [registrationEnd, setRegistrationEnd] = useState(defaultEnd)
  const [redemptionDeadline, setRedemptionDeadline] = useState(defaultRedemption)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (!capacity || Number(capacity) <= 0) {
        throw new Error('Please specify a valid capacity (> 0).')
      }

      const regStartDate = new Date(registrationStart)
      const regEndDate = new Date(registrationEnd)
      const redDeadlineDate = new Date(redemptionDeadline)

      if (regEndDate <= regStartDate) {
        throw new Error('Registration Closes must be strictly after Registration Opens.')
      }
      if (redDeadlineDate <= regEndDate) {
        throw new Error('Redemption Deadline must be strictly after Registration Closes.')
      }

      const payload = {
        name: name.trim(),
        venue: venue.trim() || undefined,
        description: description.trim(),
        capacity: Number(capacity),
        registration_start: regStartDate.toISOString(),
        registration_end: regEndDate.toISOString(),
        redemption_deadline: redDeadlineDate.toISOString(),
        max_tickets_per_participant: 1,
        allocation_method: 'UNIFORM_LOTTERY',
        standby_policy: 'FIXED_ORDER',
        policy_version: policyVersion.trim() || 'v1.0',
      }

      const newCampaign = await api.admin.createCampaign(payload)
      const targetId = newCampaign?.id || 'camp_demo_001'
      router.push(`/admin/campaigns/${targetId}`)
    } catch (err: any) {
      if (err instanceof FairDropApiError) {
        setError(`${err.code}: ${err.message}`)
      } else {
        setError(err.message || 'Failed to create campaign. Please check inputs.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AdminShell activeTab="+ New Campaign">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <span className="font-mono text-xs font-black uppercase">CAMPAIGN CREATOR</span>
          <h1 className="font-display text-3xl font-black">CREATE NEW ALLOCATION CAMPAIGN</h1>
          <p className="text-xs font-mono font-bold mt-1">CONFIGURE CAPACITY, POLICY RULES, AND LOTTERY TIMELINE</p>
        </div>

        {error && (
          <div className="mt-6 border-[3px] border-[var(--fd-ink)] bg-red-100 p-4 shadow-[4px_4px_0_var(--fd-ink)]">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="size-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <strong className="font-display text-sm font-black text-red-700 block">CREATION ERROR</strong>
                <p className="font-mono text-xs font-bold text-red-900 mt-1 leading-snug">{error}</p>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-8 grid gap-8 lg:grid-cols-2">
          
          {/* Section 1: General Info */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
            <h2 className="font-display text-xl font-black mb-4 border-b-2 border-[var(--fd-ink)] pb-3">
              1. GENERAL EVENT DETAILS
            </h2>

            <div className="flex flex-col gap-4 font-mono text-xs font-bold uppercase">
              <label className="flex flex-col gap-1.5">
                <span>Campaign Name</span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Summer Music Fest 2026"
                  required
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Venue Location</span>
                <input
                  value={venue}
                  onChange={(e) => setVenue(e.target.value)}
                  placeholder="City / Stadium / Convention Center"
                  required
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Category</span>
                <input
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="DESIGN / MUSIC / SPORTS / CONFERENCE"
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Description Summary</span>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter campaign overview, rules, and allocation details..."
                  required
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono normal-case"
                />
              </label>
            </div>
          </div>

          {/* Section 2: Capacity & Allocation Policy */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
            <h2 className="font-display text-xl font-black mb-4 border-b-2 border-[var(--fd-ink)] pb-3">
              2. CAPACITY & LOTTERY RULES
            </h2>

            <div className="flex flex-col gap-4 font-mono text-xs font-bold uppercase">
              <label className="flex flex-col gap-1.5">
                <span>Available Seats (Capacity)</span>
                <input
                  type="number"
                  min={1}
                  max={100000}
                  value={capacity === '' ? '' : capacity}
                  onChange={(e) => setCapacity(e.target.value === '' ? '' : Math.max(1, Number(e.target.value)))}
                  placeholder="e.g. 500"
                  required
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>

              <label className="flex flex-col gap-1.5 opacity-60">
                <span>Max Tickets Per Participant (Enforced 1)</span>
                <input
                  type="number"
                  value={1}
                  disabled
                  className="border-[3px] border-[var(--fd-ink)] bg-neutral-200 p-3 text-sm font-medium font-mono cursor-not-allowed"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Policy Version Tag</span>
                <input
                  value={policyVersion}
                  onChange={(e) => setPolicyVersion(e.target.value)}
                  placeholder="v1.0"
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>
              
              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                <span className="font-mono text-xs font-bold uppercase text-[var(--fd-ink)]/70">ALLOCATION ALGORITHM</span>
                <div className="font-display text-lg font-black text-[var(--fd-pink)] mt-1">
                  UNIFORM FISHER-YATES LOTTERY
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Timeline & Windows */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)] lg:col-span-2">
            <h2 className="font-display text-xl font-black mb-4 border-b-2 border-[var(--fd-ink)] pb-3">
              3. REGISTRATION & CLAIM TIMELINE
            </h2>

            <div className="grid gap-4 sm:grid-cols-3 font-mono text-xs font-bold uppercase">
              <label className="flex flex-col gap-1.5">
                <span>Registration Opens</span>
                <input
                  type="datetime-local"
                  value={registrationStart}
                  onChange={(e) => setRegistrationStart(e.target.value)}
                  required
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Registration Closes</span>
                <input
                  type="datetime-local"
                  value={registrationEnd}
                  onChange={(e) => setRegistrationEnd(e.target.value)}
                  required
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span>Redemption Deadline</span>
                <input
                  type="datetime-local"
                  value={redemptionDeadline}
                  onChange={(e) => setRedemptionDeadline(e.target.value)}
                  required
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 outline-none text-sm font-medium focus:shadow-[4px_4px_0_var(--fd-pink)] font-mono"
                />
              </label>
            </div>

            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <button
                type="submit"
                disabled={loading}
                className="button-primary flex-1 justify-center text-center bg-[var(--fd-pink)] text-lg cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RefreshCw className="size-5 animate-spin" /> Creating Campaign in Backend...
                  </>
                ) : (
                  <>
                    Create & Initialize Campaign <ArrowRight className="size-5" />
                  </>
                )}
              </button>
              <Link href="/admin/campaigns" className="button-secondary justify-center text-center text-base">
                Cancel
              </Link>
            </div>

            <div className="mt-6">
              <DemoNotice>
                Submits POST /api/v1/admin/campaigns to initialize campaign in DRAFT state. You can then prepare seat inventory and publish when ready.
              </DemoNotice>
            </div>
          </div>

        </form>
      </div>
    </AdminShell>
  )
}

