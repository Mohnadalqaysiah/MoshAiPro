import { useEffect, useState } from 'react'
import { useLang } from '../contexts/LangContext'
import { isPushSupported, getExistingSubscription, subscribeToPush, turnPushOff } from '../utils/webPush'

// (2026-10-31، طلب المالك) العميل يطفئ إشعارات التطبيق بنفسه. الاشتراك لكل جهاز، فالمفتاح لهذا الجهاز فقط، وتيليجرام له مفتاحه
// في تفضيلات الإشعارات. "محظورة" = رفضها من المتصفح، ولا يستطيع الموقع طلبها مجدداً.
export default function PushToggle() {
  const isAr = (useLang()?.lang || 'ar') === 'ar'
  const [state, setState] = useState(null)   // null = غير مدعوم | 'on' | 'off' | 'denied'
  const [busy, setBusy] = useState(false)

  const read = async () => {
    if (!isPushSupported()) return setState(null)
    if (Notification.permission === 'denied') return setState('denied')
    setState((await getExistingSubscription()) ? 'on' : 'off')
  }

  useEffect(() => { read() }, [])

  if (!state) return null

  const on = state === 'on'
  const toggle = async () => {
    setBusy(true)
    try {
      if (on) await turnPushOff()
      else await subscribeToPush()
    } catch { /* رفض الإذن: read يعرض الحالة الفعلية */ }
    await read()
    setBusy(false)
  }

  if (state === 'denied') {
    return (
      <p className="text-[11px] text-gray-400 leading-relaxed">
        {isAr ? 'إشعارات هذا الجهاز محظورة. يمكن السماح بها من إعدادات المتصفح.' : 'Notifications are blocked on this device. Allow them in your browser settings.'}
      </p>
    )
  }

  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[12px] text-gray-300">{isAr ? 'إشعارات هذا الجهاز' : 'Notifications on this device'}</span>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={isAr ? 'إشعارات هذا الجهاز' : 'Notifications on this device'}
        disabled={busy}
        onClick={toggle}
        className={`relative flex-shrink-0 w-10 h-5 rounded-full transition-colors disabled:opacity-60 ${on ? 'bg-emerald-500' : 'bg-gray-600'}`}
      >
        <span className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all" style={{ insetInlineStart: on ? 22 : 2 }} />
      </button>
    </div>
  )
}
