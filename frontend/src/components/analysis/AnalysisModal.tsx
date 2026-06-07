import { useEffect, useState } from 'react'
import { X, BarChart3, Loader2, TrendingUp, Activity } from 'lucide-react'
import { format, subMonths } from 'date-fns'
import { useDigest } from '../../hooks/useDigest'
import StatsCards from './StatsCards'
import ResolutionChart from './ResolutionChart'
import RootCauseChart from './RootCauseChart'
import DigestPlayer from './DigestPlayer'
import ErrorBanner from '../shared/ErrorBanner'

interface AnalysisModalProps {
  onClose: () => void
}

function getMonthOptions(): { value: string; label: string }[] {
  const now = new Date()
  return Array.from({ length: 6 }, (_, i) => {
    const d = subMonths(now, i)
    return {
      value: format(d, 'yyyy-MM'),
      label: format(d, 'MMMM yyyy'),
    }
  })
}

export default function AnalysisModal({ onClose }: AnalysisModalProps) {
  const months = getMonthOptions()
  const [selectedMonth, setSelectedMonth] = useState(months[0].value)
  const { meta, audioUrl, loading, error, fetch, cleanup } = useDigest()

  useEffect(() => { fetch(selectedMonth) }, [selectedMonth, fetch])
  useEffect(() => () => cleanup(), [cleanup])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      <div
        className="relative w-full max-w-5xl max-h-[90vh] mx-4 rounded-2xl shadow-2xl overflow-hidden flex flex-col border"
        style={{
          background: 'rgba(9, 11, 20, 0.97)',
          borderColor: 'rgba(167, 139, 250, 0.3)',
          boxShadow: '0 0 40px rgba(167, 139, 250, 0.15), 0 25px 50px rgba(0,0,0,0.6)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 border-b glass"
          style={{ borderBottomColor: 'rgba(167, 139, 250, 0.2)' }}
        >
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <BarChart3 size={18} className="text-purple-400" style={{ filter: 'drop-shadow(0 0 6px #a78bfa)' }} />
              <span className="text-base font-bold gradient-text">Monthly Analysis</span>
            </div>
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/25">
              <Activity size={10} className="text-purple-400" />
              <span className="text-xs text-purple-400 font-mono">ElevenLabs + Gemini</span>
            </div>
            {loading && <Loader2 size={14} className="animate-spin text-purple-400" />}
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-slate-900 border border-purple-500/30 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-purple-500/50 focus:border-purple-500/50"
            >
              {months.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>

            <button
              onClick={onClose}
              className="text-slate-500 hover:text-slate-200 transition-colors hover:bg-slate-800 rounded-lg p-1"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && <ErrorBanner message={error} />}

          {loading && !meta && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <Loader2 size={36} className="animate-spin text-purple-400" style={{ filter: 'drop-shadow(0 0 8px #a78bfa)' }} />
              <p className="text-sm text-slate-500">Generating AI digest...</p>
            </div>
          )}

          {meta && (
            <>
              <StatsCards data={meta} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div
                  className="rounded-xl border p-4"
                  style={{ background: 'rgba(15,23,42,0.8)', borderColor: 'rgba(34,211,238,0.15)' }}
                >
                  <ResolutionChart data={meta} />
                </div>
                <div
                  className="rounded-xl border p-4"
                  style={{ background: 'rgba(15,23,42,0.8)', borderColor: 'rgba(167,139,250,0.15)' }}
                >
                  <RootCauseChart data={meta} />
                </div>
              </div>

              <DigestPlayer audioUrl={audioUrl} transcript={meta.transcript} loading={loading && !audioUrl} />

              {meta.top_incidents.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp size={12} className="text-cyan-500" />
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Top Incidents This Month
                    </p>
                  </div>
                  <div className="space-y-2">
                    {meta.top_incidents.map((incident, i) => (
                      <div
                        key={i}
                        className="rounded-lg border p-3 flex items-start gap-3"
                        style={{ background: 'rgba(15,23,42,0.6)', borderColor: 'rgba(51,65,85,0.6)' }}
                      >
                        <span className="text-xs font-mono text-slate-600 shrink-0 pt-0.5">#{i + 1}</span>
                        <p className="text-xs text-slate-400 leading-relaxed">{incident}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
