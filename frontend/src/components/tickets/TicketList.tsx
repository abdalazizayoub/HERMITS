import { useState, useMemo } from 'react'
import { RefreshCw, Search, X } from 'lucide-react'
import { useTickets } from '../../hooks/useTickets'
import { useWorkbenchStore } from '../../store/workbenchStore'
import TicketItem from './TicketItem'
import SortControls, { type SortKey } from './SortControls'
import LoadingSpinner from '../shared/LoadingSpinner'
import type { Ticket } from '../../types/ticket'

const PRIORITY_ORDER: Record<string, number> = { critical: 0, high: 1 }

export default function TicketList() {
  const [sortBy, setSortBy] = useState<SortKey>('date')
  const [search, setSearch] = useState('')

  const activeTicketId = useWorkbenchStore((s) => s.activeTicketId)
  const setActiveTicket = useWorkbenchStore((s) => s.setActiveTicket)

  // Always fetch all tickets — no status filter
  const { data: tickets, isLoading, isFetching, refetch } = useTickets()

  const visible = useMemo(() => {
    if (!tickets) return []

    let list = [...tickets]

    // Filter by ticket number if the search string is a number
    const trimmed = search.trim()
    if (trimmed !== '') {
      const numericId = parseInt(trimmed, 10)
      if (!isNaN(numericId)) {
        list = list.filter((t) => t.id === numericId)
      } else {
        // Also allow partial text match on title / customer
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
  }, [tickets, sortBy, search])

  return (
    <div className="flex flex-col h-full bg-slate-950 border-r border-slate-800">
      {/* Header */}
      <div className="px-3 py-3 border-b border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-200">Tickets</span>
          <button
            onClick={() => refetch()}
            className="text-slate-500 hover:text-slate-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Search by ticket number or title */}
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Ticket # or keyword…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-7 pr-7 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X size={12} />
            </button>
          )}
        </div>

        <SortControls sortBy={sortBy} onChange={setSortBy} />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {isLoading && (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        )}

        {!isLoading && visible.length === 0 && (
          <p className="text-center text-slate-500 text-xs py-8">
            {search ? `No tickets matching "${search}"` : 'No tickets'}
          </p>
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

      <div className="px-3 py-2 border-t border-slate-800 text-xs text-slate-500">
        {visible.length} of {tickets?.length ?? 0} ticket{(tickets?.length ?? 0) !== 1 ? 's' : ''}
      </div>
    </div>
  )
}
