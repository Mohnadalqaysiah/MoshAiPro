import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useSiteSettings from '../hooks/useSiteSettings'
import { Megaphone, X } from 'lucide-react'

const DISMISS_KEY = 'qaffel_special_popup_dismissed'

// (2026-10-06) بوب أب ملء الشاشة عام — إعلان/عرض/قرار/احتفال، يحدّده
// الأدمن بالكامل (عنوان + نص حر + رابط اختياري) بلا نشر كود. يظهر لكل
// مستخدم مسجّل (بما فيهم التجريبي) بعكس DiscountPopup المقصور على
// التجربة. مفتاح الإخفاء يخزّن النص نفسه (نفس حيلة DashboardAnnouncement)
// فيظهر تلقائياً من جديد لأي مستخدم لما يغيّر الأدمن المحتوى.
export default function SpecialAnnouncementPopup() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const siteSettings = useSiteSettings()
  const [dismissed, setDismissed] = useState(true)

  const enabled = siteSettings.special_popup_enabled === 'true'
  const title = siteSettings.special_popup_title || ''
  const body = siteSettings.special_popup_body || ''
  const link = siteSettings.special_popup_link || ''
  const linkLabel = siteSettings.special_popup_link_label || (isAr ? 'التفاصيل' : 'Details')
  const contentKey = `${title}|${body}|${link}`

  useEffect(() => {
    if (!user || !enabled || !body.trim()) { setDismissed(true); return }
    try {
      setDismissed(localStorage.getItem(DISMISS_KEY) === contentKey)
    } catch { setDismissed(false) }
  }, [user, enabled, body, contentKey])

  if (!user || !enabled || !body.trim() || dismissed) return null

  const dismiss = () => {
    try { localStorage.setItem(DISMISS_KEY, contentKey) } catch { /* noop */ }
    setDismissed(true)
  }

  return (
    <div
      className="fixed inset-0 z-[75] flex items-center justify-center p-4"
      style={{ background: 'rgba(4,5,7,0.82)', backdropFilter: 'blur(4px)' }}
      onClick={dismiss}
      dir={isAr ? 'rtl' : 'ltr'}
      role="dialog"
      aria-modal="true"
    >
      <div
        onClick={e => e.stopPropagation()}
        className="relative w-full max-w-sm rounded-3xl overflow-hidden text-center"
        style={{
          background: 'linear-gradient(160deg, #1e1b4b 0%, #0B1020 55%, #0B1020 100%)',
          border: '1px solid rgba(139,92,246,0.35)',
          boxShadow: '0 30px 90px rgba(139,92,246,0.35), 0 0 0 1px rgba(255,255,255,0.03)',
        }}
      >
        <div className="absolute -top-16 -inset-x-10 h-40 opacity-40 blur-3xl"
          style={{ background: 'radial-gradient(60% 100% at 50% 0%, #8B5CF6, transparent)' }} />

        <button onClick={dismiss} className="absolute top-3 end-3 z-10 text-gray-400 hover:text-white p-1" aria-label={isAr ? 'إغلاق' : 'Close'}>
          <X size={18} />
        </button>

        <div className="relative px-6 pt-9 pb-7">
          <div className="mx-auto w-16 h-16 rounded-2xl grid place-items-center mb-4"
            style={{ background: 'linear-gradient(135deg,#8B5CF6,#6366F1)', boxShadow: '0 8px 30px rgba(99,102,241,0.4)' }}>
            <Megaphone size={28} className="text-white" />
          </div>

          {title && <h2 className="text-xl font-black text-white mb-2">{title}</h2>}
          <p className="text-sm text-gray-300 mb-6 whitespace-pre-wrap leading-relaxed">{body}</p>

          {link && (
            <a
              href={link}
              onClick={dismiss}
              className="w-full flex items-center justify-center gap-2 rounded-2xl py-3.5 text-base font-bold text-white transition-transform hover:scale-[1.02] active:scale-95"
              style={{
                background: 'linear-gradient(135deg,#8B5CF6,#EC4899)',
                boxShadow: '0 10px 30px rgba(236,72,153,0.35)',
              }}
            >
              {linkLabel}
            </a>
          )}

          <button onClick={dismiss} className="mt-3 text-xs text-gray-500 hover:text-gray-300 transition-colors">
            {isAr ? 'إغلاق' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  )
}
