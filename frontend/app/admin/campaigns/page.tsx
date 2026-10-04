'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowRight, Plus, Search, Filter, RefreshCw, ShieldAlert } from 'lucide-react'
import { AdminShell, DemoNotice, StatusPill } from '@/components/fair-shell'
import { demoEvents } from '@/lib/demo-events'
import { api, isUuid } from '@/lib/api'
import { useAuth } from '@/lib/AuthContext'

export default function AdminCampaignsPage() {
  const { user, loading: authLoading } = useAuth()
  const [campaigns, setCampaigns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [operatorNotice, setOperatorNotice] = useState<string | null>(null)

  const fetchCampaigns = async () => {
    setLoading(true)
    setOperatorNotice(null)
    try {
      const liveList = await api.admin.listCampaigns(1, 50)
      if (Array.isArray(liveList) && liveList.length > 0) {
        const mappedLive = liveList.map((c: any) => ({
          id: c.id,
          name: c.name,
          venue: c.venue || 'Online / Global',
          policyVersion: c.policy_version || 'v1.0',
          seats: c.capacity,
          registeredCount: c.registration_counts?.total ?? 0,
          status: c.status,
          isLive: true,
        }))
        const demoMissing = demoEvents
          .filter((d) => !mappedLive.some((m) => m.id === d.id))
          .map((d) => ({ ...d, isLive: false }))
        setCampaigns([...mappedLive, ...demoMissing])
      } else {
        setCampaigns(demoEvents.map((d) => ({ ...d, isLive: false })))
      }
    } catch (err: any) {
      if (err?.status === 401 || err?.status === 403) {
        setOperatorNotice(
          `Operator privileges required to fetch live campaigns. Displaying showcase demo data. Run: python -m scripts.promote_admin --email ${user?.email || '<your-email>'} to elevate this account.`
        )
      }
      setCampaigns(demoEvents.map((d) => ({ ...d, isLive: false })))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      setCampaigns(demoEvents.map((d) => ({ ...d, isLive: false })))
      setLoading(false)
      return
    }
    fetchCampaigns()
  }, [user, authLoading])

  const filteredCampaigns = campaigns.filter((c) => {
    const matchesSearch =
      searchQuery.trim() === '' ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.venue && c.venue.toLowerCase().includes(searchQuery.toLowerCase()))

    const matchesStatus =
      statusFilter === 'ALL' || c.status?.toUpperCase() === statusFilter

    return matchesSearch && matchesStatus
  })

  return (
    <AdminShell activeTab="Campaigns">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase">CAMPAIGN MANAGEMENT</span>
            <h1 className="font-display text-3xl font-black">ALL CAMPAIGNS DIRECTORY</h1>
            <p className="text-xs font-mono font-bold mt-1">
              TOTAL CONFIGURED CAMPAIGNS: {campaigns.length} ({filteredCampaigns.length} DISPLAYED)
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchCampaigns}
              disabled={loading}
              className="button-secondary text-xs py-2 px-3 flex items-center gap-1.5"
            >
              <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
            <Link href="/admin/campaigns/new" className="button-primary bg-[var(--fd-pink)]">
              <Plus className="size-5" /> Create Campaign
            </Link>
          </div>
        </div>

        {/* Showcase Mode Notice */}
        {!user && (
          <div className="mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)]/30 p-4 font-mono text-xs font-bold shadow-[4px_4px_0_var(--fd-ink)]">
            <div className="flex items-center gap-2">
              <span className="grid size-6 place-items-center bg-[var(--fd-yellow)] border border-[var(--fd-ink)]">⚡</span>
              <span>SHOWCASE DEMO MODE: Viewing demo campaigns. To manage live database campaigns, <Link href="/admin/login" className="underline text-[var(--fd-pink)] font-black">Sign In as Operator</Link>.</span>
            </div>
            <Link href="/admin/login" className="button-secondary text-xs px-3 py-1 self-start sm:self-auto">
              Operator Sign In
            </Link>
          </div>
        )}
        {operatorNotice && (
          <div className="mt-6 flex items-center gap-3 border-[3px] border-[var(--fd-ink)] bg-[#FFEBEA] p-4 font-mono text-xs font-bold text-[var(--fd-red)] shadow-[4px_4px_0_var(--fd-ink)]">
            <ShieldAlert className="size-5 shrink-0" />
            <span>{operatorNotice}</span>
          </div>
        )}

        {/* Filter bar */}
        <div className="mt-8 flex flex-col gap-4 sm:flex-row">
          <label className="flex flex-1 items-center gap-3 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-4 py-3 shadow-[3px_3px_0_var(--fd-ink)]">
            <Search className="size-5 shrink-0" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter campaigns by ID, name or location..."
              className="w-full bg-transparent outline-none font-mono text-xs font-bold"
            />
          </label>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-4 py-3 font-mono text-xs font-bold shadow-[3px_3px_0_var(--fd-ink)] outline-none"
            >
              <option value="ALL">ALL STATUSES</option>
              <option value="DRAFT">DRAFT</option>
              <option value="PREPARING">PREPARING</option>
              <option value="OPEN">OPEN</option>
              <option value="CLOSED">CLOSED</option>
              <option value="FROZEN">FROZEN</option>
              <option value="CLAIMING">CLAIMING</option>
            </select>
          </div>
        </div>

        {/* Campaigns Table */}
        <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left font-mono text-xs font-bold">
              <thead>
                <tr className="border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)]">
                  <th className="p-3">CAMPAIGN ID</th>
                  <th className="p-3">EVENT NAME</th>
                  <th className="p-3">LOCATION</th>
                  <th className="p-3">POLICY</th>
                  <th className="p-3">CAPACITY</th>
                  <th className="p-3">REGISTRATIONS</th>
                  <th className="p-3">STATUS</th>
                  <th className="p-3">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredCampaigns.map((e) => (
                  <tr key={e.id} className="border-b-2 border-[var(--fd-ink)] bg-[var(--fd-card)]">
                    <td className="p-3 font-black text-[var(--fd-pink)]">
                      <span className="break-all">{isUuid(e.id) ? `${e.id.slice(0, 8)}...` : e.id}</span>
                      {e.isLive && (
                        <span className="ml-1.5 inline-block text-[9px] bg-green-200 border border-green-800 px-1 text-green-900 font-bold">
                          LIVE DB
                        </span>
                      )}
                    </td>
                    <td className="p-3 font-display text-sm font-black">{e.name}</td>
                    <td className="p-3">{e.venue}</td>
                    <td className="p-3">{e.policyVersion}</td>
                    <td className="p-3">{e.seats} SEATS</td>
                    <td className="p-3">{e.registeredCount.toLocaleString()}</td>
                    <td className="p-3"><StatusPill>{e.status}</StatusPill></td>
                    <td className="p-3">
                      <Link href={`/admin/campaigns/${e.id}`} className="button-primary text-[11px] py-1 px-3">
                        Console <ArrowRight className="inline size-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
                {filteredCampaigns.length === 0 && (
                  <tr>
                    <td colSpan={8} className="p-8 text-center font-mono text-sm font-bold opacity-60">
                      No campaigns match current filter criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8">
          <DemoNotice>
            Connected to FastAPI /api/v1/admin/campaigns with real-time inventory and registration counts. Click Console to manage any campaign.
          </DemoNotice>
        </div>
      </div>
    </AdminShell>
  )
}

