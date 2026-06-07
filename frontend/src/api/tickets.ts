import client from './client'
import type { Ticket, TicketDetail } from '../types/ticket'

// GET /api/tickets/ → {"tickets": [...]}
export async function listTickets(status?: string): Promise<Ticket[]> {
  const params: Record<string, string> = {}
  if (status) params.status = status
  const res = await client.get('/api/tickets/', { params })
  const raw = res.data
  // Backend wraps ERP list as {"tickets": [...]}
  const list: Ticket[] = Array.isArray(raw) ? raw : (raw.tickets ?? [])
  return list
}

// GET /api/tickets/{id} → {"ticket": {...}, "system": {ticket_id, customer_id, system: {ip, port, username, os, notes}}}
export async function getTicket(id: number): Promise<TicketDetail> {
  const res = await client.get(`/api/tickets/${id}`)
  const { ticket, system } = res.data as {
    ticket: Ticket
    system: { system: { ip: string; port: number; username: string; os?: string; notes?: string } }
  }
  const sys = system?.system ?? {}
  return {
    ...ticket,
    ssh_host: sys.ip ?? null,
    ssh_user: sys.username ?? null,
    ssh_port: sys.port ?? null,
    system_os: sys.os ?? null,
    system_notes: sys.notes ?? null,
  }
}

export async function updateTicketStatus(id: number, status: string): Promise<void> {
  await client.patch(`/api/tickets/${id}/status`, { status })
}
