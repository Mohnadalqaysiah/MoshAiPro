import { useState, useEffect } from 'react'
import { Bell, X, CheckCircle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { isPushSupported, getExistingSubscription, subscribeToPush } from '../utils/webPush'

// (2026-09-27) قناة موازية لتيليجرام — خصوصاً لعميل الموقع اللي ما ربط
// حسابه بتيليجرام (لا يصله أي تنبيه شخصي حالياً بلا هاي القناة). إخفاء
// دائم لو المتصفح غير مدعوم أو الإذن مرفوض مسبقاً — لا نلحّ بلا فائدة.
export default function PushNotificationBanner() {
  const { user } = useAuth()
  const [dismissed, setDismissed] = useState(false)
  const [subscribed, setSubscribed] = useState(null)   // null = جاري الفحص
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!user || !isPushSupported() || Notification.permission === 'denied') {
      setSubscribed(true)   // يمنع أي عرض
      return
    }
    getExistingSubscription().then(sub => setSubscribed(!!sub))
  }, [user])

  if (!user || subscribed !== false || dismissed) return null

  const enable = async () => {
    setBusy(true)
    try {
      await subscribeToPush()
      setDone(true)
      setTimeout(() => setSubscribed(true), 1500)
    } catch {
      setDismissed(true)   // رفض الإذن أو خطأ — لا نكرر المحاولة بنفس الجلسة
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="bg-indigo-900/80 border-b-2 border-indigo-500 px-4 py-3 flex items-center justify-between gap-3"
      dir="rtl"
    >
      <div className="flex items-center gap-2 text-xs min-w-0">
        <Bell size={13} className="text-indigo-400 flex-shrink-0" />
        <span className="text-indigo-200">
          {done ? 'تم تفعيل إشعارات المتصفح ✅' : 'فعّل إشعارات المتصفح لتصلك الإشارات حتى بدون تيليجرام'}
        </span>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {!done && (
          <button
            onClick={enable}
            disabled={busy}
            className="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-60 text-white text-xs px-3 py-1.5 rounded-lg font-semibold transition-all"
          >
            {busy ? '...' : (<><Bell size={11} /> تفعيل</>)}
          </button>
        )}
        {done && <CheckCircle size={16} className="text-green-400" />}
        <button onClick={() => setDismissed(true)} title="إخفاء مؤقتاً" className="text-indigo-600 hover:text-indigo-300 transition-colors p-1">
          <X size={13} />
        </button>
      </div>
    </div>
  )
}
