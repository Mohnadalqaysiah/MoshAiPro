/**
 * useMarkets — يجلب الأزواج النشطة من /api/v1/markets/list
 * نتيجة مُخزَّنة في الذاكرة (module-level cache) لتجنب طلبات متكررة
 */
import { useState, useEffect } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Simple in-memory cache (مشترك بين كل الصفحات)
let _cache = null
let _fetching = false
const _listeners = []

function notifyListeners(data) {
  _listeners.forEach(fn => fn(data))
}

async function fetchOnce() {
  if (_cache) return _cache
  if (_fetching) return null
  _fetching = true
  try {
    const res = await axios.get(`${API}/api/v1/markets/list`)
    _cache = res.data.data || []
    notifyListeners(_cache)
    return _cache
  } catch {
    _cache = DEFAULT_MARKETS
    notifyListeners(_cache)
    return _cache
  } finally {
    _fetching = false
  }
}

// Fallback إذا فشل الطلب
const DEFAULT_MARKETS = [
  { symbol: 'XAUUSD', name: 'Gold',       name_ar: 'الذهب',     category: 'forex'     },
  { symbol: 'BTCUSD', name: 'Bitcoin',    name_ar: 'بيتكوين',   category: 'crypto'    },
  { symbol: 'EURUSD', name: 'EUR/USD',    name_ar: 'يورو/دولار',category: 'forex'     },
  { symbol: 'GBPUSD', name: 'GBP/USD',    name_ar: 'جنيه/دولار',category: 'forex'    },
  { symbol: 'USDJPY', name: 'USD/JPY',    name_ar: 'دولار/ين',  category: 'forex'     },
  { symbol: 'USDCHF', name: 'USD/CHF',    name_ar: 'دولار/فرنك',category: 'forex'    },
  { symbol: 'NAS100', name: 'Nasdaq 100', name_ar: 'ناسداك',    category: 'commodity' },
  { symbol: 'SP500',  name: 'S&P 500',    name_ar: 'إس آند بي', category: 'commodity' },
  { symbol: 'USOIL',  name: 'Crude Oil',  name_ar: 'النفط',     category: 'commodity' },
  { symbol: 'XAGUSD', name: 'Silver',     name_ar: 'الفضة',     category: 'commodity' },
]

export default function useMarkets() {
  const [markets, setMarkets] = useState(_cache || [])
  const [loading, setLoading] = useState(!_cache)

  useEffect(() => {
    if (_cache) { setMarkets(_cache); setLoading(false); return }

    const handler = (data) => { setMarkets(data); setLoading(false) }
    _listeners.push(handler)
    fetchOnce()

    return () => {
      const idx = _listeners.indexOf(handler)
      if (idx > -1) _listeners.splice(idx, 1)
    }
  }, [])

  // symbols-only array for convenience
  const symbols = markets.map(m => m.symbol)

  return { markets, symbols, loading }
}
