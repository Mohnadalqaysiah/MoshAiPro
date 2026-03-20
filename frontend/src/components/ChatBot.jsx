import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { MessageCircle, X, Send, BarChart2, FileText, Sparkles, Trash2 } from 'lucide-react'
import { createChart } from 'lightweight-charts'

const API = 'http://localhost:8000'

function CandlesChart({ candles }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return

    if (!chartRef.current) {
      chartRef.current = createChart(containerRef.current, {
        layout: {
          background: { color: 'transparent' },
          textColor: '#e5e7eb',
        },
        grid: {
          vertLines: { color: 'rgba(55, 65, 81, 0.3)' },
          horzLines: { color: 'rgba(55, 65, 81, 0.3)' },
        },
        width: containerRef.current.clientWidth,
        height: 220,
        crosshair: {
          mode: 0,
        },
        rightPriceScale: {
          borderColor: 'rgba(107, 114, 128, 0.4)',
        },
        timeScale: {
          borderColor: 'rgba(107, 114, 128, 0.4)',
        },
      })
      seriesRef.current = chartRef.current.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderDownColor: '#ef4444',
        borderUpColor: '#22c55e',
        wickDownColor: '#ef4444',
        wickUpColor: '#22c55e',
      })
    }

    if (seriesRef.current && candles?.length) {
      const formatted = candles.map(c => ({
        time: Math.floor(new Date(c.time).getTime() / 1000),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
      seriesRef.current.setData(formatted)
      chartRef.current.timeScale().fitContent()
    }

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [candles])

  if (!candles?.length) return null

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1 text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <BarChart2 size={14} className="text-blue-400" />
          <span>الرسم البياني (آخر {candles.length} شمعة)</span>
        </div>
      </div>
      <div ref={containerRef} className="w-full rounded-md border border-gray-700/70 overflow-hidden bg-gray-900/60" />
    </div>
  )
}

function AnalysisCard({ analysis, symbol, timeframe }) {
  if (!analysis) return null

  const rec = analysis.recommendation || analysis.signal_type || 'WATCH'
  const confidence = analysis.ai_confidence_score || analysis.ai_confidence || 0

  const getRecColor = () => {
    if (rec === 'BUY') return 'text-green-400'
    if (rec === 'SELL') return 'text-red-400'
    return 'text-yellow-400'
  }

  const getRecLabel = () => {
    if (rec === 'BUY') return 'شراء'
    if (rec === 'SELL') return 'بيع'
    return 'مراقبة'
  }

  return (
    <div className="mt-3 rounded-lg border border-gray-700/70 bg-gray-900/60 p-3 text-xs space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Sparkles size={14} className="text-blue-400" />
          <span className="font-semibold text-gray-100">تحليل ذكي</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-gray-400">
          {symbol && <span>{symbol}</span>}
          {timeframe && <span className="text-gray-500">({timeframe})</span>}
        </div>
      </div>
      <div className="flex items-center justify-between text-[11px]">
        <span className={`font-semibold ${getRecColor()}`}>{getRecLabel()}</span>
        <span className="text-gray-400">
          ثقة:{' '}
          <span className="text-gray-100 font-medium">
            {typeof confidence === 'number' ? confidence.toFixed(1) : confidence}%
          </span>
        </span>
      </div>
      {analysis.entry_zones && analysis.entry_zones.length > 0 && (
        <div className="text-gray-300">
          دخول: <span className="text-gray-100">{analysis.entry_zones[0]}</span>
        </div>
      )}
      {analysis.stop_loss_zone && (
        <div className="text-gray-300">
          وقف الخسارة: <span className="text-red-400">{analysis.stop_loss_zone}</span>
        </div>
      )}
      {analysis.take_profit_zones && analysis.take_profit_zones.length > 0 && (
        <div className="text-gray-300">
          الأهداف:{' '}
          <span className="text-green-400">
            {analysis.take_profit_zones.slice(0, 3).join(' / ')}
          </span>
        </div>
      )}
      {analysis.risk_reward && (
        <div className="text-gray-300">
          R/R:{' '}
          <span className="text-gray-100">
            {analysis.risk_reward.toFixed ? analysis.risk_reward.toFixed(2) : analysis.risk_reward}x
          </span>
        </div>
      )}
    </div>
  )
}

export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastCandles, setLastCandles] = useState(null)
  const [lastAnalysis, setLastAnalysis] = useState(null)
  const [lastMeta, setLastMeta] = useState({ symbol: null, timeframe: null })

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setError('')

    const userMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMessage])

    try {
      setLoading(true)
      const res = await axios.post(`${API}/api/v1/chat/message`, {
        message: text,
        session_id: sessionId || '',
      })

      const { session_id, response } = res.data
      if (session_id && !sessionId) setSessionId(session_id)

      const action = response?.action || 'text'
      const replyText = response?.message || 'تم استقبال الرد من الوكيل.'

      const assistantMessage = {
        role: 'assistant',
        content: replyText,
        action,
        raw: response,
      }

      setMessages(prev => [...prev, assistantMessage])

      const symbol = response?.symbol || lastMeta.symbol
      const timeframe = response?.timeframe || lastMeta.timeframe

      if (response?.data && action === 'analyze') {
        setLastAnalysis(response.data)
        setLastMeta({ symbol, timeframe })
      } else if (response?.analysis) {
        setLastAnalysis(response.analysis)
        setLastMeta({ symbol, timeframe })
      }

      let candles = null
      if (action === 'chart' && response?.data?.candles) {
        candles = response.data.candles
      } else if (response?.candles) {
        candles = response.candles
      }
      if (candles && candles.length) {
        setLastCandles(candles)
        setLastMeta({ symbol, timeframe })
      }
    } catch (e) {
      console.error(e)
      setError('فشل الاتصال بوكيل التداول. تأكد أن السيرفر يعمل وأن مفتاح Gemini مفعّل.')
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'حدث خطأ أثناء محاولة التحليل. حاول مرة أخرى لاحقاً.',
          action: 'error',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClearSession = async () => {
    setMessages([])
    setLastCandles(null)
    setLastAnalysis(null)
    setError('')
    if (sessionId) {
      try {
        await axios.delete(`${API}/api/v1/chat/session/${sessionId}`)
      } catch {
        // ignore
      }
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 shadow-xl shadow-blue-500/30 text-sm font-medium"
      >
        <MessageCircle size={18} />
        <span>مُوش - وكيل التداول</span>
      </button>

      {/* Panel */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-40 w-full max-w-md">
          <div className="rounded-2xl border border-gray-700 bg-gray-900/95 backdrop-blur shadow-2xl flex flex-col h-[460px]">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold">
                  M
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">مُوش - وكيل التداول الذكي</div>
                  <div className="text-[11px] text-gray-400">
                    اسأله عن التحليل، الفرص، الشموع أو اطلب تقرير تداول
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handleClearSession}
                  className="p-1.5 rounded-full hover:bg-gray-800 text-gray-400 hover:text-red-400"
                  title="مسح المحادثة"
                >
                  <Trash2 size={14} />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-full hover:bg-gray-800 text-gray-400 hover:text-gray-100"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 text-sm scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-700/80">
              {messages.length === 0 && (
                <div className="text-xs text-gray-400 bg-gray-800/60 border border-dashed border-gray-700 rounded-lg p-3">
                  جرّب مثلاً:
                  <ul className="mt-1 list-disc list-inside space-y-0.5">
                    <li>حلل لي الذهب XAUUSD على فريم الساعة واعطني الفرص</li>
                    <li>اعرض لي الشموع الأخيرة للبيتكوين مع تقرير مختصر</li>
                    <li>اعمل لي تقرير تداول مفصل لـ EURUSD ليوم اليوم</li>
                  </ul>
                </div>
              )}

              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-3 py-2 ${
                      m.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-sm'
                        : 'bg-gray-800 text-gray-100 rounded-bl-sm'
                    } text-sm whitespace-pre-wrap`}
                  >
                    {m.content}

                    {m.role === 'assistant' && (
                      <>
                        {m.action === 'report' && (
                          <div className="mt-2 inline-flex items-center gap-1 text-[11px] text-amber-300">
                            <FileText size={12} />
                            <span>تقرير تداول</span>
                          </div>
                        )}
                        {m.action === 'analyze' && (
                          <div className="mt-2 inline-flex items-center gap-1 text-[11px] text-blue-300">
                            <BarChart2 size={12} />
                            <span>تحليل وفرص</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}

              {error && (
                <div className="text-[11px] text-red-400 bg-red-900/20 border border-red-700 rounded-md px-2 py-1">
                  {error}
                </div>
              )}

              {lastAnalysis && (
                <AnalysisCard
                  analysis={lastAnalysis}
                  symbol={lastMeta.symbol}
                  timeframe={lastMeta.timeframe}
                />
              )}

              {lastCandles && <CandlesChart candles={lastCandles} />}
            </div>

            {/* Input */}
            <div className="border-t border-gray-800 px-3 py-2">
              <div className="flex items-end gap-2">
                <textarea
                  rows={1}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="flex-1 resize-none bg-gray-800 text-gray-100 text-sm rounded-xl px-3 py-2 border border-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 placeholder:text-gray-500"
                  placeholder="اكتب سؤالك عن التحليل، الشموع أو التقارير..."
                />
                <button
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  className="h-9 w-9 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 disabled:text-gray-500 text-white shadow-lg shadow-blue-500/30 transition-colors"
                >
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Send size={16} />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

