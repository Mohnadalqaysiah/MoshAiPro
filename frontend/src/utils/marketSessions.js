// (2026-10-09) مصدر واحد لجلسات التداول — يقرأه SessionsClock وشريط MarketTicker
// معاً. قبلها كان لكل منهما نسخة، وكلاهما يحسب الوقت فقط بلا اليوم، فيوم
// السبت والأحد تظهر الجلسات "مفتوحة" والسوق مغلق فعلياً.
//
// الجلسات الثلاث تعمل من الاثنين للجمعة (بتوقيت UTC). سوق الفوركس يغلق
// الجمعة 21:00 UTC (نهاية جلسة نيويورك) ويعود الأحد مساءً بجلسة سيدني، وهي
// خارج هذه الجلسات الثلاث، فأول جلسة بعد العطلة = آسيا الاثنين 00:00 UTC.

export const SESSIONS = [
  { id: 'asia',   labelAr: 'آسيا',    labelEn: 'Asia',     openUTC: 0,  closeUTC: 9  },
  { id: 'london', labelAr: 'لندن',    labelEn: 'London',   openUTC: 8,  closeUTC: 16 },
  { id: 'ny',     labelAr: 'نيويورك', labelEn: 'New York', openUTC: 13, closeUTC: 21 },
]

const isTradingDay = (d) => d.getUTCDay() >= 1 && d.getUTCDay() <= 5   // الاثنين–الجمعة

export function utcMinutes(now = new Date()) {
  return now.getUTCHours() * 60 + now.getUTCMinutes()
}

// عطلة نهاية الأسبوع: من الجمعة 21:00 UTC حتى الأحد 21:00 UTC (عودة السوق بسيدني)
export function isWeekendClosed(now = new Date()) {
  const day = now.getUTCDay(), m = utcMinutes(now)
  return (day === 5 && m >= 21 * 60) || day === 6 || (day === 0 && m < 21 * 60)
}

export function isSessionOpen(s, now = new Date()) {
  if (!isTradingDay(now)) return false
  const m = utcMinutes(now)
  return m >= s.openUTC * 60 && m < s.closeUTC * 60
}

// دقائق حتى أقرب افتتاح فعلي لهذه الجلسة (يتخطى السبت والأحد)
export function minutesUntilOpen(s, now = new Date()) {
  for (let k = 0; k <= 7; k++) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + k, s.openUTC))
    if (d > now && isTradingDay(d)) return Math.round((d - now) / 60000)
  }
  return null
}

export function minutesUntilClose(s, now = new Date()) {
  return s.closeUTC * 60 - utcMinutes(now)
}

export function fmtHM(mins, isAr) {
  if (mins >= 1440) {
    const d = Math.floor(mins / 1440), h = Math.floor((mins % 1440) / 60)
    return isAr ? `${d}ي ${h}س` : `${d}d ${h}h`
  }
  const h = Math.floor(mins / 60), m = mins % 60
  if (isAr) return h > 0 ? `${h}س ${m}د` : `${m}د`
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}
