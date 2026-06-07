import { useState, useCallback } from 'react'
import { getDigestMeta, getDigestAudio } from '../api/voice'
import type { MonthlyDigestResult } from '../types/digest'

export function useDigest() {
  const [meta, setMeta] = useState<MonthlyDigestResult | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async (month: string) => {
    setLoading(true)
    setError(null)

    // Revoke previous blob URL
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    }

    try {
      const [metaResult, audioResult] = await Promise.allSettled([
        getDigestMeta(month),
        getDigestAudio(month),
      ])

      if (metaResult.status === 'fulfilled') setMeta(metaResult.value)
      else setError(`Digest unavailable: ${metaResult.reason}`)

      if (audioResult.status === 'fulfilled') setAudioUrl(audioResult.value)
    } finally {
      setLoading(false)
    }
  }, [audioUrl])

  const cleanup = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
  }, [audioUrl])

  return { meta, audioUrl, loading, error, fetch, cleanup }
}
