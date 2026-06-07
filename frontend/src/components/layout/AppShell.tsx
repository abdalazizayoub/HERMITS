import { useState } from 'react'
import { BarChart3, Radio } from 'lucide-react'
import TicketList from '../tickets/TicketList'
import WorkbenchPanel from '../workbench/WorkbenchPanel'
import AnalysisModal from '../analysis/AnalysisModal'

export default function AppShell() {
  const [showAnalysis, setShowAnalysis] = useState(false)

  return (
    <div className="flex flex-col h-full bg-slate-950">
      {/* Top navigation bar */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900 shrink-0">
        <div className="flex items-center gap-2">
          <Radio size={16} className="text-blue-400" />
          <span className="text-sm font-bold text-slate-100 tracking-tight">HERMITS</span>
          <span className="text-xs text-slate-500 ml-1">Incident Response</span>
        </div>

        <button
          onClick={() => setShowAnalysis(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 text-sm transition-colors border border-slate-700"
        >
          <BarChart3 size={14} />
          Monthly Analysis
        </button>
      </header>

      {/* Main 3-panel layout */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Ticket list */}
        <div className="w-72 shrink-0">
          <TicketList />
        </div>

        {/* Right: Workbench */}
        <div className="flex-1 min-w-0">
          <WorkbenchPanel />
        </div>
      </div>

      {/* Monthly analysis modal */}
      {showAnalysis && <AnalysisModal onClose={() => setShowAnalysis(false)} />}
    </div>
  )
}
