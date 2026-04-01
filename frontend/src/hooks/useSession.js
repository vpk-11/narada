import { useState, useEffect } from 'react'

/**
 * Like useState but backed by sessionStorage.
 * Keys are cleared when the tab closes — nothing persists to the server.
 */
export function useSession(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = sessionStorage.getItem(key)
      return stored ? JSON.parse(stored) : defaultValue
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
