import { useEffect, useRef, useState } from 'react'
import { TrendingUp, TrendingDown, BarChart2, Zap, Target, Trophy } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const MARKET_FLAGS = {
  XAUUSD: '🥇', XAGUSD: '🥈', BTCUSD: '₿', ETHUSD: 'Ξ',
  EURUSD: '🇪🇺', GBPUSD: '🇬🇧', USDJPY: '🇯🇵', USOIL: '🛢',
  NAS100: '📈', US30: '📊',
}

function AnimCount({ value, suffix = '' }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current; if (!el) return
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return
      io.disconnect()
      const end = parseFloat(value) || 0
      if (!end) { el.textContent = value + suffix; return }
      let cur = 0
      const step = end / (1400 / 16)
      const t = setInterval(() => {
        cur = Math.min(cur + step, end)
        el.textContent = (Number.isInteger(end) ? Math.round(cur) : cur.toFixed(1)) + suffix
        if (cur >= end) clearInterval(t)
      }, 16)
    }, { threshold: 0.5 })
    io.observe(el)
    return () => io.disconnect()
  }, [value, suffix])
  return <span ref={ref}>{value}{suffix}</span>
}

export default function PublicPerformance({ isAr = true }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const sectionRef = useRef(null)

  useEffect(() => {
    fetch(`${API}/api/v1/signals/public-results`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    const el = sectionRef.current; if (!el) return
    const io = new IntersectionObserver(entries =>
      entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible') }),
      { threshold: 0.1 }
    )
    el.querySelectorAll('.reveal').forEach(x => io.observe(x))
    return () => io.disconnect()
  }, [data])

  const ar = isAr

  if (loading) return (
    <section className="py-20 px-4 text-center">
      <div className="inline-flex items-center gap-2 text-gray-500 text-sm">
        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        {ar ? 'جارٍ تحميل النتائج...' : 'Loading results...'}
      </div>
    </section>
  )

  if (!data || data.all_time?.total === 0) return null

  const { trades = [], week = {}, all_time = {} } = data

  const statusLabel = (s, isWin) => {
    if (s === 'TP2_HIT') return ar ? 'TP2 ✅' : 'TP2 ✅'
    if (s === 'TP1_HIT') return ar ? 'TP1 ✅' : 'TP1 ✅'
    if (s === 'SL_HIT')  return ar ? 'SL ❌'  : 'SL ❌'
    return s
  }

  return (
    <section ref={sectionRef} className="py-24 px-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-green-950/8 to-transparent pointer-events-none" />
      <div className="orb w-[500px] h-[400px] bg-green-600/6 top-1/2 left-0 -translate-x-1/3 -translate-y-1/2 pointer-events-none" />

      <div className="max-w-5xl mx-auto relative">

        {/* Header */}
        <div className="text-center mb-14 reveal">
          <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/25 text-green-300 text-xs px-4 py-1.5 rounded-full mb-5">
            <BarChart2 size={12} />
            {ar ? 'نتائج حقيقية — محققة' : 'Real Results — Verified'}
          </div>
          <h2 className="text-3xl md:text-4xl font-black mb-4">
            {ar ? 'أداء إشارات' : 'Signal'}{' '}
            <span className="bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
              {ar ? 'Qaffel AI' : 'Qaffel AI'}
            </span>
          </h2>
          <p className="text-gray-400 max-w-lg mx-auto">
            {ar
              ? 'نتائج موثّقة من إشارات فعلية — يُحدَّث بعد كل صفقة مغلقة'
              : 'Documented results from real signals — updated after every closed trade'}
          </p>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12 reveal">
          {[
            {
              icon: Trophy,
              color: 'text-yellow-400',
              bg: 'bg-yellow-500/10 border-yellow-500/20',
              value: all_time.win_rate,
              suffix: '%',
              label: ar ? 'نسبة الربح الكلية' : 'All-time Win Rate',
            },
            {
              icon: Target,
              color: 'text-blue-400',
              bg: 'bg-blue-500/10 border-blue-500/20',
              value: all_time.total,
              suffix: '',
              label: ar ? 'إجمالي الصفقات' : 'Total Closed Trades',
            },
            {
              icon: TrendingUp,
              color: 'text-green-400',
              bg: 'bg-green-500/10 border-green-500/20',
              value: week.win_rate || 0,
              suffix: '%',
              label: ar ? 'دقة هذا الأسبوع' : 'This Week Accuracy',
            },
            {
              icon: Zap,
              color: 'text-purple-400',
              bg: 'bg-purple-500/10 border-purple-500/20',
              value: week.wins || 0,
              suffix: '',
              label: ar ? 'صفقات رابحة هذا الأسبوع' : 'Wins This Week',
            },
          ].map((s, i) => (
            <div key={i} className={`${s.bg} border rounded-2xl p-5 text-center`}
                 style={{ transitionDelay: `${i * 80}ms` }}>
              <s.icon size={20} className={`${s.color} mx-auto mb-2`} />
              <div className={`text-3xl font-black ${s.color}`}>
                <AnimCount value={s.value} suffix={s.suffix} />
              </div>
              <div className="text-xs text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Trades list */}
        <div className="reveal" style={{ transitionDelay: '120ms' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-white flex items-center gap-2">
              <BarChart2 size={16} className="text-blue-400" />
              {ar ? 'آخر الصفقات المغلقة' : 'Latest Closed Trades'}
            </h3>
            <span className="text-xs text-gray-500">
              {ar ? `${trades.length} صفقة` : `${trades.length} trades`}
            </span>
          </div>

          <div className="grid md:grid-cols-2 gap-2.5">
            {trades.slice(0, 10).map((tr, i) => {
              const isWin = tr.win
              return (
                <div key={i}
                  className={`flex items-center justify-between px-4 py-3 rounded-xl border transition-all ${
                    isWin
                      ? 'bg-green-900/10 border-green-700/25 hover:border-green-600/40'
                      : 'bg-red-900/10 border-red-700/25 hover:border-red-600/40'
                  }`}
                  style={{ transitionDelay: `${i * 40}ms` }}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{MARKET_FLAGS[tr.market] || '📊'}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{tr.market}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                          tr.type === 'BUY'
                            ? 'bg-green-900/60 text-green-300'
                            : 'bg-red-900/60 text-red-300'
                        }`}>
                          {tr.type === 'BUY' ? (ar ? 'شراء' : 'BUY') : (ar ? 'بيع' : 'SELL')}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {statusLabel(tr.result, isWin)} · {tr.closed_at || '—'}
                      </div>
                    </div>
                  </div>

                  <div className={`text-right font-black text-base ${isWin ? 'text-green-400' : 'text-red-400'}`}>
                    {isWin ? '+' : ''}{tr.points.toLocaleString()}
                    <div className="text-xs font-normal text-gray-500">{ar ? 'نقطة' : 'pts'}</div>
                  </div>
                </div>
              )
            })}
          </div>

          {trades.length === 0 && (
            <div className="text-center py-12 text-gray-600">
              {ar ? 'لا توجد صفقات مغلقة بعد' : 'No closed trades yet'}
            </div>
          )}
        </div>

        {/* Disclaimer + CTA */}
        <div className="mt-10 text-center reveal">
          <p className="text-gray-600 text-xs mb-6">
            {ar
              ? '* النقاط محسوبة على أساس نقطة = 0.01$ حركة سعرية · النتائج السابقة لا تضمن المستقبل'
              : '* Points based on 1pt = $0.01 price move · Past performance does not guarantee future results'}
          </p>
          <a href="/register"
            className="inline-flex items-center gap-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white px-8 py-3.5 rounded-2xl font-bold text-sm transition-all hover:scale-105 shadow-xl shadow-green-500/20">
            <Zap size={16} />
            {ar ? 'ابدأ مجاناً وتابع الإشارات' : 'Start Free & Follow Signals'}
          </a>
        </div>

      </div>
    </section>
  )
}
