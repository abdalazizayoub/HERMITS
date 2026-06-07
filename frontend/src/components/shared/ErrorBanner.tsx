import { AlertTriangle } from 'lucide-react'

export default function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 p-3 rounded bg-red-900/40 border border-red-700 text-red-300 text-sm">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <span>{message}</span>
    </div>
  )
}
