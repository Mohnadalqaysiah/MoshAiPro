import { useState, useEffect } from 'react'
import axios from 'axios'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Activity, BarChart2, ChevronDown, Settings2 } from 'lucide-react'
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
    rolling30: 'متوسط آخر {n} يوم',
    winRate: 'نسبة النجاح',
    expectancy: 'العائد المتوقع لكل قرار',
    thisWeekInline: 'الأسبوع الحالي',
    decisions: 'قرار',
    collecting: 'قيد جمع بيانات كافية',
    collectingProgress: '{count} من {min} قرار',
    beforeJoin: 'قبل اشتراكك',
    allSymbols: 'أداء كل الرموز',
    yourSymbols: 'أداء رموزك المختارة',
    editSymbols: 'تعديل',
    activeTradesNote: '+ {n} إشارة مفتوحة لسا ما تحققت نتيجتها',
    netResult: 'صافي النتيجة',
    riskUnits: 'ضعف المخاطرة',
    perRisk: 'لو خاطرت بـ100$ في كل صفقة: {v}$',
    payoff: 'الصفقة الرابحة',
    payoffVal: '{x}× الخاسرة',
    tp2Hits: 'وصلت للهدف الثاني',
    whyProfit: 'نسبة النجاح وحدها لا تحكم: متوسط الصفقة الرابحة يساوي {x} أضعاف الخاسرة، لذلك تبقى النتيجة الصافية {sign} رغم أن الرابحة أقل عدداً.',
    disclaimer: 'محسوبة على كل الإشارات المرسلة بمخاطرة ثابتة لكل صفقة، قبل السبريد والعمولة. الأداء السابق لا يضمن المستقبل.',
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
    rolling30: 'Rolling {n}-Day Average',
    winRate: 'Win Rate',
    expectancy: 'Expectancy / Decision',
    thisWeekInline: 'Current Week',
    decisions: 'decisions',
    collecting: 'Collecting Enough Data',
    collectingProgress: '{count} of {min} decisions',
    beforeJoin: 'Before you joined',
    allSymbols: 'Performance across all symbols',
    yourSymbols: 'Performance for your selected symbols',
    editSymbols: 'Edit',
    activeTradesNote: '+ {n} signal(s) still open, not yet resolved',
    netResult: 'Net Result',
    riskUnits: 'x risk',
    perRisk: 'Risking $100 per trade: {v}$',
    payoff: 'Average Win',
    payoffVal: '{x}× the loss',
    tp2Hits: 'Reached TP2',
    whyProfit: 'Win rate alone doesn’t decide it: the average win is {x}× the average loss, so the net result stays {sign} even with fewer winners.',
    disclaimer: 'Computed over every signal sent, fixed risk per trade, before spread and commission. Past performance does not guarantee future results.',
  },
}

export default function PerformanceSection() {
  const { lang } = useLang()
  const tx = T[lang] || T.ar
  const isAr = lang === 'ar'

  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [tradesLimit, setTradesLimit] = useState(10)

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

  const { current_week, rolling_30d, daily_stats, weekly_stats, watchlist_filter } = data
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
  const allRecentTrades = daily_stats.flatMap(d => d.trades_detail)

  return (
    <div className="space-y-4" dir={isAr ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <BarChart2 size={20} className="text-blue-400" />
          <h2 className="text-white font-semibold text-lg">{tx.title}</h2>
        </div>
        <Link
          to="/profile#watchlist"
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white q-glass px-3 py-1.5 rounded-full transition-colors"
        >
          <span>
            {watchlist_filter?.length > 0
              ? `${tx.yourSymbols} (${watchlist_filter.join('، ')})`
              : tx.allSymbols}
          </span>
          <Settings2 size={12} />
        </Link>
      </div>

      {/* 30-Day Rolling Headline — leads with the fairer, less volatile number.
          Below min_decisions the sample itself is too small to be a fair
          number (same volatility problem we're trying to avoid), so we show
          a "collecting data" state instead — same real counts, no misleading
          win-rate/expectancy headline yet. */}
      {rolling_30d && (
        rolling_30d.sufficient_data ? (
          <div className={`border rounded-xl p-5 ${ptBg(rolling_30d.total_points)}`}>
            <div className="text-xs text-gray-400 mb-1">
              {tx.rolling30.replace('{n}', Math.max(0, Math.round(rolling_30d.window_days ?? 30)))}
              {' '}({rolling_30d.total_trades} {tx.decisions})
            </div>
            {/* (2026-10-10) الأرقام البارزة بمضاعف المخاطرة R لا بالنقاط — "العائد
                لكل قرار" بالنقاط كان يخلط الذهب بالغاز (فارق المضاعف 1200 ضعف)
                فلا معنى له. نسبة النجاح وحدها (~34%) توحي بخسارة بينما المنصة
                رابحة لأن الرابحة أكبر بأضعاف — نعرض الصورة كاملة بأرقام حقيقية. */}
            <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
              <div>
                <div className="text-[11px] text-gray-500 mb-0.5">{tx.netResult}</div>
                <div className={`text-3xl font-bold ${ptColor(rolling_30d.net_r)}`}>
                  {rolling_30d.net_r > 0 ? '+' : ''}{rolling_30d.net_r}
                  <span className="text-sm font-medium text-gray-400"> {tx.riskUnits}</span>
                </div>
                <div className="text-[11px] text-gray-400 mt-0.5">
                  {tx.perRisk.replace('{v}', `${rolling_30d.net_r > 0 ? '+' : ''}${Math.round(rolling_30d.net_r * 100).toLocaleString()}`)}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-gray-500 mb-0.5">{tx.winRate}</div>
                <div className="text-2xl font-semibold text-white">{rolling_30d.win_rate}%</div>
              </div>
              {rolling_30d.avg_win_r > 0 && (
                <div>
                  <div className="text-[11px] text-gray-500 mb-0.5">{tx.payoff}</div>
                  <div className="text-2xl font-semibold text-green-400">
                    {tx.payoffVal.replace('{x}', rolling_30d.avg_win_r)}
                  </div>
                </div>
              )}
              <div>
                <div className="text-[11px] text-gray-500 mb-0.5">{tx.tp2Hits}</div>
                <div className="text-2xl font-semibold text-purple-300">{rolling_30d.tp2_hits}</div>
              </div>
            </div>
            {rolling_30d.avg_win_r > 0 && (
              <p className="text-[12px] text-gray-400 mt-3 leading-relaxed">
                {tx.whyProfit
                  .replace('{x}', rolling_30d.avg_win_r)
                  .replace('{sign}', rolling_30d.net_r >= 0 ? (isAr ? 'موجبة' : 'positive') : (isAr ? 'سالبة' : 'negative'))}
              </p>
            )}
            <div className="flex gap-6 mt-3 text-sm">
              <div>
                <span className="text-gray-400">{tx.wins}: </span>
                <span className="text-green-400 font-semibold">{rolling_30d.wins}</span>
              </div>
              <div>
                <span className="text-gray-400">{tx.losses}: </span>
                <span className="text-red-400 font-semibold">{rolling_30d.losses}</span>
              </div>
            </div>
            <p className="text-[10px] text-gray-500 mt-2">{tx.disclaimer}</p>
          </div>
        ) : (
          <div className="border border-gray-700 bg-gray-800 rounded-xl p-5">
            <div className="flex items-center gap-2 text-white font-semibold mb-2">
              <Activity size={16} className="text-blue-400" />
              {tx.collecting}
            </div>
            <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden mb-2">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${Math.min(100, (rolling_30d.total_trades / rolling_30d.min_decisions) * 100)}%` }}
              />
            </div>
            <div className="text-xs text-gray-400">
              {tx.collectingProgress
                .replace('{count}', rolling_30d.total_trades)
                .replace('{min}', rolling_30d.min_decisions)}
            </div>
          </div>
        )
      )}

      {/* Weekly Stats Table — current week's total now lives here (inline), not as the page headline */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h3 className="text-white font-medium mb-3 flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-400" />
          {tx.weeklyPerf}
        </h3>
        <div className="flex items-center justify-between mb-1 pb-3 border-b border-gray-700/60">
          <div className="text-xs text-gray-400">{tx.thisWeekInline} — {current_week.week_label}</div>
          <div className="flex items-center gap-3">
            {/* (2026-10-03) نسبة الربح % صارت الرقم البارز — مقارنة عادلة
                بين كل الرموز (راجع DECISIONS.md: النقاط فارق مضاعفها
                1200 ضعف بين الرموز). النقاط تبقى تفصيلاً ثانوياً بعدها. */}
            {/* (2026-10-10) اللون من صافي النتيجة لا من نسبة النجاح ≥50% — أسبوع
                رابح بنسبة 35% كان يظهر أحمر */}
            <span className="text-sm font-bold font-mono text-gray-200">
              {current_week.win_rate}% <span className="font-normal text-gray-500">({current_week.wins}/{current_week.total_trades})</span>
            </span>
            <span className={`text-sm font-semibold ${ptColor(current_week.net_r)}`}>
              {current_week.net_r > 0 ? '+' : ''}{current_week.net_r} {tx.riskUnits}
            </span>
          </div>
        </div>
        {current_week.active_trades > 0 && (
          <div className="text-[11px] text-indigo-400 mb-3 -mt-2">
            {tx.activeTradesNote.replace('{n}', current_week.active_trades)}
          </div>
        )}
        {(() => {
          // مشترك جديد ما لازم يشوف أسابيع قبل ما ينضم — لا حتى كـ"0
          // صفقات" (بيوحي غلط إنه ما كان في نشاط، بينما النظام كان شغال)
          const visibleWeeks = weekly_stats.filter(w => !w.before_join)
          if (visibleWeeks.filter(w => w.total_trades > 0).length === 0) {
            return <p className="text-gray-500 text-sm text-center py-4">{tx.noData}</p>
          }
          // (2026-10-10) الأعمدة بصافي R لا بالنقاط — أسبوع ذهب يطغى بالنقاط على
          // أسبوع كريبتو أفضل منه فعلاً
          const maxR = Math.max(...visibleWeeks.map(x => Math.abs(x.net_r || 0)), 1)
          return (
          <div className="space-y-2">
            {visibleWeeks.map((w, i) => {
              const barPct = Math.min(100, (Math.abs(w.net_r || 0) / maxR) * 100)
              return (
                <div key={i} className="flex items-center gap-3">
                  <div className="text-xs text-gray-400 w-16 flex-shrink-0 text-left ltr:text-left rtl:text-right">{w.week}</div>
                  <div className="flex-1 h-5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${(w.net_r || 0) >= 0 ? 'bg-green-600' : 'bg-red-600'}`}
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                  <div className={`text-xs font-mono w-20 text-right ${ptColor(w.net_r || 0)}`}>
                    {(w.net_r || 0) > 0 ? '+' : ''}{w.net_r || 0} R
                  </div>
                  <div className="text-xs text-gray-500 w-16 text-right">{w.total_trades} {tx.trades}</div>
                </div>
              )
            })}
          </div>
          )
        })()}
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
      {allRecentTrades.length > 0 && (
        <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700/60">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <TrendingDown size={15} className="text-yellow-400" />
              {tx.recentTrades}
              <span className="text-xs text-gray-500 font-normal">({allRecentTrades.length})</span>
            </h3>
          </div>

          <div className="divide-y divide-gray-700/40">
            {allRecentTrades.slice(0, tradesLimit).map((t, i) => {
              const st  = statusLabel(t.status)
              const ty  = typeLabel(t.type)
              const isWin  = t.status === 'TP1_HIT' || t.status === 'TP2_HIT'
              const isLoss = t.status === 'SL_HIT'
              const accentBar = isWin ? 'bg-green-500' : isLoss ? 'bg-red-500' : 'bg-gray-600'
              const ptsBadge  = isWin
                ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                : isLoss
                ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                : 'bg-gray-600/30 text-gray-400 border border-gray-600/30'

              return (
                <div key={i} className="flex items-center gap-0 hover:bg-gray-700/20 transition-colors">
                  <div className={`w-1 self-stretch flex-shrink-0 ${accentBar} opacity-60`} />
                  <div className="flex-1 flex items-center justify-between gap-3 px-4 py-2.5 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-bold text-sm">{t.market}</span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ty.cls}`}>{ty.label}</span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span>
                    </div>
                    <span className={`text-sm font-bold font-mono px-2.5 py-0.5 rounded-full ${ptsBadge}`}>
                      {t.points > 0 ? '+' : ''}{t.points} {tx.points}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {allRecentTrades.length > tradesLimit && (
            <button
              onClick={() => setTradesLimit(l => l + 10)}
              className="w-full py-3 text-sm text-gray-400 hover:text-white hover:bg-gray-700/30 transition-colors flex items-center justify-center gap-2 border-t border-gray-700/60"
            >
              <ChevronDown size={15} />
              {isAr
                ? `عرض المزيد (${allRecentTrades.length - tradesLimit} متبقية)`
                : `Show more (${allRecentTrades.length - tradesLimit} remaining)`}
            </button>
          )}
          {tradesLimit > 10 && allRecentTrades.length <= tradesLimit && (
            <p className="py-3 text-center text-xs text-gray-400 border-t border-gray-700/40">
              {isAr ? `تم عرض جميع الصفقات (${allRecentTrades.length})` : `All trades shown (${allRecentTrades.length})`}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
