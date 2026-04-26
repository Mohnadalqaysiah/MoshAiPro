import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { RefreshCw, Flame } from 'lucide-react'
import useMarkets from '../hooks/useMarkets'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const CAT_LABEL = {
  forex:   { ar: 'فوركس',   en: 'Forex'    },
  metals:  { ar: 'معادن',   en: 'Metals'   },
  crypto:  { ar: 'كريبتو',  en: 'Crypto'   },
  indices: { ar: 'مؤشرات',  en: 'Indices'  },
  energy:  { ar: 'طاقة',    en: 'Energy'   },
  other:   { ar: 'أخرى',    en: 'Other'    },
}

function cellStyle(rec, conf) {
  if (rec === 'BUY') {
    return conf >= 75
      ? { bg: 'bg-green-500/25 border-green-500/50',  text: 'text-green-300', labelAr: '▲ شراء',  labelEn: '▲ BUY'  }
      : { bg: 'bg-green-500/12 border-green-700/30',  text: 'text-green-400', labelAr: '▲ شراء',  labelEn: '▲ BUY'  }
  }
  if (rec === 'SELL') {
    return conf >= 75
      ? { bg: 'bg-red-500/25 border-red-500/50',      text: 'text-red-300',   labelAr: '▼ بيع',   labelEn: '▼ SELL' }
      : { bg: 'bg-red-500/12 border-red-700/30',      text: 'text-red-400',   labelAr: '▼ بيع',   labelEn: '▼ SELL' }
  }
  if (rec === 'WATCH' || rec === 'WAIT') {
    return { bg: 'bg-gray-800/50 border-gray-700/30', text: 'text-gray-500',   labelAr: '◈ راقب',  labelEn: '◈ WATCH' }
  }
  return { bg: 'bg-gray-900/30 border-gray-800/20',   text: 'text-gray-700',   labelAr: '—',        labelEn: '—' }
}

export default function MarketHeatmap({ onAnalyzeResult }) {
  const { markets } = useMarkets()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const [signals, setSignals]   = useState({})
  const [loading, setLoading]   = useState(false)
  const [analyzing, setAnalyzing] = useState(null)

  // Fetch latest signals for all markets
  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API}/api/v1/signals/latest?limit=200`)
      const map = {}
      for (const s of (res.data.data || [])) {
        const sym = s.market || s.symbol
        if (!map[sym]) map[sym] = s   // first = most recent
      }
      setSignals(map)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const analyze = async (symbol) => {
    setAnalyzing(symbol)
    try {
      const res = await axios.post(
        `${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=1h&advanced_mode=true`
      )
      const d = res.data.data
      setSignals(prev => ({ ...prev, [symbol]: { ...d, market: symbol } }))
      if (onAnalyzeResult) onAnalyzeResult({ ...d, market: symbol })
    } catch {}
    setAnalyzing(null)
  }

  // Compute summary counts
  const total = markets.length
  const buys  = markets.filter(m => (signals[m.symbol]?.recommendation || signals[m.symbol]?.signal_type) === 'BUY').length
  const sells = markets.filter(m => (signals[m.symbol]?.recommendation || signals[m.symbol]?.signal_type) === 'SELL').length

  // Group by category
  const grouped = {}
  for (const m of markets) {
    const cat = m.category || 'other'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(m)
  }

  return (
    <div className="bg-gray-900/60 border border-white/8 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-orange-500/15 flex items-center justify-center">
            <Flame size={15} className="text-orange-400" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">
              {isAr ? 'خريطة الأسواق' : 'Market Heatmap'}
            </h3>
            <p className="text-xs text-gray-500">
              {isAr
                ? `${buys} شراء · ${sells} بيع · ${total - buys - sells} محايد`
                : `${buys} BUY · ${sells} SELL · ${total - buys - sells} Neutral`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Mini bull/bear bar */}
          {total > 0 && (
            <div className="hidden sm:flex items-center gap-1 text-[10px] text-gray-600">
              <span className="text-green-400 font-bold">{buys}</span>
              <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden flex">
                <div className="bg-green-500 h-full" style={{ width: `${(buys / total) * 100}%` }} />
                <div className="bg-red-500 h-full"   style={{ width: `${(sells / total) * 100}%` }} />
              </div>
              <span className="text-red-400 font-bold">{sells}</span>
            </div>
          )}
          <button
            onClick={fetchAll}
            disabled={loading}
            className="p-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-40"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="p-4 space-y-4">
        {Object.entries(grouped).map(([cat, items]) => (
          <div key={cat}>
            <p className="text-[10px] text-gray-600 uppercase tracking-wider font-bold mb-2">
              {CAT_LABEL[cat]?.[isAr ? 'ar' : 'en'] || cat}
            </p>
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
              {items.map(m => {
                const sig  = signals[m.symbol]
                const rec  = sig?.recommendation || sig?.signal_type || 'NONE'
                const conf = sig?.ai_confidence_score || sig?.ai_confidence || 0
                const c    = cellStyle(rec, conf)
                const isAn = analyzing === m.symbol

                return (
                  <button
                    key={m.symbol}
                    onClick={() => analyze(m.symbol)}
                    disabled={!!analyzing}
                    className={`relative rounded-xl border px-2 py-3 text-center transition-all duration-200 select-none
                      ${c.bg}
                      ${isAn ? 'opacity-60 cursor-not-allowed' : 'hover:scale-105 active:scale-95 cursor-pointer'}
                    `}
                  >
                    <div className="text-[11px] font-bold text-white truncate mb-1">{m.symbol}</div>
                    {isAn ? (
                      <RefreshCw size={10} className="animate-spin mx-auto text-gray-400" />
                    ) : (
                      <>
                        <div className={`text-[10px] font-semibold ${c.text}`}>
                          {isAr ? c.labelAr : c.labelEn}
                        </div>
                        {conf > 0 && (
                          <div className="text-[9px] text-gray-600 mt-0.5">{Math.round(conf)}%</div>
                        )}
                      </>
                    )}

                    {/* Intensity glow for high conf */}
                    {rec === 'BUY' && conf >= 80 && (
                      <span className="absolute inset-0 rounded-xl bg-green-500/10 animate-pulse pointer-events-none" />
                    )}
                    {rec === 'SELL' && conf >= 80 && (
                      <span className="absolute inset-0 rounded-xl bg-red-500/10 animate-pulse pointer-events-none" />
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="px-5 py-3 border-t border-white/5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-600">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-green-500/50 inline-block" />
          {isAr ? 'شراء قوي (≥75%)' : 'Strong BUY (≥75%)'}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-red-500/50 inline-block" />
          {isAr ? 'بيع قوي (≥75%)' : 'Strong SELL (≥75%)'}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-gray-700 inline-block" />
          {isAr ? 'مراقبة / بدون بيانات' : 'Watch / No data'}
        </span>
        <span className="ms-auto text-gray-700">
          {isAr ? 'اضغط أي خلية لتحليل فوري' : 'Tap any cell for instant analysis'}
        </span>
      </div>
    </div>
  )
}
