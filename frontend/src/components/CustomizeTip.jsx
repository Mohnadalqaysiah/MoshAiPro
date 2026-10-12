import { useState } from 'react'
import { Link } from 'react-router-dom'
import { SlidersHorizontal, X } from 'lucide-react'
import { useLang } from '../contexts/LangContext'

// (2026-10-12) تنبيه لمرة واحدة: العميل يقدر يخصّص الإشارات التي تصله.
// التخصيص كان موجوداً لكن مخفياً بصفحة الحساب، وأغلب المشتركين (212 من 280)
// لم يفتحوه أبداً. يُخفى نهائياً عند الإغلاق أو بعد فتح الإعدادات.
const KEY = 'qaffel_tip_customize_v1'

export default function CustomizeTip() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const [hidden, setHidden] = useState(() => {
    try { return localStorage.getItem(KEY) === '1' } catch { return false }
  })
  if (hidden) return null
  const dismiss = () => { try { localStorage.setItem(KEY, '1') } catch {} setHidden(true) }

  return (
    <div className="relative mb-4 rounded-xl border border-blue-700/40 bg-gradient-to-l from-blue-900/30 to-indigo-900/20 px-4 py-3 flex items-center gap-3 flex-wrap"
         dir={isAr ? 'rtl' : 'ltr'}>
      <div className="w-9 h-9 rounded-lg bg-blue-500/15 grid place-items-center flex-shrink-0">
        <SlidersHorizontal size={17} className="text-blue-300" />
      </div>
      <div className="flex-1 min-w-[200px]">
        <div className="text-sm font-semibold text-white">
          {isAr ? 'جديد: خصّص الإشارات التي تصلك' : 'New: customize the signals you receive'}
        </div>
        <div className="text-xs text-gray-300 mt-0.5">
          {isAr
            ? 'اختر أزواجك والفريمات (15 دقيقة، ساعة، 4 ساعات) وأقل نسبة ثقة — وغيّرها بأي وقت.'
            : 'Pick your markets, timeframes (15m, 1h, 4h) and minimum confidence — change them any time.'}
        </div>
      </div>
      <Link to="/profile#watchlist" onClick={dismiss}
        className="text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg transition">
        {isAr ? 'خصّص الآن' : 'Customize'}
      </Link>
      <button onClick={dismiss} aria-label={isAr ? 'إغلاق' : 'Close'}
        className="absolute top-2 end-2 p-1 text-gray-500 hover:text-white">
        <X size={14} />
      </button>
    </div>
  )
}
