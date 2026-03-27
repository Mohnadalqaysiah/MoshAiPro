import { useState, useEffect } from 'react'
import axios from 'axios'
import { TrendingUp, TrendingDown, Activity, BarChart2 } from 'lucide-react'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const T = {
  ar: {
    title: 'أداء الإشارات',
    thisWeek: 'هذا الأسبوع',
    points: 'نقطة',
    wins: 'صفقات رابحة',
    losses: 'صفقات خاسرة',
    trades: 'صفقات',
    weeklyPerf: 'الأداء الأسبوعي',
    dailyPerf: 'الأداء اليومي (آخر 14 يوم)',
    week: 'الأسبوع',
    totalPts: 'إجمالي النقاط',
    noData: 'لا توجد بيانات أداء بعد',
    buy: 'شراء',
    sell: 'بيع',
    tp1: 'TP1',
    tp2: 'TP2',
    sl: 'SL',
    recentTrades: 'آخر الصفقات المغلقة',
  },
  en: {
    title: 'Signal Performance',
    thisWeek: 'This Week',
    points: 'pts',
    wins: 'Winning Trades',
    losses: 'Losing Trades',
    trades: 'Trades',
    weeklyPerf: 'Weekly Performance',
    dailyPerf: 'Daily Performance (Last 14 Days)',
    week: 'Week',
    totalPts: 'Total Points',
    noData: 'No performance data yet',
    buy: 'BUY',
    sell: 'SELL',
    tp1: 'TP1',
    tp2: 'TP2',
    sl: 'SL',
    recentTrades: 'Recent Closed Trades',
  },
}

export default function PerformanceSection() {
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'

  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const r = await axios.get(`${API}/api/v1/signals/performance`)
        setData(r.data)
      } catch (e) {
        setError(e.response?.data?.detail || 'Failed to load performance')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  if (loading) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Activity size={16} className="animate-pulse" />
          {isAr ? 'جاري تحميل بيانات الأداء...' : 'Loading performance data...'}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const { current_week, daily_stats, weekly_stats } = data
  const ptColor = (pts) => pts > 0 ? 'text-green-400' : pts < 0 ? 'text-red-400' : 'text-gray-400'
  const ptBg    = (pts) => pts > 0 ? 'bg-green-900/30 border-green-800' : pts < 0 ? 'bg-red-900/30 border-red-800' : 'bg-gray-800 border-gray-700'

  const statusLabel = (status) => {
    if (status === 'TP1_HIT') return { label: tx.tp1, cls: 'bg-blue-900/50 text-blue-300' }
    if (status === 'TP2_HIT') return { label: tx.tp2, cls: 'bg-purple-900/50 text-purple-300' }
    if (status === 'SL_HIT')  return { label: tx.sl,  cls: 'bg-red-900/50 text-red-300' }
    return { label: status, cls: 'bg-gray-700 text-gray-400' }
  }

  const typeLabel = (t) => t === 'BUY'
    ? { label: tx.buy,  cls: 'bg-green-900/50 text-green-300' }
    : { label: tx.sell, cls: 'bg-red-900/50 text-red-300' }

  // Collect all closed trades from daily_stats for "recent trades"
  const recentTrades = daily_stats
    .flatMap(d => d.trades_detail)
    .slice(0, 20)

  return (
    <div className="space-y-4" dir={isAr ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <BarChart2 size={20} className="text-blue-400" />
        <h2 className="text-white font-semibold text-lg">{tx.title}</h2>
      </div>

      {/* Current Week Summary */}
      <div className={`border rounded-xl p-5 ${ptBg(current_week.total_points)}`}>
        <div className="text-xs text-gray-400 mb-1">{tx.thisWeek} — {current_week.week_label}</div>
        <div className={`text-3xl font-bold ${ptColor(current_week.total_points)}`}>
          {current_week.total_points > 0 ? '+' : ''}{current_week.total_points} {tx.points}
        </div>
        <div className="flex gap-6 mt-3 text-sm">
          <div>
            <span className="text-gray-400">{tx.wins}: </span>
            <span className="text-green-400 font-semibold">{current_week.wins}</span>
            {current_week.win_points !== 0 && (
              <span className="text-green-500 text-xs mr-1">(+{current_week.win_points} {tx.points})</span>
            )}
          </div>
          <div>
            <span className="text-gray-400">{tx.losses}: </span>
            <span className="text-red-400 font-semibold">{current_week.losses}</span>
            {current_week.loss_points !== 0 && (
              <span className="text-red-500 text-xs mr-1">({current_week.loss_points} {tx.points})</span>
            )}
          </div>
          <div>
            <span className="text-gray-400">{tx.trades}: </span>
            <span className="text-white font-semibold">{current_week.total_trades}</span>
          </div>
        </div>
      </div>

      {/* Weekly Stats Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h3 className="text-white font-medium mb-3 flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-400" />
          {tx.weeklyPerf}
        </h3>
        {weekly_stats.filter(w => w.total_trades > 0).length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-4">{tx.noData}</p>
        ) : (
          <div className="space-y-2">
            {weekly_stats.map((w, i) => {
              const maxPts = Math.max(...weekly_stats.map(x => Math.abs(x.total_points)), 1)
              const barPct = Math.min(100, (Math.abs(w.total_points) / maxPts) * 100)
              return (
                <div key={i} className="flex items-center gap-3">
                  <div className="text-xs text-gray-400 w-16 flex-shrink-0 text-left ltr:text-left rtl:text-right">{w.week}</div>
                  <div className="flex-1 h-5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${w.total_points >= 0 ? 'bg-green-600' : 'bg-red-600'}`}
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                  <div className={`text-xs font-mono w-20 text-right ${ptColor(w.total_points)}`}>
                    {w.total_points > 0 ? '+' : ''}{w.total_points}
                  </div>
                  <div className="text-xs text-gray-500 w-16 text-right">{w.total_trades} {tx.trades}</div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Daily Stats */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h3 className="text-white font-medium mb-3 flex items-center gap-2">
          <Activity size={16} className="text-purple-400" />
          {tx.dailyPerf}
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs" dir={isAr ? 'rtl' : 'ltr'}>
            <thead>
              <tr className="text-gray-400 border-b border-gray-700">
                <th className="pb-2 text-right font-medium">{isAr ? 'اليوم' : 'Date'}</th>
                <th className="pb-2 text-right font-medium">{tx.trades}</th>
                <th className="pb-2 text-right font-medium">{isAr ? 'رابح' : 'Wins'}</th>
                <th className="pb-2 text-right font-medium">{isAr ? 'خاسر' : 'Losses'}</th>
                <th className="pb-2 text-right font-medium">{tx.totalPts}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/40">
              {daily_stats.filter(d => d.trades > 0).map((d, i) => (
                <tr key={i} className="hover:bg-gray-700/20">
                  <td className="py-1.5 text-gray-300">{d.date}</td>
                  <td className="py-1.5 text-gray-300">{d.trades}</td>
                  <td className="py-1.5 text-green-400">{d.wins}</td>
                  <td className="py-1.5 text-red-400">{d.losses}</td>
                  <td className={`py-1.5 font-semibold font-mono ${ptColor(d.points)}`}>
                    {d.points > 0 ? '+' : ''}{d.points}
                  </td>
                </tr>
              ))}
              {daily_stats.filter(d => d.trades > 0).length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-gray-500">{tx.noData}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Closed Trades */}
      {recentTrades.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <h3 className="text-white font-medium mb-3 flex items-center gap-2">
            <TrendingDown size={16} className="text-yellow-400" />
            {tx.recentTrades}
          </h3>
          <div className="space-y-2">
            {recentTrades.map((t, i) => {
              const st = statusLabel(t.status)
              const ty = typeLabel(t.type)
              return (
                <div key={i} className="flex items-center justify-between bg-gray-700/30 rounded-lg px-3 py-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold text-xs">{t.market}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${ty.cls}`}>{ty.label}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${st.cls}`}>{st.label}</span>
                  </div>
                  <span className={`text-sm font-bold font-mono ${ptColor(t.points)}`}>
                    {t.points > 0 ? '+' : ''}{t.points} {tx.points}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
