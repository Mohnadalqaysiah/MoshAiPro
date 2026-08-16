import { useEffect, useRef, useState, useCallback } from 'react'
import axios from 'axios'
import { MessageCircle, X, Send, LifeBuoy } from 'lucide-react'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function SupportChatWidget() {
  const { lang } = useLang()
  const isAr = lang === 'ar'

  const [open, setOpen]         = useState(false)
  const [messages, setMessages] = useState([])
  const [unread, setUnread]     = useState(0)
  const [input, setInput]       = useState('')
  const [sending, setSending]   = useState(false)
  const bodyRef = useRef(null)
  const lastIdRef = useRef(0)

  const poll = useCallback(async (opening = false) => {
    try {
      const res = await axios.get(`${API}/api/v1/support/messages`, { params: { after_id: opening ? 0 : lastIdRef.current } })
      const { messages: newMsgs } = res.data
      if (newMsgs?.length) {
        lastIdRef.current = Math.max(lastIdRef.current, ...newMsgs.map(m => m.id))
        setMessages(prev => opening ? newMsgs : [...prev, ...newMsgs])
      }
    } catch (e) {}
  }, [])

  // فحص خفيف كل 20 ثانية للرسائل الجديدة وقت إغلاق النافذة (بادج فقط)
  useEffect(() => {
    const check = async () => {
      try {
        const res = await axios.get(`${API}/api/v1/support/thread`)
        if (!open) setUnread(res.data.unread_for_user || 0)
      } catch (e) {}
    }
    check()
    const id = setInterval(check, 20000)
    return () => clearInterval(id)
  }, [open])

  // بوّلينج للرسائل وقت فتح النافذة
  useEffect(() => {
    if (!open) return
    poll(true)
    setUnread(0)
    const id = setInterval(() => poll(false), 5000)
    return () => clearInterval(id)
  }, [open, poll])

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [messages, open])

  const send = async () => {
    const body = input.trim()
    if (!body || sending) return
    setSending(true)
    setInput('')
    try {
      const res = await axios.post(`${API}/api/v1/support/messages`, { body })
      lastIdRef.current = Math.max(lastIdRef.current, res.data.id)
      setMessages(prev => [...prev, res.data])
    } catch (e) {
      alert(isAr ? 'تعذّر إرسال الرسالة' : 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-5 right-4 md:right-auto md:left-6 z-50 flex items-center gap-2 rounded-full bg-gray-800 border border-gray-700 hover:bg-gray-700 text-gray-200 px-4 py-2.5 shadow-xl text-sm font-medium transition-all"
      >
        {open ? <X size={16} /> : <LifeBuoy size={16} className="text-emerald-400" />}
        <span>{isAr ? 'الدعم' : 'Support'}</span>
        {!open && unread > 0 && (
          <span className="bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">{unread}</span>
        )}
      </button>

      {open && (
        <div className="fixed bottom-20 right-4 md:right-auto md:left-6 z-50 w-[90vw] max-w-sm h-[28rem] bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2 bg-gray-800/50">
            <MessageCircle size={16} className="text-emerald-400" />
            <span className="text-sm font-semibold text-white">{isAr ? 'الدعم الفني' : 'Support'}</span>
          </div>

          <div ref={bodyRef} className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {messages.length === 0 && (
              <p className="text-center text-gray-500 text-xs py-8">
                {isAr ? 'اكتب رسالتك وسيتواصل معك فريق الدعم قريباً' : 'Send a message and support will reply shortly'}
              </p>
            )}
            {messages.map(m => (
              <div key={m.id} className={`flex ${m.sender_role === 'admin' ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${m.sender_role === 'admin' ? 'bg-gray-700 text-gray-100' : 'bg-blue-600 text-white'}`}>
                  {m.body}
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 border-t border-gray-800 flex items-center gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && send()}
              placeholder={isAr ? 'اكتب رسالتك...' : 'Type a message...'}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button onClick={send} disabled={sending || !input.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white p-2.5 rounded-lg flex-shrink-0">
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
