/**
 * EconomicCalendar — تقويم الأخبار الاقتصادية للأسبوع الحالي
 *
 * (2026-11-09) كان قائمة ثابتة تتكرر كل أسبوع: FOMC كل أربعاء، NFP كل جمعة، CPI كل ثلاثاء، ECB كل خميس…
 * والحقيقي شهري أو أندر. وساعاتها ثابتة بـUTC فتنزاح ساعة في شتاء نيويورك. نفس خطأ تحذيرات البوت
 * (telegram-bot/econ_calendar.py) — المنطق هنا مطابق له:
 *   - الأسبوعي حقاً: مخزونات النفط (الأربعاء 10:30 نيويورك) وطلبات إعانة البطالة (الخميس 08:30 نيويورك).
 *   - NFP: أول جمعة بالشهر 08:30 نيويورك.
 *   - CPI وFOMC: فقط بتاريخ مكتوب في DATED_EVENTS (نسخة من EXTRA_EVENTS بالبوت — حدّث الاثنين معاً).
 *   - IFO وECB وثقة المستهلك حُذفت: لا تاريخ رسمي مكتوب لها، ولا نخترع مواعيد.
 */
import { useLang } from '../contexts/LangContext'
import { AlertTriangle, Calendar, Clock, TrendingUp } from 'lucide-react'

const TZ = 'Asia/Riyadh'

const EVENT_INFO = {
  CPI:    { impact: 'high', currency: '🇺🇸 USD',
            nameAr: 'مؤشر أسعار المستهلك CPI', nameEn: 'US CPI Inflation',
            affectAr: 'الذهب، USD', affectEn: 'Gold, USD pairs' },
  FOMC:   { impact: 'high', currency: '🇺🇸 USD',
            nameAr: 'قرار الفيدرالي / FOMC', nameEn: 'FOMC / Fed Rate Decision',
            affectAr: 'جميع الأسواق', affectEn: 'All markets' },
  NFP:    { impact: 'high', currency: '🇺🇸 USD',
            nameAr: 'وظائف غير الزراعية NFP', nameEn: 'Non-Farm Payrolls (NFP)',
            affectAr: 'الذهب، USD، كل الأسواق', affectEn: 'Gold, USD, all markets' },
  CRUDE:  { impact: 'medium', currency: '🇺🇸 USD',
            nameAr: 'مخزونات النفط الخام', nameEn: 'Crude Oil Inventories',
            affectAr: 'نفط، USD', affectEn: 'Oil, USD' },
  CLAIMS: { impact: 'medium', currency: '🇺🇸 USD',
            nameAr: 'طلبات إعانة البطالة', nameEn: 'Jobless Claims',
            affectAr: 'USD، الذهب', affectEn: 'USD, Gold' },
}

// مواعيد رسمية بتوقيت UTC — مطابقة لـ EXTRA_EVENTS في telegram-bot/econ_calendar.py
export const DATED_EVENTS = [
  ['CPI',  '2026-11-10T13:30:00Z'],   // تضخم أكتوبر
  ['FOMC', '2026-12-09T19:00:00Z'],   // قرار الفائدة
  ['CPI',  '2026-12-10T13:30:00Z'],   // تضخم نوفمبر
]

const DAY_MS = 86400000

function nthSundayUTC(year, month, n) {           // month 0-based
  const first = new Date(Date.UTC(year, month, 1))
  const add = (7 - first.getUTCDay()) % 7
  return Date.UTC(year, month, 1 + add + (n - 1) * 7)
}

// فرق نيويورك عن UTC: 4 صيفاً (من ثاني أحد بمارس) و5 شتاءً (من أول أحد بنوفمبر)
function nyOffset(y, m, d) {
  const t = Date.UTC(y, m, d)
  return t >= nthSundayUTC(y, 2, 2) && t < nthSundayUTC(y, 10, 1) ? 4 : 5
}

function nyTime(y, m, d, h, min) {
  return new Date(Date.UTC(y, m, d, h + nyOffset(y, m, d), min))
}

function firstFriday(y, m) {
  const wd = new Date(Date.UTC(y, m, 1)).getUTCDay()
  return 1 + ((5 - wd + 7) % 7)
}

// اليوم الحالي بتوقيت الرياض كتاريخ (سنة، شهر، يوم، يوم الأسبوع)
function riyadhParts(date) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: TZ, year: 'numeric', month: 'numeric', day: 'numeric',
  }).formatToParts(date).map(x => [x.type, x.value]))
  const y = +p.year, m = +p.month - 1, d = +p.day
  return { y, m, d, wd: new Date(Date.UTC(y, m, d)).getUTCDay() }
}

// أحداث أسبوع (الاثنين–الجمعة) بتوقيت الرياض. بالسبت والأحد يُعرض الأسبوع القادم.
export function weekEvents(now = new Date()) {
  const { y, m, d, wd } = riyadhParts(now)
  const toMon = wd === 0 ? 1 : wd === 6 ? 2 : 1 - wd
  const monday = Date.UTC(y, m, d + toMon)
  const days = [0, 1, 2, 3, 4].map(i => {
    const dt = new Date(monday + i * DAY_MS)
    return { y: dt.getUTCFullYear(), m: dt.getUTCMonth(), d: dt.getUTCDate(), wd: i + 1,
             key: dt.toISOString().slice(0, 10), events: [] }
  })
  const dayOf = t => {
    const r = riyadhParts(t)
    return days.find(x => x.y === r.y && x.m === r.m && x.d === r.d)
  }
  const add = (kind, t) => { const day = dayOf(t); if (day) day.events.push({ kind, t, ...EVENT_INFO[kind] }) }

  for (const day of days) {
    if (day.wd === 3) add('CRUDE', nyTime(day.y, day.m, day.d, 10, 30))
    if (day.wd === 4) add('CLAIMS', nyTime(day.y, day.m, day.d, 8, 30))
    if (day.wd === 5 && day.d === firstFriday(day.y, day.m)) add('NFP', nyTime(day.y, day.m, day.d, 8, 30))
  }
  for (const [kind, iso] of DATED_EVENTS) add(kind, new Date(iso))
  for (const day of days) day.events.sort((a, b) => a.t - b.t)
  return { days, nextWeek: wd === 0 || wd === 6, todayKey: `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}` }
}

const IMPACT_CFG = {
  high:   { label: { ar: 'عالي',   en: 'High'   }, cls: 'bg-red-500/20 text-red-300 border-red-500/30' },
  medium: { label: { ar: 'متوسط', en: 'Medium' }, cls: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30' },
  low:    { label: { ar: 'منخفض', en: 'Low'   }, cls: 'bg-gray-500/15 text-gray-400 border-gray-500/20' },
}

const fmtTime = t => new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false }).format(t)

function fmtDay(day, isAr) {
  const dt = new Date(Date.UTC(day.y, day.m, day.d, 12))
  return new Intl.DateTimeFormat(isAr ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-GB',
    { timeZone: 'UTC', weekday: 'long', day: 'numeric', month: 'long' }).format(dt)
}

export default function EconomicCalendar() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const { days, nextWeek, todayKey } = weekEvents()

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
            {nextWeek
              ? (isAr ? 'أخبار الأسبوع القادم — بتوقيت الرياض (AST)' : 'Next week\'s events — Riyadh time (AST)')
              : (isAr ? 'أخبار هذا الأسبوع — بتوقيت الرياض (AST)' : 'This week\'s events — Riyadh time (AST)')}
          </p>
        </div>
        <div className="ms-auto flex items-center gap-1.5 text-xs text-gray-400">
          <Clock size={11} />
          UTC+3
        </div>
      </div>

      <div className="divide-y divide-white/4">
        {days.map(day => {
          const today = day.key === todayKey
          return (
            <div key={day.key}
              className={`px-5 py-3 ${today ? 'bg-blue-950/20' : ''}`}>
              {/* Day label */}
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs font-bold ${today ? 'text-blue-400' : 'text-gray-500'}`}>
                  {fmtDay(day, isAr)}
                </span>
                {today && (
                  <span className="text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded-full">
                    {isAr ? 'اليوم' : 'Today'}
                  </span>
                )}
              </div>

              {/* Events */}
              {day.events.length === 0 ? (
                <p className="text-xs text-gray-700 ps-1">
                  {isAr ? 'لا أخبار مهمة' : 'No major events'}
                </p>
              ) : (
                <div className="space-y-2">
                  {day.events.map(ev => {
                    const cfg = IMPACT_CFG[ev.impact]
                    return (
                      <div key={ev.kind + ev.t.getTime()}
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
                              {fmtTime(ev.t)}
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
          )
        })}
      </div>

      {/* Footer note */}
      <div className="px-5 py-3 border-t border-white/5 flex items-center gap-2 text-[11px] text-gray-400">
        <TrendingUp size={11} className="text-red-400/60" />
        {isAr
          ? 'الأخبار عالية التأثير 🔴 — أغلق صفقاتك أو ضيّق الوقف قبل الإعلان'
          : 'High impact events 🔴 — close trades or tighten SL before release'}
      </div>
    </div>
  )
}
