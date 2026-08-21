/**
 * SignalScorecard — لوحة أداء الإشارات
 * نسبة الفوز لكل رمز + إجمالي المنصة
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { BarChart2, ChevronRight, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function WinBar({ pct }) {
  const color = pct >= 65 ? '#22c55e' : pct >= 50 ? '#eab308' : '#ef4444'
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-1.5 bg-gray-700/60 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-xs font-bold w-10 text-right" style={{ color }}>{pct}%</span>
    </div>
  )
}

export default function SignalScorecard() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    axios.get(`${API}/api/v1/signals/scorecard`)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl p-5 animate-pulse h-24" />
  )
  if (!data) return null

  const { scorecard = [], overall = {} } = data
  const wr = overall.win_rate

  const overallColor = wr >= 65 ? 'text-green-400' : wr >= 50 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="bg-gradient-to-br from-blue-950/40 via-gray-900/80 to-gray-950/60 border border-blue-700/25 rounded-2xl overflow-hidden" dir="rtl">

      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer select-none"
        onClick={() => setExpanded(p => !p)}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 flex items-center justify-center rounded-xl bg-blue-500/15 border border-blue-500/25">
            <BarChart2 size={16} className="text-blue-400" />
          </div>
          <div>
            <h3 className="text-white font-semibold text-sm">أداء الإشارات</h3>
            <p className="text-blue-300/60 text-xs mt-0.5">
              {overall.total || 0} إشارة · {overall.wins || 0} فوز · {overall.losses || 0} خسارة
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className={`text-xl font-bold leading-none ${overallColor}`}>
              {wr != null ? `${wr}%` : '—'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">نسبة الفوز</p>
          </div>
          <ChevronRight
            size={16}
            className={`text-gray-500 transition-transform duration-200 ${expanded ? 'rotate-90' : '-rotate-90'}`}
          />
        </div>
      </div>

      {/* شريط الفوز المضغوط */}
      {wr != null && (
        <div className="px-5 pb-4">
          <WinBar pct={wr} />
        </div>
      )}

      {/* التفاصيل الموسّعة */}
      {expanded && (
        <div className="border-t border-gray-700/40 px-5 py-4 space-y-4">

          {/* بطاقات الإحصاء العامة */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'إجمالي',  value: overall.total   || 0, color: 'text-white' },
              { label: 'فوز',     value: overall.wins    || 0, color: 'text-green-400' },
              { label: 'خسارة',   value: overall.losses  || 0, color: 'text-red-400' },
            ].map((s, i) => (
              <div key={i} className="bg-gray-800/50 rounded-xl p-3 text-center border border-gray-700/40">
                <p className={`text-lg font-bold leading-none ${s.color}`}>{s.value}</p>
                <p className="text-gray-500 text-xs mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* جدول الأداء لكل رمز */}
          {scorecard.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-gray-500 mb-2">أداء كل رمز</p>
              {scorecard.map((row) => (
                <div key={row.market} className="flex items-center gap-3 bg-gray-800/40 rounded-xl px-3 py-2.5 border border-gray-700/30">
                  <span className="text-white text-xs font-mono font-semibold w-16">{row.market}</span>
                  {row.win_rate != null
                    ? <WinBar pct={row.win_rate} />
                    : <span className="text-xs text-gray-400 flex-1">لا توجد نتائج بعد</span>}
                  <div className="flex items-center gap-1 text-xs w-16 justify-end">
                    <span className="text-green-400">{row.wins}W</span>
                    <span className="text-gray-400">/</span>
                    <span className="text-red-400">{row.losses}L</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-500 text-sm py-2">لا توجد إشارات مكتملة بعد</p>
          )}

          <p className="text-center text-gray-400 text-xs">
            * يحتسب فقط الإشارات التي أُغلقت (TP/SL)
          </p>
        </div>
      )}
    </div>
  )
}
