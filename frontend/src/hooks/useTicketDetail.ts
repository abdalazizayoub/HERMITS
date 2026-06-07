import { useQuery } from '@tanstack/react-query'
import { getTicket } from '../api/tickets'
import type { TicketDetail } from '../types/ticket'

export function useTicketDetail(id: number | null) {
  return useQuery<TicketDetail>({
    queryKey: ['ticket', id],
    queryFn: () => getTicket(id!),
    enabled: id !== null,
    staleTime: 60_000,
  })
}
