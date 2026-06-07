import { Volume2, Loader2 } from 'lucide-react'

interface DigestPlayerProps {
  audioUrl: string | null
  transcript: string | null
  loading: boolean
}

export default function DigestPlayer({ audioUrl, transcript, loading }: DigestPlayerProps) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-3">
      <div className="flex items-center gap-2 text-slate-400 text-sm font-medium">
        <Volume2 size={16} />
        Voice Digest — ElevenLabs
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Loader2 size={14} className="animate-spin" />
          Generating audio...
        </div>
      ) : audioUrl ? (
        <audio
          controls
          src={audioUrl}
          className="w-full h-10"
          style={{ accentColor: '#3b82f6' }}
        />
      ) : (
        <p className="text-sm text-slate-500">Audio unavailable</p>
      )}

      {transcript && (
        <details className="group">
          <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300 select-none">
            Transcript
          </summary>
          <div className="mt-2 text-xs text-slate-400 leading-relaxed bg-slate-800/50 rounded p-3 max-h-40 overflow-y-auto whitespace-pre-wrap">
            {transcript}
          </div>
        </details>
      )}
    </div>
  )
}
