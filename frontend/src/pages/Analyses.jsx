import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { History, RefreshCw, Zap, ChevronDown, ChevronUp, AlertCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useLang } from '../contexts/LangContext'
import useMarkets from '../hooks/useMarkets'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const T = {
  ar: {
    title:      'سجل التحليلات',
    sub:        'جميع تحليلاتك المحفوظة مع إمكانية إعادة التحليل',
    refresh:    'تحديث',
    reAnalyze:  'إعادة تحليل',
    noData:     'لا توجد تحليلات بعد. قم بتحليل سوق من صفحة الإشارات.',
    market:     'السوق',
    timeframe:  'الفريم',
    rec:        'التوصية',
    confidence: 'الثقة',
    price:      'السعر',
    entry:      'الدخول',
    sl:         'الإيقاف',
    tp1:        'الهدف 1',
    lot:        'اللوت',
    time:       'الوقت',
    detail:     'التفاصيل',
    buy:  'شراء', sell: 'بيع', wait: 'انتظار', watch: 'مراقبة',
    cached: 'من الكاش',
    filter: 'فلتر السوق',
    all: 'الكل',
    analyzing: 'جاري التحليل...',
  },
  en: {
    title:      'Analysis History',
    sub:        'All your saved analyses with re-analyze option',
    refresh:    'Refresh',
    reAnalyze:  'Re-Analyze',
    noData:     'No analyses yet. Analyze a market from the Signals page.',
    market:     'Market',
    timeframe:  'Timeframe',
    rec:        'Signal',
    confidence: 'Conf.',
    price:      'Price',
    entry:      'Entry',
    sl:         'SL',
    tp1:        'TP1',
    lot:        'Lot',
    time:       'Time',
    detail:     'Details',
    buy:  'BUY', sell: 'SELL', wait: 'WAIT', watch: 'WATCH',
    cached: 'Cached',
    filter: 'Filter Market',
    all: 'All',
    analyzing: 'Analyzing...',
  },
}

const REC_STYLE = {
  BUY:   { bg: 'bg-green-900/30 text-green-400',  icon: <TrendingUp  size={13} /> },
  SELL:  { bg: 'bg-red-900/30   text-red-400',    icon: <TrendingDown size={13} /> },
  WAIT:  { bg: 'bg-gray-700     text-gray-400',   icon: <Minus size={13} /> },
  WATCH: { bg: 'bg-gray-700     text-gray-400',   icon: <Minus size={13} /> },
}

export default function Analyses() {
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'
  const { markets } = useMarkets()

  const [logs,     setLogs]     = useState([])
  const [total,    setTotal]    = useState(0)
  const [loading,  setLoading]  = useState(false)
  const [filterM,  setFilterM]  = useState('')
  const [expanded, setExpanded] = useState(null)
  const [reanalyzing, setReanalyzing] = useState(null)
  const [error,    setError]    = useState(null)
  const [logsLimit, setLogsLimit] = useState(10)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { limit: 50 }
      if (filterM) params.market = filterM
      const res = await axios.get(`${API}/api/v1/analyses/history`, { params })
      setLogs(res.data.logs || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [filterM])

  useEffect(() => { load() }, [load])

  const reAnalyze = async (log) => {
    setReanalyzing(log.id)
    try {
      await axios.post(`${API}/api/v1/signals/analyze?symbol=${log.market}&timeframe=${log.timeframe}&advanced_mode=true&force_refresh=true`)
      await load()
    } catch (e) {
      alert(e.response?.data?.detail || e.message)
    } finally {
      setReanalyzing(null)
    }
  }

  const fmt = (v, d = 5) => v != null ? Number(v).toFixed(d) : '—'
  const fmtPrice = (v, market) => v != null ? Number(v).toFixed(market === 'BTCUSD' ? 2 : 5) : '—'
  const fmtTime = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleString(isAr ? 'ar-SA' : 'en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <History size={22} className="text-blue-400" /> {tx.title}
          </h1>
          <p className="text-gray-400 text-sm mt-1">{tx.sub} — {total} {isAr ? 'تحليل' : 'analyses'}</p>
        </div>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm disabled:opacity-50">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> {tx.refresh}
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => { setFilterM(''); setLogsLimit(10) }}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${!filterM ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
          {tx.all}
        </button>
        {markets.map(m => (
          <button key={m.symbol} onClick={() => { setFilterM(filterM === m.symbol ? '' : m.symbol); setLogsLimit(10) }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filterM === m.symbol ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
            {m.symbol}
          </button>
        ))}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-900/30 border border-red-700 rounded-xl text-red-400 text-sm">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">{isAr ? 'جاري التحميل...' : 'Loading...'}</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">{tx.noData}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-gray-400 text-xs">
                  {[tx.time, tx.market, tx.timeframe, tx.rec, tx.confidence, tx.price, tx.entry, tx.sl, tx.tp1, tx.lot, ''].map((h, i) => (
                    <th key={i} className="px-3 py-3 text-right font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.slice(0, logsLimit).map((log) => {
                  const style = REC_STYLE[log.recommendation] || REC_STYLE.WATCH
                  const isExp = expanded === log.id
                  return (
                    <>
                      <tr key={log.id} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                        <td className="px-3 py-2.5 text-gray-400 text-xs whitespace-nowrap">{fmtTime(log.created_at)}</td>
                        <td className="px-3 py-2.5 font-mono font-semibold text-white">{log.market}</td>
                        <td className="px-3 py-2.5 text-gray-300">{log.timeframe}</td>
                        <td className="px-3 py-2.5">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${style.bg}`}>
                            {style.icon}
                            {tx[log.recommendation?.toLowerCase()] || log.recommendation}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className={`font-semibold ${log.confidence >= 75 ? 'text-green-400' : log.confidence >= 60 ? 'text-yellow-400' : 'text-gray-400'}`}>
                            {log.confidence?.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-blue-300 text-xs">{fmtPrice(log.current_price, log.market)}</td>
                        <td className="px-3 py-2.5 font-mono text-xs">{fmt(log.entry)}</td>
                        <td className="px-3 py-2.5 font-mono text-red-400 text-xs">{fmt(log.sl)}</td>
                        <td className="px-3 py-2.5 font-mono text-green-400 text-xs">{fmt(log.tp1)}</td>
                        <td className="px-3 py-2.5 font-mono text-xs">
                          {log.lot_size ? <span className="text-yellow-400 font-semibold">{log.lot_size}</span> : '—'}
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => reAnalyze(log)}
                              disabled={reanalyzing === log.id}
                              className="flex items-center gap-1 px-2 py-1 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 rounded text-xs disabled:opacity-50"
                            >
                              {reanalyzing === log.id
                                ? <><RefreshCw size={11} className="animate-spin" /> {tx.analyzing}</>
                                : <><Zap size={11} /> {tx.reAnalyze}</>}
                            </button>
                            {log.full_result && (
                              <button
                                onClick={() => setExpanded(isExp ? null : log.id)}
                                className="p-1 text-gray-400 hover:text-white rounded"
                              >
                                {isExp ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                      {isExp && log.full_result && (
                        <tr key={`${log.id}-detail`} className="bg-gray-900/50">
                          <td colSpan={11} className="px-4 py-3">
                            <AnalysisDetail data={log.full_result} market={log.market} isAr={isAr} />
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
            {logs.length > logsLimit && (
              <button
                onClick={() => setLogsLimit(l => l + 10)}
                className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 text-sm text-gray-400 hover:text-white bg-gray-700/40 hover:bg-gray-700 rounded-xl transition-colors border border-gray-700/50"
              >
                <ChevronDown size={16} />
                {isAr ? `عرض المزيد (${logs.length - logsLimit} متبقية)` : `Show more (${logs.length - logsLimit} remaining)`}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function AnalysisDetail({ data, market, isAr }) {
  const levels = data?.levels || {}
  const items = [
    [isAr ? 'الاتجاه'       : 'Trend',    data?.trend?.direction ? `${data.trend.direction} (${data.trend.strength}%)` : null],
    [isAr ? 'Wyckoff'        : 'Wyckoff',  data?.wyckoff_analysis?.phase],
    [isAr ? 'المنطقة'       : 'Zone',     data?.premium_discount?.current_zone],
    [isAr ? 'Kill Zone'      : 'Kill Zone',data?.killzone?.name],
    [isAr ? 'منطقة الدخول'  : 'Entry Zone',levels.entry_zone_min ? `${levels.entry_zone_min} — ${levels.entry_zone_max}` : levels.entry],
    [isAr ? 'R/R'            : 'R/R',      levels.risk_reward ? `${Number(levels.risk_reward).toFixed(2)}x` : null],
    [isAr ? 'البالانس'       : 'Balance',  data?.account_balance ? `$${data.account_balance}` : null],
    [isAr ? 'المخاطرة'       : 'Risk',     data?.risk_percent    ? `${data.risk_percent}%`    : null],
    [isAr ? 'اللوت المحسوب'  : 'Lot Size', data?.lot_size        ? data.lot_size              : null],
  ].filter(([, v]) => v != null)

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 text-xs">
      {items.map(([label, val]) => (
        <div key={label} className="bg-gray-800 rounded-lg p-2">
          <div className="text-gray-500 mb-0.5">{label}</div>
          <div className="text-white font-mono font-medium">{val}</div>
        </div>
      ))}
    </div>
  )
}
