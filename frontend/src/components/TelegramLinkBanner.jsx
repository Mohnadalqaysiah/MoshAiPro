import { useState, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { Send, X, Copy, CheckCircle, ExternalLink } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DISMISS_KEY = 'mosh_tg_dismissed'

export default function TelegramLinkBanner() {
  const { user } = useAuth()
  const [link, setLink]           = useState('')
  const [botName, setBotName]     = useState('Qaffelbot')
  const [dismissed, setDismissed] = useState(false)
  const [copied, setCopied]       = useState(false)

  // جلب الرابط فوراً عند وجود المستخدم — لازم قبل أي return
  useEffect(() => {
    if (user && !user.telegram_linked) {
      localStorage.removeItem(DISMISS_KEY)
      setDismissed(false)
      axios.get(`${API}/api/v1/auth/telegram-link`)
        .then(r => {
          setLink(r.data.link)
          if (r.data.bot_username) setBotName(r.data.bot_username)
        })
        .catch(() => {})
    }
  }, [user?.id, user?.telegram_linked])

  // إخفاء لمدة الجلسة فقط (مش localStorage)
  if (!user || user.telegram_linked || dismissed) return null

  const copyLink = () => {
    if (!link) return
    navigator.clipboard.writeText(link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className="bg-indigo-900/80 border-b-2 border-indigo-500 px-4 py-3 flex items-center justify-between gap-3"
      dir="rtl"
    >
      {/* نص */}
      <div className="flex items-center gap-2 text-xs min-w-0">
        <Send size={13} className="text-indigo-400 flex-shrink-0" />
        <span className="text-indigo-200">
          اربط حسابك بـ Telegram لتلقي إشارات وتنبيهات مباشرة
        </span>
      </div>

      {/* أزرار */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {link ? (
          <>
            <a
              href={link}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-xs px-3 py-1.5 rounded-lg font-semibold transition-all"
            >
              <ExternalLink size={11} />
              ربط مع @{botName}
            </a>
            <button
              onClick={copyLink}
              title="نسخ الرابط"
              className="text-indigo-400 hover:text-white transition-colors p-1"
            >
              {copied
                ? <CheckCircle size={14} className="text-green-400" />
                : <Copy size={14} />
              }
            </button>
          </>
        ) : (
          <span className="text-indigo-500 text-xs animate-pulse">⏳ جاري التحميل...</span>
        )}

        <button
          onClick={() => setDismissed(true)}
          title="إخفاء مؤقتاً"
          className="text-indigo-600 hover:text-indigo-300 transition-colors p-1"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  )
}
