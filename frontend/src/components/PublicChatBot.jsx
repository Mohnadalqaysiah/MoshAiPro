import { useState, useRef, useEffect } from 'react'
import { X, Send, UserPlus, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { useLang } from '../contexts/LangContext'
import { BRAND, BRAND_CSS, NeuralOrb } from './SmartAnalysisBrand'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const SEEN_KEY = 'qaffel_smart_analysis_seen'

// session ID ثابت للمتصفح
const getSessionId = () => {
  let sid = localStorage.getItem('qaffel_public_sid')
  if (!sid) {
    sid = Math.random().toString(36).slice(2) + Date.now().toString(36)
    localStorage.setItem('qaffel_public_sid', sid)
  }
  return sid
}

const T = {
  ar: {
    welcome: 'أهلاً! أنا «تحليل ذكي» — محلّل الأسواق بالذكاء الاصطناعي 👋\nاسألني عن الذهب، البيتكوين، النازداك وأكثر!\n(5 محادثات مجانية)',
    online: 'متاح الآن',
    placeholder: 'اسألني عن الذهب...',
    register: 'سجّل مجاناً',
    registerFull: 'سجّل للوصول الكامل',
    error: '⚠️ خطأ مؤقت، حاول مجدداً.',
    thinking: 'يفكّر…',
    disclaimer: 'تحليل تقني تعليمي وليس نصيحة مالية.',
    suggestions: ['حلل الذهب', 'توصية البيتكوين', 'ما رأيك في النازداك؟'],
  },
  en: {
    welcome: 'Hi! I\'m "Smart Analysis" — your AI market analyst 👋\nAsk me about Gold, Bitcoin, NASDAQ and more!\n(5 free chats)',
    online: 'Online now',
    placeholder: 'Ask me about Gold...',
    register: 'Sign up free',
    registerFull: 'Sign up for full access',
    error: '⚠️ Temporary error, please try again.',
    thinking: 'Thinking…',
    disclaimer: 'Educational technical analysis — not financial advice.',
    suggestions: ['Analyze Gold', 'Bitcoin outlook', 'What about NASDAQ?'],
  },
}

export default function PublicChatBot() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']
  const brand = BRAND[isAr ? 'ar' : 'en']

  const [open, setOpen]       = useState(false)
  // رسالة الترحيب تُمثَّل بعلَم لا بنص حتى تتبع اللغة عند تبديلها
  const [msgs, setMsgs]       = useState([{ role: 'bot', welcome: true }])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [locked, setLocked]   = useState(false)
  const bottomRef = useRef(null)

  const [seen, setSeen] = useState(() => {
    try { return localStorage.getItem(SEEN_KEY) === '1' } catch { return false }
  })
  useEffect(() => {
    if (open && !seen) {
      setSeen(true)
      try { localStorage.setItem(SEEN_KEY, '1') } catch { /* تصفّح خاص */ }
    }
  }, [open, seen])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, loading])

  const send = async (override) => {
    const text = (override ?? input).trim()
    if (!text || loading || locked) return
    setInput('')
    setMsgs(m => [...m, { role: 'user', text }])
    setLoading(true)
    try {
      const { data } = await axios.post(`${API}/api/v1/public/chat`, {
        message: text,
        session_id: getSessionId(),
        lang: isAr ? 'ar' : 'en',
      })
      if (data.action === 'register_cta') setLocked(true)
      setMsgs(m => [...m, {
        role: 'bot',
        text: data.message,
        locked: data.action === 'locked_analysis' || data.action === 'register_cta',
        direction: data.direction,
        confidence: data.confidence,
        messagesLeft: data.messages_left,
      }])
    } catch {
      setMsgs(m => [...m, { role: 'bot', error: true }])
    } finally { setLoading(false) }
  }

  const showSuggestions = msgs.length === 1 && !loading

  return (
    <>
      <style>{BRAND_CSS}</style>

      {/* زر الفتح */}
      <button
        onClick={() => setOpen(o => !o)}
        aria-label={open ? (isAr ? 'إغلاق' : 'Close') : brand.name}
        className="fixed bottom-5 right-5 z-50 group"
      >
        {open ? (
          <div className="flex items-center justify-center w-11 h-11 rounded-full bg-[#0B1020] border border-white/15 text-gray-300 hover:text-white shadow-xl">
            <X size={18} />
          </div>
        ) : (
          <div className="relative">
            {!seen && (
              <span className="absolute inset-0 rounded-full animate-ping opacity-25" style={{ background: 'linear-gradient(135deg,#22D3EE,#8B5CF6)', animationDuration: '2.4s' }} />
            )}
            <div
              className="relative flex items-center gap-2.5 rounded-full ps-2 pe-2 sm:pe-4 py-2 text-sm font-semibold text-white shadow-2xl transition-transform group-hover:scale-[1.03]"
              style={{
                background: 'linear-gradient(#0B1020,#0B1020) padding-box, linear-gradient(135deg,#22D3EE,#8B5CF6) border-box',
                border: '1.5px solid transparent',
                boxShadow: '0 8px 30px rgba(34,211,238,0.22), 0 0 0 1px rgba(139,92,246,0.15)',
              }}
            >
              <NeuralOrb size={32} />
              <span className="hidden sm:flex flex-col leading-tight text-start">
                <span>{brand.name}</span>
                <span className="text-[10px] font-normal text-cyan-300/70 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> {tx.online}
                </span>
              </span>
            </div>
          </div>
        )}
      </button>

      {/* النافذة */}
      {open && (
        <div
          className="fixed bottom-20 right-4 sm:right-5 z-40 w-[calc(100vw-2rem)] sm:w-96 rounded-2xl border border-white/10 shadow-2xl flex flex-col overflow-hidden sa-panel"
          style={{ height: '440px', background: 'radial-gradient(120% 60% at 50% 0%, rgba(34,211,238,0.07), transparent 60%), #0B1020' }}
          dir={isAr ? 'rtl' : 'ltr'}
        >
          {/* Header */}
          <div className={`relative overflow-hidden flex items-center justify-between px-4 py-3 border-b border-white/[0.07] ${loading ? 'sa-scan' : ''}`}>
            <div className="flex items-center gap-3">
              <NeuralOrb size={36} active={loading} />
              <div>
                <div className="text-sm font-semibold text-white leading-tight">{brand.name}</div>
                <div className="text-[10.5px] text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" /> {tx.online}
                </div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white" aria-label={isAr ? 'إغلاق' : 'Close'}>
              <X size={16} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {msgs.map((m, i) => {
              const body = m.welcome ? tx.welcome : m.error ? tx.error : m.text
              const isUser = m.role === 'user'
              return (
                <div key={i} className={`flex gap-2 ${isUser ? 'justify-end' : 'justify-start'}`} style={{ direction: 'ltr' }}>
                  {!isUser && <div className="mt-0.5 flex-shrink-0"><NeuralOrb size={22} /></div>}
                  <div
                    dir={isAr ? 'rtl' : 'ltr'}
                    className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-line ${
                      isUser
                        ? 'text-white rounded-br-sm'
                        : 'bg-white/[0.045] border border-white/[0.06] text-gray-100 rounded-tl-sm'
                    }`}
                    style={isUser ? { background: 'linear-gradient(135deg,#4f46e5,#2563eb)' } : undefined}
                  >
                    {body}
                    {m.locked && !isUser && (
                      <Link to="/register" className="mt-2 flex items-center justify-center gap-1.5 text-white text-xs py-1.5 px-3 rounded-lg hover:opacity-90 transition"
                        style={{ background: 'linear-gradient(135deg,#0891B2,#6D28D9)' }}>
                        <UserPlus size={12} /> {tx.register}
                      </Link>
                    )}
                  </div>
                </div>
              )
            })}

            {showSuggestions && (
              <div className="flex flex-wrap gap-1.5 justify-center pt-1">
                {tx.suggestions.map(s => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-[11.5px] px-3 py-1.5 rounded-full border border-cyan-500/25 text-cyan-200 hover:bg-cyan-500/10 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {loading && (
              <div className="flex items-center gap-2" style={{ direction: 'ltr' }}>
                <NeuralOrb size={22} active />
                <span className="text-xs text-cyan-300/80" dir={isAr ? 'rtl' : 'ltr'}>{tx.thinking}</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-white/[0.07]">
            {locked ? (
              <Link to="/register" className="flex items-center justify-center gap-2 w-full text-white py-2.5 rounded-xl text-sm font-medium hover:opacity-90 transition"
                style={{ background: 'linear-gradient(135deg,#0891B2,#6D28D9)' }}>
                <UserPlus size={14} /> {tx.registerFull}
              </Link>
            ) : (
              <>
                <div className="flex gap-2">
                  <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && send()}
                    placeholder={tx.placeholder}
                    className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500 placeholder:text-gray-500"
                  />
                  <button
                    onClick={() => send()}
                    disabled={loading || !input.trim()}
                    aria-label={isAr ? 'إرسال' : 'Send'}
                    className="p-2.5 text-white rounded-xl transition-opacity disabled:opacity-40"
                    style={{ background: 'linear-gradient(135deg,#0891B2,#6D28D9)' }}
                  >
                    <Send size={14} className={isAr ? 'scale-x-[-1]' : ''} />
                  </button>
                </div>
                <div className="mt-1.5 flex items-center justify-center gap-1 text-[10px] text-gray-600">
                  <ShieldAlert size={10} /> {tx.disclaimer}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
