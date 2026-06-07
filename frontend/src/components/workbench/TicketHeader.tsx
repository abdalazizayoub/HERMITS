import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { TicketDetail } from '../../types/ticket'
import Badge from '../shared/Badge'
import SLATimer from '../shared/SLATimer'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { Server, User, Clock, Volume2, Loader2 } from 'lucide-react'
import { getTicketVoiceSummary } from '../../api/voice'

export default function TicketHeader({ ticket }: { ticket: TicketDetail }) {
  const age = formatDistanceToNow(parseISO(ticket.created_at), { addSuffix: true })
  const [voiceState, setVoiceState] = useState<'idle' | 'loading' | 'playing'>('idle')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)

  async function handleVoice() {
    if (voiceState === 'playing' && audioUrl) {
      const el = document.getElementById('ticket-voice-player') as HTMLAudioElement | null
      if (el) el.pause()
      setVoiceState('idle')
      return
    }
    setVoiceState('loading')
    try {
      const url = await getTicketVoiceSummary(ticket.id)
      setAudioUrl(url)
      setVoiceState('playing')
      const el = document.getElementById('ticket-voice-player') as HTMLAudioElement | null
      if (el) { el.src = url; el.play() }
    } catch {
      setVoiceState('idle')
    }
  }

  return (
    <div
      className="px-4 py-3 border-b bg-slate-900/80 glass"
      style={{ borderBottomColor: 'rgba(34,211,238,0.15)' }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-slate-600">#{ticket.id}</span>
            <Badge variant={ticket.priority as 'critical' | 'high'}>
              {ticket.priority.toUpperCase()}
            </Badge>
            <Badge variant={ticket.status === 'DONE' ? 'done' : 'open'}>
              {ticket.status}
            </Badge>
          </div>
          <h2 className="text-sm font-bold text-slate-100 leading-tight">{ticket.title}</h2>
          <div className="text-xs text-slate-400 mt-1.5 prose prose-xs prose-invert max-w-none
            prose-p:my-0.5 prose-p:leading-relaxed
            prose-ul:my-1 prose-ul:pl-4 prose-li:my-0
            prose-code:bg-slate-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-cyan-400 prose-code:text-xs
            prose-strong:text-slate-200 prose-strong:font-semibold
            prose-headings:text-slate-300 prose-headings:font-semibold prose-headings:text-xs">
            <ReactMarkdown>{ticket.description}</ReactMarkdown>
          </div>
        </div>

        {/* Voice summary button */}
        <button
          onClick={handleVoice}
          title="AI Voice Summary"
          className={`shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all border ${
            voiceState === 'playing'
              ? 'bg-pink-500/20 text-pink-400 border-pink-500/40 shadow-glow-pink'
              : voiceState === 'loading'
              ? 'bg-pink-950/40 text-pink-500 border-pink-500/30'
              : 'bg-slate-800/60 text-slate-500 hover:text-pink-400 hover:bg-pink-950/30 hover:border-pink-500/30 border-slate-700/60'
          }`}
        >
          {voiceState === 'loading' ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <Volume2 size={12} />
          )}
          {voiceState === 'playing' ? 'Stop' : 'Voice'}
        </button>
      </div>

      <audio id="ticket-voice-player" className="hidden" onEnded={() => setVoiceState('idle')} />

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2.5 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <User size={11} />
          {ticket.customer_name}
        </span>
        <span className="flex items-center gap-1">
          <Clock size={11} />
          {age}
        </span>
        {ticket.sla_due_at && <SLATimer dueAt={ticket.sla_due_at} />}
        {ticket.ssh_host && (
          <span className="flex items-center gap-1 font-mono text-cyan-600">
            <Server size={11} />
            {ticket.ssh_host}:{ticket.ssh_port ?? 22}
          </span>
        )}
        {ticket.service_hint && (
          <span className="font-mono text-purple-500/70">[{ticket.service_hint}]</span>
        )}
      </div>
    </div>
  )
}
