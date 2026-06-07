import { useState, useCallback, useRef } from 'react'
import { getDigestMeta, getDigestAudio } from '../api/voice'
import type { MonthlyDigestResult } from '../types/digest'

export function useDigest() {
  const [meta, setMeta] = useState<MonthlyDigestResult | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Keep the current audio URL in a ref so cleanup doesn't need it as a dep
  const audioUrlRef = useRef<string | null>(null)

  const fetch = useCallback(async (month: string) => {
    setLoading(true)
    setError(null)

    // Revoke previous blob URL
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
      setAudioUrl(null)
    }

    try {
      // Fetch metadata first (fast — no ElevenLabs call)
      const metaResult = await getDigestMeta(month)
      setMeta(metaResult)

      // Then fetch audio separately (slower)
      try {
        const url = await getDigestAudio(month)
        audioUrlRef.current = url
        setAudioUrl(url)
      } catch (audioErr) {
        console.warn('Audio generation failed:', audioErr)
        // Metadata still available — don't surface this as a fatal error
      }
    } catch (err) {
      setError(`Could not load digest: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }, []) // stable — no deps that change

  const cleanup = useCallback(() => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
  }, [])

  return { meta, audioUrl, loading, error, fetch, cleanup }
}
