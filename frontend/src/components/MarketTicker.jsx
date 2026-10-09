import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { useLang } from '../contexts/LangContext'
import { SESSIONS, isSessionOpen, isWeekendClosed, minutesUntilClose, fmtHM } from '../utils/marketSessions'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// أقل عدد بنود بالنسخة الواحدة من الحلقة — لو البنود قليلة تُكرَّر حتى تملأ
// الشاشات العريضة، وإلا يظهر فراغ قبل ما تبدأ النسخة الثانية
const MIN_PER_HALF = 6

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

  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 30000)
    return () => clearInterval(t)
  }, [])

  const items = useMemo(() => {
    const out = []

    // 1) الجلسات — المفتوحة فعلاً فقط (مع الوقت المتبقي لكل واحدة).
    //    عطلة نهاية الأسبوع تُعلن صراحة بدل جلسات "مفتوحة" والسوق مغلق.
    const now = new Date()
    if (isWeekendClosed(now)) {
      out.push({
        key: 'weekend', dot: 'bg-amber-400',
        text: isAr ? '🔒 عطلة نهاية الأسبوع — الفوركس والمعادن مغلقة، الكريبتو فقط يتداول'
                   : '🔒 Weekend — forex & metals closed, only crypto trading',
      })
    } else {
      for (const s of SESSIONS.filter(x => isSessionOpen(x, now))) {
        const left = fmtHM(minutesUntilClose(s, now), isAr)
        out.push({
          key: `sess-${s.id}`, dot: 'bg-green-400',
          text: isAr ? `🟢 جلسة ${s.labelAr} مفتوحة — تغلق خلال ${left}`
                     : `🟢 ${s.labelEn} session open — closes in ${left}`,
        })
      }
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
  }, [signals, isAr, tick])

  if (items.length === 0) return null

  // (2026-10-09) إصلاح "الشريط لا يدور ويقف ولا يظهر كل البنود":
  // 1) المسار كان بعرض الحاوية لا بعرض المحتوى، فـtranslateX(-50%) يحرّك نصف
  //    الشاشة لا نصف البنود — الحلقة تقفز وتنقطع قبل ظهور البنود الأخيرة.
  //    w-max يجعل عرضه = المحتوى فعلاً.
  // 2) باتجاه RTL كان المحتوى الفائض يمتد يساراً خارج الحاوية بينما الحركة
  //    لليسار أيضاً، فيفرغ الجزء الظاهر. المسار نفسه صار LTR دائماً (النص
  //    بداخل كل بند يبقى بلغته)، والعربي يتحرك لليمين.
  // 3) التوقف عند المرور كان يعلق على الهاتف (اللمس يبقي حالة hover) — صار
  //    للأجهزة ذات الماوس فقط.
  // 4) المدة تتناسب مع عدد البنود، فالسرعة ثابتة مهما زادت.
  const half = []
  while (half.length < MIN_PER_HALF) half.push(...items)
  const loop = [...half, ...half]
  const duration = Math.max(20, half.length * 5)

  return (
    <div className="relative overflow-hidden bg-gray-900/70 border border-white/8 rounded-xl mb-4">
      <div
        dir="ltr"
        className="ticker-track flex w-max whitespace-nowrap py-2.5"
        style={{ animation: `${isAr ? 'ticker-rtl' : 'ticker-ltr'} ${duration}s linear infinite` }}
      >
        {loop.map((it, i) => (
          <span key={`${it.key}-${i}`} dir={isAr ? 'rtl' : 'ltr'}
                className="flex items-center gap-2 px-5 text-xs text-gray-300 flex-shrink-0">
            <span className={`w-1.5 h-1.5 rounded-full ${it.dot} flex-shrink-0`} />
            {it.text}
            <span className="text-gray-700 mx-2">•</span>
          </span>
        ))}
      </div>
      <style>{`
        @keyframes ticker-ltr { from { transform: translateX(0); }    to { transform: translateX(-50%); } }
        @keyframes ticker-rtl { from { transform: translateX(-50%); } to { transform: translateX(0); } }
        @media (hover: hover) { .ticker-track:hover { animation-play-state: paused !important; } }
      `}</style>
    </div>
  )
}
