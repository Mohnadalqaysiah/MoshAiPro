import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// نفس جلسات SessionsClock.jsx بالضبط — لازم يتطابقوا، هاد الشريط ملخّص لهم لا مصدر منفصل
const SESSIONS = [
  { id: 'asia',   labelAr: 'آسيا',     labelEn: 'Asia',     openUTC: 0,  closeUTC: 9  },
  { id: 'london', labelAr: 'لندن',     labelEn: 'London',   openUTC: 8,  closeUTC: 16 },
  { id: 'ny',     labelAr: 'نيويورك',  labelEn: 'New York', openUTC: 13, closeUTC: 21 },
]

function getUTCMinutes() {
  const n = new Date()
  return n.getUTCHours() * 60 + n.getUTCMinutes()
}
function isOpen(s) {
  const m = getUTCMinutes()
  const open = s.openUTC * 60, close = s.closeUTC * 60
  return open < close ? (m >= open && m < close) : (m >= open || m < close)
}
function minutesUntil(targetUTCHour) {
  const diff = targetUTCHour * 60 - getUTCMinutes()
  return diff <= 0 ? diff + 1440 : diff
}
function fmtHM(mins, isAr) {
  const h = Math.floor(mins / 60), m = mins % 60
  if (isAr) return h > 0 ? `${h}س ${m}د` : `${m}د`
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

// (2026-10-09) شريط إخباري علوي بالداشبورد — ملخّص سريع قبل ما يدخل
// المستخدم بالتفاصيل. كل بند هون مبني على بيانات حقيقية موجودة أصلاً
// (نفس مصدر MarketHeatmap/SessionsClock)، ولا رقم مُلفَّق أو "نشاط"
// يُعرض كأنه حجم تداول حقيقي — العدّ هون عدد الإشارات الحيّة فقط،
// مسمّى بوضوح "نشاط" لا "فوليوم" (راجع درس 2026-10-08 بـDECISIONS.md
// عن عرض أرقام غير حقيقية للعميل).
export default function MarketTicker() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const [signals, setSignals] = useState([])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const res = await axios.get(`${API}/api/v1/signals/latest?limit=200`)
        if (!cancelled) setSignals(res.data.data || [])
      } catch { /* الشريط اختياري — فشل الجلب يخفيه بصمت */ }
    }
    load()
    const id = setInterval(load, 5 * 60 * 1000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  const [, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 30000)
    return () => clearInterval(t)
  }, [])

  const items = useMemo(() => {
    const out = []

    // 1) الجلسات — المفتوحة حالياً + أقرب جلسة جاية
    const active = SESSIONS.filter(isOpen)
    if (active.length) {
      const names = active.map(s => isAr ? s.labelAr : s.labelEn).join(isAr ? ' + ' : ' + ')
      out.push({ key: 'sess-open', dot: 'bg-green-400', text: isAr ? `🟢 جلسة ${names} نشطة الآن` : `🟢 ${names} session active now` })
    }
    const next = SESSIONS
      .filter(s => !isOpen(s))
      .map(s => ({ s, mins: minutesUntil(s.openUTC) }))
      .sort((a, b) => a.mins - b.mins)[0]
    if (next) {
      out.push({
        key: 'sess-next', dot: 'bg-gray-500',
        text: isAr
          ? `🔴 جلسة ${next.s.labelAr} خلال ${fmtHM(next.mins, true)}`
          : `🔴 ${next.s.labelEn} session in ${fmtHM(next.mins, false)}`,
      })
    }

    // 2) الاتجاه العام — نسبة إشارات الشراء مقابل البيع بآخر الإشارات الحيّة
    if (signals.length) {
      const buys  = signals.filter(s => (s.recommendation || s.signal_type) === 'BUY').length
      const sells = signals.filter(s => (s.recommendation || s.signal_type) === 'SELL').length
      if (buys || sells) {
        const bias = buys > sells ? 'up' : sells > buys ? 'down' : 'flat'
        const label = bias === 'up'
          ? (isAr ? `📈 الاتجاه العام: صاعد (${buys} شراء / ${sells} بيع)` : `📈 Overall bias: Bullish (${buys} buy / ${sells} sell)`)
          : bias === 'down'
          ? (isAr ? `📉 الاتجاه العام: هابط (${sells} بيع / ${buys} شراء)` : `📉 Overall bias: Bearish (${sells} sell / ${buys} buy)`)
          : (isAr ? `⚖️ الاتجاه العام: متوازن (${buys} شراء / ${sells} بيع)` : `⚖️ Overall bias: Balanced (${buys} buy / ${sells} sell)`)
        out.push({ key: 'bias', dot: bias === 'up' ? 'bg-green-400' : bias === 'down' ? 'bg-red-400' : 'bg-gray-400', text: label })
      }

      // 3) أعلى رمز نشاطاً — عدد الإشارات الحيّة له (نشاط، لا فوليوم)
      const counts = {}
      for (const s of signals) {
        const sym = s.market || s.symbol
        if (sym) counts[sym] = (counts[sym] || 0) + 1
      }
      const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
      if (top && top[1] > 1) {
        out.push({
          key: 'top-activity', dot: 'bg-indigo-400',
          text: isAr ? `⚡ نشاط مرتفع على ${top[0]} (${top[1]} إشارة حيّة)` : `⚡ High activity on ${top[0]} (${top[1]} live signals)`,
        })
      }

      // 4) أعلى ثقة حالياً
      const highest = [...signals].sort((a, b) => (b.ai_confidence || 0) - (a.ai_confidence || 0))[0]
      if (highest?.ai_confidence >= 70) {
        out.push({
          key: 'top-conf', dot: 'bg-yellow-400',
          text: isAr
            ? `🎯 أعلى ثقة حالياً: ${highest.market || highest.symbol} (${Math.round(highest.ai_confidence)}%)`
            : `🎯 Highest confidence now: ${highest.market || highest.symbol} (${Math.round(highest.ai_confidence)}%)`,
        })
      }
    }

    return out
  }, [signals, isAr])

  if (items.length === 0) return null

  // تكرار القائمة مرتين لعمل حلقة سلسة بالأنيميشن (CSS فقط، بلا مكتبة)
  const loop = [...items, ...items]

  return (
    <div className="relative overflow-hidden bg-gray-900/70 border border-white/8 rounded-xl mb-4" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="flex whitespace-nowrap py-2.5 animate-[ticker_32s_linear_infinite] hover:[animation-play-state:paused]">
        {loop.map((it, i) => (
          <span key={`${it.key}-${i}`} className="flex items-center gap-2 px-5 text-xs text-gray-300 flex-shrink-0">
            <span className={`w-1.5 h-1.5 rounded-full ${it.dot} flex-shrink-0`} />
            {it.text}
            <span className="text-gray-700 mx-2">•</span>
          </span>
        ))}
      </div>
      <style>{`
        @keyframes ticker {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  )
}
