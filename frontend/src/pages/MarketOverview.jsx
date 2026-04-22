import { useState, useEffect } from 'react'
import axios from 'axios'
import { TrendingUp, TrendingDown, Minus, RefreshCw, Activity } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DIR_CONFIG = {
  BUY:  { label:'شراء', cls:'bg-green-900/40 border-green-700/50 text-green-300', dot:'bg-green-400', Icon: TrendingUp  },
  SELL: { label:'بيع',  cls:'bg-red-900/40 border-red-700/50 text-red-300',       dot:'bg-red-400',   Icon: TrendingDown },
  WAIT: { label:'انتظار', cls:'bg-gray-800/60 border-gray-700/40 text-gray-400',  dot:'bg-gray-600',  Icon: Minus        },
}

function WinBar({ wr }) {
  if (wr == null) return <span className="text-gray-600 text-xs">—</span>
  const color = wr >= 65 ? 'bg-green-500' : wr >= 50 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 bg-gray-800 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{width:`${wr}%`}}/>
      </div>
      <span className="text-xs text-gray-300">{wr}%</span>
    </div>
  )
}

function MarketCard({ m }) {
  const cfg = DIR_CONFIG[m.direction] || DIR_CONFIG.WAIT
  const Icon = cfg.Icon
  return (
    <div className={`rounded-2xl border p-4 flex flex-col gap-3 ${cfg.cls}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="font-bold text-white text-base">{m.symbol}</p>
          {m.live_price && (
            <p className="text-xs text-gray-400 font-mono mt-0.5">{m.live_price.toLocaleString()}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${cfg.dot}`}/>
          <span className="text-xs font-semibold">{cfg.label}</span>
          <Icon size={14}/>
        </div>
      </div>

      {/* Confidence bar */}
      {m.direction !== 'WAIT' && m.confidence > 0 && (
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>الثقة</span>
            <span className="text-gray-300">{Math.round(m.confidence)}%</span>
          </div>
          <div className="w-full bg-gray-900/60 rounded-full h-1">
            <div
              className={`h-1 rounded-full ${m.direction==='BUY'?'bg-green-500':'bg-red-500'}`}
              style={{width:`${Math.min(100, m.confidence)}%`}}/>
          </div>
        </div>
      )}

      {/* Win rate */}
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-500">نجاح 30ي</span>
        <WinBar wr={m.win_rate_30d}/>
      </div>

      {m.wins_30d + m.losses_30d > 0 && (
        <p className="text-xs text-gray-600 text-center">
          {m.wins_30d}✓ {m.losses_30d}✗
        </p>
      )}
    </div>
  )
}

export default function MarketOverview() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter]   = useState('all')  // all | BUY | SELL | WAIT
  const [error, setError]     = useState(null)

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const r = await axios.get(`${API}/api/v1/markets/overview`)
      setData(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'تعذّر تحميل البيانات')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const markets = (data?.markets || []).filter(m =>
    filter === 'all' ? true : m.direction === filter
  )
  const summary = data?.summary || { buy:0, sell:0, wait:0 }

  return (
    <div className="min-h-screen bg-gray-950 text-white" dir="rtl">
      <div className="max-w-7xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Activity size={22} className="text-blue-400"/> نظرة عامة على الأسواق
            </h1>
            <p className="text-sm text-gray-400 mt-1">خريطة حرارية لجميع الأسواق — آخر إشارة + أداء 30 يوم</p>
          </div>
          <button onClick={load} disabled={loading}
            className="flex items-center gap-2 text-sm bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-xl transition border border-gray-700">
            <RefreshCw size={14} className={loading?'animate-spin':''}/>
            تحديث
          </button>
        </div>

        {/* Summary cards */}
        {data && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[
              { label:'إشارات شراء', value:summary.buy,  color:'text-green-400', bg:'bg-green-900/20 border-green-800/40' },
              { label:'إشارات بيع',  value:summary.sell, color:'text-red-400',   bg:'bg-red-900/20 border-red-800/40'   },
              { label:'انتظار',      value:summary.wait, color:'text-gray-400',  bg:'bg-gray-800/40 border-gray-700/40' },
            ].map(s => (
              <div key={s.label} className={`rounded-2xl border ${s.bg} p-4 text-center`}>
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-gray-400 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filter */}
        <div className="flex gap-2 mb-6">
          {['all','BUY','SELL','WAIT'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-sm px-4 py-1.5 rounded-xl border transition ${
                filter===f ? 'border-blue-500 text-blue-400 bg-blue-900/20' : 'border-gray-700 text-gray-500 hover:text-gray-300'
              }`}>
              {f==='all'?'الكل':f==='BUY'?'شراء':f==='SELL'?'بيع':'انتظار'}
              {data && f !== 'all' && (
                <span className="mr-1.5 opacity-60">
                  ({f==='BUY'?summary.buy:f==='SELL'?summary.sell:summary.wait})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-900/20 border border-red-700/40 rounded-xl p-4 text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && !data && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {Array(10).fill(0).map((_,i) => (
              <div key={i} className="h-36 bg-gray-800/40 rounded-2xl border border-gray-800 animate-pulse"/>
            ))}
          </div>
        )}

        {/* Market grid */}
        {!loading && markets.length === 0 && !error && (
          <div className="text-center py-16 text-gray-500">
            <Activity size={32} className="mx-auto mb-3 opacity-30"/>
            <p>لا توجد بيانات بعد — سيتم التحديث تلقائياً بعد أول إشارة</p>
          </div>
        )}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {markets.map(m => <MarketCard key={m.symbol} m={m}/>)}
        </div>

      </div>
    </div>
  )
}
