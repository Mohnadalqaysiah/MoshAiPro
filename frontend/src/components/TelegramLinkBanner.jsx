import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { Send, X, Copy, CheckCircle, ExternalLink } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function TelegramLinkBanner() {
  const { user } = useAuth()
  const [link, setLink]           = useState('')
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem('tg_banner_dismissed') === '1'
  )
  const [copied, setCopied] = useState(false)

  // لا تعرض إذا مرتبط أو مُخفي
  if (!user || user.telegram_linked || dismissed) return null

  // جلب الرابط عند أول ظهور
  useEffect(() => {
    axios.get(`${API}/api/v1/auth/telegram-link`)
      .then(r => setLink(r.data.link))
      .catch(() => {})
  }, [])

  const copyLink = () => {
    if (!link) return
    navigator.clipboard.writeText(link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const dismiss = () => {
    localStorage.setItem('tg_banner_dismissed', '1')
    setDismissed(true)
  }

  return (
    <div
      className="bg-indigo-950/60 border-b border-indigo-700/40 px-4 py-2.5 flex items-center justify-between gap-3 text-xs"
      dir="rtl"
    >
      {/* أيقونة + نص */}
      <div className="flex items-center gap-2 text-indigo-300 min-w-0">
        <Send size={13} className="flex-shrink-0" />
        <span className="truncate">
          🔗 اربط حسابك بـ Telegram لتلقي إشارات مباشرة
        </span>
      </div>

      {/* أزرار الرابط */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {link ? (
          <>
            <a
              href={link}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded-lg font-semibold transition-colors"
            >
              <ExternalLink size={11} />
              افتح البوت
            </a>
            <button
              onClick={copyLink}
              title="نسخ الرابط"
              className="text-indigo-400 hover:text-white transition-colors"
            >
              {copied
                ? <CheckCircle size={14} className="text-green-400" />
                : <Copy size={14} />
              }
            </button>
          </>
        ) : (
          <span className="text-indigo-500 animate-pulse text-xs">جاري التحميل...</span>
        )}

        <button
          onClick={dismiss}
          title="إخفاء"
          className="text-indigo-600 hover:text-indigo-400 transition-colors mr-1"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  )
}
