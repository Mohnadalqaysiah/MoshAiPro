import { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Lock, UserPlus } from 'lucide-react'
import { Link } from 'react-router-dom'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// session ID ثابت للمتصفح
const getSessionId = () => {
  let sid = localStorage.getItem('qaffel_public_sid')
  if (!sid) {
    sid = Math.random().toString(36).slice(2) + Date.now().toString(36)
    localStorage.setItem('qaffel_public_sid', sid)
  }
  return sid
}

export default function PublicChatBot() {
  const [open, setOpen]       = useState(false)
  const [msgs, setMsgs]       = useState([{
    role: 'bot',
    text: 'أهلاً! أنا كفيل — وكيل التداول الذكي 👋\nاسألني عن الذهب، البيتكوين، النازداك وأكثر!\n(5 محادثات مجانية)',
    locked: false,
  }])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [locked, setLocked]   = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = async () => {
    if (!input.trim() || loading || locked) return
    const text = input.trim()
    setInput('')
    setMsgs(m => [...m, { role: 'user', text }])
    setLoading(true)
    try {
      const { data } = await axios.post(`${API}/api/v1/public/chat`, {
        message: text,
        session_id: getSessionId(),
      })
      if (data.action === 'register_cta') {
        setLocked(true)
      }
      setMsgs(m => [...m, {
        role: 'bot',
        text: data.message,
        locked: data.action === 'locked_analysis' || data.action === 'register_cta',
        direction: data.direction,
        confidence: data.confidence,
        messagesLeft: data.messages_left,
      }])
    } catch {
      setMsgs(m => [...m, { role: 'bot', text: '⚠️ خطأ مؤقت، حاول مجدداً.' }])
    } finally { setLoading(false) }
  }

  return (
    <>
      {/* زر الفتح */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-5 right-5 z-50 flex items-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white px-4 py-3 rounded-full shadow-xl shadow-blue-500/30 text-sm font-medium transition-all"
      >
        {open ? <X size={18}/> : <MessageCircle size={18}/>}
        <span>كفيل AI</span>
        {!open && <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"/>}
      </button>

      {/* النافذة */}
      {open && (
        <div className="fixed bottom-20 right-5 z-40 w-80 md:w-96 rounded-2xl border border-gray-700/80 bg-gray-900 shadow-2xl flex flex-col" style={{height:'420px'}}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gradient-to-r from-blue-900/40 to-purple-900/40 rounded-t-2xl">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">ك</div>
              <div>
                <div className="text-sm font-semibold text-white">كفيل AI</div>
                <div className="text-[10px] text-green-400 flex items-center gap-1"><span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"/> متاح الآن</div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white"><X size={16}/></button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-line ${
                  m.role==='user'
                    ? 'bg-blue-600 text-white rounded-br-sm'
                    : 'bg-gray-800 text-gray-100 rounded-bl-sm'
                }`}>
                  {m.text}
                  {m.locked && m.role==='bot' && (
                    <Link to="/register" className="mt-2 flex items-center justify-center gap-1.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-90 text-white text-xs py-1.5 px-3 rounded-lg transition">
                      <UserPlus size={12}/> سجّل مجاناً
                    </Link>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-3 py-2">
                  <div className="flex gap-1">{[0,1,2].map(i=><div key={i} className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:`${i*0.15}s`}}/>)}</div>
                </div>
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          {/* Input */}
          <div className="p-3 border-t border-gray-800">
            {locked ? (
              <Link to="/register" className="flex items-center justify-center gap-2 w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-2.5 rounded-xl text-sm font-medium hover:opacity-90 transition">
                <UserPlus size={14}/> سجّل للوصول الكامل
              </Link>
            ) : (
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key==='Enter' && send()}
                  placeholder="اسألني عن الذهب..."
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  dir="rtl"
                />
                <button onClick={send} disabled={loading || !input.trim()}
                  className="p-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-xl transition">
                  <Send size={14}/>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
