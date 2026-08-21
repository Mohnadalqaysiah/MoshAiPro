/**
 * EconomicCalendar — تقويم الأخبار الاقتصادية الأسبوعية
 * بيانات ثابتة (لا تحتاج API خارجي)، تُحدَّث كل أسبوع يدوياً أو آلياً مستقبلاً.
 * تعرض: الخبر، التوقيت، التأثير المتوقع، والسوق المتأثر.
 */
import { useLang } from '../contexts/LangContext'
import { AlertTriangle, Calendar, Clock, TrendingUp } from 'lucide-react'

// ── Static weekly events (UTC times) ────────────────────────────────────────
// impact: 'high' | 'medium' | 'low'
const WEEKLY_EVENTS = [
  // الاثنين
  { day: 1, utcH: 8,  utcM: 55, impact: 'medium', currency: '🇩🇪 EUR',
    nameAr: 'مؤشر IFO الألماني',          nameEn: 'German IFO Business Climate',
    affectAr: 'يورو/دولار',               affectEn: 'EUR/USD' },
  // الثلاثاء
  { day: 2, utcH: 12, utcM: 30, impact: 'high',   currency: '🇺🇸 USD',
    nameAr: 'مؤشر أسعار المستهلك CPI',   nameEn: 'US CPI Inflation',
    affectAr: 'الذهب، USD',               affectEn: 'Gold, USD pairs' },
  // الأربعاء
  { day: 3, utcH: 14, utcM: 30, impact: 'medium', currency: '🇺🇸 USD',
    nameAr: 'مخزونات النفط الخام',        nameEn: 'Crude Oil Inventories',
    affectAr: 'نفط، USD',                 affectEn: 'Oil, USD' },
  { day: 3, utcH: 18, utcM: 0,  impact: 'high',   currency: '🇺🇸 USD',
    nameAr: 'قرار الفيدرالي / FOMC',      nameEn: 'FOMC / Fed Rate Decision',
    affectAr: 'جميع الأسواق',             affectEn: 'All markets' },
  // الخميس
  { day: 4, utcH: 12, utcM: 30, impact: 'medium', currency: '🇺🇸 USD',
    nameAr: 'طلبات إعانة البطالة',        nameEn: 'Jobless Claims',
    affectAr: 'USD، الذهب',               affectEn: 'USD, Gold' },
  { day: 4, utcH: 11, utcM: 45, impact: 'medium', currency: '🇪🇺 EUR',
    nameAr: 'قرار الفائدة الأوروبي ECB',  nameEn: 'ECB Interest Rate Decision',
    affectAr: 'يورو، جنيه',               affectEn: 'EUR, GBP' },
  // الجمعة
  { day: 5, utcH: 12, utcM: 30, impact: 'high',   currency: '🇺🇸 USD',
    nameAr: 'وظائف غير الزراعية NFP',     nameEn: 'Non-Farm Payrolls (NFP)',
    affectAr: 'الذهب، USD، كل الأسواق',  affectEn: 'Gold, USD, all markets' },
  { day: 5, utcH: 14, utcM: 0,  impact: 'medium', currency: '🇺🇸 USD',
    nameAr: 'ثقة المستهلك الأمريكي',      nameEn: 'US Consumer Sentiment',
    affectAr: 'USD',                       affectEn: 'USD' },
]

const DAY_NAMES_AR = ['', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', '', '']
const DAY_NAMES_EN = ['', 'Monday',  'Tuesday',  'Wednesday', 'Thursday', 'Friday',  '', '']

const IMPACT_CFG = {
  high:   { label: { ar: 'عالي',   en: 'High'   }, cls: 'bg-red-500/20 text-red-300 border-red-500/30' },
  medium: { label: { ar: 'متوسط', en: 'Medium' }, cls: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30' },
  low:    { label: { ar: 'منخفض', en: 'Low'   }, cls: 'bg-gray-500/15 text-gray-400 border-gray-500/20' },
}

function fmtUTC(h, m) {
  const pad = n => String(n).padStart(2, '0')
  // Convert UTC → Arabia Standard Time (UTC+3)
  const localH = (h + 3) % 24
  return `${pad(localH)}:${pad(m)}`
}

export default function EconomicCalendar() {
  const { lang } = useLang()
  const isAr = lang === 'ar'

  // Get today's weekday (1=Mon … 5=Fri)
  const now     = new Date()
  const todayWD = now.getDay() === 0 ? 7 : now.getDay()  // Sun=7, Mon=1

  // Group events by day, only Mon–Fri
  const days = [1, 2, 3, 4, 5]
  const grouped = days.map(d => ({
    day:    d,
    label:  isAr ? DAY_NAMES_AR[d] : DAY_NAMES_EN[d],
    today:  d === todayWD,
    events: WEEKLY_EVENTS.filter(e => e.day === d)
                          .sort((a, b) => a.utcH * 60 + a.utcM - (b.utcH * 60 + b.utcM)),
  }))

  return (
    <div className="bg-gray-900/60 border border-white/8 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/6">
        <div className="w-8 h-8 rounded-lg bg-yellow-500/15 flex items-center justify-center">
          <Calendar size={15} className="text-yellow-400" />
        </div>
        <div>
          <h3 className="font-bold text-white text-sm">
            {isAr ? 'التقويم الاقتصادي' : 'Economic Calendar'}
          </h3>
          <p className="text-xs text-gray-500">
            {isAr ? 'أخبار هذا الأسبوع — بتوقيت الرياض (AST)' : 'This week\'s events — Riyadh time (AST)'}
          </p>
        </div>
        <div className="ms-auto flex items-center gap-1.5 text-xs text-gray-400">
          <Clock size={11} />
          {isAr ? 'UTC+3' : 'UTC+3'}
        </div>
      </div>

      <div className="divide-y divide-white/4">
        {grouped.map(({ day, label, today, events }) => (
          <div key={day}
            className={`px-5 py-3 ${today ? 'bg-blue-950/20' : ''}`}>
            {/* Day label */}
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs font-bold ${today ? 'text-blue-400' : 'text-gray-500'}`}>
                {label}
              </span>
              {today && (
                <span className="text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded-full">
                  {isAr ? 'اليوم' : 'Today'}
                </span>
              )}
            </div>

            {/* Events */}
            {events.length === 0 ? (
              <p className="text-xs text-gray-700 ps-1">
                {isAr ? 'لا أخبار مهمة' : 'No major events'}
              </p>
            ) : (
              <div className="space-y-2">
                {events.map((ev, i) => {
                  const cfg = IMPACT_CFG[ev.impact]
                  return (
                    <div key={i}
                      className="flex items-start gap-3 rounded-xl p-2.5 hover:bg-white/3 transition-colors">
                      {/* Impact dot */}
                      <div className={`mt-0.5 flex-shrink-0 w-1.5 h-1.5 rounded-full ${
                        ev.impact === 'high' ? 'bg-red-400' :
                        ev.impact === 'medium' ? 'bg-yellow-400' : 'bg-gray-500'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-0.5">
                          <span className="text-white text-xs font-semibold truncate">
                            {isAr ? ev.nameAr : ev.nameEn}
                          </span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-md border font-medium ${cfg.cls}`}>
                            {cfg.label[lang] || cfg.label.en}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-gray-500">
                          <span className="flex items-center gap-1">
                            <Clock size={9} />
                            {fmtUTC(ev.utcH, ev.utcM)}
                          </span>
                          <span>{ev.currency}</span>
                          <span className="text-gray-400 truncate">
                            {isAr ? ev.affectAr : ev.affectEn}
                          </span>
                        </div>
                      </div>
                      {ev.impact === 'high' && (
                        <AlertTriangle size={13} className="text-red-400/70 flex-shrink-0 mt-0.5" />
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer note */}
      <div className="px-5 py-3 border-t border-white/5 flex items-center gap-2 text-[11px] text-gray-400">
        <TrendingUp size={11} className="text-red-400/60" />
        {isAr
          ? 'الأخبار عالية التأثير ⚫ — أغلق صفقاتك أو ضيّق الوقف قبل الإعلان'
          : 'High impact events ⚫ — close trades or tighten SL before release'}
      </div>
    </div>
  )
}
