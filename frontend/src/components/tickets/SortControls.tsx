export type SortKey = 'date' | 'customer' | 'priority'

interface SortControlsProps {
  sortBy: SortKey
  onChange: (s: SortKey) => void
}

const OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'date', label: 'Date' },
  { key: 'customer', label: 'Customer' },
  { key: 'priority', label: 'Priority' },
]

export default function SortControls({ sortBy, onChange }: SortControlsProps) {
  return (
    <div className="flex gap-1">
      {OPTIONS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            sortBy === key
              ? 'bg-blue-600 text-white'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
