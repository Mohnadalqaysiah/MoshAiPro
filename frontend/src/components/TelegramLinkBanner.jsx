import { useState } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { Send, X, Copy, CheckCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function TelegramLinkBanner() {
  const { user } = useAuth()
  const [link, setLink]       = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied]   = useState(false)
  const [dismissed, setDismissed] = useState(false)

  // لا تعرض إذا مرتبط مسبقاً أو مُخفي
  if (!user || user.telegram_linked || dismissed) return null

  const fetchLink = async () => {
    setLoading(true)
    try {
      const r = await axios.get(`${API}/api/v1/auth/telegram-link`)
      setLink(r.data.link)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const copyLink = () => {
    navigator.clipboard.writeText(link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-indigo-900/25 border-b border-indigo-700/40 px-4 py-2 flex items-center justify-between text-xs" dir="rtl">
      <div className="flex items-center gap-3 text-gray-300">
        <Send size={13} className="text-indigo-400 flex-shrink-0" />
        <span>ربط حسابك بـ Telegram لتلقي إشعارات الإشارات مباشرة</span>

        {!link ? (
          <button
            onClick={fetchLink}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-0.5 rounded-md font-semibold text-xs"
          >
            {loading ? '...' : 'احصل على الرابط'}
          </button>
        ) : (
          <div className="flex items-center gap-1.5">
            <a
              href={link}
              target="_blank"
              rel="noreferrer"
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-0.5 rounded-md font-semibold text-xs"
            >
              فتح البوت
            </a>
            <button onClick={copyLink} className="text-gray-400 hover:text-white">
              {copied ? <CheckCircle size={13} className="text-green-400" /> : <Copy size={13} />}
            </button>
          </div>
        )}
      </div>

      <button onClick={() => setDismissed(true)} className="text-gray-500 hover:text-gray-300 mr-2">
        <X size={13} />
      </button>
    </div>
  )
}
