export type Priority = 'high' | 'critical'
export type TicketStatus = 'OPEN' | 'DONE'

// Shape returned by GET /api/tickets/ (list) — matches ERP fields exactly
export interface Ticket {
  id: number
  title: string
  description: string
  priority: Priority
  status: TicketStatus
  customer_id: number
  customer_name: string
  sla_due_at: string | null
  created_at: string
  tags: string[]
  // Not returned by ERP list — only available after fetching detail
  service_hint?: string | null
  ssh_host?: string | null
  ssh_user?: string | null
  ssh_port?: number | null
}

// Shape returned by GET /api/tickets/{id} — ticket + flattened system info
export interface TicketDetail extends Ticket {
  ssh_host: string | null
  ssh_user: string | null
  ssh_port: number | null
  system_os?: string | null
  system_notes?: string | null
}
