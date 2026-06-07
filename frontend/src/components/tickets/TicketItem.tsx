import type { Ticket } from '../../types/ticket'
import Badge from '../shared/Badge'
import SLATimer from '../shared/SLATimer'
import { useWorkbenchStore } from '../../store/workbenchStore'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { Cpu, CheckCircle2, XCircle } from 'lucide-react'

interface TicketItemProps {
  ticket: Ticket
  isActive: boolean
  onClick: () => void
}

export default function TicketItem({ ticket, isActive, onClick }: TicketItemProps) {
  const age = formatDistanceToNow(parseISO(ticket.created_at), { addSuffix: true })
  const isCritical = ticket.priority === 'critical'
  const ticketSessions = useWorkbenchStore((s) => s.ticketSessions)

  // Derive local validation state from cached session
  const session = ticketSessions[ticket.id]
  const localValidationPassed = session?.validationPassed ?? null

  // Effective status: use local session validation truth, fall back to ERP status
  const isDone = localValidationPassed === true || ticket.status === 'DONE'
  const isValidationFailed = localValidationPassed === false

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2.5 rounded-lg border transition-all ${
        isActive
          ? 'bg-cyan-950/40 border-cyan-500/50 shadow-glow-cyan neon-active'
          : isDone
          ? 'bg-emerald-950/15 border-emerald-500/20 hover:border-emerald-500/35'
          : isValidationFailed
          ? 'bg-amber-950/15 border-amber-500/25 hover:border-amber-500/40'
          : isCritical
          ? 'bg-red-950/20 border-red-500/30 hover:border-red-500/50 hover:bg-red-950/30'
          : 'bg-slate-900/50 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className={`text-xs font-semibold truncate leading-tight ${isActive ? 'text-cyan-100' : isDone ? 'text-slate-400' : 'text-slate-200'}`}>
          {ticket.title}
        </span>
        <Badge variant={ticket.priority as 'critical' | 'high'} className="shrink-0">
          {ticket.priority === 'critical' ? 'CRIT' : 'HIGH'}
        </Badge>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500 truncate">{ticket.customer_name}</span>
        <span className="text-xs text-slate-600 font-mono shrink-0 ml-1">#{ticket.id}</span>
      </div>

      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-slate-600">{age}</span>
        <div className="flex items-center gap-1.5">
          {/* Validation-based status — more precise than ERP status alone */}
          {localValidationPassed === true ? (
            <span className="flex items-center gap-1 text-xs text-emerald-500 font-semibold">
              <CheckCircle2 size={10} />
              DONE
            </span>
          ) : localValidationPassed === false ? (
            <span className="flex items-center gap-1 text-xs text-amber-500 font-semibold">
              <XCircle size={10} />
              FAILED
            </span>
          ) : ticket.status === 'DONE' ? (
            <Badge variant="done">DONE</Badge>
          ) : null}
          {ticket.sla_due_at && <SLATimer dueAt={ticket.sla_due_at} compact />}
        </div>
      </div>

      {ticket.service_hint && (
        <div className="mt-1.5 flex items-center gap-1">
          <Cpu size={9} className="text-slate-600" />
          <span className="text-xs text-slate-600 font-mono">{ticket.service_hint}</span>
        </div>
      )}
    </button>
  )
}
