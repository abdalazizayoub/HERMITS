import { useQuery } from '@tanstack/react-query'
import { listTickets } from '../api/tickets'
import type { Ticket } from '../types/ticket'

export function useTickets(status?: string) {
  return useQuery<Ticket[]>({
    queryKey: ['tickets', status],
    queryFn: () => listTickets(status),
    refetchInterval: 30_000,
  })
}
