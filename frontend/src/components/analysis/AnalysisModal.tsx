import { useEffect, useState } from 'react'
import { X, BarChart3, Loader2 } from 'lucide-react'
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

  useEffect(() => {
    fetch(selectedMonth)
  }, [selectedMonth, fetch])

  useEffect(() => {
    return () => cleanup()
  }, [cleanup])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[90vh] mx-4 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <BarChart3 size={18} className="text-blue-400" />
            <span className="text-base font-semibold text-slate-100">Monthly Analysis</span>
            {loading && <Loader2 size={14} className="animate-spin text-slate-400" />}
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {months.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-100 transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && <ErrorBanner message={error} />}

          {loading && !meta && (
            <div className="flex justify-center py-16">
              <Loader2 size={32} className="animate-spin text-blue-400" />
            </div>
          )}

          {meta && (
            <>
              <StatsCards data={meta} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
                  <ResolutionChart data={meta} />
                </div>
                <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
                  <RootCauseChart data={meta} />
                </div>
              </div>

              <DigestPlayer
                audioUrl={audioUrl}
                transcript={meta.transcript}
                loading={loading && !audioUrl}
              />

              {meta.top_incidents.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                    Top Incidents
                  </p>
                  <div className="space-y-2">
                    {meta.top_incidents.map((incident, i) => (
                      <div key={i} className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                        <p className="text-xs text-slate-400">{incident}</p>
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
