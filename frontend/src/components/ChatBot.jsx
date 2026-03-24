import { useEffect, useRef, useState, useCallback } from 'react'
import axios from 'axios'
import {
  MessageCircle, X, Send, BarChart2, FileText,
  Sparkles, Trash2, TrendingUp, TrendingDown, Minus
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ─── Candlestick Chart ────────────────────────────────────────────────────────
function CandlesChart({ candles, symbol, timeframe }) {
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
          layout: { background: { color: '#111827' }, textColor: '#9ca3af' },
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

        // deduplicate by time
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
    <div className="mt-2 rounded-lg overflow-hidden border border-gray-700/60">
      <div className="flex items-center gap-1.5 px-2 py-1.5 bg-gray-800/80 text-xs text-gray-400">
        <BarChart2 size={12} className="text-blue-400" />
        <span>{symbol} · {timeframe} · {candles.length} شمعة</span>
      </div>
      <div ref={ref} className="w-full bg-gray-900" />
    </div>
  )
}

// ─── Analysis Card ────────────────────────────────────────────────────────────
function AnalysisCard({ data, symbol, timeframe }) {
  if (!data || data.error) return null

  const rec = data.recommendation || 'WAIT'
  const conf = data.ai_confidence_score || 0
  const entry = data.entry_zones?.[0]
  const sl = data.stop_loss_zone
  const tps = data.take_profit_zones || []
  const rr = data.risk_reward_ratio
  const gemini = data.gemini_analysis

  const recStyles = {
    BUY:  { icon: TrendingUp,   color: 'text-green-400', bg: 'bg-green-400/10 border-green-500/30', label: 'شراء' },
    SELL: { icon: TrendingDown, color: 'text-red-400',   bg: 'bg-red-400/10 border-red-500/30',     label: 'بيع' },
    WAIT: { icon: Minus,        color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-500/30', label: 'انتظار' },
  }
  const style = recStyles[rec] || recStyles.WAIT
  const Icon = style.icon

  const confColor = conf >= 70 ? 'text-green-400' : conf >= 50 ? 'text-yellow-400' : 'text-gray-400'

  return (
    <div className={`mt-2 rounded-xl border p-3 text-xs space-y-2 ${style.bg}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon size={14} className={style.color} />
          <span className={`font-bold text-sm ${style.color}`}>{style.label}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-400">
          {symbol && <span className="font-mono">{symbol}</span>}
          {timeframe && <span className="text-gray-500">({timeframe})</span>}
          <span className={`font-semibold ${confColor}`}>{conf.toFixed(1)}%</span>
        </div>
      </div>

      {/* Price Levels */}
      {(entry || sl || tps.length > 0) && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 border-t border-gray-700/40 pt-2">
          {entry && (
            <div>
              <span className="text-gray-500">دخول</span>
              <span className="ml-1 font-mono text-gray-100">{+entry % 1 === 0 ? entry : (+entry).toFixed(5)}</span>
            </div>
          )}
          {sl && (
            <div>
              <span className="text-gray-500">وقف</span>
              <span className="ml-1 font-mono text-red-400">{+sl % 1 === 0 ? sl : (+sl).toFixed(5)}</span>
            </div>
          )}
          {tps.slice(0, 3).map((tp, i) => tp ? (
            <div key={i}>
              <span className="text-gray-500">هدف {i + 1}</span>
              <span className="ml-1 font-mono text-green-400">{+tp % 1 === 0 ? tp : (+tp).toFixed(5)}</span>
            </div>
          ) : null)}
          {rr && (
            <div className="col-span-2">
              <span className="text-gray-500">R/R</span>
              <span className="ml-1 font-mono text-blue-400">1:{(+rr).toFixed(1)}</span>
            </div>
          )}
        </div>
      )}

      {/* Gemini grade */}
      {gemini?.signal_grade && gemini.signal_grade !== '?' && (
        <div className="flex items-center gap-1.5 border-t border-gray-700/40 pt-1.5">
          <Sparkles size={11} className="text-purple-400" />
          <span className="text-gray-400">جودة الإشارة:</span>
          <span className="font-bold text-purple-300">{gemini.signal_grade}</span>
          {gemini.ict_setup && <span className="text-gray-500 ml-1">{gemini.ict_setup}</span>}
        </div>
      )}
    </div>
  )
}

// ─── Message Bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm px-3 py-2 bg-blue-600 text-white text-sm whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    )
  }

  const actionLabel = {
    analyze: { icon: BarChart2, label: 'تحليل', color: 'text-blue-400' },
    chart:   { icon: BarChart2, label: 'رسم بياني', color: 'text-cyan-400' },
    report:  { icon: FileText,  label: 'تقرير', color: 'text-amber-400' },
  }[msg.action]

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-1">
        {actionLabel && (
          <div className={`flex items-center gap-1 text-[11px] ${actionLabel.color} mb-0.5`}>
            <actionLabel.icon size={11} />
            <span>{actionLabel.label}</span>
          </div>
        )}
        <div className="rounded-2xl rounded-bl-sm px-3 py-2 bg-gray-800 text-gray-100 text-sm whitespace-pre-wrap leading-relaxed">
          {msg.content}
        </div>
        {msg.analysisData && (
          <AnalysisCard
            data={msg.analysisData}
            symbol={msg.symbol}
            timeframe={msg.timeframe}
          />
        )}
        {msg.candles?.length > 0 && (
          <CandlesChart
            candles={msg.candles}
            symbol={msg.symbol}
            timeframe={msg.timeframe}
          />
        )}
      </div>
    </div>
  )
}

// ─── Quick Actions ────────────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { label: '📊 تحليل الذهب', msg: 'حلل الذهب XAUUSD ساعة' },
  { label: '₿ بيتكوين', msg: 'تحليل BTCUSD 1h' },
  { label: '💶 يورو', msg: 'تحليل EURUSD 1h' },
  { label: '🕯️ شموع الذهب', msg: 'اعرض شموع الذهب XAUUSD' },
]

// ─── Main ChatBot ─────────────────────────────────────────────────────────────
export default function ChatBot() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, scrollToBottom])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return
    setInput('')
    setError('')

    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])

    try {
      setLoading(true)
      const res = await axios.post(`${API}/api/v1/chat/message`, {
        message: text,
        session_id: sessionId || '',
      })

      const { session_id, response } = res.data
      if (session_id && !sessionId) setSessionId(session_id)

      const assistantMsg = {
        role: 'assistant',
        content: response?.message || 'تم استقبال الرد.',
        action: response?.action || 'text',
        symbol: response?.symbol,
        timeframe: response?.timeframe,
        analysisData: response?.data || response?.analysis || null,
        candles: response?.candles || response?.data?.candles || null,
      }

      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      console.error(e)
      setError('فشل الاتصال. تأكد أن الخادم يعمل.')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ حدث خطأ. حاول مرة أخرى.',
        action: 'error',
      }])
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId])

  const handleClear = async () => {
    setMessages([])
    setError('')
    if (sessionId) {
      try { await axios.delete(`${API}/api/v1/chat/session/${sessionId}`) } catch {}
      setSessionId('')
    }
  }

  return (
    <>
      {/* Floating Button — يختفي على الموبايل عند فتح الشات */}
      <button
        onClick={() => setOpen(o => !o)}
        className={`fixed bottom-5 left-4 md:left-auto md:right-6 z-50 flex items-center gap-2 rounded-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white px-4 py-2.5 shadow-xl shadow-blue-500/30 text-sm font-medium transition-all ${open ? 'hidden md:flex' : 'flex'}`}
      >
        {open ? <X size={18} /> : <MessageCircle size={18} />}
        <span>كفيل AI</span>
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed inset-0 md:inset-auto md:bottom-20 md:right-6 z-40 md:w-full md:max-w-md">
          <div className="rounded-none md:rounded-2xl border-0 md:border border-gray-700/80 bg-gray-900 backdrop-blur-sm shadow-2xl flex flex-col h-full md:h-[520px]">

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-lg">
                  ك
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">كفيل — وكيل التداول الذكي</div>
                  <div className="text-[11px] text-gray-400">ICT · SMC · Wyckoff · Real-time</div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={handleClear} className="p-1.5 rounded-full hover:bg-gray-800 text-gray-400 hover:text-red-400 transition-colors" title="مسح المحادثة">
                  <Trash2 size={14} />
                </button>
                <button onClick={() => setOpen(false)} className="p-1.5 rounded-full hover:bg-gray-800 text-gray-400 hover:text-gray-100 transition-colors">
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-700">

              {/* Empty state */}
              {messages.length === 0 && (
                <div className="space-y-3">
                  <p className="text-center text-xs text-gray-500 pt-2">
                    خبير تداول بمدارس ICT/SMC/Wyckoff جاهز لمساعدتك
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {QUICK_ACTIONS.map((qa, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(qa.msg)}
                        className="text-xs bg-gray-800/80 hover:bg-gray-700 border border-gray-700/60 rounded-xl px-3 py-2 text-gray-300 text-right transition-colors"
                      >
                        {qa.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <MessageBubble key={i} msg={m} />
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              {error && (
                <div className="text-xs text-red-400 bg-red-900/20 border border-red-700/50 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-800 px-3 py-2.5">
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
                  placeholder="اكتب سؤالك... مثل: حلل الذهب ساعة"
                  className="flex-1 resize-none bg-gray-800 text-gray-100 text-sm rounded-xl px-3 py-2 border border-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-gray-500"
                />
                <button
                  onClick={() => sendMessage(input)}
                  disabled={loading || !input.trim()}
                  className="h-9 w-9 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white shadow-lg transition-colors"
                >
                  {loading
                    ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    : <Send size={15} />
                  }
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
