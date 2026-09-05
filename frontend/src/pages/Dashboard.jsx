import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { TrendingUp, TrendingDown, Activity, Zap, AlertCircle, RefreshCw, Send, ExternalLink, Copy, CheckCircle, X, ChevronDown, ChevronUp, BarChart2, User, LayoutDashboard, Share2, Wallet, Calculator, Lock } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import useMarkets from '../hooks/useMarkets'
import { useLang } from '../contexts/LangContext'
import PerformanceSection from '../components/PerformanceSection'
import ReferralWidget from '../components/ReferralWidget'
import PriceAlertWidget from '../components/PriceAlertWidget'
import SignalScorecard from '../components/SignalScorecard'
import RedemptionWidget from '../components/RedemptionWidget'
import BestOpportunityWidget from '../components/BestOpportunityWidget'
import EconomicCalendar from '../components/EconomicCalendar'
import SessionsClock from '../components/SessionsClock'
import MarketHeatmap from '../components/MarketHeatmap'
import ConfluenceModal from '../components/ConfluenceModal'
import AchievementBadges from '../components/AchievementBadges'
import PWAInstallBanner from '../components/PWAInstallBanner'
import DashboardAnnouncement from '../components/DashboardAnnouncement'

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
  const navigate = useNavigate()
  const { user, refreshUser } = useAuth()
  const { markets } = useMarkets()
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'
  const [signals, setSignals]       = useState([])
  const [signalHistory, setSignalHistory] = useState([])
  const [analyzing, setAnalyzing]   = useState(null)
  const [quickCat, setQuickCat]     = useState(() => localStorage.getItem('mosh_quick_cat') || '')
  const [error, setError]           = useState(null)
  const [limitReached, setLimitReached] = useState(false)
  const [tgLink, setTgLink]         = useState('')
  const [tgBot, setTgBot]           = useState('Qaffelbot')
  const [tgCopied, setTgCopied]     = useState(false)
  const [tgLoading, setTgLoading]   = useState(false)
  const [relinking, setRelinking]   = useState(false)
  const [relinkDone, setRelinkDone] = useState(false)
  const [unlinking, setUnlinking]   = useState(false)
  const [quickResult, setQuickResult] = useState(null)   // modal result
  const [historyLimit,    setHistoryLimit]    = useState(10)
  const [signalsLimit,    setSignalsLimit]    = useState(10)
  const [activeTab,       setActiveTab]       = useState('home')
  const [confluenceSymbol, setConfluenceSymbol] = useState(null)  // ConfluenceModal
  const [showCalc, setShowCalc]           = useState(false)      // position size calc
  const [calcBalance, setCalcBalance]     = useState(1000)
  const [calcRisk, setCalcRisk]           = useState(1)
  const [copiedSignal, setCopiedSignal]   = useState(false)
  const [heroSymbol, setHeroSymbol]       = useState('')
  const [heroTf, setHeroTf]               = useState('1h')
  const [searchParams] = useSearchParams()

  // جلب آخر الإشارات
  useEffect(() => { fetchSignals(); fetchSignalHistory() }, [])

  // الشريط الجانبي (AppShell) يوجّه لـ /dashboard?cat=… و ?tab=…
  useEffect(() => {
    const cat = searchParams.get('cat')
    const tab = searchParams.get('tab')
    if (cat) { setQuickCat(cat); localStorage.setItem('mosh_quick_cat', cat) }
    if (tab) setActiveTab(tab)
  }, [searchParams])

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

  const analyzeMarket = async (symbol, forceRefresh = false, timeframe = '1h') => {
    setAnalyzing(symbol)
    setError(null)
    setLimitReached(false)
    try {
      const res = await axios.post(
        `${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=${timeframe}&advanced_mode=true&force_refresh=${forceRefresh}`
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

  const unlinkTelegram = async () => {
    if (!window.confirm('متأكد إنك بدك تفك ربط Telegram؟ رح توقف تنبيهات وإشارات البوت لحد ما تربط من جديد.')) return
    setUnlinking(true)
    try {
      await axios.post(`${API}/api/v1/auth/unlink-telegram`)
      setTgLink('')
      await refreshUser()
    } catch { /* ignore */ } finally { setUnlinking(false) }
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
    const sym   = result.market || result.symbol || ''
    const fmt   = (v, d = 5) => v != null ? (typeof v === 'number' ? v.toFixed(d) : v) : '—'

    const recColor = rec === 'BUY' ? 'text-green-400' : rec === 'SELL' ? 'text-red-400' : 'text-yellow-400'
    const recBg    = rec === 'BUY' ? 'bg-green-500/10 border-green-600/40' : rec === 'SELL' ? 'bg-red-500/10 border-red-600/40' : 'bg-yellow-500/10 border-yellow-600/40'
    const recLabel = rec === 'BUY' ? '🟢 شراء' : rec === 'SELL' ? '🔴 بيع' : '👁 مراقبة'

    // ── Position Size Calculator logic ──────────────────────────────────
    const getPipValue = (s) => {
      if (/XAUUSD|XAGUSD|XPTUSD/i.test(s)) return 100     // metals: $100/lot per $1 move
      if (/JPY/i.test(s))                   return 1000    // JPY pairs: ~$1000/lot per 1 move
      if (/NAS100|US30|SP500|DAX|UK100/i.test(s)) return 1 // indices: $1/lot per 1 pt
      if (/USOIL|BRENT/i.test(s))           return 1000    // oil
      if (/BTC|ETH|SOL|XRP|BNB/i.test(s))  return 1       // crypto
      return 100000  // standard forex: $100k/lot per 1.0 move
    }

    let calcLot = null, calcRiskUSD = null, calcProfitUSD = null
    if (entry != null && sl != null && calcBalance > 0 && calcRisk > 0) {
      const slDist    = Math.abs(Number(entry) - Number(sl))
      const pipVal    = getPipValue(sym)
      if (slDist > 0) {
        calcRiskUSD   = calcBalance * (calcRisk / 100)
        calcLot       = calcRiskUSD / (slDist * pipVal)
        if (tp1 != null) {
          const tp1Dist  = Math.abs(Number(tp1) - Number(entry))
          calcProfitUSD  = calcLot * tp1Dist * pipVal
        }
      }
    }

    const buildSignalText = () => [
      `📊 ${sym} — ${rec === 'BUY' ? '🟢 BUY' : rec === 'SELL' ? '🔴 SELL' : '👁 WATCH'}`,
      `✏️ Entry: ${fmt(entry)}`,
      `🛑 SL: ${fmt(sl)}`,
      tp1 ? `🎯 TP1: ${fmt(tp1)}` : null,
      tp2 ? `🎯 TP2: ${fmt(tp2)}` : null,
      rr  ? `⚖️ R/R: 1:${typeof rr === 'number' ? rr.toFixed(1) : rr}` : null,
      `💡 Conf: ${Math.round(conf)}%`,
      `🤖 Qaffel AI`,
    ].filter(Boolean).join('\n')

    const handleCopy = () => {
      navigator.clipboard.writeText(buildSignalText())
      setCopiedSignal(true)
      setTimeout(() => setCopiedSignal(false), 2000)
    }

    const handleShare = async () => {
      const text = buildSignalText()
      if (navigator.share) {
        try { await navigator.share({ text }) } catch { /* cancelled */ }
      } else {
        navigator.clipboard.writeText(text)
        setCopiedSignal(true)
        setTimeout(() => setCopiedSignal(false), 2000)
      }
    }

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
        <div
          className="relative bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm shadow-2xl animate-fade-in max-h-[90vh] overflow-y-auto"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className={`flex items-center justify-between px-5 py-4 border-b ${recBg} rounded-t-2xl border-b-gray-700/50`}>
            <div className="flex items-center gap-3">
              <span className="text-white font-bold text-lg">{sym}</span>
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

            {/* News context — advisory only, never part of the decision */}
            {result.news_context && (
              <div className="bg-blue-900/20 border border-blue-800/40 rounded-xl px-3 py-2.5 text-xs text-blue-300 leading-relaxed flex items-start gap-2">
                <span className="flex-shrink-0">📰</span>
                <span>{result.news_context}</span>
              </div>
            )}

            {/* ── Position Size Calculator ──────────────────────────── */}
            <div className="border border-gray-700/60 rounded-xl overflow-hidden">
              <button
                onClick={() => setShowCalc(v => !v)}
                className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-800/60 hover:bg-gray-800 transition-colors text-sm"
              >
                <span className="flex items-center gap-2 text-gray-300 font-medium">
                  <Calculator size={14} className="text-purple-400" />
                  {isAr ? 'حاسبة حجم الصفقة' : 'Position Size Calc'}
                </span>
                {showCalc ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />}
              </button>

              {showCalc && (
                <div className="px-4 py-3 space-y-3 bg-gray-800/30" dir="rtl">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-500 block mb-1">الرصيد ($)</label>
                      <input
                        type="number"
                        value={calcBalance}
                        onChange={e => setCalcBalance(Number(e.target.value))}
                        className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-purple-500 focus:outline-none"
                        min="1"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 block mb-1">المخاطرة (%)</label>
                      <input
                        type="number"
                        value={calcRisk}
                        onChange={e => setCalcRisk(Number(e.target.value))}
                        className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-purple-500 focus:outline-none"
                        min="0.1"
                        max="10"
                        step="0.1"
                      />
                    </div>
                  </div>

                  {calcLot !== null ? (
                    <div className="grid grid-cols-3 gap-2">
                      <div className="bg-purple-900/20 border border-purple-700/30 rounded-lg px-2 py-2 text-center">
                        <p className="text-[10px] text-purple-400 mb-0.5">حجم اللوت</p>
                        <p className="text-white font-bold text-sm font-mono">{calcLot.toFixed(2)}</p>
                      </div>
                      <div className="bg-red-900/20 border border-red-700/30 rounded-lg px-2 py-2 text-center">
                        <p className="text-[10px] text-red-400 mb-0.5">الخسارة</p>
                        <p className="text-white font-bold text-sm font-mono">${calcRiskUSD?.toFixed(0)}</p>
                      </div>
                      {calcProfitUSD != null && (
                        <div className="bg-green-900/20 border border-green-700/30 rounded-lg px-2 py-2 text-center">
                          <p className="text-[10px] text-green-400 mb-0.5">الربح (TP1)</p>
                          <p className="text-white font-bold text-sm font-mono">${calcProfitUSD.toFixed(0)}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500 text-center py-1">أدخل الرصيد والمخاطرة لحساب اللوت</p>
                  )}
                  <p className="text-[10px] text-gray-400 text-center">* تقديري — يختلف حسب الوسيط والرافعة المالية</p>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-5 pb-4 flex gap-2">
            <button
              onClick={handleCopy}
              className={`flex items-center gap-1.5 px-3 py-2.5 border rounded-xl text-sm font-medium transition-all ${
                copiedSignal
                  ? 'bg-green-600/20 border-green-500/40 text-green-300'
                  : 'bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border-blue-500/30'
              }`}
            >
              {copiedSignal ? <CheckCircle size={14} /> : <Copy size={14} />}
              {copiedSignal ? (isAr ? 'تم!' : 'Copied!') : (isAr ? 'نسخ' : 'Copy')}
            </button>
            <button
              onClick={handleShare}
              className="flex items-center gap-1.5 px-3 py-2.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-xl text-sm font-medium transition-colors"
            >
              <Share2 size={14} />
              {isAr ? 'مشاركة' : 'Share'}
            </button>
            <button
              onClick={onClose}
              className="flex-1 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-xl text-sm font-medium transition-colors"
            >
              {isAr ? 'إغلاق' : 'Close'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Tab definitions ───────────────────────────────────────────────────────
  const TABS = [
    { id: 'home',        labelAr: 'الرئيسية',  labelEn: 'Home',        icon: <LayoutDashboard size={16} /> },
    { id: 'markets',     labelAr: 'الأسواق',   labelEn: 'Markets',     icon: <BarChart2 size={16} />       },
    { id: 'performance', labelAr: 'الأداء',    labelEn: 'Performance', icon: <TrendingUp size={16} />      },
    { id: 'account',     labelAr: 'الحساب',    labelEn: 'Account',     icon: <User size={16} />            },
  ]

  // ── Markets grouped by category (shared by the hero form + symbol grid) ──
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
    gulf:    { label: '🕌 أسواق خليجية', color: 'from-emerald-600/20 to-emerald-700/10 border-emerald-700/40 hover:border-emerald-500/60 text-emerald-300', ring: 'ring-emerald-500/40' },
    // الفئتان الفعليتان بـmarket_configs اللي كانتا تسقطان على "أخرى" (فتظهر مرتين)
    commodity: { label: 'سلع ومؤشرات', color: 'from-yellow-600/20 to-yellow-700/10 border-yellow-700/40 hover:border-yellow-500/60 text-yellow-300', ring: 'ring-yellow-500/40' },
    stock:   { label: 'أسهم أمريكية', color: 'from-sky-600/20 to-sky-700/10 border-sky-700/40 hover:border-sky-500/60 text-sky-300', ring: 'ring-sky-500/40' },
    other:   { label: 'أخرى',     color: 'from-gray-600/20 to-gray-700/10 border-gray-700/40 hover:border-gray-500/60 text-gray-300', ring: 'ring-gray-500/40' },
  }
  const catKeys   = Object.keys(cats)
  const activeCat = catKeys.includes(quickCat) ? quickCat : (catKeys[0] || '')
  const setCat    = (c) => { setQuickCat(c); localStorage.setItem('mosh_quick_cat', c); setHeroSymbol('') }
  const catItems  = cats[activeCat] || []
  const heroSym   = catItems.some(m => m.symbol === heroSymbol) ? heroSymbol : (catItems[0]?.symbol || '')

  const featured = signals.slice(0, 2)
  const rest     = signals.slice(2)

  return (
    <div className="space-y-0" dir={isAr ? 'rtl' : 'ltr'}>
      <DashboardAnnouncement />

      {/* Modals */}
      <QuickModal result={quickResult} onClose={() => setQuickResult(null)} />
      {confluenceSymbol && (
        <ConfluenceModal symbol={confluenceSymbol} onClose={() => setConfluenceSymbol(null)} />
      )}

      {/* PWA Install Banner */}
      <PWAInstallBanner />

      {/* ── Global error banner (always visible) ── */}
      {error && (
        <div className="flex items-center justify-between gap-2 p-3 mb-4 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
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

      {/* ── Tab Bar ── */}
      <div className="flex items-center gap-2 mb-5">
        <div className="flex-1 flex gap-1 p-1 rounded-2xl q-glass">
          {TABS.map(tab => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all active:scale-95 ${
                  isActive ? 'q-nav-on text-white' : 'text-gray-400 hover:text-white q-glass-hover'
                }`}
              >
                <span className={isActive ? 'text-[var(--q-acc3)]' : ''}>{tab.icon}</span>
                <span className="leading-none">{isAr ? tab.labelAr : tab.labelEn}</span>
              </button>
            )
          })}
        </div>
        <button
          onClick={fetchSignals}
          title={tx.refresh}
          className="w-10 h-10 rounded-xl q-glass q-glass-hover grid place-items-center text-gray-300 hover:text-white"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {/* ══ TAB: الرئيسية ══ */}
      {activeTab === 'home' && (
        <div className="space-y-6">

          {/* ── Telegram CTA — prominent for unlinked users ── */}
          {showTgCard && (
            <div className="relative overflow-hidden rounded-2xl p-5 border q-line bg-gradient-to-br from-cyan-500/10 via-violet-600/10 to-fuchsia-500/10" dir="rtl">
              {/* Background glow */}
              <div className="absolute -top-6 -end-6 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />
              <div className="relative flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Send size={20} className="text-indigo-300" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-white font-bold text-sm">اربط حسابك مع Telegram</h3>
                    <span className="text-[10px] bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 px-2 py-0.5 rounded-full font-bold">مهم</span>
                  </div>
                  <p className="text-indigo-300/80 text-xs leading-relaxed mb-3">
                    استقبل إشارات التداول، تنبيهات الجلسات، والأخبار الاقتصادية مباشرة على هاتفك عبر @{tgBot}
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={openTgLink}
                      disabled={tgLoading}
                      className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-60 text-white px-5 py-2 rounded-xl font-semibold text-sm transition-all"
                    >
                      {tgLoading ? <RefreshCw size={14} className="animate-spin" /> : <ExternalLink size={14} />}
                      {tgLoading ? 'جاري...' : `ربط مع @${tgBot}`}
                    </button>
                    <button
                      onClick={copyTgLink}
                      disabled={tgLoading}
                      className="flex items-center gap-1.5 text-indigo-400 hover:text-white border border-indigo-700/60 hover:border-indigo-400 px-3 py-2 rounded-xl text-sm transition-all"
                    >
                      {tgCopied ? <CheckCircle size={13} className="text-green-400" /> : <Copy size={13} />}
                      {tgCopied ? 'تم النسخ' : 'نسخ الرابط'}
                    </button>
                    <button
                      onClick={() => setActiveTab('account')}
                      className="text-xs text-indigo-600 hover:text-indigo-400 transition-colors ms-auto"
                    >
                      {isAr ? 'لاحقاً' : 'Later'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <BestOpportunityWidget />

          {/* ── Hero: quick analysis ── */}
          <section className="relative overflow-hidden rounded-3xl q-hero p-6 sm:p-7 grid md:grid-cols-[1fr_auto] gap-5 items-center">
            <div className="relative">
              <h1 className="q-hero-text text-2xl sm:text-3xl font-extrabold leading-tight max-w-[18ch]" style={{ textWrap: 'balance' }}>
                {isAr ? 'حلّل أي سوق خلال ثوانٍ بالذكاء الاصطناعي' : 'Analyze any market in seconds with AI'}
              </h1>
              <p className="q-hero-text opacity-85 text-sm mt-2 mb-4 max-w-[46ch]">
                {isAr
                  ? 'Smart Money Concepts + Gemini — هيكل السوق، السيولة، Order Blocks وFVG، مع توصية واضحة ومستويات دخول ووقف وأهداف.'
                  : 'Smart Money Concepts + Gemini — structure, liquidity, Order Blocks & FVG, with a clear call and entry / SL / TP levels.'}
              </p>
              <form
                className="relative flex flex-wrap gap-2"
                onSubmit={e => { e.preventDefault(); if (heroSym && !analyzing) analyzeMarket(heroSym, false, heroTf) }}
              >
                <select
                  value={activeCat}
                  onChange={e => setCat(e.target.value)}
                  aria-label={isAr ? 'الفئة' : 'Category'}
                  className="q-hero-text px-3 py-2 rounded-xl bg-[rgba(20,8,48,0.55)] border border-white/25 text-sm backdrop-blur focus:outline-none focus:ring-2 focus:ring-white/40"
                >
                  {catKeys.map(cat => <option key={cat} value={cat}>{(catMeta[cat] || catMeta.other).label}</option>)}
                </select>
                <select
                  value={heroSym}
                  onChange={e => setHeroSymbol(e.target.value)}
                  aria-label={isAr ? 'الرمز' : 'Symbol'}
                  className="q-hero-text px-3 py-2 rounded-xl bg-[rgba(20,8,48,0.55)] border border-white/25 text-sm backdrop-blur focus:outline-none focus:ring-2 focus:ring-white/40 min-w-[150px]"
                >
                  {catItems.map(m => <option key={m.symbol} value={m.symbol}>{m.symbol} — {isAr ? (m.name_ar || m.name) : (m.name || m.name_ar)}</option>)}
                </select>
                <select
                  value={heroTf}
                  onChange={e => setHeroTf(e.target.value)}
                  aria-label={isAr ? 'الإطار الزمني' : 'Timeframe'}
                  className="q-hero-text px-3 py-2 rounded-xl bg-[rgba(20,8,48,0.55)] border border-white/25 text-sm backdrop-blur focus:outline-none focus:ring-2 focus:ring-white/40"
                >
                  {['15m', '30m', '1h', '4h', '1d'].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <button
                  type="submit"
                  disabled={!heroSym || !!analyzing}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl bg-white text-violet-900 font-extrabold text-sm shadow-lg shadow-black/20 disabled:opacity-60 active:scale-95 transition"
                >
                  {analyzing === heroSym ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
                  {analyzing === heroSym ? tx.analyzing : (isAr ? 'تحليل الآن' : 'Analyze now')}
                </button>
              </form>
            </div>
            <div className="relative hidden md:block w-[200px] h-[150px]" aria-hidden="true">
              <i className="absolute rounded-full end-0 top-1.5 w-[140px] h-[140px] shadow-2xl" style={{ background: 'radial-gradient(circle at 35% 30%,#FFD1F5,#FF4FD8 45%,#7C3AED 90%)' }} />
              <i className="absolute rounded-full end-[130px] top-[70px] w-16 h-16 opacity-90" style={{ background: 'radial-gradient(circle at 35% 30%,#CFFAFE,#22D3EE 50%,#0E7490)' }} />
              <i className="absolute rounded-full end-[118px] top-3.5 w-[30px] h-[30px]" style={{ background: 'radial-gradient(circle at 35% 30%,#fff,#C4B5FD 60%,#7C3AED)' }} />
              <div className="absolute bottom-0 end-6 flex items-end gap-1.5 h-[60px]">
                {[22, 34, 40, 28, 18, 48, 56].map((h, i) => (
                  <b key={i} className={`w-2 rounded-[3px] ${i % 3 === 1 ? 'bg-[rgba(15,7,36,0.7)]' : 'bg-white/85'}`} style={{ height: h }} />
                ))}
              </div>
            </div>
          </section>

          {/* Quick Analyze — كل الأزواج */}
          <div className="rounded-2xl q-glass overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3.5 border-b q-line">
              <h2 className="text-white font-semibold flex items-center gap-2 text-sm">
                <Zap size={15} className="text-[var(--q-acc3)]" />
                {isAr ? 'كل الأزواج' : 'All pairs'}
                <span className="text-xs text-gray-500 font-normal">({catItems.length})</span>
              </h2>
              <span className="text-xs text-gray-500 hidden sm:block">كليك = كاش · شيفت+كليك = تحديث · كليك يمين = Confluence</span>
            </div>
            <div className="p-4">
              <div className="flex flex-wrap gap-1.5 mb-3">
                {catKeys.map(cat => {
                  const meta = catMeta[cat] || catMeta.other
                  const on = cat === activeCat
                  return (
                    <button
                      key={cat}
                      onClick={() => setCat(cat)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition ${on ? 'q-nav-on border-transparent text-white font-semibold' : 'q-line text-gray-400 hover:text-white q-glass-hover'}`}
                    >
                      {meta.label} <span className="opacity-60">({cats[cat].length})</span>
                    </button>
                  )
                })}
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
                {catItems.map(m => {
                  const meta = catMeta[activeCat] || catMeta.other
                  const isAnalyzing = analyzing === m.symbol
                  return (
                    <button
                      key={m.symbol}
                      onClick={(e) => e.shiftKey ? analyzeMarket(m.symbol, true) : analyzeMarket(m.symbol, false)}
                      onContextMenu={(e) => { e.preventDefault(); setConfluenceSymbol(m.symbol) }}
                      disabled={isAnalyzing}
                      className={`relative py-2.5 px-2 bg-gradient-to-b border rounded-xl text-xs font-semibold transition-all duration-200 select-none
                        ${meta.color}
                        ${isAnalyzing ? 'opacity-60 cursor-not-allowed scale-95' : 'hover:scale-105 active:scale-95 cursor-pointer'}
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
                      {isAnalyzing && <span className="absolute inset-0 rounded-xl animate-pulse bg-white/5" />}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
            {[
              { label: isAr ? 'إجمالي الإشارات' : 'Total Signals', value: signals.length, icon: <Activity size={16} />, color: 'text-[var(--q-acc3)]' },
              { label: isAr ? 'إشارات شراء' : 'Buy Signals', value: signals.filter(s => (s.recommendation || s.signal_type) === 'BUY').length, icon: <TrendingUp size={16} />, color: 'text-emerald-400' },
              { label: isAr ? 'إشارات بيع' : 'Sell Signals', value: signals.filter(s => (s.recommendation || s.signal_type) === 'SELL').length, icon: <TrendingDown size={16} />, color: 'text-rose-400' },
              { label: isAr ? 'متوسط الثقة' : 'Avg Confidence', value: signals.length ? Math.round(signals.reduce((a, s) => a + (s.ai_confidence_score || s.ai_confidence || 0), 0) / signals.length) + '%' : 'N/A', icon: <Zap size={16} />, color: 'text-amber-300' },
            ].map((stat, i) => (
              <div key={i} className="rounded-xl q-glass px-3.5 py-3 flex items-center gap-3">
                <span className={`w-9 h-9 rounded-xl grid place-items-center bg-white/5 flex-shrink-0 ${stat.color}`}>{stat.icon}</span>
                <div className="min-w-0">
                  <div className="text-xl font-extrabold text-white leading-none tabular-nums">{stat.value}</div>
                  <div className="text-[11px] text-gray-400 mt-1 truncate">{stat.label}</div>
                </div>
              </div>
            ))}
          </div>

          {/* ── Featured signals (latest two) ── */}
          <div>
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="text-white font-extrabold text-lg flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[var(--q-acc3)] animate-pulse inline-block" />
                {isAr ? 'إشارات مميزة' : 'Featured signals'}
              </h2>
              <Link to="/signals" className="text-xs text-gray-400 hover:text-[var(--q-acc3)]">{isAr ? 'عرض الكل' : 'View all'}</Link>
            </div>
            {signals.length === 0 ? (
              <div className="rounded-2xl q-glass py-10 text-center text-gray-500 text-sm">
                {isAr ? 'لا توجد إشارات بعد. حلّل سوقاً من الأعلى للبدء.' : 'No signals yet. Analyze a market above to start.'}
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-3.5">
                {featured.map((sig, i) => {
                  const rec        = sig.recommendation || sig.signal_type || 'WATCH'
                  const confidence = sig.ai_confidence_score || sig.ai_confidence || 0
                  const market     = sig.market || sig.symbol || 'N/A'
                  const levels     = sig.levels || {}
                  const entry      = levels.entry || sig.entry_zones?.[0] || sig.entry_price
                  const sl         = levels.stop_loss || sig.stop_loss_zone || sig.stop_loss
                  const tp1        = levels.tp1 || sig.take_profit_zones?.[0] || sig.take_profit_1
                  const tp2        = levels.tp2 || sig.take_profit_zones?.[1] || sig.take_profit_2
                  const rr         = sig.risk_reward || levels.risk_reward || sig.risk_reward_ratio
                  const locked     = !!sig.locked
                  const livePrice  = sig.current_price
                  const fmt = (v, d = 5) => v != null ? (typeof v === 'number' ? v.toFixed(d) : v) : '—'
                  const isBuy = rec === 'BUY', isSell = rec === 'SELL'
                  const art = isBuy ? 'q-art-buy' : isSell ? 'q-art-sell' : 'q-art-wait'
                  const recLabel = isBuy ? `▲ ${tx.buy}` : isSell ? `▼ ${tx.sell}` : `◈ ${tx.watch}`
                  const recCls = isBuy ? 'text-emerald-300 border-emerald-400/40' : isSell ? 'text-rose-300 border-rose-400/40' : 'text-gray-200 border-white/20'
                  const isMetal = /^XA[UG]/.test(market)
                  return (
                    <article
                      key={sig.id || i}
                      onClick={() => locked ? navigate('/pricing') : setQuickResult({ ...sig, market })}
                      className="rounded-3xl q-glass overflow-hidden cursor-pointer q-glass-hover transition-colors"
                    >
                      <div className={`relative h-24 ${art}`}>
                        <div className="absolute top-3 start-3 flex gap-1.5">
                          <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full bg-black/40 border backdrop-blur ${recCls}`}>{recLabel}</span>
                          {sig.timeframe && <span className="text-[11px] px-2 py-1 rounded-full bg-black/40 border border-white/15 text-gray-200">{sig.timeframe}</span>}
                          {sig.from_cache && <span className="text-[11px] px-2 py-1 rounded-full bg-black/40 border border-white/15 text-gray-300">كاش</span>}
                        </div>
                        <div className={`absolute -bottom-5 start-4 w-12 h-12 rounded-2xl grid place-items-center font-extrabold text-[11px] border-[3px] border-gray-800 ${isMetal ? 'bg-gradient-to-br from-amber-300 to-amber-600 text-amber-950' : 'bg-gradient-to-br from-[var(--q-acc3)] to-[var(--q-acc2)] text-white'}`}>
                          {market.slice(0, 3)}
                        </div>
                      </div>
                      <div className="px-4 pt-7 pb-4">
                        <h3 className="text-white font-extrabold text-base">{market}</h3>
                        {locked ? (
                          <div className="flex items-center gap-2 mt-3 text-xs">
                            <Lock size={12} className="text-amber-300 flex-shrink-0" />
                            <span className="text-gray-400">{isAr ? 'تفاصيل الدخول وSL/TP مقفلة —' : 'Entry & SL/TP locked —'}</span>
                            <span className="text-amber-300 font-semibold hover:underline">{isAr ? 'اشترك لرؤيتها' : 'Subscribe to view'}</span>
                          </div>
                        ) : (
                          <div className="grid grid-cols-3 gap-x-3 gap-y-2 mt-3 tabular-nums">
                            {[
                              { l: isAr ? 'سعر الدخول' : 'Entry', v: fmt(entry), c: 'text-white' },
                              { l: isAr ? 'وقف الخسارة' : 'Stop loss', v: fmt(sl), c: 'text-rose-400' },
                              { l: 'R/R', v: rr ? `1:${typeof rr === 'number' ? rr.toFixed(1) : rr}` : '—', c: 'text-amber-300' },
                              { l: isAr ? 'الهدف الأول' : 'TP1', v: fmt(tp1), c: 'text-emerald-400' },
                              { l: isAr ? 'الهدف الثاني' : 'TP2', v: fmt(tp2), c: 'text-emerald-300' },
                              // /signals/latest لا يرجّع سعراً حياً (بس نتيجة التحليل المباشر) — نخفي الخلية بدل "—" دائمة
                              ...(livePrice != null ? [{ l: isAr ? 'السعر الحالي' : 'Price', v: fmt(livePrice, market === 'BTCUSD' ? 2 : 4), c: 'text-cyan-300' }] : []),
                            ].map(x => (
                              <div key={x.l} className="min-w-0">
                                <div className="text-[11px] text-gray-500">{x.l}</div>
                                <div className={`text-[13px] font-semibold truncate ${x.c}`}>{x.v}</div>
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="flex items-center justify-between gap-3 mt-3 pt-3 border-t q-line text-xs text-gray-400">
                          <span className="truncate">{sig.news_context ? `📰 ${sig.news_context}` : (sig.summary || '')}</span>
                          <span className="flex items-center gap-2 flex-shrink-0">
                            {tx.conf}
                            <span className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden"><span className="block h-full q-conf" style={{ width: `${confidence}%` }} /></span>
                            <b className="text-white tabular-nums">{Math.round(confidence)}%</b>
                          </span>
                        </div>
                      </div>
                    </article>
                  )
                })}
              </div>
            )}
          </div>

          {/* Latest signals (the rest) */}
          {rest.length > 0 && (
          <div className="rounded-2xl q-glass overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b q-line">
              <h2 className="text-white font-semibold flex items-center gap-2">
                {isAr ? 'آخر الإشارات' : 'Latest Signals'}
                <span className="text-xs text-gray-500 font-normal">({rest.length})</span>
              </h2>
              <button onClick={fetchSignals} className="text-gray-500 hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-gray-700">
                <RefreshCw size={14} />
              </button>
            </div>

            {(
              <div className="divide-y divide-gray-700/40">
                {rest.slice(0, signalsLimit).map((sig, i) => {
                  const rec        = sig.recommendation || sig.signal_type || 'WATCH'
                  const confidence = sig.ai_confidence_score || sig.ai_confidence || 0
                  const market     = sig.market || sig.symbol || 'N/A'
                  const levels     = sig.levels || {}
                  const entryMin   = levels.entry_zone_min || sig.entry_zone_min
                  const entryMax   = levels.entry_zone_max || sig.entry_zone_max
                  const entryExact = levels.entry || sig.entry_zones?.[0] || sig.entry_price
                  const sl         = levels.stop_loss || sig.stop_loss_zone || sig.stop_loss
                  const tp1        = levels.tp1 || sig.take_profit_zones?.[0] || sig.take_profit_1
                  const tp2        = levels.tp2 || sig.take_profit_zones?.[1] || sig.take_profit_2
                  const rr         = sig.risk_reward || levels.risk_reward || sig.risk_reward_ratio
                  const locked     = !!sig.locked
                  const livePrice  = sig.current_price
                  const newsContext = sig.news_context
                  const fmt = (v, d = 5) => v != null ? (typeof v === 'number' ? v.toFixed(d) : v) : null

                  const isBuy  = rec === 'BUY'
                  const isSell = rec === 'SELL'
                  const accentBg  = isBuy ? 'bg-green-500' : isSell ? 'bg-red-500' : 'bg-gray-500'
                  const recLabel  = isBuy ? '▲ شراء' : isSell ? '▼ بيع' : '◈ مراقبة'
                  const recBadge  = isBuy
                    ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                    : isSell
                    ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                    : 'bg-gray-600/30 text-gray-400 border border-gray-600/40'
                  const confColor = confidence >= 75 ? 'bg-green-500' : confidence >= 60 ? 'bg-yellow-500' : 'bg-red-400'

                  return (
                    <div key={sig.id || i}
                      className="flex gap-0 hover:bg-gray-700/20 transition-colors cursor-pointer"
                      onClick={() => locked ? navigate('/pricing') : setQuickResult({ ...sig, market })}
                    >
                      <div className={`w-1 flex-shrink-0 ${accentBg} opacity-70`} />
                      <div className="flex-1 px-4 py-3">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-2.5">
                            <span className="text-white font-bold text-sm tracking-wide">{market}</span>
                            <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${recBadge}`}>{recLabel}</span>
                            {sig.from_cache && <span className="text-xs text-gray-400 bg-gray-700/50 px-1.5 py-0.5 rounded">كاش</span>}
                          </div>
                          <div className="flex items-center gap-3">
                            {rr != null && (
                              <span className="text-xs text-gray-400">R/R <span className="text-white font-medium">{typeof rr === 'number' ? rr.toFixed(1) : rr}</span></span>
                            )}
                            <div className="flex items-center gap-1.5">
                              <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full ${confColor}`} style={{ width: `${confidence}%` }} />
                              </div>
                              <span className="text-xs text-gray-300 font-medium w-9 text-left">{Math.round(confidence)}%</span>
                            </div>
                          </div>
                        </div>
                        {locked ? (
                          <div className="flex items-center gap-2 mt-2 text-xs">
                            <Lock size={12} className="text-yellow-500 flex-shrink-0" />
                            <span className="text-gray-500">تفاصيل الدخول وSL/TP مقفلة — </span>
                            <span className="text-yellow-400 font-semibold hover:underline">اشترك لرؤية التفاصيل الكاملة</span>
                          </div>
                        ) : (entryMin || entryExact || sl || tp1) && (
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
                        {!locked && newsContext && (
                          <div className="flex items-start gap-1.5 mt-2 text-xs text-blue-300">
                            <span className="flex-shrink-0">📰</span>
                            <span className="leading-relaxed">{newsContext}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {rest.length > signalsLimit && (
              <button
                onClick={() => setSignalsLimit(l => l + 10)}
                className="w-full py-3 text-sm text-gray-400 hover:text-white hover:bg-gray-700/30 transition-colors flex items-center justify-center gap-2 border-t q-line"
              >
                <ChevronDown size={15} />
                {isAr ? `عرض المزيد (${rest.length - signalsLimit} متبقية)` : `Show more (${rest.length - signalsLimit} left)`}
              </button>
            )}
          </div>
          )}
        </div>
      )}

      {/* ══ TAB: الأسواق ══ */}
      {activeTab === 'markets' && (
        <div className="space-y-6">
          <SessionsClock />
          <MarketHeatmap onAnalyzeResult={(r) => setQuickResult(r)} />
          <EconomicCalendar />
          <SignalScorecard />
          <PriceAlertWidget />
        </div>
      )}

      {/* ══ TAB: الأداء ══ */}
      {activeTab === 'performance' && (
        <div className="space-y-6">
          <PerformanceSection />

          {/* Signal History */}
          <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700/60">
              <h2 className="text-white font-semibold flex items-center gap-2">
                <Activity size={16} className="text-purple-400" />
                {isAr ? 'سجل الصفقات المغلقة' : 'Closed Trades History'}
                {signalHistory.length > 0 && <span className="text-xs text-gray-500 font-normal">({signalHistory.length})</span>}
              </h2>
            </div>

            {signalHistory.length === 0 ? (
              <p className="text-gray-500 text-center py-10 text-sm">{isAr ? 'لا يوجد سجل بعد.' : 'No history yet.'}</p>
            ) : (
              <div className="divide-y divide-gray-700/40">
                {signalHistory.slice(0, historyLimit).map((s) => {
                  const STATUS = {
                    ACTIVE:  { label: 'نشطة',      icon: '🟢', bar: 'bg-green-500',  txt: 'text-green-400' },
                    TP1_HIT: { label: 'هدف 1',     icon: '✅', bar: 'bg-blue-500',   txt: 'text-blue-400'  },
                    TP2_HIT: { label: 'هدف 2',     icon: '🎯', bar: 'bg-purple-500', txt: 'text-purple-400'},
                    SL_HIT:  { label: 'وقف خسارة', icon: '❌', bar: 'bg-red-500',    txt: 'text-red-400'   },
                    EXPIRED: { label: 'منتهية',    icon: '⏰', bar: 'bg-gray-600',   txt: 'text-gray-500'  },
                  }
                  const st      = STATUS[s.status] || { label: s.status, icon: '•', bar: 'bg-gray-600', txt: 'text-gray-400' }
                  const isBuy   = s.type === 'BUY'
                  const isWin   = ['TP1_HIT', 'TP2_HIT'].includes(s.status)
                  const isLoss  = s.status === 'SL_HIT'
                  const createdAt = s.created_at
                    ? new Date(s.created_at).toLocaleDateString('ar-EG', { month: 'short', day: 'numeric' })
                    : '—'

                  return (
                    <div key={s.id} className="flex items-center gap-0 hover:bg-gray-700/20 transition-colors">
                      <div className={`w-1 self-stretch flex-shrink-0 ${st.bar} opacity-60`} />
                      <div className="flex-1 flex items-center justify-between gap-3 px-4 py-3 flex-wrap">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="font-bold text-white text-sm">{s.market}</span>
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${isBuy ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}`}>
                            {isBuy ? '▲' : '▼'} {isBuy ? 'شراء' : 'بيع'}
                          </span>
                          <span className="text-xs text-gray-500">{createdAt}</span>
                        </div>
                        <div className="flex items-center gap-3 flex-wrap">
                          {s.entry != null && (
                            <span className="text-xs text-gray-500 font-mono">
                              {typeof s.entry === 'number' ? s.entry.toFixed(4) : s.entry}
                            </span>
                          )}
                          {s.confidence != null && (
                            <span className="text-xs text-yellow-400 font-medium">{Math.round(s.confidence)}%</span>
                          )}
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
                {isAr ? `عرض المزيد (${signalHistory.length - historyLimit} متبقية)` : `Show more (${signalHistory.length - historyLimit} left)`}
              </button>
            )}
            {historyLimit > 10 && signalHistory.length <= historyLimit && (
              <p className="py-3 text-center text-xs text-gray-400 border-t border-gray-700/40">
                {isAr ? `تم عرض جميع السجلات (${signalHistory.length})` : `All ${signalHistory.length} records shown`}
              </p>
            )}
          </div>
        </div>
      )}

      {/* ══ TAB: الحساب ══ */}
      {activeTab === 'account' && (
        <div className="space-y-6">

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
                <div className="flex items-center gap-2">
                  <button
                    onClick={relinkTelegram}
                    disabled={relinking || unlinking}
                    className="flex items-center gap-2 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition"
                  >
                    {relinking ? <RefreshCw size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                    إعادة ربط @{tgBot}
                  </button>
                  <button
                    onClick={unlinkTelegram}
                    disabled={relinking || unlinking}
                    className="flex items-center gap-2 text-xs bg-red-950/60 hover:bg-red-900/60 border border-red-800/60 disabled:opacity-50 text-red-300 px-4 py-2 rounded-lg transition"
                  >
                    {unlinking ? <RefreshCw size={13} className="animate-spin" /> : <X size={13} />}
                    فك الربط
                  </button>
                </div>
              </div>
            </div>
          )}

          <AchievementBadges />
          <ReferralWidget />
          <RedemptionWidget />
        </div>
      )}

    </div>
  )
}
