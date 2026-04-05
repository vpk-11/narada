import { useState, useEffect } from 'react'

/**
 * Like useState but backed by sessionStorage.
 * Keys are cleared when the tab closes — nothing persists to the server.
 */
export function useSession(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = sessionStorage.getItem(key)
      if (!stored) return defaultValue
      const parsed = JSON.parse(stored)
      // Shallow-merge so new fields added to defaultValue get their defaults
      // when old sessionStorage data is missing them.
      if (
        parsed !== null &&
        typeof parsed === 'object' &&
        !Array.isArray(parsed) &&
        typeof defaultValue === 'object' &&
        defaultValue !== null
      ) {
        return { ...defaultValue, ...parsed }
      }
      return parsed
    } catch {
      return defaultValue
    }
  })

  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(value))
    } catch {
      // sessionStorage unavailable -- degrade gracefully
    }
  }, [key, value])

  return [value, setValue]
}
