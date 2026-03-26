import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let _cache = null

export default function useSiteSettings() {
  const [settings, setSettings] = useState(
    _cache || { site_name: 'Qaffel AI', site_logo_url: '' }
  )

  useEffect(() => {
    if (_cache) return
    axios.get(`${API}/api/v1/settings/public`)
      .then(r => { _cache = r.data; setSettings(r.data) })
      .catch(() => {})
  }, [])

  return settings
}
