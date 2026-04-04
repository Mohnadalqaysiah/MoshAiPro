import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { TrendingUp, TrendingDown, Activity, Zap, AlertCircle, RefreshCw, Send, ExternalLink, Copy, CheckCircle, X, ChevronDown } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import useMarkets from '../hooks/useMarkets'
import { useLang } from '../contexts/LangContext'
import PerformanceSection from '../components/PerformanceSection'

const T = {
  ar: {
    title: 'لوحة التحكم', sub: 'تحليل الأسواق بالذكاء الاصطناعي',
    refresh: 'تحديث', analyze: 'حلل الآن', analyzing: 'جاري...',
    signals: 'آخر الإشارات', markets: 'الأسواق',
    buy: 'شراء', sell: 'بيع', watch: 'مراقبة',
    entry: 'الدخول', sl: 'الإيقاف', tp: 'الهدف', rr: 'R/R', lot: 'اللوت',
    conf: 'الثقة', price: 'السعر', limitMsg: 'وصلت للحد الأقصى',
    tgLink: 'ربط مع Telegram', tgLinked: 'مرتبط بـ Telegram', tgRelink: 'إعادة الربط',
    tgDesc: 'استقبل التنبيهات مباشرة على هاتفك',
    noSignals: 'لا توجد إشارات بعد. حلل سوقاً للبدء.',
    history: 'السجل',
  },
  en: {
    title: 'Dashboard', sub: 'AI-powered market analysis',
    refresh: 'Refresh', analyze: 'Analyze', analyzing: 'Loading...',
    signals: 'Latest Signals', markets: 'Markets',
    buy: 'BUY', sell: 'SELL', watch: 'WATCH',
    entry: 'Entry', sl: 'SL', tp: 'TP', rr: 'R/R', lot: 'Lot',
    conf: 'Conf', price: 'Price', limitMsg: 'Limit reached',
    tgLink: 'Link Telegram', tgLinked: 'Linked to Telegram', tgRelink: 'Re-link',
    tgDesc: 'Receive alerts directly on your phone',
    noSignals: 'No signals yet. Analyze a market to start.',
    history: 'History',
  },
}

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Dashboard() {
  const { user } = useAuth()
  const { markets } = useMarkets()
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'
  const [signals, setSignals]       = useState([])
  const [signalHistory, setSignalHistory] = useState([])
  const [analyzing, setAnalyzing]   = useState(null)
  const [error, setError]           = useState(null)
  const [limitReached, setLimitReached] = useState(false)
  const [tgLink, setTgLink]         = useState('')
  const [tgBot, setTgBot]           = useState('Qaffelbot')
  const [tgCopied, setTgCopied]     = useState(false)
  const [tgLoading, setTgLoading]   = useState(false)
  const [relinking, setRelinking]   = useState(false)
  const [relinkDone, setRelinkDone] = useState(false)
  const [quickResult, setQuickResult] = useState(null)   // modal result
  const [historyLimit, setHistoryLimit] = useState(10)   // show more — signal history
  const [signalsLimit, setSignalsLimit] = useState(10)   // show more — recent signals

  // جلب آخر الإشارات
  useEffect(() => { fetchSignals(); fetchSignalHistory() }, [])

  const fetchSignals = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/signals/latest?limit=10`)
      setSignals(res.data.data || [])
    } catch (e) {
      // no signals yet
    }
  }

  const fetchSignalHistory = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/signals/history?limit=20`)
      setSignalHistory(res.data.signals || [])
    } catch (e) {
      // no history yet
    }
  }

  const analyzeMarket = async (symbol, forceRefresh = false) => {
    setAnalyzing(symbol)
    setError(null)
    setLimitReached(false)
    try {
      const res = await axios.post(
        `${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=1h&advanced_mode=true&force_refresh=${forceRefresh}`
      )
      const data = res.data.data
      const entry = { ...data, market: symbol, id: Date.now() }
      setSignals(prev => [entry, ...prev.slice(0, 9)])
      setQuickResult(entry)  // فتح الـ modal
    } catch (e) {
      if (e.response?.status === 403) {
        setLimitReached(true)
        setError(e.response.data.detail)
      } else {
        setError(`فشل تحليل ${symbol}: ${e.response?.data?.detail || e.message}`)
      }
    } finally {
      setAnalyzing(null)
    }
  }

  const fetchTgLink = async () => {
    if (tgLink) return tgLink
    setTgLoading(true)
    try {
      const r = await axios.get(`${API}/api/v1/auth/telegram-link`)
      const link = r.data.link || ''
      setTgLink(link)
      if (r.data.bot_username) setTgBot(r.data.bot_username)
      return link
    } catch {
      return ''
    } finally {
      setTgLoading(false)
    }
  }

  const openTgLink = async () => {
    const link = await fetchTgLink()
    if (link) window.open(link, '_blank', 'noreferrer')
  }

  const copyTgLink = async () => {
    const link = await fetchTgLink()
    if (!link) return
    navigator.clipboard.writeText(link)
    setTgCopied(true)
    setTimeout(() => setTgCopied(false), 2000)
  }

  const relinkTelegram = async () => {
    setRelinking(true)
    try {
      const r = await axios.post(`${API}/api/v1/auth/relink-telegram`)
      const link = r.data.link || ''
      setTgLink(link)
      if (r.data.bot_username) setTgBot(r.data.bot_username)
      setRelinkDone(true)
      if (link) window.open(link, '_blank', 'noreferrer')
    } catch { /* ignore */ } finally { setRelinking(false) }
  }

  const getSignalColor = (rec) => {
    if (rec === 'BUY') return 'text-green-400'
    if (rec === 'SELL') return 'text-red-400'
    return 'text-gray-400'
  }

  const getSignalBg = (rec) => {
    if (rec === 'BUY') return 'bg-green-900/30 border-green-700'
    if (rec === 'SELL') return 'bg-red-900/30 border-red-700'
    return 'bg-gray-800 border-gray-700'
  }

  const getSignalAr = (rec) => {
    if (rec === 'BUY') return tx.buy
    if (rec === 'SELL') return tx.sell
    return tx.watch
  }

  const showTgCard     = user && !user.telegram_linked && !relinkDone
  const showRelinkCard = user && user.telegram_linked && !relinkDone

  // ── Quick Analysis Modal ──────────────────────────────────────────────────
  const QuickModal = ({ result, onClose }) => {
    if (!result) return null
    const rec   = result.recommendation || result.signal_type || 'WATCH'
    const conf  = result.ai_confidence_score || result.ai_confidence || 0
    const lvl   = result.levels || {}
    const entry = lvl.entry || result.entry_zones?.[0]
    const sl    = lvl.stop_loss || result.stop_loss_zone
    const tp1   = lvl.tp1 || result.take_profit_zones?.[0]
    const tp2   = lvl.tp2 || result.take_profit_zones?.[1]
    const rr    = result.risk_reward || lvl.risk_reward
    const price = result.current_price
    const fmt   = (v, d = 5) => v != null ? (typeof v === 'number' ? v.toFixed(d) : v) : '—'

    const recColor = rec === 'BUY' ? 'text-green-400' : rec === 'SELL' ? 'text-red-400' : 'text-yellow-400'
    const recBg    = rec === 'BUY' ? 'bg-green-500/10 border-green-600/40' : rec === 'SELL' ? 'bg-red-500/10 border-red-600/40' : 'bg-yellow-500/10 border-yellow-600/40'
    const recLabel = rec === 'BUY' ? '🟢 شراء' : rec === 'SELL' ? '🔴 بيع' : '👁 مراقبة'

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
        <div
          className="relative bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm shadow-2xl animate-fade-in"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className={`flex items-center justify-between px-5 py-4 border-b ${recBg} rounded-t-2xl border-b-gray-700/50`}>
            <div className="flex items-center gap-3">
              <span className="text-white font-bold text-lg">{result.market || result.symbol}</span>
              <span className={`font-bold text-base ${recColor}`}>{recLabel}</span>
            </div>
            <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <div className="px-5 py-4 space-y-4">
            {/* Confidence */}
            <div className="flex items-center justify-between">
              <span className="text-gray-400 text-sm">نسبة الثقة</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${conf >= 75 ? 'bg-green-500' : conf >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${conf}%` }}
                  />
                </div>
                <span className="text-white font-bold text-sm">{Math.round(conf)}%</span>
              </div>
            </div>

            {/* Levels grid */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'السعر الحالي', val: fmt(price, 4), color: 'text-blue-300' },
                { label: 'سعر الدخول',  val: fmt(entry, 5), color: 'text-white' },
                { label: 'وقف الخسارة', val: fmt(sl, 5),    color: 'text-red-400' },
                { label: 'الهدف الأول', val: fmt(tp1, 5),   color: 'text-green-400' },
                { label: 'الهدف الثاني',val: fmt(tp2, 5),   color: 'text-green-300' },
                { label: 'R/R',          val: rr ? `1:${typeof rr === 'number' ? rr.toFixed(1) : rr}` : '—', color: 'text-yellow-400' },
              ].map(({ label, val, color }) => (
                <div key={label} className="bg-gray-800 rounded-xl px-3 py-2.5">
                  <p className="text-xs text-gray-500 mb-0.5">{label}</p>
                  <p className={`font-semibold text-sm font-mono ${color}`}>{val}</p>
                </div>
              ))}
            </div>

            {/* Summary */}
            {result.summary && (
              <div className="bg-gray-800 rounded-xl px-3 py-3 text-xs text-gray-400 leading-relaxed line-clamp-3">
                {result.summary}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-5 pb-4">
            <button
              onClick={onClose}
              className="w-full py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-xl text-sm font-medium transition-colors"
            >
              إغلاق
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6" dir={isAr ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{tx.title}</h1>
          <p className="text-gray-400 text-sm mt-1">{tx.sub}</p>
        </div>
        <button
          onClick={fetchSignals}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
        >
          <RefreshCw size={14} />
          {tx.refresh}
        </button>
      </div>

      {/* Quick Analysis Modal */}
      <QuickModal result={quickResult} onClose={() => setQuickResult(null)} />

      {error && (
        <div className="flex items-center justify-between gap-2 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle size={16} />
            {error}
          </div>
          {limitReached && (
            <Link to="/pricing" className="flex-shrink-0 bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded-lg text-xs font-semibold">
              اشترك الآن
            </Link>
          )}
        </div>
      )}

      {/* Telegram Linking Card — not linked yet */}
      {showTgCard && (
        <div className="bg-indigo-950/60 border border-indigo-500/70 rounded-xl p-5" dir="rtl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-indigo-600/40 flex items-center justify-center flex-shrink-0">
              <Send size={18} className="text-indigo-300" />
            </div>
            <div>
              <h3 className="text-white font-semibold">اربط حسابك مع Telegram</h3>
              <p className="text-indigo-300 text-sm mt-0.5">استقبل الإشارات والتنبيهات مباشرة على هاتفك عبر @{tgBot}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 mt-4 flex-wrap">
            <button
              onClick={openTgLink}
              disabled={tgLoading}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-60 text-white px-5 py-2.5 rounded-lg font-semibold text-sm transition-all"
            >
              {tgLoading ? <RefreshCw size={15} className="animate-spin" /> : <ExternalLink size={15} />}
              {tgLoading ? 'جاري التحميل...' : `ربط مع @${tgBot}`}
            </button>
            <button
              onClick={copyTgLink}
              disabled={tgLoading}
              className="flex items-center gap-1.5 text-indigo-400 hover:text-white border border-indigo-700 hover:border-indigo-400 px-3 py-2.5 rounded-lg text-sm transition-all"
            >
              {tgCopied ? <CheckCircle size={14} className="text-green-400" /> : <Copy size={14} />}
              {tgCopied ? 'تم النسخ' : 'نسخ الرابط'}
            </button>
          </div>
        </div>
      )}

      {/* Re-link Telegram Card — already linked */}
      {showRelinkCard && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4" dir="rtl">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-green-900/40 flex items-center justify-center flex-shrink-0">
                <CheckCircle size={16} className="text-green-400" />
              </div>
              <div>
                <p className="text-sm text-white font-medium">
                  Telegram مربوط{user.telegram_username ? ` — @${user.telegram_username}` : ''}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">إذا تغيّر البوت أو انقطع الربط، أعد التفعيل</p>
              </div>
            </div>
            <button
              onClick={relinkTelegram}
              disabled={relinking}
              className="flex items-center gap-2 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition"
            >
              {relinking ? <RefreshCw size={13} className="animate-spin" /> : <RefreshCw size={13} />}
              إعادة ربط @{tgBot}
            </button>
          </div>
        </div>
      )}

      {/* Quick Analyze */}
      <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700/60">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Zap size={16} className="text-yellow-400" />
            تحليل سريع
          </h2>
          <span className="text-xs text-gray-500 hidden sm:block">كليك يسار = كاش · كليك يمين = تحديث فوري</span>
        </div>

        <div className="p-4">
          {/* تجميع الأسواق حسب الفئة */}
          {(() => {
            const cats = {}
            markets.forEach(m => {
              const c = m.category || 'other'
              if (!cats[c]) cats[c] = []
              cats[c].push(m)
            })
            const catMeta = {
              forex:   { label: 'فوركس',    color: 'from-blue-600/20 to-blue-700/10 border-blue-700/40 hover:border-blue-500/60 text-blue-300', ring: 'ring-blue-500/40' },
              metals:  { label: 'معادن',    color: 'from-yellow-600/20 to-yellow-700/10 border-yellow-700/40 hover:border-yellow-500/60 text-yellow-300', ring: 'ring-yellow-500/40' },
              crypto:  { label: 'كريبتو',   color: 'from-purple-600/20 to-purple-700/10 border-purple-700/40 hover:border-purple-500/60 text-purple-300', ring: 'ring-purple-500/40' },
              indices: { label: 'مؤشرات',   color: 'from-green-600/20 to-green-700/10 border-green-700/40 hover:border-green-500/60 text-green-300', ring: 'ring-green-500/40' },
              energy:  { label: 'طاقة',     color: 'from-orange-600/20 to-orange-700/10 border-orange-700/40 hover:border-orange-500/60 text-orange-300', ring: 'ring-orange-500/40' },
              other:   { label: 'أخرى',     color: 'from-gray-600/20 to-gray-700/10 border-gray-700/40 hover:border-gray-500/60 text-gray-300', ring: 'ring-gray-500/40' },
            }
            return Object.entries(cats).map(([cat, items]) => {
              const meta = catMeta[cat] || catMeta.other
              return (
                <div key={cat} className="mb-4 last:mb-0">
                  <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">{meta.label}</p>
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 gap-2">
                    {items.map(m => {
                      const isAnalyzing = analyzing === m.symbol
                      return (
                        <button
                          key={m.symbol}
                          onClick={() => analyzeMarket(m.symbol, false)}
                          onContextMenu={(e) => { e.preventDefault(); analyzeMarket(m.symbol, true) }}
                          disabled={isAnalyzing}
                          className={`relative py-2.5 px-2 bg-gradient-to-b border rounded-xl text-xs font-semibold transition-all duration-200 select-none
                            ${meta.color}
                            ${isAnalyzing
                              ? 'opacity-60 cursor-not-allowed scale-95'
                              : 'hover:scale-105 active:scale-95 cursor-pointer'
                            }
                            ${isAnalyzing ? `ring-2 ${meta.ring}` : ''}
                          `}
                        >
                          {isAnalyzing ? (
                            <span className="flex items-center justify-center gap-1">
                              <RefreshCw size={11} className="animate-spin" />
                              <span className="truncate">{m.symbol}</span>
                            </span>
                          ) : (
                            <span className="truncate">{m.symbol}</span>
                          )}
                          {isAnalyzing && (
                            <span className="absolute inset-0 rounded-xl animate-pulse bg-white/5" />
                          )}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })
          })()}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: isAr ? 'إجمالي الإشارات' : 'Total Signals', value: signals.length, icon: <Activity size={20} />, color: 'text-blue-400' },
          { label: isAr ? 'إشارات شراء' : 'Buy Signals', value: signals.filter(s => (s.recommendation || s.signal_type) === 'BUY').length, icon: <TrendingUp size={20} />, color: 'text-green-400' },
          { label: isAr ? 'إشارات بيع' : 'Sell Signals', value: signals.filter(s => (s.recommendation || s.signal_type) === 'SELL').length, icon: <TrendingDown size={20} />, color: 'text-red-400' },
          { label: isAr ? 'متوسط الثقة' : 'Avg Confidence', value: signals.length ? Math.round(signals.reduce((a, s) => a + (s.ai_confidence_score || s.ai_confidence || 0), 0) / signals.length) + '%' : 'N/A', icon: <Zap size={20} />, color: 'text-yellow-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className={`${stat.color} mb-2`}>{stat.icon}</div>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
            <div className="text-gray-400 text-sm">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Recent Signals */}
      <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700/60">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse inline-block" />
            آخر الإشارات
            {signals.length > 0 && <span className="text-xs text-gray-500 font-normal">({signals.length})</span>}
          </h2>
          <button onClick={fetchSignals} className="text-gray-500 hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-gray-700">
            <RefreshCw size={14} />
          </button>
        </div>

        {signals.length === 0 ? (
          <p className="text-gray-500 text-center py-10 text-sm">لا توجد إشارات. اضغط على زر التحليل أعلاه.</p>
        ) : (
          <div className="divide-y divide-gray-700/40">
            {signals.slice(0, signalsLimit).map((sig, i) => {
              const rec        = sig.recommendation || sig.signal_type || 'WATCH'
              const confidence = sig.ai_confidence_score || sig.ai_confidence || 0
              const market     = sig.market || sig.symbol || 'N/A'
              const levels     = sig.levels || {}
              const entryMin   = levels.entry_zone_min || sig.entry_zone_min
              const entryMax   = levels.entry_zone_max || sig.entry_zone_max
              const entryExact = levels.entry || sig.entry_zones?.[0]
              const sl         = levels.stop_loss || sig.stop_loss_zone
              const tp1        = levels.tp1 || sig.take_profit_zones?.[0]
              const tp2        = levels.tp2 || sig.take_profit_zones?.[1]
              const rr         = sig.risk_reward || levels.risk_reward
              const livePrice  = sig.current_price
              const fmt = (v, d = 5) => v != null ? (typeof v === 'number' ? v.toFixed(d) : v) : null

              const isBuy  = rec === 'BUY'
              const isSell = rec === 'SELL'
              const accentBg   = isBuy ? 'bg-green-500' : isSell ? 'bg-red-500' : 'bg-gray-500'
              const recLabel   = isBuy ? '▲ شراء' : isSell ? '▼ بيع' : '◈ مراقبة'
              const recBadge   = isBuy
                ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                : isSell
                ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                : 'bg-gray-600/30 text-gray-400 border border-gray-600/40'
              const confColor  = confidence >= 75 ? 'bg-green-500' : confidence >= 60 ? 'bg-yellow-500' : 'bg-red-400'

              return (
                <div key={sig.id || i}
                  className="flex gap-0 hover:bg-gray-700/20 transition-colors cursor-pointer"
                  onClick={() => setQuickResult({ ...sig, market })}
                >
                  {/* شريط اللون الجانبي */}
                  <div className={`w-1 flex-shrink-0 ${accentBg} opacity-70`} />

                  <div className="flex-1 px-4 py-3">
                    {/* الصف الأول */}
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2.5">
                        <span className="text-white font-bold text-sm tracking-wide">{market}</span>
                        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${recBadge}`}>{recLabel}</span>
                        {sig.from_cache && <span className="text-xs text-gray-600 bg-gray-700/50 px-1.5 py-0.5 rounded">كاش</span>}
                      </div>
                      <div className="flex items-center gap-3">
                        {rr != null && (
                          <span className="text-xs text-gray-400">R/R <span className="text-white font-medium">{typeof rr === 'number' ? rr.toFixed(1) : rr}</span></span>
                        )}
                        {/* شريط الثقة */}
                        <div className="flex items-center gap-1.5">
                          <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${confColor}`} style={{ width: `${confidence}%` }} />
                          </div>
                          <span className="text-xs text-gray-300 font-medium w-9 text-left">{Math.round(confidence)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* الصف الثاني: مستويات */}
                    {(entryMin || entryExact || sl || tp1) && (
                      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
                        {(entryMin || entryExact) && (
                          <span className="text-xs">
                            <span className="text-gray-500">دخول </span>
                            <span className="text-white font-mono">{entryMin && entryMax ? `${fmt(entryMin)}–${fmt(entryMax)}` : fmt(entryExact)}</span>
                          </span>
                        )}
                        {sl != null && <span className="text-xs"><span className="text-gray-500">SL </span><span className="text-red-400 font-mono">{fmt(sl)}</span></span>}
                        {tp1 != null && <span className="text-xs"><span className="text-gray-500">TP1 </span><span className="text-green-400 font-mono">{fmt(tp1)}</span></span>}
                        {tp2 != null && <span className="text-xs"><span className="text-gray-500">TP2 </span><span className="text-green-300 font-mono">{fmt(tp2)}</span></span>}
                        {livePrice != null && (
                          <span className="text-xs"><span className="text-gray-500">السعر </span><span className="text-blue-300 font-mono">{fmt(livePrice, market === 'BTCUSD' ? 2 : 4)}</span></span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {signals.length > signalsLimit && (
          <button
            onClick={() => setSignalsLimit(l => l + 10)}
            className="w-full py-3 text-sm text-gray-400 hover:text-white hover:bg-gray-700/30 transition-colors flex items-center justify-center gap-2 border-t border-gray-700/60"
          >
            <ChevronDown size={15} />
            عرض المزيد ({signals.length - signalsLimit} متبقية)
          </button>
        )}
      </div>

      {/* Performance Section */}
      <PerformanceSection />

      {/* Signal History */}
      <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700/60">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Activity size={16} className="text-purple-400" />
            سجل الصفقات المغلقة
            {signalHistory.length > 0 && <span className="text-xs text-gray-500 font-normal">({signalHistory.length})</span>}
          </h2>
        </div>

        {signalHistory.length === 0 ? (
          <p className="text-gray-500 text-center py-10 text-sm">لا يوجد سجل بعد. قم بتحليل سوق للبدء.</p>
        ) : (
          <div className="divide-y divide-gray-700/40">
            {signalHistory.slice(0, historyLimit).map((s) => {
              const STATUS = {
                ACTIVE:  { label: 'نشطة',    icon: '🟢', bar: 'bg-green-500',  txt: 'text-green-400' },
                TP1_HIT: { label: 'هدف 1',   icon: '✅', bar: 'bg-blue-500',   txt: 'text-blue-400'  },
                TP2_HIT: { label: 'هدف 2',   icon: '🎯', bar: 'bg-purple-500', txt: 'text-purple-400'},
                SL_HIT:  { label: 'وقف خسارة',icon: '❌',bar: 'bg-red-500',    txt: 'text-red-400'   },
                EXPIRED: { label: 'منتهية',  icon: '⏰', bar: 'bg-gray-600',   txt: 'text-gray-500'  },
              }
              const st      = STATUS[s.status] || { label: s.status, icon: '•', bar: 'bg-gray-600', txt: 'text-gray-400' }
              const isBuy   = s.type === 'BUY'
              const isWin   = ['TP1_HIT','TP2_HIT'].includes(s.status)
              const isLoss  = s.status === 'SL_HIT'
              const createdAt = s.created_at
                ? new Date(s.created_at).toLocaleDateString('ar-EG', { month: 'short', day: 'numeric' })
                : '—'

              return (
                <div key={s.id} className="flex items-center gap-0 hover:bg-gray-700/20 transition-colors">
                  {/* شريط اللون */}
                  <div className={`w-1 self-stretch flex-shrink-0 ${st.bar} opacity-60`} />

                  <div className="flex-1 flex items-center justify-between gap-3 px-4 py-3 flex-wrap">
                    {/* يسار: رمز + نوع */}
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="font-bold text-white text-sm">{s.market}</span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${isBuy ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}`}>
                        {isBuy ? '▲' : '▼'} {isBuy ? 'شراء' : 'بيع'}
                      </span>
                      <span className="text-xs text-gray-500">{createdAt}</span>
                    </div>

                    {/* يمين: الدخول + الثقة + الحالة */}
                    <div className="flex items-center gap-3 flex-wrap">
                      {s.entry != null && (
                        <span className="text-xs text-gray-500 font-mono">
                          {typeof s.entry === 'number' ? s.entry.toFixed(4) : s.entry}
                        </span>
                      )}
                      {s.confidence != null && (
                        <span className="text-xs text-yellow-400 font-medium">{Math.round(s.confidence)}%</span>
                      )}
                      {/* بادج الحالة */}
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${
                        isWin  ? 'bg-green-500/15 text-green-400 border border-green-500/30' :
                        isLoss ? 'bg-red-500/15 text-red-400 border border-red-500/30' :
                        s.status === 'ACTIVE' ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30' :
                        'bg-gray-600/30 text-gray-400 border border-gray-600/40'
                      }`}>
                        {st.icon} {st.label}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {signalHistory.length > historyLimit && (
          <button
            onClick={() => setHistoryLimit(l => l + 10)}
            className="w-full py-3 text-sm text-gray-400 hover:text-white hover:bg-gray-700/30 transition-colors flex items-center justify-center gap-2 border-t border-gray-700/60"
          >
            <ChevronDown size={15} />
            عرض المزيد ({signalHistory.length - historyLimit} متبقية)
          </button>
        )}
        {historyLimit > 10 && signalHistory.length <= historyLimit && (
          <p className="py-3 text-center text-xs text-gray-600 border-t border-gray-700/40">
            تم عرض جميع السجلات ({signalHistory.length})
          </p>
        )}
      </div>
    </div>
  )
}
