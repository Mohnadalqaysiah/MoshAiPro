import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Layers, Send, CheckCircle2, Circle, Zap, Sparkles,
  TrendingUp, Clock, Activity, Gauge, ArrowRight,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

// نفس أنواع الشروط الحقيقية المدعومة بمحرك الاستراتيجيات
// (backend/app/services/strategy_engine.py::SUPPORTED_CONDITION_TYPES)
// — الأوزان هنا توضيحية لأغراض المعاينة فقط، مجموعها 100.
const CONDITIONS = [
  { id: 'bos',       labelAr: 'كسر هيكل (BOS)',           labelEn: 'Break of Structure',    weight: 20, group: 'smc' },
  { id: 'liquidity', labelAr: 'اكتساح سيولة',              labelEn: 'Liquidity Sweep',       weight: 20, group: 'smc' },
  { id: 'fvg',       labelAr: 'فجوة سعرية (FVG)',          labelEn: 'Fair Value Gap',        weight: 15, group: 'smc' },
  { id: 'ob',        labelAr: 'كتلة أوامر (Order Block)',  labelEn: 'Order Block',           weight: 15, group: 'smc' },
  { id: 'killzone',  labelAr: 'منطقة تفعيل زمنية',         labelEn: 'Kill Zone Session',     weight: 10, group: 'time' },
  { id: 'rsi',       labelAr: 'RSI < 30 (تشبع بيعي)',      labelEn: 'RSI < 30 (Oversold)',   weight: 10, group: 'indicator' },
  { id: 'ema',       labelAr: 'السعر فوق EMA20',           labelEn: 'Price Above EMA20',     weight: 10, group: 'indicator' },
]

const MIN_SCORE = 70

export default function StrategyBuilderDemo({ isAr = true }) {
  const { user } = useAuth()
  const [active, setActive] = useState(() => new Set(['bos', 'liquidity']))

  const toggle = (id) => {
    setActive(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const score = useMemo(
    () => Math.min(100, CONDITIONS.filter(c => active.has(c.id)).reduce((s, c) => s + c.weight, 0)),
    [active]
  )
  const triggered = score >= MIN_SCORE
  const matched = CONDITIONS.filter(c => active.has(c.id))

  const alertText = isAr
    ? `━━━━━━━━━━━━━━\n🔥 الاستراتيجية تحققت\n\nXAUUSD — 15M\n\nالشروط المتحققة:\n${matched.map(m => `✓ ${m.labelAr}`).join('\n') || '—'}\n\nالثقة: ${score}%\n━━━━━━━━━━━━━━`
    : `━━━━━━━━━━━━━━\n🔥 STRATEGY TRIGGERED\n\nXAUUSD — 15M\n\nMatched Conditions:\n${matched.map(m => `✓ ${m.labelEn}`).join('\n') || '—'}\n\nConfidence: ${score}%\n━━━━━━━━━━━━━━`

  return (
    <section id="strategy-builder-demo" className="py-24 px-4 relative overflow-hidden bg-white/[0.01]">
      <div className="orb w-[500px] h-[400px] bg-indigo-600/8 top-0 right-0 pointer-events-none" />
      <div className="max-w-6xl mx-auto relative">
        <div className="text-center mb-14 reveal">
          <p className="text-indigo-400 text-sm font-semibold mb-3 uppercase tracking-widest">
            {isAr ? 'أداة بناء الاستراتيجيات' : 'Strategy Builder'}
          </p>
          <h2 className="text-3xl md:text-4xl font-black mb-4 section-title">
            {isAr ? 'ابنِ استراتيجيتك بنفسك — جرّبها الآن' : 'Build Your Own Strategy — Try It Now'}
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto leading-relaxed">
            {isAr
              ? 'اختر شروط SMC/ICT ومؤشرات فنية حقيقية، وشاهد كيف تتحول لاستراتيجية تراقبها المنصة تلقائياً وترسل لك تنبيه Telegram فوري عند تحققها — على الذهب، البيتكوين، الفوركس، وأسواق الخليج مثل تداول وأرامكو.'
              : 'Pick real SMC/ICT conditions and technical indicators, and watch them turn into a strategy the platform monitors automatically — with an instant Telegram alert when it triggers, across Gold, Bitcoin, Forex, and Gulf markets like Tadawul and Aramco.'}
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8 items-start">

          {/* LEFT: condition palette + score */}
          <div className="reveal">
            <div className="glass border border-white/8 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <Layers size={15} className="text-indigo-400" />
                <h3 className="font-bold text-white text-sm">
                  {isAr ? 'اختر شروط استراتيجيتك' : 'Select your strategy conditions'}
                </h3>
              </div>

              <div className="grid sm:grid-cols-2 gap-2.5 mb-6">
                {CONDITIONS.map(c => {
                  const on = active.has(c.id)
                  return (
                    <button
                      key={c.id}
                      onClick={() => toggle(c.id)}
                      className={`flex items-center gap-2.5 text-start px-3.5 py-3 rounded-xl border text-sm transition-all ${
                        on
                          ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-200'
                          : 'bg-gray-900/50 border-gray-700/50 text-gray-400 hover:border-gray-600'
                      }`}
                    >
                      {on ? <CheckCircle2 size={16} className="text-indigo-400 flex-shrink-0" /> : <Circle size={16} className="text-gray-600 flex-shrink-0" />}
                      <span className="flex-1">{isAr ? c.labelAr : c.labelEn}</span>
                      <span className={`text-xs font-mono ${on ? 'text-indigo-300' : 'text-gray-600'}`}>+{c.weight}</span>
                    </button>
                  )
                })}
              </div>

              {/* Score bar */}
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-gray-500 flex items-center gap-1.5"><Gauge size={12} /> {isAr ? 'قوة التحقق' : 'Match Score'}</span>
                <span className={`font-bold ${triggered ? 'text-green-400' : 'text-gray-400'}`}>{score}%</span>
              </div>
              <div className="h-2.5 bg-gray-800 rounded-full overflow-hidden relative">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${triggered ? 'bg-gradient-to-r from-green-500 to-emerald-400' : 'bg-gradient-to-r from-indigo-500 to-purple-500'}`}
                  style={{ width: `${score}%` }}
                />
                <div className="absolute top-0 bottom-0 w-px bg-white/40" style={{ left: `${MIN_SCORE}%` }} />
              </div>
              <p className="text-xs text-gray-600 mt-2">
                {isAr ? `الحد الأدنى للتفعيل: ${MIN_SCORE}%` : `Activation threshold: ${MIN_SCORE}%`}
              </p>
            </div>

            <p className="text-xs text-gray-600 mt-3 flex items-center gap-1.5">
              <Sparkles size={11} className="text-gray-600" />
              {isAr
                ? 'معاينة توضيحية بأوزان تعليمية — النسخة الحقيقية تحلل بيانات السوق الفعلية لحظياً.'
                : 'Illustrative preview with sample weights — the real tool analyzes live market data.'}
            </p>
          </div>

          {/* RIGHT: live status + telegram preview */}
          <div className="reveal space-y-5" style={{ transitionDelay: '120ms' }}>
            {/* Status card */}
            <div className={`glass border rounded-2xl p-5 transition-all duration-500 ${triggered ? 'border-green-500/30 shadow-xl shadow-green-500/10' : 'border-white/8'}`}>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-gray-500 flex items-center gap-1.5"><Activity size={12} /> XAUUSD · 15M</span>
                <span className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${
                  triggered ? 'text-green-400 bg-green-500/10 border-green-500/20' : 'text-gray-500 bg-gray-800/50 border-gray-700/50'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${triggered ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
                  {triggered ? (isAr ? 'تحققت' : 'Triggered') : (isAr ? 'بانتظار شروط أكثر' : 'Waiting for more conditions')}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Clock size={13} />
                {isAr ? 'يفحص الخادم السوق تلقائياً كل 5 دقائق' : 'The server auto-checks the market every 5 minutes'}
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-400 mt-2">
                <TrendingUp size={13} />
                {isAr ? '25+ سوق مدعوم — عالمي وخليجي' : '25+ supported markets — global & Gulf'}
              </div>
            </div>

            {/* Telegram preview */}
            <div className="glass border border-blue-500/15 rounded-2xl overflow-hidden">
              <div className="bg-gray-900/80 border-b border-white/5 px-4 py-2.5 flex items-center gap-2">
                <Send size={13} className="text-blue-400" />
                <span className="text-xs text-gray-400 font-mono">Telegram · Qaffel AI Bot</span>
              </div>
              <div className="p-4 min-h-[190px] flex items-end">
                <div className={`w-full rounded-2xl rounded-bl-sm px-4 py-3 text-xs font-mono whitespace-pre-wrap leading-relaxed transition-all duration-500 ${
                  triggered ? 'bg-green-900/20 border border-green-500/25 text-green-200' : 'bg-gray-800/60 border border-gray-700/50 text-gray-500'
                }`}>
                  {triggered ? alertText : (isAr ? '⏳ لا يوجد تنبيه بعد — أضف شروطاً حتى تتجاوز 70%' : '⏳ No alert yet — add conditions to cross 70%')}
                </div>
              </div>
            </div>

            <Link
              to={user ? '/strategies' : '/register'}
              className="group flex items-center justify-center gap-2 w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white px-6 py-3.5 rounded-2xl font-bold text-sm transition-all shadow-xl shadow-indigo-500/20 hover:shadow-indigo-500/40"
            >
              <Zap size={16} className="fill-white" />
              {isAr ? 'جرّب أداة بناء الاستراتيجيات الحقيقية' : 'Try the Real Strategy Builder'}
              <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform rtl:rotate-180" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
