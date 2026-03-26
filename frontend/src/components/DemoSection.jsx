import { useState, useEffect, useRef } from 'react'
import {
  TrendingUp, TrendingDown, Zap, Brain, BarChart2,
  Shield, Target, CheckCircle, AlertTriangle,
  Activity, Cpu, Database, ArrowRight
} from 'lucide-react'

// ── Typing animation hook ────────────────────────────────────────────
function useTyping(text, speed = 28, active = true) {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)
  useEffect(() => {
    if (!active) return
    setDisplayed('')
    setDone(false)
    let i = 0
    const t = setInterval(() => {
      i++
      setDisplayed(text.slice(0, i))
      if (i >= text.length) { clearInterval(t); setDone(true) }
    }, speed)
    return () => clearInterval(t)
  }, [text, active])
  return { displayed, done }
}

// ── Pipeline step ────────────────────────────────────────────────────
function PipelineStep({ icon: Icon, label, sublabel, color, active, done, delay = 0 }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  return (
    <div className={`flex flex-col items-center gap-2 transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
      <div className={`w-12 h-12 rounded-2xl border-2 flex items-center justify-center transition-all duration-500 ${
        done  ? `border-green-500/60 bg-green-500/10 shadow-lg shadow-green-500/20` :
        active ? `border-${color}-500/70 bg-${color}-500/15 shadow-lg shadow-${color}-500/25 animate-pulse` :
                 'border-gray-700/60 bg-gray-800/40'
      }`}>
        {done
          ? <CheckCircle size={20} className="text-green-400" />
          : <Icon size={20} className={active ? `text-${color}-400` : 'text-gray-600'} />
        }
      </div>
      <div className="text-center">
        <p className={`text-xs font-bold transition-colors ${done ? 'text-green-400' : active ? `text-${color}-300` : 'text-gray-600'}`}>{label}</p>
        <p className="text-xs text-gray-600 mt-0.5">{sublabel}</p>
      </div>
    </div>
  )
}

// ── Connector ────────────────────────────────────────────────────────
function Connector({ active, done }) {
  return (
    <div className="flex items-center pt-0 pb-4">
      <div className={`h-px flex-1 transition-all duration-700 ${done || active ? 'bg-gradient-to-r from-blue-500/50 to-blue-400/30' : 'bg-gray-800'}`} />
      <ArrowRight size={12} className={`transition-colors ${done || active ? 'text-blue-400' : 'text-gray-700'}`} />
    </div>
  )
}

// ── Main Demo ────────────────────────────────────────────────────────
export default function DemoSection({ isAr = true }) {
  const [phase, setPhase] = useState(0) // 0=idle 1=fetch 2=ict 3=ai 4=done
  const [running, setRunning] = useState(false)
  const [activeTab, setActiveTab] = useState('signal') // signal | agent
  const sectionRef = useRef(null)

  // Auto-start when section in view
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !running) startDemo()
    }, { threshold: 0.3 })
    if (sectionRef.current) io.observe(sectionRef.current)
    return () => io.disconnect()
  }, [running])

  const startDemo = () => {
    if (running) return
    setRunning(true)
    setPhase(1)
    setTimeout(() => setPhase(2), 1200)
    setTimeout(() => setPhase(3), 2400)
    setTimeout(() => setPhase(4), 3800)
    setTimeout(() => setRunning(false), 4200)
  }

  const reset = () => { setPhase(0); setRunning(false); setTimeout(startDemo, 300) }

  const agentText = isAr
    ? `🔍 تحليل XAUUSD / 1H

📊 السياق المؤسسي:
• الإطار الأعلى 4H: اتجاه صاعد قوي
• Wyckoff: مرحلة Spring — ضغط تراكم
• المنطقة: Premium/Discount حياد

💧 تحليل السيولة ICT:
• SSL مكتسح عند 2,318.50 ✅
• Rejection شمعي مؤكد (3 شمعات)
• جودة Sweep: STRONG 🟢

🧱 Order Blocks:
• OB صاعد: 2,319.20 → 2,321.80
• السعر داخل المنطقة الآن ⚡

✅ القرار النهائي: BUY
• الثقة: 87% | Grade: A`
    : `🔍 Analyzing XAUUSD / 1H

📊 Institutional Context:
• HTF 4H: Strong bullish trend
• Wyckoff: Spring phase — accumulation
• Zone: Premium/Discount neutral

💧 ICT Liquidity Analysis:
• SSL swept at 2,318.50 ✅
• Rejection confirmed (3 candles)
• Sweep Quality: STRONG 🟢

🧱 Order Blocks:
• Bullish OB: 2,319.20 → 2,321.80
• Price inside zone now ⚡

✅ Final Decision: BUY
• Confidence: 87% | Grade: A`

  const { displayed: agentDisplayed, done: agentDone } = useTyping(agentText, 18, phase >= 4 && activeTab === 'agent')

  const pipeline = [
    { icon: Database, label: isAr ? 'بيانات السوق' : 'Market Data', sublabel: 'yfinance · TwelveData', color: 'blue',   activeAt: 1 },
    { icon: BarChart2, label: isAr ? 'محرك ICT' : 'ICT Engine',     sublabel: 'OB · FVG · Sweep',     color: 'purple', activeAt: 2 },
    { icon: Brain,     label: isAr ? 'Gemini AI' : 'Gemini AI',      sublabel: 'HTF+LTF · Scoring',    color: 'pink',   activeAt: 3 },
    { icon: Zap,       label: isAr ? 'الإشارة' : 'Signal',           sublabel: 'BUY/SELL/WAIT',        color: 'green',  activeAt: 4 },
  ]

  return (
    <section ref={sectionRef} className="py-24 px-4 relative overflow-hidden">
      {/* background */}
      <div className="orb w-[500px] h-[400px] bg-purple-600/8 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none" />

      <div className="max-w-6xl mx-auto">
        {/* Title */}
        <div className="text-center mb-14 reveal">
          <p className="text-purple-400 text-sm font-semibold mb-3 uppercase tracking-widest">
            {isAr ? 'النموذج البصري' : 'Live Demo'}
          </p>
          <h2 className="text-3xl md:text-4xl font-black mb-4 section-title">
            {isAr ? 'شاهد الذكاء الاصطناعي يعمل' : 'Watch the AI in Action'}
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto">
            {isAr
              ? 'من بيانات السوق الخام إلى إشارة دقيقة — في ثوانٍ'
              : 'From raw market data to a precise signal — in seconds'}
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8 items-start">

          {/* LEFT: Pipeline + Controls */}
          <div className="space-y-6 reveal">

            {/* Pipeline */}
            <div className="glass border border-white/8 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-5">
                <h3 className="font-bold text-white text-sm flex items-center gap-2">
                  <Activity size={15} className="text-blue-400" />
                  {isAr ? 'مسار التحليل' : 'Analysis Pipeline'}
                </h3>
                {phase >= 4 && (
                  <span className="flex items-center gap-1.5 text-xs text-green-400 bg-green-500/10 border border-green-500/20 px-2.5 py-1 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                    {isAr ? 'اكتمل' : 'Complete'}
                  </span>
                )}
              </div>

              {/* Steps row */}
              <div className="grid grid-cols-4 gap-1 items-center">
                {pipeline.map((s, i) => (
                  <>
                    <PipelineStep
                      key={s.label}
                      icon={s.icon}
                      label={s.label}
                      sublabel={s.sublabel}
                      color={s.color}
                      active={phase === s.activeAt}
                      done={phase > s.activeAt}
                      delay={i * 150}
                    />
                    {i < pipeline.length - 1 && (
                      <div key={`c${i}`} className="hidden" />
                    )}
                  </>
                ))}
              </div>

              {/* Progress bar */}
              <div className="mt-5 h-1 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-green-500 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(phase * 25, 100)}%` }}
                />
              </div>

              {/* Run button */}
              <button
                onClick={reset}
                disabled={running}
                className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed">
                {running
                  ? <><span className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" /> {isAr ? 'جاري التحليل...' : 'Analyzing...'}</>
                  : <><Zap size={14} className="fill-blue-400" /> {isAr ? 'تشغيل التحليل' : 'Run Analysis'}</>
                }
              </button>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: isAr ? 'نماذج AI' : 'AI Models',    value: '4',    icon: <Brain size={14}/>,  color: 'purple' },
                { label: isAr ? 'مؤشر ICT' : 'ICT Signals',  value: '12+',  icon: <BarChart2 size={14}/>, color: 'blue' },
                { label: isAr ? 'وقت التحليل' : 'Latency',   value: '<3s',  icon: <Zap size={14}/>,   color: 'green' },
              ].map((s, i) => (
                <div key={i} className={`glass border border-${s.color}-500/15 rounded-xl p-3 text-center`}>
                  <div className={`text-${s.color}-400 flex justify-center mb-1`}>{s.icon}</div>
                  <div className="text-white font-black text-lg">{s.value}</div>
                  <div className="text-gray-600 text-xs">{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT: Signal card + Agent */}
          <div className="reveal" style={{ transitionDelay: '150ms' }}>
            {/* Tabs */}
            <div className="flex gap-1 mb-4 glass border border-white/8 rounded-xl p-1 w-fit">
              {[
                { key: 'signal', label: isAr ? '📊 الإشارة' : '📊 Signal' },
                { key: 'agent',  label: isAr ? '🤖 الوكيل' : '🤖 AI Agent' },
              ].map(tab => (
                <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                  className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    activeTab === tab.key
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}>
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Signal Card */}
            {activeTab === 'signal' && (
              <div className={`glass border rounded-2xl overflow-hidden transition-all duration-500 ${
                phase >= 4 ? 'border-green-500/30 shadow-xl shadow-green-500/10' : 'border-white/8'
              }`}>
                {/* Header */}
                <div className="bg-gradient-to-r from-green-900/30 to-emerald-900/20 border-b border-green-500/20 px-5 py-4 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 text-xs">XAUUSD / 1H</span>
                      <span className="text-xs bg-gray-700/50 text-gray-400 px-2 py-0.5 rounded">Live</span>
                    </div>
                    <div className={`text-2xl font-black mt-0.5 transition-all duration-700 ${phase >= 4 ? 'text-green-400' : 'text-gray-600'}`}>
                      {phase >= 4 ? (isAr ? '▲ شراء' : '▲ BUY') : '• • •'}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-gray-500 text-xs">{isAr ? 'الثقة' : 'Confidence'}</div>
                    <div className={`text-3xl font-black transition-all duration-700 ${phase >= 4 ? 'text-white' : 'text-gray-700'}`}>
                      {phase >= 4 ? '87%' : '—'}
                    </div>
                    {phase >= 4 && (
                      <div className="text-xs text-green-400 font-bold">Grade A</div>
                    )}
                  </div>
                </div>

                {/* Body */}
                <div className="p-5 space-y-3">
                  {/* Price */}
                  <div className="flex justify-between text-sm border-b border-white/5 pb-3">
                    <span className="text-gray-500">{isAr ? 'السعر الحالي' : 'Current Price'}</span>
                    <span className="text-blue-300 font-mono font-bold">2,321.45 <span className="text-green-400 text-xs">● live</span></span>
                  </div>

                  {/* Levels */}
                  {[
                    { label: isAr ? 'منطقة الدخول' : 'Entry Zone', value: '2,319.20 — 2,321.80', color: 'text-white', show: phase >= 4 },
                    { label: isAr ? 'وقف الخسارة'  : 'Stop Loss',   value: '2,313.50',            color: 'text-red-400',   show: phase >= 4 },
                    { label: isAr ? 'هدف 1'         : 'Target 1',    value: '2,332.00',            color: 'text-green-400', show: phase >= 4 },
                    { label: isAr ? 'هدف 2'         : 'Target 2',    value: '2,341.50',            color: 'text-green-300', show: phase >= 4 },
                  ].map((l, i) => (
                    <div key={i} className={`flex justify-between text-sm transition-all duration-500 ${l.show ? 'opacity-100' : 'opacity-0'}`}
                      style={{ transitionDelay: `${i * 100}ms` }}>
                      <span className="text-gray-500">{l.label}</span>
                      <span className={`font-mono font-semibold ${l.color}`}>{l.value}</span>
                    </div>
                  ))}

                  {/* RR + Lot */}
                  {phase >= 4 && (
                    <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
                      <div className="glass border border-white/8 rounded-xl px-3 py-2 text-center">
                        <div className="text-blue-400 font-black text-base">2.14x</div>
                        <div className="text-gray-600 text-xs">Risk/Reward</div>
                      </div>
                      <div className="glass border border-white/8 rounded-xl px-3 py-2 text-center">
                        <div className="text-yellow-400 font-black text-base">0.23</div>
                        <div className="text-gray-600 text-xs">{isAr ? 'حجم اللوت' : 'Lot Size'}</div>
                      </div>
                    </div>
                  )}

                  {/* Sweep + OB */}
                  {phase >= 4 && (
                    <div className="mt-3 p-3 bg-green-900/15 border border-green-500/20 rounded-xl">
                      <p className="text-xs font-bold text-green-400 mb-2 flex items-center gap-1.5">
                        <CheckCircle size={12} /> {isAr ? 'Stop Hunt مؤكد — SSL Sweep' : 'Confirmed Stop Hunt — SSL Sweep'}
                      </p>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="text-center">
                          <div className="text-white font-bold">STRONG</div>
                          <div className="text-gray-500">{isAr ? 'الجودة' : 'Quality'}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-white font-bold">3</div>
                          <div className="text-gray-500">{isAr ? 'شمعات' : 'Candles'}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-green-400 font-bold">✅</div>
                          <div className="text-gray-500">Rejection</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* OB */}
                  {phase >= 4 && (
                    <div className="p-3 bg-blue-900/15 border border-blue-500/20 rounded-xl flex justify-between items-center">
                      <span className="text-xs text-gray-400 flex items-center gap-1.5">
                        <TrendingUp size={12} className="text-green-400" />
                        {isAr ? 'Order Block صاعد' : 'Bullish Order Block'}
                      </span>
                      <span className="text-green-400 font-mono text-xs font-bold">2,319.20 → 2,321.80</span>
                    </div>
                  )}

                  {/* Waiting state */}
                  {phase < 4 && (
                    <div className="py-6 flex flex-col items-center gap-3 text-gray-600">
                      <div className="flex gap-1">
                        {[0,1,2].map(i => (
                          <div key={i} className="w-2 h-2 rounded-full bg-gray-700 animate-bounce" style={{ animationDelay: `${i*150}ms` }} />
                        ))}
                      </div>
                      <p className="text-xs">{isAr ? 'جاري التحليل...' : 'Analyzing market...'}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Agent Tab */}
            {activeTab === 'agent' && (
              <div className="glass border border-purple-500/20 rounded-2xl overflow-hidden">
                {/* Terminal header */}
                <div className="bg-gray-900/80 border-b border-white/5 px-4 py-3 flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/70" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
                    <div className="w-3 h-3 rounded-full bg-green-500/70" />
                  </div>
                  <div className="flex-1 text-center">
                    <span className="text-xs text-gray-500 font-mono">Qaffel AI Agent — Gemini 2.0</span>
                  </div>
                  <Cpu size={13} className="text-purple-400" />
                </div>

                {/* Chat area */}
                <div className="p-4 min-h-[340px]">
                  {/* User message */}
                  <div className="flex justify-end mb-4">
                    <div className="bg-blue-600/20 border border-blue-500/20 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[85%]">
                      <p className="text-sm text-blue-100">{isAr ? 'حلّل XAUUSD على الـ 1H' : 'Analyze XAUUSD on 1H'}</p>
                    </div>
                  </div>

                  {/* AI response */}
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-purple-500/20">
                      <Brain size={14} className="text-white" />
                    </div>
                    <div className="flex-1">
                      {phase < 4 ? (
                        <div className="glass border border-purple-500/15 rounded-2xl rounded-tl-sm px-4 py-3">
                          <div className="flex items-center gap-2 text-purple-300 text-xs">
                            <div className="flex gap-1">
                              {[0,1,2].map(i => (
                                <div key={i} className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: `${i*150}ms` }} />
                              ))}
                            </div>
                            {isAr ? 'يحلل البيانات...' : 'Analyzing data...'}
                          </div>
                        </div>
                      ) : (
                        <div className="glass border border-purple-500/15 rounded-2xl rounded-tl-sm px-4 py-3">
                          <pre className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed font-mono">
                            {agentDisplayed}
                            {!agentDone && <span className="inline-block w-1.5 h-3.5 bg-purple-400 animate-pulse align-middle ml-0.5" />}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Input bar */}
                <div className="border-t border-white/5 px-4 py-3 flex gap-2">
                  <div className="flex-1 glass border border-white/8 rounded-xl px-3 py-2 text-xs text-gray-600">
                    {isAr ? 'اسأل عن أي زوج أو إطار زمني...' : 'Ask about any pair or timeframe...'}
                  </div>
                  <button className="w-8 h-8 rounded-xl bg-blue-600/30 border border-blue-500/30 flex items-center justify-center text-blue-400">
                    <Zap size={13} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
