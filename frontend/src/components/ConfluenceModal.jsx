import { useState } from 'react'
import axios from 'axios'
import { X, RefreshCw, Zap, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TIMEFRAMES = ['15m', '1h', '4h', '1day']
const TF_META = {
  '15m':  { ar: '15 دقيقة',  en: '15 Min',   weight: 1 },
  '1h':   { ar: 'ساعة',      en: '1 Hour',   weight: 2 },
  '4h':   { ar: '4 ساعات',   en: '4 Hours',  weight: 3 },
  '1day': { ar: 'يومي',       en: 'Daily',    weight: 4 },
}

export default function ConfluenceModal({ symbol, onClose }) {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const [results, setResults] = useState({})
  const [loading, setLoading] = useState(false)
  const [analyzed, setAnalyzed] = useState(false)

  const runAnalysis = async () => {
    setLoading(true)
    try {
      const calls = TIMEFRAMES.map(tf =>
        axios.post(`${API}/api/v1/signals/analyze?symbol=${symbol}&timeframe=${tf}&advanced_mode=true`)
          .then(r => [tf, r.data.data])
          .catch(() => [tf, null])
      )
      const pairs = await Promise.all(calls)
      setResults(Object.fromEntries(pairs))
      setAnalyzed(true)
    } catch {}
    setLoading(false)
  }

  // Weighted confluence score
  const scored = TIMEFRAMES.map(tf => {
    const d   = results[tf]
    const rec = d?.recommendation || d?.signal_type || 'NONE'
    const w   = TF_META[tf].weight
    return { tf, rec, conf: d?.ai_confidence_score || d?.ai_confidence || 0, weight: w }
  })

  const weightedBuy  = scored.filter(s => s.rec === 'BUY').reduce((a, s) => a + s.weight, 0)
  const weightedSell = scored.filter(s => s.rec === 'SELL').reduce((a, s) => a + s.weight, 0)
  const totalWeight  = scored.reduce((a, s) => a + s.weight, 0)
  const overallRec   = weightedBuy > weightedSell ? 'BUY' : weightedSell > weightedBuy ? 'SELL' : 'NEUTRAL'
  const confPct      = totalWeight > 0 ? Math.round(Math.max(weightedBuy, weightedSell) / totalWeight * 100) : 0

  const strengthLabel = confPct >= 80
    ? { ar: 'قوي جداً ⭐', en: 'Very Strong ⭐' }
    : confPct >= 60
    ? { ar: 'متوسط',      en: 'Moderate' }
    : { ar: 'ضعيف / تعارض', en: 'Weak / Conflicted' }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[#0d1420] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/8">
          <div>
            <h3 className="font-bold text-white text-base">
              {symbol}
              <span className="text-gray-500 font-normal ms-2 text-sm">
                {isAr ? '— تحليل متعدد الفريمات' : '— Multi-TF Confluence'}
              </span>
            </h3>
            <p className="text-xs text-gray-600 mt-0.5">
              {isAr ? '4 فريمات مرجّحة · كلما ارتفع الفريم زاد وزنه' : '4 weighted timeframes · higher TF = more weight'}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white p-1 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {!analyzed ? (
            /* Pre-analysis state */
            <div className="text-center py-8 space-y-4">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                <Zap size={28} className="text-blue-400" />
              </div>
              <div>
                <p className="text-white font-semibold">{isAr ? 'تحليل شامل لـ' : 'Full analysis for'} {symbol}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {isAr
                    ? 'يحلل السوق على 4 فريمات ويحسب قوة التوافق المرجّح'
                    : 'Analyzes across 4 timeframes with weighted confluence scoring'}
                </p>
              </div>
              <button
                onClick={runAnalysis}
                className="flex items-center gap-2 mx-auto bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-7 py-2.5 rounded-xl font-semibold text-sm transition-all"
              >
                <Zap size={15} />
                {isAr ? 'بدء التحليل' : 'Start Analysis'}
              </button>
            </div>
          ) : loading ? (
            <div className="py-10 flex flex-col items-center gap-3">
              <RefreshCw size={24} className="animate-spin text-blue-400" />
              <p className="text-gray-400 text-sm">{isAr ? 'جاري تحليل 4 فريمات...' : 'Analyzing 4 timeframes...'}</p>
            </div>
          ) : (
            <>
              {/* Overall Confluence Card */}
              <div className={`rounded-2xl p-4 border text-center ${
                overallRec === 'BUY'
                  ? 'bg-green-500/10 border-green-500/30'
                  : overallRec === 'SELL'
                  ? 'bg-red-500/10 border-red-500/30'
                  : 'bg-gray-800/60 border-gray-700/40'
              }`}>
                <div className={`text-3xl font-black mb-1 ${
                  overallRec === 'BUY' ? 'text-green-400' : overallRec === 'SELL' ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {overallRec === 'BUY' ? '🟢 ' : overallRec === 'SELL' ? '🔴 ' : '⚪ '}
                  {isAr
                    ? (overallRec === 'BUY' ? 'شراء' : overallRec === 'SELL' ? 'بيع' : 'تعارض')
                    : overallRec}
                </div>

                {/* Confluence bar */}
                <div className="flex items-center justify-center gap-2 mb-2">
                  <div className="w-32 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        overallRec === 'BUY' ? 'bg-green-500' : overallRec === 'SELL' ? 'bg-red-500' : 'bg-gray-500'
                      }`}
                      style={{ width: `${confPct}%` }}
                    />
                  </div>
                  <span className={`text-sm font-bold ${
                    overallRec === 'BUY' ? 'text-green-400' : overallRec === 'SELL' ? 'text-red-400' : 'text-gray-400'
                  }`}>{confPct}%</span>
                </div>

                <p className="text-xs text-gray-400">
                  {isAr ? strengthLabel.ar : strengthLabel.en}
                </p>
              </div>

              {/* Per-timeframe breakdown */}
              <div className="space-y-2">
                {TIMEFRAMES.map(tf => {
                  const d    = results[tf]
                  const rec  = d?.recommendation || d?.signal_type || 'N/A'
                  const conf = d?.ai_confidence_score || d?.ai_confidence || 0
                  const isBuy  = rec === 'BUY'
                  const isSell = rec === 'SELL'
                  const Icon = isBuy ? TrendingUp : isSell ? TrendingDown : Minus

                  return (
                    <div key={tf} className="flex items-center gap-3 bg-gray-800/40 rounded-xl px-4 py-3">
                      {/* TF label */}
                      <div className="w-16 flex-shrink-0">
                        <div className="text-xs font-bold text-white">{TF_META[tf]?.[isAr ? 'ar' : 'en']}</div>
                        <div className="text-[10px] text-gray-600">w={TF_META[tf].weight}</div>
                      </div>

                      {/* Conf bar */}
                      <div className="flex-1 flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              isBuy ? 'bg-green-500' : isSell ? 'bg-red-500' : 'bg-gray-600'
                            }`}
                            style={{ width: `${conf}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-8 text-right">{conf > 0 ? `${Math.round(conf)}%` : '—'}</span>
                      </div>

                      {/* Signal badge */}
                      <div className={`flex items-center gap-1.5 text-xs font-bold flex-shrink-0 px-2.5 py-1 rounded-lg ${
                        isBuy  ? 'bg-green-500/15 text-green-400' :
                        isSell ? 'bg-red-500/15 text-red-400' :
                        'bg-gray-700/40 text-gray-500'
                      }`}>
                        <Icon size={11} />
                        {isAr
                          ? (isBuy ? 'شراء' : isSell ? 'بيع' : 'راقب')
                          : rec}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Re-analyze */}
              <button
                onClick={runAnalysis}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-gray-500 hover:text-white hover:bg-white/5 rounded-xl transition-colors border border-white/5 hover:border-white/10"
              >
                <RefreshCw size={13} />
                {isAr ? 'إعادة التحليل' : 'Re-analyze'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
