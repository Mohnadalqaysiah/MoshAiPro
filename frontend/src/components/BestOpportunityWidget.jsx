import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Zap, RefreshCw } from 'lucide-react'
import axios from 'axios'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const T = {
  ar: {
    title: 'أفضل فرصة الآن',
    sub: 'أعلى إشارة ثقة في جميع الأسواق',
    entry: 'دخول', sl: 'إيقاف', tp: 'هدف', rr: 'R/R', conf: 'الثقة',
    buy: 'شراء', sell: 'بيع', none: 'لا توجد فرصة قوية الآن',
    tf: 'الإطار الزمني',
  },
  en: {
    title: 'Best Opportunity Now',
    sub: 'Highest confidence signal across all markets',
    entry: 'Entry', sl: 'SL', tp: 'TP', rr: 'R/R', conf: 'Conf',
    buy: 'BUY', sell: 'SELL', none: 'No strong opportunity right now',
    tf: 'Timeframe',
  },
}

export default function BestOpportunityWidget() {
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'

  const [best, setBest]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadBest = async () => {
    setLoading(true)
    try {
      // hours=12: only ACTIVE/PENDING signals from last 12h
      const res = await axios.get(`${API}/api/v1/signals/latest?limit=50&hours=12`)
      const signals = res.data.data || []

      const now = Date.now()
      const active = signals.filter(s => {
        const rec  = s.recommendation || s.signal_type || ''
        const conf = s.ai_confidence_score || s.ai_confidence || 0
        const rr   = s.risk_reward_ratio || 0
        const age  = s.created_at ? (now - new Date(s.created_at).getTime()) / 3600000 : 99
        return (
          ['BUY', 'SELL'].includes(rec) &&
          conf >= 55 && conf <= 95 &&
          rr >= 1.3 &&
          age <= 12   // client-side age guard (backup)
        )
      })

      if (active.length === 0) { setBest(null); return }

      // Sort by combined score: 60% conf + 40% RR (normalised, max RR 4)
      const scored = active.map(s => ({
        ...s,
        _score: (
          (s.ai_confidence_score || s.ai_confidence || 0) * 0.6 +
          Math.min((s.risk_reward_ratio || 0) / 4, 1) * 100 * 0.4
        ),
      }))
      const top = scored.reduce((a, b) => b._score > a._score ? b : a)
      setBest(top)
      setLastUpdated(new Date())
    } catch {
      setBest(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBest()
    const id = setInterval(loadBest, 2 * 60 * 1000)
    return () => clearInterval(id)
  }, [])

  const signalAge = best?.created_at
    ? Math.round((Date.now() - new Date(best.created_at).getTime()) / 60000)
    : null

  const rec   = best?.recommendation || best?.signal_type || ''
  const conf  = best?.ai_confidence_score || best?.ai_confidence || 0
  const lvl   = best?.levels || {}
  const entry = lvl.entry      || best?.entry_price
  const sl    = lvl.stop_loss  || best?.stop_loss
  const tp1   = lvl.tp1        || best?.take_profit_1
  const rr    = best?.risk_reward_ratio || lvl.risk_reward
  const sym   = best?.symbol || best?.market || ''
  const tf    = best?.timeframe || '1h'
  const tier  = best?.signal_tier || ''

  // حدد عدد الخانات العشرية بناءً على حجم السعر
  const decimals = (v) => {
    if (!v) return 5
    const n = Number(v)
    if (n >= 100) return 2
    if (n >= 10)  return 3
    return 5
  }
  const fmt = (v) => v != null && v !== 0 ? Number(v).toFixed(decimals(v)) : '—'

  const isBuy  = rec === 'BUY'
  const isSell = rec === 'SELL'

  return (
    <div className="rounded-2xl border overflow-hidden best-opp-widget" dir={isAr ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b best-opp-header">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-yellow-400" />
          <span className="font-semibold text-sm">{tx.title}</span>
          {lastUpdated && (
            <span className="text-xs opacity-40 hidden sm:block">
              {lastUpdated.toLocaleTimeString(isAr ? 'ar' : 'en', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
        <button
          onClick={loadBest}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-white/10 transition-colors opacity-60 hover:opacity-100"
          title={isAr ? 'تحديث' : 'Refresh'}
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="px-5 py-4">
        {loading && !best ? (
          <div className="flex items-center justify-center py-6 gap-2 opacity-50">
            <RefreshCw size={14} className="animate-spin" />
            <span className="text-sm">{isAr ? 'جاري التحميل...' : 'Loading...'}</span>
          </div>
        ) : !best ? (
          <div className="flex items-center justify-center py-6 gap-2 opacity-40 text-sm">
            <Zap size={15} />
            {tx.none}
          </div>
        ) : (
          <div className="space-y-3">
            {/* Symbol + Direction row */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl font-bold tracking-wide">{sym}</span>
                <div className="flex flex-col leading-tight">
                  <span className="text-xs opacity-50 best-opp-sub">{tx.tf}: {tf}</span>
                  {signalAge !== null && (
                    <span className="text-xs opacity-35 best-opp-sub">
                      {signalAge < 60
                        ? `${signalAge}${isAr ? 'د' : 'm'} ${isAr ? 'مضى' : 'ago'}`
                        : `${Math.floor(signalAge/60)}${isAr ? 'س' : 'h'} ${isAr ? 'مضى' : 'ago'}`}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {tier === 'TIER_A' && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-500/15 text-yellow-400 border border-yellow-500/30 font-semibold">A</span>
                )}
                {tier === 'TIER_B' && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30 font-semibold">B</span>
                )}
                <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-bold text-sm ${
                  isBuy
                    ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                    : 'bg-red-500/15 text-red-400 border border-red-500/30'
                }`}>
                  {isBuy ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {isBuy ? tx.buy : tx.sell}
                </div>
              </div>
            </div>

            {/* Confidence bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs opacity-60">
                <span>{tx.conf}</span>
                <span className="font-semibold">{conf.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 rounded-full best-opp-track overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    isBuy ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(conf, 100)}%` }}
                />
              </div>
            </div>

            {/* Levels */}
            <div className="grid grid-cols-4 gap-2 pt-1">
              {[
                { label: tx.entry, val: fmt(entry) },
                { label: tx.sl,    val: fmt(sl)    },
                { label: tx.tp,    val: fmt(tp1)   },
                { label: tx.rr,    val: rr ? `${Number(rr).toFixed(2)}×` : '—' },
              ].map(({ label, val }) => (
                <div key={label} className="text-center best-opp-level-card rounded-lg py-2 px-1">
                  <p className="text-xs opacity-50 mb-0.5">{label}</p>
                  <p className="text-xs font-semibold font-mono tracking-tight truncate">{val}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
