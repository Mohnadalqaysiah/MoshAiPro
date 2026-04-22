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

  const fetch = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API}/api/v1/signals/latest?limit=30`)
      const signals = res.data.data || []
      // find highest-confidence BUY or SELL
      const active = signals.filter(s =>
        ['BUY', 'SELL'].includes(s.recommendation || s.signal_type) &&
        (s.ai_confidence_score || s.ai_confidence || 0) >= 55
      )
      if (active.length === 0) { setBest(null); return }
      const top = active.reduce((a, b) =>
        (b.ai_confidence_score || b.ai_confidence || 0) > (a.ai_confidence_score || a.ai_confidence || 0) ? b : a
      )
      setBest(top)
      setLastUpdated(new Date())
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
    const id = setInterval(fetch, 2 * 60 * 1000) // refresh every 2 min
    return () => clearInterval(id)
  }, [])

  const rec   = best?.recommendation || best?.signal_type || ''
  const conf  = best?.ai_confidence_score || best?.ai_confidence || 0
  const lvl   = best?.levels || {}
  const entry = lvl.entry   || best?.entry_price   || best?.entry_zones?.[0]
  const sl    = lvl.stop_loss || best?.stop_loss   || best?.stop_loss_zone
  const tp1   = lvl.tp1    || best?.take_profit_1 || best?.take_profit_zones?.[0]
  const rr    = best?.risk_reward_ratio || lvl.risk_reward
  const sym   = best?.symbol || best?.market || ''
  const tf    = best?.timeframe || '1h'

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
          onClick={fetch}
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
                <span className="text-xs opacity-50 best-opp-sub">{tx.tf}: {tf}</span>
              </div>
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-bold text-sm ${
                isBuy
                  ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                  : 'bg-red-500/15 text-red-400 border border-red-500/30'
              }`}>
                {isBuy ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {isBuy ? tx.buy : tx.sell}
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
