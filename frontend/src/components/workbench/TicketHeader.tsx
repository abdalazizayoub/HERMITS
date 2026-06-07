import type { TicketDetail } from '../../types/ticket'
import Badge from '../shared/Badge'
import SLATimer from '../shared/SLATimer'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { Server, User, Clock } from 'lucide-react'

export default function TicketHeader({ ticket }: { ticket: TicketDetail }) {
  const age = formatDistanceToNow(parseISO(ticket.created_at), { addSuffix: true })

  return (
    <div className="px-4 py-3 border-b border-slate-800 bg-slate-900">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-slate-500">#{ticket.id}</span>
            <Badge variant={ticket.priority as 'critical' | 'high'}>
              {ticket.priority.toUpperCase()}
            </Badge>
            <Badge variant={ticket.status === 'DONE' ? 'done' : 'open'}>
              {ticket.status}
            </Badge>
          </div>
          <h2 className="text-base font-semibold text-slate-100 leading-tight">{ticket.title}</h2>
          <p className="text-xs text-slate-400 mt-1 line-clamp-2">{ticket.description}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <User size={12} />
          {ticket.customer_name}
        </span>
        <span className="flex items-center gap-1">
          <Clock size={12} />
          {age}
        </span>
        {ticket.sla_due_at && <SLATimer dueAt={ticket.sla_due_at} />}
        {ticket.ssh_host && (
          <span className="flex items-center gap-1 font-mono">
            <Server size={12} />
            {ticket.ssh_host}
          </span>
        )}
        {ticket.service_hint && (
          <span className="font-mono text-slate-500">[{ticket.service_hint}]</span>
        )}
      </div>
    </div>
  )
}
