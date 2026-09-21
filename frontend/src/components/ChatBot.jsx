import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import axios from 'axios'
import {
  X, Send, BarChart2, FileText,
  Sparkles, Trash2, TrendingUp, TrendingDown, Minus, Zap, Copy, Check, ShieldAlert,
} from 'lucide-react'
import useMarkets from '../hooks/useMarkets'
import { useLang } from '../contexts/LangContext'
import { BRAND, BRAND_CSS, NeuralOrb } from './SmartAnalysisBrand'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const SEEN_KEY = 'qaffel_smart_analysis_seen'

const TIMEFRAMES = ['15m', '30m', '1h', '4h', '1d']

const CATEGORY_LABELS = {
  ar: {
    forex: 'فوركس', crypto: 'كريبتو', commodity: 'سلع', metal: 'معادن',
    metals: 'معادن', index: 'مؤشرات', indices: 'مؤشرات', stock: 'أسهم',
    stocks: 'أسهم', gulf: 'أسهم خليجية',
  },
  en: {
    forex: 'Forex', crypto: 'Crypto', commodity: 'Commodities', metal: 'Metals',
    metals: 'Metals', index: 'Indices', indices: 'Indices', stock: 'Stocks',
    stocks: 'Stocks', gulf: 'Gulf Stocks',
  },
}
const categoryLabel = (cat, isAr) =>
  CATEGORY_LABELS[isAr ? 'ar' : 'en'][(cat || '').toLowerCase()] || cat || (isAr ? 'أخرى' : 'Other')

// كل نصوص الودجت بلغتين — الأرقام والرموز (XAUUSD, ICT/SMC...) تبقى كما هي
const T = {
  ar: {
    close: 'إغلاق', clear: 'مسح المحادثة', online: 'متصل',
    analyze: 'حلّل', analyzeNow: 'حلّل الآن',
    ask: 'اكتب سؤالك... مثل: حلل الذهب ساعة', subscribeToContinue: 'اشترك للمتابعة...',
    subscribe: 'اشترك الآن',
    emptyTitle: 'ماذا تريد أن تحلّل؟',
    emptySub: 'اختر سوقاً، أو اسأل عن أي مفهوم في ICT / SMC',
    orType: 'أو اكتب سؤالك مباشرة بالأسفل',
    noSymbols: 'لا رموز بهذي الفئة',
    thinking: 'يفكّر…',
    copy: 'نسخ التحليل كاملاً', copied: 'تم النسخ',
    candles: 'شمعة', chart: 'رسم بياني', report: 'تقرير', analysisLbl: 'تحليل',
    buy: 'شراء', sell: 'بيع', wait: 'انتظار',
    entry: 'دخول', stop: 'وقف', target: 'هدف',
    grade: 'جودة الإشارة:',
    received: 'تم استقبال الرد.',
    trialOut: 'استهلكت رسائل المحادثة التجريبية.',
    connFail: 'فشل الاتصال. تأكد أن الخادم يعمل.',
    genericErr: '⚠️ حدث خطأ. حاول مرة أخرى.',
    disclaimer: 'تحليل تقني تعليمي وليس نصيحة مالية.',
    symbolLbl: 'الرمز', recLbl: 'التوصية', confLbl: 'الثقة', entryLbl: 'الدخول', stopLbl: 'الوقف',
    suggestions: [
      { label: 'حلّل الذهب على ساعة', msg: 'حلل الذهب على ساعة' },
      { label: 'اشرح Order Block', msg: 'اشرح لي Order Block' },
      { label: 'كيف أربط تلجرام؟', msg: 'كيف أربط تلجرام؟' },
    ],
    cmd: (s, tf) => `تحليل ${s} ${tf}`,
  },
  en: {
    close: 'Close', clear: 'Clear conversation', online: 'Online',
    analyze: 'Analyze', analyzeNow: 'Analyze now',
    ask: 'Ask anything... e.g. Analyze gold 1h', subscribeToContinue: 'Subscribe to continue...',
    subscribe: 'Subscribe now',
    emptyTitle: 'What do you want to analyze?',
    emptySub: 'Pick a market, or ask about any ICT / SMC concept',
    orType: 'Or type your question below',
    noSymbols: 'No symbols in this category',
    thinking: 'Thinking…',
    copy: 'Copy full analysis', copied: 'Copied',
    candles: 'candles', chart: 'Chart', report: 'Report', analysisLbl: 'Analysis',
    buy: 'BUY', sell: 'SELL', wait: 'WAIT',
    entry: 'Entry', stop: 'SL', target: 'TP',
    grade: 'Signal grade:',
    received: 'Reply received.',
    trialOut: 'Chat limit reached. Subscribe to continue or try again tomorrow.',
    connFail: 'Connection failed. Please check the server is running.',
    genericErr: '⚠️ Something went wrong. Please try again.',
    disclaimer: 'Educational technical analysis — not financial advice.',
    symbolLbl: 'Symbol', recLbl: 'Signal', confLbl: 'Confidence', entryLbl: 'Entry', stopLbl: 'Stop',
    suggestions: [
      { label: 'Analyze gold on 1h', msg: 'Analyze gold on 1h' },
      { label: 'Explain Order Block', msg: 'Explain Order Block' },
      { label: 'How do I link Telegram?', msg: 'How do I link Telegram?' },
    ],
    cmd: (s, tf) => `Analyze ${s} ${tf}`,
  },
}

const fmtNum = (v) => (+v % 1 === 0 ? v : (+v).toFixed(5))

// ─── Candlestick Chart ────────────────────────────────────────────────────────
function CandlesChart({ candles, symbol, timeframe, tx }) {
  const ref = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!ref.current || !candles?.length) return

    const init = async () => {
      try {
        const { createChart } = await import('lightweight-charts')
        if (chartRef.current) {
          chartRef.current.remove()
          chartRef.current = null
        }

        const chart = createChart(ref.current, {
          layout: { background: { color: '#0B1020' }, textColor: '#9ca3af' },
          grid: {
            vertLines: { color: 'rgba(55,65,81,0.3)' },
            horzLines: { color: 'rgba(55,65,81,0.3)' },
          },
          width: ref.current.clientWidth,
          height: 200,
          rightPriceScale: { borderColor: 'rgba(75,85,99,0.4)' },
          timeScale: { borderColor: 'rgba(75,85,99,0.4)', timeVisible: true },
        })

        const series = chart.addCandlestickSeries({
          upColor: '#22c55e', downColor: '#ef4444',
          borderUpColor: '#22c55e', borderDownColor: '#ef4444',
          wickUpColor: '#22c55e', wickDownColor: '#ef4444',
        })

        const formatted = candles
          .map(c => ({
            time: Math.floor(new Date(c.time).getTime() / 1000),
            open: +c.open, high: +c.high, low: +c.low, close: +c.close,
          }))
          .filter(c => c.time && !isNaN(c.open))
          .sort((a, b) => a.time - b.time)

        const seen = new Set()
        const deduped = formatted.filter(c => {
          if (seen.has(c.time)) return false
          seen.add(c.time)
          return true
        })

        series.setData(deduped)
        chart.timeScale().fitContent()
        chartRef.current = chart

        const handleResize = () => {
          if (ref.current && chartRef.current) {
            chartRef.current.applyOptions({ width: ref.current.clientWidth })
          }
        }
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
      } catch (e) {
        console.error('Chart error:', e)
      }
    }

    init()
    return () => {
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }
    }
  }, [candles])

  if (!candles?.length) return null

  return (
    <div className="mt-2 rounded-lg overflow-hidden border border-cyan-500/15">
      <div className="flex items-center gap-1.5 px-2 py-1.5 bg-[#0B1020] text-xs text-gray-400" dir="ltr">
        <BarChart2 size={12} className="text-cyan-400" />
        <span>{symbol} · {timeframe} · {candles.length} {tx.candles}</span>
      </div>
      <div ref={ref} className="w-full bg-[#0B1020]" dir="ltr" />
    </div>
  )
}

// ─── Analysis Card ────────────────────────────────────────────────────────────
function AnalysisCard({ data, symbol, timeframe, tx }) {
  if (!data || data.error) return null

  const rec = data.recommendation || 'WAIT'
  const conf = data.ai_confidence_score || 0
  const entry = data.entry_zones?.[0]
  const sl = data.stop_loss_zone
  const tps = data.take_profit_zones || []
  const rr = data.risk_reward_ratio
  const gemini = data.gemini_analysis

  const recStyles = {
    BUY:  { icon: TrendingUp,   color: 'text-emerald-400', bg: 'bg-emerald-400/[0.07] border-emerald-500/30', label: tx.buy },
    SELL: { icon: TrendingDown, color: 'text-rose-400',    bg: 'bg-rose-400/[0.07] border-rose-500/30',       label: tx.sell },
    WAIT: { icon: Minus,        color: 'text-amber-400',   bg: 'bg-amber-400/[0.07] border-amber-500/30',     label: tx.wait },
  }
  const style = recStyles[rec] || recStyles.WAIT
  const Icon = style.icon
  const confColor = conf >= 70 ? 'text-emerald-400' : conf >= 50 ? 'text-amber-400' : 'text-gray-400'
  const barColor = conf >= 70 ? 'bg-emerald-400' : conf >= 50 ? 'bg-amber-400' : 'bg-gray-500'

  return (
    <div className={`mt-2 rounded-xl border p-3 text-xs space-y-2 ${style.bg}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon size={14} className={style.color} />
          <span className={`font-bold text-sm ${style.color}`}>{style.label}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-400" dir="ltr">
          {symbol && <span className="font-mono">{symbol}</span>}
          {timeframe && <span className="text-gray-500">({timeframe})</span>}
          <span className={`font-semibold ${confColor}`}>{conf.toFixed(1)}%</span>
        </div>
      </div>

      {/* شريط الثقة */}
      <div className="h-1 rounded-full bg-white/5 overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(100, Math.max(0, conf))}%`, transition: 'width .5s' }} />
      </div>

      {(entry || sl || tps.length > 0) && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 border-t border-white/5 pt-2">
          {entry && (
            <div className="flex items-center justify-between gap-1">
              <span className="text-gray-500">{tx.entry}</span>
              <span className="font-mono text-gray-100" dir="ltr">{fmtNum(entry)}</span>
            </div>
          )}
          {sl && (
            <div className="flex items-center justify-between gap-1">
              <span className="text-gray-500">{tx.stop}</span>
              <span className="font-mono text-rose-400" dir="ltr">{fmtNum(sl)}</span>
            </div>
          )}
          {tps.slice(0, 3).map((tp, i) => tp ? (
            <div key={i} className="flex items-center justify-between gap-1">
              <span className="text-gray-500">{tx.target} {i + 1}</span>
              <span className="font-mono text-emerald-400" dir="ltr">{fmtNum(tp)}</span>
            </div>
          ) : null)}
          {rr && (
            <div className="col-span-2 flex items-center justify-between gap-1">
              <span className="text-gray-500">R/R</span>
              <span className="font-mono text-cyan-400" dir="ltr">1:{(+rr).toFixed(1)}</span>
            </div>
          )}
        </div>
      )}

      {gemini?.signal_grade && gemini.signal_grade !== '?' && (
        <div className="flex items-center gap-1.5 border-t border-white/5 pt-1.5">
          <Sparkles size={11} className="text-violet-400" />
          <span className="text-gray-400">{tx.grade}</span>
          <span className="font-bold text-violet-300">{gemini.signal_grade}</span>
          {gemini.ict_setup && <span className="text-gray-500">{gemini.ict_setup}</span>}
        </div>
      )}
    </div>
  )
}

// ─── نسخ التحليل كامل (نص الرد + الأرقام المهيكلة إن وجدت) ─────────────────────
function buildCopyText(msg, tx) {
  const lines = [msg.content || '']
  const d = msg.analysisData
  if (d && !d.error) {
    const recLabel = { BUY: tx.buy, SELL: tx.sell, WAIT: tx.wait }[d.recommendation] || d.recommendation
    const entry = d.entry_zones?.[0]
    const sl = d.stop_loss_zone
    const tps = d.take_profit_zones || []
    lines.push('')
    if (msg.symbol) lines.push(`${tx.symbolLbl}: ${msg.symbol}${msg.timeframe ? ` (${msg.timeframe})` : ''}`)
    if (recLabel) lines.push(`${tx.recLbl}: ${recLabel}${d.ai_confidence_score ? ` · ${tx.confLbl} ${(+d.ai_confidence_score).toFixed(1)}%` : ''}`)
    if (entry) lines.push(`${tx.entryLbl}: ${fmtNum(entry)}`)
    if (sl)    lines.push(`${tx.stopLbl}: ${fmtNum(sl)}`)
    tps.slice(0, 3).forEach((tp, i) => { if (tp) lines.push(`${tx.target} ${i + 1}: ${fmtNum(tp)}`) })
    if (d.risk_reward_ratio) lines.push(`R/R: 1:${(+d.risk_reward_ratio).toFixed(1)}`)
  }
  lines.push('', 'via Qaffel AI — qaffel.com')
  return lines.join('\n')
}

// ─── Message Bubble ───────────────────────────────────────────────────────────
// الصفوف ltr ثابتة (المستخدم يمين، الذكاء يسار) والنص داخل الفقاعة يتبع لغة الواجهة
function MessageBubble({ msg, tx, isAr }) {
  const isUser = msg.role === 'user'
  const [copied, setCopied] = useState(false)
  const textDir = isAr ? 'rtl' : 'ltr'

  if (isUser) {
    return (
      <div className="flex justify-end" style={{ direction: 'ltr' }}>
        <div
          dir={textDir}
          className="max-w-[80%] rounded-2xl rounded-br-sm px-3 py-2 text-white text-sm whitespace-pre-wrap"
          style={{ background: 'linear-gradient(135deg,#4f46e5,#2563eb)' }}
        >
          {msg.content}
        </div>
      </div>
    )
  }

  const actionLabel = {
    analyze: { icon: BarChart2, label: tx.analysisLbl, color: 'text-cyan-400' },
    chart:   { icon: BarChart2, label: tx.chart,       color: 'text-sky-400' },
    report:  { icon: FileText,  label: tx.report,      color: 'text-amber-400' },
  }[msg.action]

  const copyAll = () => {
    navigator.clipboard?.writeText(buildCopyText(msg, tx)).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    }).catch(() => {})
  }

  return (
    <div className="flex justify-start gap-2" style={{ direction: 'ltr' }}>
      <div className="mt-0.5 flex-shrink-0"><NeuralOrb size={22} /></div>
      <div className="max-w-[88%] space-y-1" dir={textDir}>
        {actionLabel && (
          <div className={`flex items-center gap-1 text-[11px] ${actionLabel.color} mb-0.5`}>
            <actionLabel.icon size={11} />
            <span>{actionLabel.label}</span>
          </div>
        )}
        <div className="rounded-2xl rounded-tl-sm px-3 py-2 bg-white/[0.045] border border-white/[0.06] text-gray-100 text-sm whitespace-pre-wrap leading-relaxed">
          {msg.content}
        </div>
        {msg.analysisData && (
          <AnalysisCard data={msg.analysisData} symbol={msg.symbol} timeframe={msg.timeframe} tx={tx} />
        )}
        {msg.candles?.length > 0 && (
          <CandlesChart candles={msg.candles} symbol={msg.symbol} timeframe={msg.timeframe} tx={tx} />
        )}
        {msg.action !== 'error' && (
          <button
            onClick={copyAll}
            className="flex items-center gap-1 text-[11px] text-gray-500 hover:text-cyan-300 transition-colors px-0.5"
          >
            {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
            {copied ? tx.copied : tx.copy}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Main ChatBot ─────────────────────────────────────────────────────────────
export default function ChatBot() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']
  const brand = BRAND[isAr ? 'ar' : 'en']

  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [limitReached, setLimitReached] = useState(false)
  const bottomRef = useRef(null)

  // النبض الخارجي للزر يظهر حتى أول فتح فقط — بعدها يهدأ (حركة دائمة تشتّت وتستهلك)
  const [seen, setSeen] = useState(() => {
    try { return localStorage.getItem(SEEN_KEY) === '1' } catch { return false }
  })
  useEffect(() => {
    if (open && !seen) {
      setSeen(true)
      try { localStorage.setItem(SEEN_KEY, '1') } catch { /* تصفّح خاص */ }
    }
  }, [open, seen])

  const { markets } = useMarkets()
  const [quickSymbol, setQuickSymbol] = useState('XAUUSD')
  const [quickTf, setQuickTf] = useState('1h')
  const categories = useMemo(() => {
    const s = [...new Set(markets.map(m => m.category || 'forex'))]
    return s.length ? s : ['forex']
  }, [markets])
  const [activeCategory, setActiveCategory] = useState('')
  useEffect(() => {
    if (!activeCategory && categories.length) setActiveCategory(categories[0])
  }, [categories, activeCategory])
  const categoryMarkets = useMemo(
    () => markets.filter(m => (m.category || 'forex') === activeCategory),
    [markets, activeCategory]
  )
  const marketName = (m) => (isAr ? (m.name_ar || m.symbol) : (m.name || m.symbol))

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }, [])
  useEffect(() => { scrollToBottom() }, [messages, loading, scrollToBottom])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return
    setInput('')
    setError('')
    setLimitReached(false)

    setMessages(prev => [...prev, { role: 'user', content: text }])

    try {
      setLoading(true)
      const res = await axios.post(`${API}/api/v1/chat/message`, {
        message: text,
        session_id: sessionId || '',
        lang: isAr ? 'ar' : 'en',
      })

      const { session_id, response } = res.data
      if (session_id && !sessionId) setSessionId(session_id)

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response?.message || tx.received,
        action: response?.action || 'text',
        symbol: response?.symbol,
        timeframe: response?.timeframe,
        analysisData: response?.data || response?.analysis || null,
        candles: response?.candles || response?.data?.candles || null,
      }])
    } catch (e) {
      console.error(e)
      if (e.response?.status === 403) {
        // رسالة الخادم عربية — تُعرض كما هي بالعربية، وبالإنجليزية نص عام مطابق
        const detail = isAr ? (e.response.data?.detail || tx.trialOut) : tx.trialOut
        setLimitReached(true)
        setError(detail)
        setMessages(prev => [...prev, { role: 'assistant', content: `🔒 ${detail}`, action: 'error' }])
      } else {
        setError(tx.connFail)
        setMessages(prev => [...prev, { role: 'assistant', content: tx.genericErr, action: 'error' }])
      }
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId, isAr, tx])

  const handleClear = async () => {
    setMessages([])
    setError('')
    if (sessionId) {
      try { await axios.delete(`${API}/api/v1/chat/session/${sessionId}`) } catch { /* لا يهم */ }
      setSessionId('')
    }
  }

  return (
    <>
      <style>{BRAND_CSS}</style>

      {/* Floating launcher */}
      <button
        onClick={() => setOpen(o => !o)}
        aria-label={open ? tx.close : brand.name}
        className={`fixed bottom-5 left-4 md:left-auto md:right-6 z-50 group ${open ? 'hidden md:flex' : 'flex'}`}
      >
        {open ? (
          <div className="flex items-center gap-2 rounded-full bg-[#0B1020] border border-white/10 hover:border-white/25 text-gray-300 px-4 py-2.5 shadow-xl text-sm font-medium transition-colors">
            <X size={16} />
            <span>{tx.close}</span>
          </div>
        ) : (
          <div className="relative">
            {!seen && (
              <span className="absolute inset-0 rounded-full animate-ping opacity-25" style={{ background: 'linear-gradient(135deg,#22D3EE,#8B5CF6)', animationDuration: '2.4s' }} />
            )}
            <div
              className="relative flex items-center gap-2.5 rounded-full ps-2 pe-2 sm:pe-4 py-2 text-sm font-semibold text-white shadow-2xl transition-transform group-hover:scale-[1.03]"
              style={{
                background: 'linear-gradient(#0B1020,#0B1020) padding-box, linear-gradient(135deg,#22D3EE,#8B5CF6) border-box',
                border: '1.5px solid transparent',
                boxShadow: '0 8px 30px rgba(34,211,238,0.22), 0 0 0 1px rgba(139,92,246,0.15)',
              }}
            >
              <NeuralOrb size={32} />
              <span className="hidden sm:flex flex-col leading-tight text-start">
                <span>{brand.name}</span>
                <span className="text-[10px] font-normal text-cyan-300/70 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> {tx.online}
                </span>
              </span>
            </div>
          </div>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed inset-0 md:inset-auto md:bottom-20 md:right-6 z-40 md:w-full md:max-w-md sa-panel" dir={isAr ? 'rtl' : 'ltr'}>
          <div
            className="rounded-none md:rounded-2xl border-0 md:border border-white/10 shadow-2xl flex flex-col h-full md:h-[560px] overflow-hidden"
            style={{ background: 'radial-gradient(120% 60% at 50% 0%, rgba(34,211,238,0.07), transparent 60%), #0B1020' }}
          >
            {/* Header */}
            <div className={`relative overflow-hidden flex items-center justify-between px-4 py-3 border-b border-white/[0.07] ${loading ? 'sa-scan' : ''}`}>
              <div className="flex items-center gap-3">
                <NeuralOrb size={38} active={loading} />
                <div>
                  <div className="text-sm font-semibold text-white leading-tight">{brand.name}</div>
                  <div className="text-[11px] text-cyan-300/70">{brand.tagline}</div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={handleClear} className="p-1.5 rounded-full hover:bg-white/5 text-gray-400 hover:text-rose-400 transition-colors" title={tx.clear} aria-label={tx.clear}>
                  <Trash2 size={14} />
                </button>
                <button onClick={() => setOpen(false)} className="p-1.5 rounded-full hover:bg-white/5 text-gray-400 hover:text-gray-100 transition-colors" title={tx.close} aria-label={tx.close}>
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* شريط التحليل السريع */}
            <div className="flex items-center gap-1.5 px-3 py-2 border-b border-white/[0.07]" dir="ltr">
              <select
                value={quickSymbol}
                onChange={e => setQuickSymbol(e.target.value)}
                className="flex-1 min-w-0 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                {(markets.length ? markets : [{ symbol: quickSymbol }]).map(m => (
                  <option key={m.symbol} value={m.symbol} className="bg-[#0B1020]">{marketName(m)} ({m.symbol})</option>
                ))}
              </select>
              <select
                value={quickTf}
                onChange={e => setQuickTf(e.target.value)}
                className="w-16 flex-shrink-0 bg-white/5 border border-white/10 rounded-lg px-1.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                {TIMEFRAMES.map(tf => <option key={tf} value={tf} className="bg-[#0B1020]">{tf}</option>)}
              </select>
              <button
                onClick={() => sendMessage(tx.cmd(quickSymbol, quickTf))}
                disabled={loading || limitReached}
                title={tx.analyzeNow}
                className="flex-shrink-0 flex items-center gap-1 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-opacity disabled:opacity-50 hover:opacity-90"
                style={{ background: 'linear-gradient(135deg,#0891B2,#6D28D9)' }}
              >
                <Zap size={12} />
                {tx.analyze}
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">

              {messages.length === 0 && (
                <div className="space-y-4">
                  <div className="flex flex-col items-center text-center pt-2">
                    <NeuralOrb size={56} />
                    <div className="mt-2 text-sm font-semibold text-white">{tx.emptyTitle}</div>
                    <div className="text-[11px] text-gray-500 mt-0.5">{tx.emptySub}</div>
                  </div>

                  <div className="flex flex-wrap gap-1.5 justify-center">
                    {tx.suggestions.map(s => (
                      <button
                        key={s.label}
                        onClick={() => sendMessage(s.msg)}
                        className="text-[11.5px] px-3 py-1.5 rounded-full border border-cyan-500/25 text-cyan-200 hover:bg-cyan-500/10 transition-colors"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {categories.map(cat => (
                      <button
                        key={cat}
                        onClick={() => setActiveCategory(cat)}
                        className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors ${
                          activeCategory === cat
                            ? 'bg-cyan-600/90 border-cyan-400 text-white'
                            : 'bg-white/[0.04] border-white/10 text-gray-400 hover:text-gray-200 hover:border-white/20'
                        }`}
                      >
                        {categoryLabel(cat, isAr)}
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {categoryMarkets.map(m => (
                      <button
                        key={m.symbol}
                        onClick={() => sendMessage(tx.cmd(m.symbol, quickTf))}
                        className="text-xs bg-white/[0.04] hover:bg-white/[0.09] border border-white/10 rounded-lg px-2.5 py-1.5 text-gray-300 transition-colors"
                      >
                        {marketName(m)}
                      </button>
                    ))}
                    {categoryMarkets.length === 0 && (
                      <p className="text-center text-gray-600 text-xs py-2 w-full">{tx.noSymbols}</p>
                    )}
                  </div>

                  <p className="text-center text-[11px] text-gray-600">{tx.orType}</p>
                </div>
              )}

              {messages.map((m, i) => (
                <MessageBubble key={i} msg={m} tx={tx} isAr={isAr} />
              ))}

              {loading && (
                <div className="flex items-center gap-2" style={{ direction: 'ltr' }}>
                  <NeuralOrb size={22} active />
                  <span className="text-xs text-cyan-300/80" dir={isAr ? 'rtl' : 'ltr'}>{tx.thinking}</span>
                </div>
              )}

              {error && (
                <div className="flex items-center justify-between gap-2 text-xs text-rose-300 bg-rose-900/20 border border-rose-700/40 rounded-lg px-3 py-2">
                  <span>{error}</span>
                  {limitReached && (
                    <a
                      href="/pricing"
                      className="flex-shrink-0 text-white px-3 py-1 rounded-lg font-semibold whitespace-nowrap"
                      style={{ background: 'linear-gradient(135deg,#0891B2,#6D28D9)' }}
                    >
                      {tx.subscribe}
                    </a>
                  )}
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-t border-white/[0.07] px-3 pt-2.5 pb-2">
              <div className="flex items-end gap-2">
                <textarea
                  rows={1}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      sendMessage(input)
                    }
                  }}
                  disabled={limitReached}
                  placeholder={limitReached ? tx.subscribeToContinue : tx.ask}
                  className="flex-1 resize-none bg-white/5 text-gray-100 text-sm rounded-xl px-3 py-2 border border-white/10 focus:outline-none focus:ring-1 focus:ring-cyan-500 placeholder:text-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  onClick={() => sendMessage(input)}
                  disabled={loading || !input.trim() || limitReached}
                  aria-label={tx.analyze}
                  className="h-9 w-9 flex items-center justify-center rounded-full text-white shadow-lg transition-opacity disabled:opacity-40"
                  style={{ background: 'linear-gradient(135deg,#0891B2,#6D28D9)' }}
                >
                  <Send size={15} className={isAr ? 'scale-x-[-1]' : ''} />
                </button>
              </div>
              <div className="mt-1.5 flex items-center justify-center gap-1 text-[10px] text-gray-600">
                <ShieldAlert size={10} /> {tx.disclaimer}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
