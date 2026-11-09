/**
 * (2026-11-09) نسب التوفير تُحسب من الأسعار الحية — لا تُكتب نصاً.
 * كان "توفير 46%" و"شهران مجاناً" مكتوبين ثابتين، والأسبوعي صار 15$ من لوحة الإدارة:
 * الحقيقي ~54% للشهري و~50% (6 أشهر) للسنوي. أي ميزة تذكر توفيراً تُحذف من القائمة ويُعرض المحسوب.
 */
export const SAVINGS_RE = /توفير|وفّر|وفر |save|%|شهران مجان|months free/i

export function planSavings({ weekly = 0, monthly = 0, yearly = 0 } = {}) {
  const w = Number(weekly) || 0
  const m = Number(monthly) || 0
  const y = Number(yearly) || 0
  const saveM = w && m ? Math.round((1 - m / (w * 52 / 12)) * 100) : 0
  const saveY = m && y ? Math.round((1 - y / (m * 12)) * 100) : 0
  return { monthly: saveM >= 5 ? saveM : 0, yearly: saveY >= 5 ? saveY : 0 }
}
