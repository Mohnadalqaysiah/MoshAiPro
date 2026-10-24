import { useState, useEffect } from 'react'
import { useLang } from '../contexts/LangContext'
import axios from 'axios'
import { BarChart2, TrendingUp, RefreshCw, Filter, Clock } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SYMBOLS  = ['','XAUUSD','BTCUSD','ETHUSD','EURUSD','GBPUSD','USDJPY','NAS100','US30','USOIL','XAGUSD']
const TFS      = ['','1h','4h','15m','30m','1d']
const DAYS_OPT = [30, 60, 90, 180, 365]

function WinRateBadge({ wr, sufficient = true, total, minSample }) {
  const isAr = (useLang()?.lang || 'ar') === 'ar'
  if (wr == null) return <span className="text-gray-500 text-xs">—</span>
  // (2026-09-04) عينة صغيرة (مثلاً إشارة وحدة = 100%) توحي بموثوقية وهمية
  // لو ظهرت بشارة خضراء واثقة — نفس منطق sufficient_data بصفحة الأداء.
  if (!sufficient) {
    return (
      <span
        className="text-xs font-medium px-2 py-0.5 rounded-lg border bg-gray-800 text-gray-400 border-gray-700"
        title={isAr ? `عينة صغيرة جداً (${total} من ${minSample} على الأقل) — النسبة مو موثوقة بعد` : `Very small sample (${total} of at least ${minSample}) — the rate is not reliable yet`}
      >
        {isAr ? 'عينة صغيرة' : 'Small sample'} ({total})
      </span>
    )
  }
  const cls = wr >= 65 ? 'bg-green-900/40 text-green-400 border-green-700/40'
            : wr >= 50 ? 'bg-yellow-900/40 text-yellow-400 border-yellow-700/40'
            :            'bg-red-900/40 text-red-400 border-red-700/40'
  return <span className={`text-xs font-bold px-2 py-0.5 rounded-lg border ${cls}`}>{wr}%</span>
}

function MiniBar({ value, max, color = 'bg-blue-500' }) {
  const pct = max > 0 ? (value / max) * 100 : 0
  return (
    <div className="w-full bg-gray-800 rounded-full h-1.5">
      <div className={`${color} h-1.5 rounded-full transition-all`} style={{width:`${pct}%`}}/>
    </div>
  )
}

export default function Backtesting() {
  const isAr = (useLang()?.lang || 'ar') === 'ar'
  const [symbol, setSymbol]   = useState('')
  const [tf, setTf]           = useState('')
  const [days, setDays]       = useState(90)
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const params = new URLSearchParams()
      if (symbol) params.set('symbol', symbol)
      if (tf)     params.set('timeframe', tf)
      params.set('days', days)
      const r = await axios.get(`${API}/api/v1/signals/backtest?${params}`)
      setData(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || (isAr ? 'خطأ في تحميل البيانات' : 'Error loading data'))
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const maxTotal = Math.max(...(data?.by_symbol || []).map(x => x.total), 1)

  return (
    <div className="text-white" dir="rtl">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart2 size={22} className="text-purple-400"/> Backtesting Lite
          </h1>
          <p className="text-sm text-gray-400 mt-1">{isAr ? 'أداء الإشارات التاريخية — بيانات حقيقية من قاعدة البيانات' : 'Historical signal performance — real data from the database'}</p>
        </div>

        {/* Filters */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-4 mb-6">
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">{isAr ? 'الرمز' : 'Symbol'}</label>
              <select value={symbol} onChange={e => setSymbol(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-purple-500">
                {SYMBOLS.map(s => <option key={s} value={s}>{s || (isAr ? 'جميع الرموز' : 'All symbols')}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">{isAr ? 'الإطار الزمني' : 'Timeframe'}</label>
              <select value={tf} onChange={e => setTf(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-purple-500">
                {TFS.map(t => <option key={t} value={t}>{t || (isAr ? 'جميع الإطارات' : 'All timeframes')}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">{isAr ? 'المدة' : 'Period'}</label>
              <select value={days} onChange={e => setDays(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-purple-500">
                {DAYS_OPT.map(d => <option key={d} value={d}>{d} {isAr ? 'يوم' : 'days'}</option>)}
              </select>
            </div>
            <button onClick={load} disabled={loading}
              className="flex items-center gap-2 bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white px-5 py-2 rounded-xl text-sm transition">
              <Filter size={14}/> {isAr ? 'تطبيق' : 'Apply'}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-700/40 rounded-xl p-4 text-red-400 text-sm mb-6">{error}</div>
        )}

        {loading && (
          <div className="flex justify-center py-16">
            <RefreshCw size={24} className="animate-spin text-purple-400"/>
          </div>
        )}

        {data && !loading && (
          <>
            {/* Overall Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { label: isAr ? 'إجمالي الإشارات' : 'Total signals', value: data.overall.total,    color:'text-white' },
                { label: isAr ? 'نسبة النجاح' : 'Win rate',      value: !data.overall.sufficient_sample ? (isAr ? `عينة صغيرة (${data.overall.total})` : `Small sample (${data.overall.total})`) : (data.overall.win_rate != null ? `${data.overall.win_rate}%` : '—'), color: !data.overall.sufficient_sample ? 'text-gray-400' : (data.overall.win_rate >= 65?'text-green-400':data.overall.win_rate>=50?'text-yellow-400':'text-red-400') },
                { label: isAr ? 'فوز / خسارة' : 'Wins / losses',      value: `${data.overall.wins} / ${data.overall.losses}`, color:'text-gray-300' },
                { label: isAr ? 'متوسط R/R' : 'Avg R/R',         value: data.overall.avg_rr ? `${data.overall.avg_rr}×` : '—', color:'text-blue-400' },
              ].map(s => (
                <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-2xl p-4 text-center">
                  <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-xs text-gray-500 mt-1">{s.label}</p>
                </div>
              ))}
            </div>

            {/* By Symbol */}
            {data.by_symbol.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 mb-6">
                <h2 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                  <TrendingUp size={15} className="text-purple-400"/> {isAr ? 'الأداء حسب الرمز' : 'Performance by symbol'}
                </h2>
                <div className="space-y-4">
                  {data.by_symbol.map(row => (
                    <div key={row.symbol}>
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-white text-sm w-20">{row.symbol}</span>
                          <span className="text-xs text-gray-500">{row.total} {isAr ? 'إشارة' : 'signals'}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-gray-400">{row.wins}✓ {row.losses}✗</span>
                          {row.avg_winning_rr && <span className="text-xs text-blue-400">RR {row.avg_winning_rr}×</span>}
                          <WinRateBadge wr={row.win_rate} sufficient={row.sufficient_sample} total={row.total} minSample={data.min_sample}/>
                        </div>
                      </div>
                      <MiniBar value={row.wins} max={row.total}
                        color={!row.sufficient_sample ? 'bg-gray-500' : row.win_rate>=65?'bg-green-500':row.win_rate>=50?'bg-yellow-500':'bg-red-500'}/>
                      {/* Last 5 signals */}
                      {row.recent?.length > 0 && (
                        <div className="flex gap-1.5 mt-1.5">
                          {row.recent.map((s, i) => (
                            <span key={i} title={`${s.direction} | ${s.status}`}
                              className={`text-xs px-2 py-0.5 rounded font-mono ${
                                s.status?.includes('TP') ? 'bg-green-900/40 text-green-400'
                                : s.status === 'sl_hit' ? 'bg-red-900/40 text-red-400'
                                : 'bg-gray-800 text-gray-500'
                              }`}>
                              {s.direction === 'BUY' ? '▲' : '▼'} {s.rr > 0 ? s.rr.toFixed(1) : '?'}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* By Timeframe */}
            {data.by_timeframe.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                <h2 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                  <Clock size={15} className="text-blue-400"/> {isAr ? 'الأداء حسب الإطار الزمني' : 'Performance by timeframe'}
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {data.by_timeframe.map(row => (
                    <div key={row.timeframe} className="bg-gray-800/50 rounded-xl p-3 text-center">
                      <p className="text-lg font-bold text-white font-mono">{row.timeframe}</p>
                      <p className="text-xs text-gray-500 my-1">{row.wins + row.losses} {isAr ? 'إشارة' : 'signals'}</p>
                      <WinRateBadge wr={row.win_rate} sufficient={row.sufficient_sample} total={row.wins + row.losses} minSample={data.min_sample}/>
                      <p className="text-xs text-gray-400 mt-1">{row.wins}✓ {row.losses}✗</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {data.overall.total === 0 && (
              <div className="text-center py-12 text-gray-500">
                <BarChart2 size={32} className="mx-auto mb-3 opacity-30"/>
                <p>{isAr ? 'لا توجد إشارات مغلقة في هذه الفترة' : 'No closed signals in this period'}</p>
                <p className="text-xs mt-1">{isAr ? 'جرّب تغيير الفلاتر أو توسيع المدة الزمنية' : 'Try changing the filters or widening the period'}</p>
              </div>
            )}
          </>
        )}

      </div>
    </div>
  )
}
