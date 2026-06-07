import { AlertTriangle, X } from 'lucide-react'

export default function ErrorBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/40 text-red-400 text-sm">
      <AlertTriangle size={15} className="mt-0.5 shrink-0" />
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="shrink-0 hover:text-red-200 transition-colors">
          <X size={14} />
        </button>
      )}
    </div>
  )
}
