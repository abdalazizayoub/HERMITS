import type { Ticket } from '../../types/ticket'
import Badge from '../shared/Badge'
import SLATimer from '../shared/SLATimer'
import { formatDistanceToNow, parseISO } from 'date-fns'

interface TicketItemProps {
  ticket: Ticket
  isActive: boolean
  onClick: () => void
}

export default function TicketItem({ ticket, isActive, onClick }: TicketItemProps) {
  const age = formatDistanceToNow(parseISO(ticket.created_at), { addSuffix: true })

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-3 rounded-lg border transition-all ${
        isActive
          ? 'bg-blue-950/60 border-blue-700 shadow-md shadow-blue-900/30'
          : 'bg-slate-900/50 border-slate-800 hover:bg-slate-800/50 hover:border-slate-700'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-sm font-medium text-slate-100 truncate leading-tight">
          {ticket.title}
        </span>
        <Badge variant={ticket.priority as 'critical' | 'high'} className="shrink-0">
          {ticket.priority.toUpperCase()}
        </Badge>
      </div>

      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-slate-400 truncate">{ticket.customer_name}</span>
        <span className="text-xs text-slate-500 shrink-0 ml-1">#{ticket.id}</span>
      </div>

      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-slate-500">{age}</span>
        {ticket.sla_due_at && <SLATimer dueAt={ticket.sla_due_at} compact />}
      </div>

      {ticket.service_hint && (
        <span className="mt-1 inline-block text-xs text-slate-500 font-mono">
          [{ticket.service_hint}]
        </span>
      )}
    </button>
  )
}
