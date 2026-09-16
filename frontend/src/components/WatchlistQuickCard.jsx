/**
 * WatchlistQuickCard — مدخل مباشر لتخصيص الأزواج من الداشبورد.
 *
 * (2026-09-16) سببه شكوى متكررة بالدعم من مستخدمي الهاتف: "ما بعرف من
 * وين أخصص الأزواج". المسار الوحيد كان 5 خطوات بلا أي دلالة — ☰ ثم
 * تمرير لأسفل الدرج ثم الضغط على الاسم (المكتوب "حسابي" فقط، لا شيء
 * يوحي بالأزواج) ثم صفحة الملف ثم تمرير طويل للأسفل.
 *
 * الأرقام وقتها: 120 من 129 مستخدماً مرتبطاً لم يضبطوا watchlist
 * إطلاقاً — أي أن الافتراضي (كل الأزواج) يعمل بشكل صحيح والوظيفة
 * سليمة؛ المشكلة كانت اكتشاف المكان فقط. لذلك البطاقة تُطمئن أولاً
 * ("تستقبل كل الأزواج") بدل أن توحي بوجود إعداد ناقص، ثم تعرض التخصيص
 * كخيار لمن يريد التضييق.
 */
import { Link } from 'react-router-dom'
import { SlidersHorizontal, Bell, BellOff, ChevronLeft, ChevronRight } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'

export default function WatchlistQuickCard() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const Chevron = isAr ? ChevronLeft : ChevronRight

  if (!user) return null

  const wl      = user.notify_watchlist || []
  const all     = wl.length === 0
  const enabled = user.notifications_enabled !== false

  return (
    <Link
      to="/profile#watchlist"
      className="flex items-center gap-3 rounded-2xl q-glass border q-line px-4 py-3 hover:border-blue-500/40 transition-colors"
    >
      <span className="w-10 h-10 rounded-xl grid place-items-center shrink-0 bg-blue-500/15 border border-blue-500/25">
        <SlidersHorizontal size={18} className="text-blue-300" />
      </span>

      <span className="min-w-0 flex-1">
        <span className="block text-sm font-bold text-white">
          {isAr ? 'الأزواج التي تصلك' : 'Your Signal Pairs'}
        </span>
        <span className="block text-xs text-gray-400 mt-0.5 truncate">
          {!enabled ? (
            <span className="text-amber-400 inline-flex items-center gap-1">
              <BellOff size={11} /> {isAr ? 'الإشعارات مطفأة — لن تصلك إشارات' : 'Notifications off — no signals'}
            </span>
          ) : all ? (
            <span className="inline-flex items-center gap-1">
              <Bell size={11} className="text-green-400" />
              {isAr ? 'تستقبل إشارات كل الأزواج' : 'Receiving all pairs'}
              <span className="text-gray-500">· {isAr ? 'اضغط للتخصيص' : 'tap to customize'}</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1">
              <Bell size={11} className="text-green-400" />
              {isAr ? `${wl.length} زوج مختار` : `${wl.length} pairs selected`}
              <span className="text-gray-500 truncate">· {wl.slice(0, 3).join('، ')}{wl.length > 3 ? '…' : ''}</span>
            </span>
          )}
        </span>
      </span>

      <Chevron size={18} className="text-gray-500 shrink-0" />
    </Link>
  )
}
