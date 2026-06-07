import { useState, useMemo } from 'react'
import { RefreshCw, Search, X, InboxIcon } from 'lucide-react'
import { useTickets } from '../../hooks/useTickets'
import { useWorkbenchStore } from '../../store/workbenchStore'
import TicketItem from './TicketItem'
import SortControls, { type SortKey } from './SortControls'
import LoadingSpinner from '../shared/LoadingSpinner'
import type { Ticket } from '../../types/ticket'

const PRIORITY_ORDER: Record<string, number> = { critical: 0, high: 1 }

export default function TicketList() {
  const [sortBy, setSortBy] = useState<SortKey>('priority')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'DONE'>('OPEN')

  const activeTicketId = useWorkbenchStore((s) => s.activeTicketId)
  const setActiveTicket = useWorkbenchStore((s) => s.setActiveTicket)

  const { data: tickets, isLoading, isFetching, refetch } = useTickets()

  const visible = useMemo(() => {
    if (!tickets) return []
    let list = [...tickets]

    if (statusFilter !== 'ALL') {
      list = list.filter((t) => t.status === statusFilter)
    }

    const trimmed = search.trim()
    if (trimmed !== '') {
      const numericId = parseInt(trimmed, 10)
      if (!isNaN(numericId)) {
        list = list.filter((t) => t.id === numericId)
      } else {
        const lower = trimmed.toLowerCase()
        list = list.filter(
          (t) =>
            t.title.toLowerCase().includes(lower) ||
            t.customer_name.toLowerCase().includes(lower),
        )
      }
    }

    if (sortBy === 'date') {
      list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } else if (sortBy === 'customer') {
      list.sort((a, b) => a.customer_name.localeCompare(b.customer_name))
    } else {
      list.sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 2) - (PRIORITY_ORDER[b.priority] ?? 2))
    }

    return list
  }, [tickets, sortBy, search, statusFilter])

  const openCount = tickets?.filter((t) => t.status === 'OPEN').length ?? 0
  const criticalCount = tickets?.filter((t) => t.priority === 'critical' && t.status === 'OPEN').length ?? 0

  return (
    <div
      className="flex flex-col h-full bg-slate-950 border-r"
      style={{ borderRightColor: 'rgba(34,211,238,0.12)' }}
    >
      {/* Header */}
      <div className="px-3 py-3 border-b space-y-2.5" style={{ borderBottomColor: 'rgba(34,211,238,0.12)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-100">Tickets</span>
            {openCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                {openCount}
              </span>
            )}
            {criticalCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                {criticalCount} CRIT
              </span>
            )}
          </div>
          <button
            onClick={() => refetch()}
            className="text-slate-600 hover:text-cyan-400 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={13} className={isFetching ? 'animate-spin text-cyan-400' : ''} />
          </button>
        </div>

        {/* Status filter tabs */}
        <div className="flex gap-1">
          {(['OPEN', 'ALL', 'DONE'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`flex-1 py-1 text-xs rounded font-medium transition-all ${
                statusFilter === s
                  ? s === 'OPEN'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                    : s === 'DONE'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'bg-slate-700 text-slate-200 border border-slate-600'
                  : 'text-slate-500 hover:text-slate-300 border border-transparent'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tickets…"
            className="w-full bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-cyan-500/50 rounded-lg pl-7 pr-7 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition-all"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-300"
            >
              <X size={11} />
            </button>
          )}
        </div>

        <SortControls sortBy={sortBy} onChange={setSortBy} />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {isLoading && (
          <div className="flex justify-center py-10">
            <LoadingSpinner />
          </div>
        )}

        {!isLoading && visible.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-12 text-slate-600">
            <InboxIcon size={28} />
            <p className="text-xs">{search ? `No results for "${search}"` : 'No tickets'}</p>
          </div>
        )}

        {visible.map((t: Ticket) => (
          <TicketItem
            key={t.id}
            ticket={t}
            isActive={t.id === activeTicketId}
            onClick={() => setActiveTicket(t.id)}
          />
        ))}
      </div>

      <div className="px-3 py-2 border-t text-xs text-slate-600 font-mono" style={{ borderTopColor: 'rgba(34,211,238,0.1)' }}>
        {visible.length}/{tickets?.length ?? 0} tickets
      </div>
    </div>
  )
}
