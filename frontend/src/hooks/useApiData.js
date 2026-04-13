import { useState, useEffect, useRef } from 'react'

const POLL_MS = 2000

export function useApiData() {
  const [data, setData]     = useState(null)
  const [error, setError]   = useState(null)
  const timerRef            = useRef(null)

  const fetchData = async () => {
    try {
      const res = await fetch('/api/data')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    fetchData()
    timerRef.current = setInterval(fetchData, POLL_MS)
    return () => clearInterval(timerRef.current)
  }, [])

  return { data, error }
}
