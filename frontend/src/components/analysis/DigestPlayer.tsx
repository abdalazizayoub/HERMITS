import { Volume2, Loader2, Mic } from 'lucide-react'

interface DigestPlayerProps {
  audioUrl: string | null
  transcript: string | null
  loading: boolean
}

export default function DigestPlayer({ audioUrl, transcript, loading }: DigestPlayerProps) {
  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{
        background: 'rgba(244, 114, 182, 0.04)',
        borderColor: 'rgba(244, 114, 182, 0.25)',
      }}
    >
      <div className="flex items-center gap-2">
        <Mic size={15} className="text-pink-400" style={{ filter: 'drop-shadow(0 0 5px #f472b6)' }} />
        <span className="text-sm font-semibold text-pink-400">AI Voice Digest</span>
        <span className="text-xs text-slate-600 font-mono">// ElevenLabs</span>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-slate-500 text-xs py-1">
          <Loader2 size={13} className="animate-spin text-pink-500" />
          Synthesizing audio...
        </div>
      ) : audioUrl ? (
        <audio
          controls
          src={audioUrl}
          className="w-full h-9 rounded-lg"
          style={{ accentColor: '#f472b6' }}
        />
      ) : (
        <div className="flex items-center gap-2 py-1">
          <Volume2 size={13} className="text-slate-600" />
          <p className="text-xs text-slate-600">Audio unavailable — ElevenLabs key may be missing</p>
        </div>
      )}

      {transcript && (
        <details className="group">
          <summary className="text-xs text-slate-600 cursor-pointer hover:text-pink-400 select-none transition-colors">
            View transcript ▸
          </summary>
          <div
            className="mt-2 text-xs text-slate-400 leading-relaxed rounded-lg p-3 max-h-40 overflow-y-auto whitespace-pre-wrap border"
            style={{ background: 'rgba(9,11,20,0.7)', borderColor: 'rgba(244,114,182,0.15)' }}
          >
            {transcript}
          </div>
        </details>
      )}
    </div>
  )
}
