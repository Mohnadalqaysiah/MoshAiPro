import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { TrendingUp, TrendingDown, Activity, Zap, AlertCircle, RefreshCw, Send, ExternalLink, Copy, CheckCircle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const MARKETS = ['XAUUSD', 'BTCUSD', 'EURUSD', 'GBPUSD']

export default function Dashboard() {
  const { user } = useAuth()
  const [signals, setSignals]       = useState([])
  const [analyzing, setAnalyzing]   = useState(null)
  const [error, setError]           = useState(null)
  const [limitReached, setLimitReached] = useState(false)
  const [tgLink, setTgLink]         = useState('')
  const [tgBot, setTgBot]           = useState('Qaffelbot')
  const [tgCopied, setTgCopied]     = useState(false)
  const [tgLoading, setTgLoading]   = useState(false)
  const [relinking, setRelinking]   = useState(false)
  const [relinkDone, setRelinkDone] = useState(false)

  // جلب آخر الإشارات
  useEffect(() => { fetchSignals() }, [])

  const fetchSignals = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/signals/latest?limit=10`)
      setSignals(res.data.data || [])
    } catch (e) {
      // no signals yet
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
      setSignals(prev => [{ ...data, market: symbol, id: Date.now() }, ...prev.slice(0, 9)])
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
    if (rec === 'BUY') return 'شراء'
    if (rec === 'SELL') return 'بيع'
    return 'مراقبة'
  }

  const showTgCard     = user && !user.telegram_linked && !relinkDone
  const showRelinkCard = user && user.telegram_linked && !relinkDone

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">لوحة التحكم</h1>
          <p className="text-gray-400 text-sm mt-1">تحليل الأسواق بالذكاء الاصطناعي</p>
        </div>
        <button
          onClick={fetchSignals}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors"
        >
          <RefreshCw size={14} />
          تحديث
        </button>
      </div>

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
              {tgLoading ? 'جاري التحميل...' : 'ربط مع @{tgBot}'}
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
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Zap size={18} className="text-blue-400" />
            تحليل سريع
          </h2>
          <span className="text-xs text-gray-500">النتائج مُخزَّنة مؤقتاً · اضغط مطوّلاً للتحديث الإجباري</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {MARKETS.map(market => (
            <button
              key={market}
              onClick={() => analyzeMarket(market, false)}
              onContextMenu={(e) => { e.preventDefault(); analyzeMarket(market, true) }}
              disabled={analyzing === market}
              className="py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {analyzing === market ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  جاري...
                </>
              ) : market}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'إجمالي الإشارات', value: signals.length, icon: <Activity size={20} />, color: 'text-blue-400' },
          { label: 'إشارات شراء', value: signals.filter(s => (s.recommendation || s.signal_type) === 'BUY').length, icon: <TrendingUp size={20} />, color: 'text-green-400' },
          { label: 'إشارات بيع', value: signals.filter(s => (s.recommendation || s.signal_type) === 'SELL').length, icon: <TrendingDown size={20} />, color: 'text-red-400' },
          { label: 'متوسط الثقة', value: signals.length ? Math.round(signals.reduce((a, s) => a + (s.ai_confidence_score || s.ai_confidence || 0), 0) / signals.length) + '%' : 'N/A', icon: <Zap size={20} />, color: 'text-yellow-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className={`${stat.color} mb-2`}>{stat.icon}</div>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
            <div className="text-gray-400 text-sm">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Recent Signals */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h2 className="text-white font-semibold mb-4">آخر الإشارات</h2>
        {signals.length === 0 ? (
          <p className="text-gray-500 text-center py-8">لا توجد إشارات. اضغط على زر التحليل أعلاه.</p>
        ) : (
          <div className="space-y-3">
            {signals.map((sig, i) => {
              const rec = sig.recommendation || sig.signal_type || 'WATCH'
              const confidence = sig.ai_confidence_score || sig.ai_confidence || 0
              const market = sig.market || sig.symbol || 'N/A'
              return (
                <div key={sig.id || i} className={`border rounded-lg p-4 ${getSignalBg(rec)}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-white font-bold">{market}</span>
                      <span className={`font-semibold ${getSignalColor(rec)}`}>{getSignalAr(rec)}</span>
                      {sig.from_cache && (
                        <span className="text-xs text-gray-500 bg-gray-700 px-2 py-0.5 rounded">محفوظ</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-gray-400">ثقة: <span className="text-white font-medium">{confidence.toFixed ? confidence.toFixed(1) : confidence}%</span></span>
                      {sig.risk_reward && (
                        <span className="text-gray-400">R/R: <span className="text-white font-medium">{sig.risk_reward.toFixed ? sig.risk_reward.toFixed(2) : sig.risk_reward}x</span></span>
                      )}
                    </div>
                  </div>
                  {sig.entry_zones && sig.entry_zones.length > 0 && (
                    <div className="mt-2 text-sm text-gray-400">
                      دخول: <span className="text-white">{sig.entry_zones[0]}</span>
                      {sig.stop_loss_zone && <> | SL: <span className="text-red-400">{sig.stop_loss_zone}</span></>}
                      {sig.take_profit_zones && sig.take_profit_zones[0] && <> | TP1: <span className="text-green-400">{sig.take_profit_zones[0]}</span></>}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
