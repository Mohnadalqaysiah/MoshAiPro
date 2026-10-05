import { useEffect, useRef, useState, useCallback } from 'react'
import axios from 'axios'
import { MessageCircle, X, Send, LifeBuoy, Paperclip, FileText, Mic, Square } from 'lucide-react'
import { useLang } from '../contexts/LangContext'
import useSiteSettings from '../hooks/useSiteSettings'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// (2026-10-05) الحد الأقصى صار يُقرأ من الإعدادات الحية (يضبطه الأدمن،
// لا رقم ثابت بالكود) — هذا بس احتياط للحظة ما قبل وصول الرد. التسجيل
// الصوتي أُضيف هون كنوع مرفق إضافي، بنفس آلية الرفع الموجودة أصلاً.
const FALLBACK_MAX_BYTES = 5 * 1024 * 1024
const ALLOWED_TYPES = [
  'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf',
  'audio/webm', 'audio/ogg', 'audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/x-m4a',
]

function Attachment({ url, name, type, isAr }) {
  const full = `${API}${url}`
  if (type?.startsWith('image/')) {
    return (
      <a href={full} target="_blank" rel="noreferrer" className="block mt-1.5">
        <img src={full} alt={name || 'attachment'} className="max-w-[200px] max-h-[200px] rounded-lg border border-black/10" />
      </a>
    )
  }
  if (type?.startsWith('audio/')) {
    return <audio controls src={full} className="mt-1.5 max-w-full h-9" style={{ minWidth: 220 }} />
  }
  return (
    <a href={full} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 mt-1.5 text-xs underline opacity-90 hover:opacity-100">
      <FileText size={13} /> {name || (isAr ? 'ملف مرفق' : 'Attachment')}
    </a>
  )
}

export default function SupportChatWidget() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const siteSettings = useSiteSettings()
  const maxAttachmentBytes = (Number(siteSettings.support_attachment_max_mb) || 5) * 1024 * 1024

  const [open, setOpen]         = useState(false)
  const [messages, setMessages] = useState([])
  const [unread, setUnread]     = useState(0)
  const [input, setInput]       = useState('')
  const [sending, setSending]   = useState(false)
  const [file, setFile]         = useState(null)
  const [fileError, setFileError] = useState('')
  const [recording, setRecording] = useState(false)
  const bodyRef = useRef(null)
  const fileRef = useRef(null)
  const lastIdRef = useRef(0)
  const mediaRecorderRef = useRef(null)
  const recordedChunksRef = useRef([])

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

  useEffect(() => {
    if (!open) document.body.style.overflow = ''
    else if (window.innerWidth < 768) document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [open])

  const pickFile = (f) => {
    setFileError('')
    if (!f) { setFile(null); return }
    if (!ALLOWED_TYPES.includes(f.type)) {
      setFileError(isAr ? 'نوع الملف غير مدعوم — صورة، PDF، أو تسجيل صوتي فقط' : 'Unsupported file type — image, PDF, or voice note only')
      return
    }
    if (f.size > maxAttachmentBytes) {
      const mb = Math.round(maxAttachmentBytes / (1024 * 1024))
      setFileError(isAr ? `حجم الملف أكبر من ${mb} ميجابايت` : `File is larger than ${mb}MB`)
      return
    }
    setFile(f)
  }

  // (2026-10-05) تسجيل صوتي — نفس آلية الرفع/الإرسال الموجودة أصلاً
  // للمرفقات (Blob يُغلَّف كـFile ويُمرَّر لنفس pickFile/send، بلا أي
  // مسار منفصل جديد).
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      recordedChunksRef.current = []
      mr.ondataavailable = (e) => { if (e.data.size > 0) recordedChunksRef.current.push(e.data) }
      mr.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(recordedChunksRef.current, { type: mr.mimeType || 'audio/webm' })
        const ext = (mr.mimeType || 'audio/webm').split('/')[1]?.split(';')[0] || 'webm'
        pickFile(new File([blob], `voice-note.${ext}`, { type: blob.type }))
      }
      mediaRecorderRef.current = mr
      mr.start()
      setRecording(true)
    } catch (e) {
      setFileError(isAr ? 'تعذّر الوصول للميكروفون' : 'Could not access the microphone')
    }
  }
  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  const send = async () => {
    const body = input.trim()
    if ((!body && !file) || sending) return
    setSending(true)
    try {
      const form = new FormData()
      form.append('body', body)
      if (file) form.append('file', file)
      const res = await axios.post(`${API}/api/v1/support/messages`, form)
      lastIdRef.current = Math.max(lastIdRef.current, res.data.id)
      setMessages(prev => [...prev, res.data])
      setInput('')
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (e) {
      alert(e.response?.data?.detail || (isAr ? 'تعذّر إرسال الرسالة' : 'Failed to send message'))
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(o => !o)}
        className={`fixed bottom-5 right-4 md:right-auto md:left-6 z-50 flex items-center gap-2 rounded-full bg-gray-800 border border-gray-700 hover:bg-gray-700 text-gray-200 px-4 py-2.5 shadow-xl text-sm font-medium transition-all ${open ? 'hidden md:flex' : 'flex'}`}
      >
        <LifeBuoy size={16} className="text-emerald-400" />
        <span>{isAr ? 'الدعم' : 'Support'}</span>
        {unread > 0 && (
          <span className="bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">{unread}</span>
        )}
      </button>

      {/* موبايل: بوب أب بملء الشاشة (بدل صندوق صغير بالزاوية ممكن ينقطع بمتصفحات الموبايل) */}
      {open && (
        <div className="fixed inset-0 md:inset-auto md:bottom-20 md:left-6 z-50 md:w-[90vw] md:max-w-sm">
          <div className="bg-gray-900 border-0 md:border border-gray-700 rounded-none md:rounded-2xl shadow-2xl flex flex-col h-full md:h-[28rem] overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between bg-gray-800/50">
              <div className="flex items-center gap-2">
                <MessageCircle size={16} className="text-emerald-400" />
                <span className="text-sm font-semibold text-white">{isAr ? 'الدعم الفني' : 'Support'}</span>
              </div>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white p-1">
                <X size={18} />
              </button>
            </div>

            <div ref={bodyRef} className="flex-1 overflow-y-auto p-3 space-y-2.5">
              {messages.length === 0 && (
                <p className="text-center text-gray-500 text-xs py-8">
                  {isAr ? 'اكتب رسالتك وسيتواصل معك فريق الدعم قريباً' : 'Send a message and support will reply shortly'}
                </p>
              )}
              {messages.map(m => (
                <div key={m.id} className={`flex ${m.sender_role === 'admin' ? 'justify-start' : 'justify-end'}`}>
                  <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap break-words ${m.sender_role === 'admin' ? 'bg-gray-700 text-gray-100' : 'bg-blue-600 text-white'}`}>
                    {m.body}
                    {m.attachment_url && <Attachment url={m.attachment_url} name={m.attachment_name} type={m.attachment_type} isAr={isAr} />}
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-gray-800">
              {file && (
                <div className="flex items-center gap-2 px-3 pt-2 text-xs text-gray-300">
                  <Paperclip size={12} />
                  <span className="truncate flex-1">{file.name}</span>
                  <button onClick={() => { setFile(null); if (fileRef.current) fileRef.current.value = '' }} className="text-gray-500 hover:text-red-400"><X size={13} /></button>
                </div>
              )}
              {fileError && <p className="px-3 pt-1 text-[11px] text-red-400">{fileError}</p>}
              <div className="p-3 flex items-center gap-2">
                <input ref={fileRef} type="file" accept={ALLOWED_TYPES.join(',')} className="hidden" onChange={e => pickFile(e.target.files?.[0])} />
                <button onClick={() => fileRef.current?.click()} title={isAr ? 'إرفاق ملف' : 'Attach file'} className="text-gray-400 hover:text-white p-2 flex-shrink-0">
                  <Paperclip size={16} />
                </button>
                <button
                  onClick={recording ? stopRecording : startRecording}
                  title={isAr ? (recording ? 'إيقاف التسجيل' : 'تسجيل صوتي') : (recording ? 'Stop recording' : 'Record voice note')}
                  className={`p-2 flex-shrink-0 rounded-lg ${recording ? 'text-red-400 animate-pulse bg-red-500/10' : 'text-gray-400 hover:text-white'}`}>
                  {recording ? <Square size={16} /> : <Mic size={16} />}
                </button>
                <textarea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      if (!sending) send()
                    }
                  }}
                  placeholder={isAr ? 'اكتب رسالتك... (Shift+Enter لسطر جديد)' : 'Type a message... (Shift+Enter for new line)'}
                  rows={1}
                  style={{ maxHeight: '7rem' }}
                  onInput={e => { e.target.style.height = 'auto'; e.target.style.height = `${Math.min(e.target.scrollHeight, 112)}px` }}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none overflow-y-auto leading-relaxed"
                />
                <button onClick={send} disabled={sending || (!input.trim() && !file)}
                  className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white p-2.5 rounded-lg flex-shrink-0">
                  <Send size={15} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
