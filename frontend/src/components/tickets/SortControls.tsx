export type SortKey = 'date' | 'customer' | 'priority'

interface SortControlsProps {
  sortBy: SortKey
  onChange: (s: SortKey) => void
}

const OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'priority', label: 'Priority' },
  { key: 'date', label: 'Date' },
  { key: 'customer', label: 'Customer' },
]

export default function SortControls({ sortBy, onChange }: SortControlsProps) {
  return (
    <div className="flex gap-1">
      {OPTIONS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`px-2 py-1 text-xs rounded transition-all font-medium ${
            sortBy === key
              ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
              : 'bg-slate-800/60 text-slate-500 hover:bg-slate-700/60 hover:text-slate-300 border border-transparent'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
