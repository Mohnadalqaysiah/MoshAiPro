import { useState, useEffect } from 'react'
import { Sparkles, X, ArrowLeft, ArrowRight } from 'lucide-react'
import useSiteSettings from '../hooks/useSiteSettings'
import { useLang } from '../contexts/LangContext'

const DISMISS_KEY = 'mosh_announcement_dismissed'

export default function DashboardAnnouncement() {
  const settings = useSiteSettings()
  const { lang } = useLang()
  const isAr = lang !== 'en'
  const [dismissed, setDismissed] = useState(false)

  const enabled = settings.dashboard_announcement_enabled === 'true'
  const text    = (settings.dashboard_announcement_text || '').trim()
  const link    = (settings.dashboard_announcement_link || '').trim()
  const linkLabel = (settings.dashboard_announcement_link_label || (isAr ? 'التفاصيل' : 'Details')).trim()

  // كل نص جديد يعتبر إعلان جديد — لو الأدمن غيّر النص، يظهر حتى لو المستخدم
  // كان سكّر إعلان سابق.
  useEffect(() => {
    if (!text) return
    setDismissed(localStorage.getItem(DISMISS_KEY) === text)
  }, [text])

  if (!enabled || !text || dismissed) return null

  const close = () => {
    localStorage.setItem(DISMISS_KEY, text)
    setDismissed(true)
  }

  const Arrow = isAr ? ArrowLeft : ArrowRight

  return (
    <div
      className="relative overflow-hidden rounded-2xl mb-5 animate-fade-up"
      dir={isAr ? 'rtl' : 'ltr'}
    >
      <div className="absolute inset-0 bg-gradient-to-l from-indigo-600 via-purple-600 to-blue-600 animate-shimmer" />
      <div className="relative flex items-center gap-3 px-4 sm:px-5 py-3.5">
        <span className="flex-shrink-0 w-8 h-8 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center">
          <Sparkles size={16} className="text-white animate-pulse-glow" />
        </span>

        <div className="flex-1 min-w-0 flex items-center flex-wrap gap-x-2 gap-y-1">
          <span className="text-[10px] font-bold tracking-wide bg-white/20 text-white px-2 py-0.5 rounded-full flex-shrink-0">
            {isAr ? 'جديد' : 'NEW'}
          </span>
          <p className="text-white text-sm font-medium leading-snug">{text}</p>
        </div>

        {link && (
          <a
            href={link}
            target={link.startsWith('http') ? '_blank' : undefined}
            rel="noreferrer"
            className="flex-shrink-0 hidden sm:flex items-center gap-1 bg-white/15 hover:bg-white/25 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
          >
            {linkLabel}
            <Arrow size={12} />
          </a>
        )}

        <button
          onClick={close}
          className="flex-shrink-0 text-white/70 hover:text-white transition-colors p-1"
          title={isAr ? 'إخفاء' : 'Dismiss'}
        >
          <X size={15} />
        </button>
      </div>
    </div>
  )
}
