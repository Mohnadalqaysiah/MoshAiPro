import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Bell } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const POLL_MS = 60000

// (2026-09-28) آخر إشعارات وصلت فعلياً عبر Web Push (web_push.py:send_push) —
// خصوصاً لمستخدمي الهاتف يلي بيفوّتوا/يرفضوا إشعار المتصفح بسرعة، فيضيع
// بلا أي مكان يرجعوا يشوفوه فيه غير هالزر.
export default function NotificationBell() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(false)
  const boxRef = useRef(null)

  const load = async () => {
    try {
      const r = await axios.get(`${API}/api/v1/auth/notifications?limit=7`)
      setItems(r.data.notifications || [])
      setUnread(r.data.unread_count || 0)
    } catch { /* noop */ }
  }

  useEffect(() => {
    if (!user) return
    load()
    const id = setInterval(load, POLL_MS)
    return () => clearInterval(id)
  }, [user])

  useEffect(() => {
    const onClickOutside = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const toggle = async () => {
    const next = !open
    setOpen(next)
    if (next && unread > 0) {
      setUnread(0)
      try { await axios.post(`${API}/api/v1/auth/notifications/read`) } catch { /* noop */ }
    }
    if (next) { setLoading(true); await load(); setLoading(false) }
  }

  const openItem = (n) => {
    setOpen(false)
    navigate(n.url || '/dashboard')
  }

  const timeAgo = (iso) => {
    if (!iso) return ''
    const diffMin = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000))
    if (diffMin < 1) return isAr ? 'الآن' : 'now'
    if (diffMin < 60) return isAr ? `منذ ${diffMin} د` : `${diffMin}m ago`
    const diffH = Math.round(diffMin / 60)
    if (diffH < 24) return isAr ? `منذ ${diffH} س` : `${diffH}h ago`
    return isAr ? `منذ ${Math.round(diffH / 24)} يوم` : `${Math.round(diffH / 24)}d ago`
  }

  if (!user) return null

  return (
    <div className="relative" ref={boxRef}>
      <button
        onClick={toggle}
        aria-label={isAr ? 'الإشعارات' : 'Notifications'}
        className="relative w-9 h-9 rounded-xl q-glass grid place-items-center text-gray-200"
      >
        <Bell size={17} />
        {unread > 0 && (
          <span className="absolute -top-1 -end-1 min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[10px] font-bold grid place-items-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute top-11 end-0 w-72 max-h-96 overflow-y-auto rounded-2xl q-panel border q-line shadow-2xl z-40"
          dir={isAr ? 'rtl' : 'ltr'}
        >
          <div className="px-4 py-3 border-b q-line">
            <h3 className="text-sm font-bold text-white">{isAr ? 'الإشعارات' : 'Notifications'}</h3>
          </div>
          {loading ? (
            <p className="text-gray-500 text-xs text-center py-6">{isAr ? 'جاري التحميل...' : 'Loading...'}</p>
          ) : items.length === 0 ? (
            <p className="text-gray-500 text-xs text-center py-6">{isAr ? 'لا توجد إشعارات بعد' : 'No notifications yet'}</p>
          ) : (
            <div className="divide-y divide-white/5">
              {items.map(n => (
                <button
                  key={n.id}
                  onClick={() => openItem(n)}
                  className={`w-full text-start px-4 py-3 hover:bg-white/5 transition-colors ${!n.read ? 'bg-indigo-500/5' : ''}`}
                >
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <span className="text-xs font-semibold text-white truncate">{n.title}</span>
                    <span className="text-[10px] text-gray-500 flex-shrink-0">{timeAgo(n.created_at)}</span>
                  </div>
                  <p className="text-[11px] text-gray-400 leading-relaxed line-clamp-2">{n.body}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
