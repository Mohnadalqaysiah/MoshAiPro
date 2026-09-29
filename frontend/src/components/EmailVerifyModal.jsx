import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { MailCheck, X, AlertCircle, CheckCircle2, Send, Mail, ExternalLink, RefreshCw } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// (2026-09-29) بعض مزوّدي البريد (خصوصاً خطط استضافة رخيصة) يرفضون أو
// يؤخّرون رسائل SMTP، فتبقى حسابات عالقة بلا سبب يخصّنا — نفس رمز الـ6
// أرقام صار متاحاً عبر تلغرام كقناة بديلة (يتطلب ربط الحساب أولاً).
export default function EmailVerifyModal({ open, onClose }) {
  const { user, refreshUser } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'

  const [channel, setChannel]   = useState('email')   // 'email' | 'telegram'
  const [otp, setOtp]           = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [sent, setSent]         = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const timerRef = useRef(null)

  const [tgLink, setTgLink]         = useState('')
  const [tgBotName, setTgBotName]   = useState('Qaffelbot')
  const [tgLinkLoading, setTgLinkLoading] = useState(false)

  useEffect(() => {
    if (cooldown <= 0) { clearInterval(timerRef.current); return }
    timerRef.current = setInterval(() => setCooldown(c => (c > 0 ? c - 1 : 0)), 1000)
    return () => clearInterval(timerRef.current)
  }, [cooldown])

  useEffect(() => {
    if (!open) return
    const onKey = e => { if (e.key === 'Escape') onClose?.() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  // رابط ربط تلغرام — يُجلب فقط لما المستخدم يفتح تبويب تلغرام وحسابه غير مربوط بعد
  useEffect(() => {
    if (channel !== 'telegram' || user?.telegram_linked || tgLink) return
    setTgLinkLoading(true)
    axios.get(`${API}/api/v1/auth/telegram-link`)
      .then(r => {
        setTgLink(r.data.link)
        if (r.data.bot_username) setTgBotName(r.data.bot_username)
      })
      .catch(() => {})
      .finally(() => setTgLinkLoading(false))
  }, [channel, user?.telegram_linked, tgLink])

  if (!open || !user || user.is_verified) return null

  const verify = async () => {
    if (!otp.trim()) { setError(isAr ? 'أدخل رمز التفعيل' : 'Enter the code'); return }
    setLoading(true); setError('')
    try {
      await axios.post(`${API}/api/v1/auth/verify-email`, { otp: otp.trim() })
      await refreshUser()
      onClose?.()
    } catch (err) {
      setError(err.response?.data?.detail || (isAr ? 'رمز غير صحيح' : 'Invalid code'))
    } finally {
      setLoading(false)
    }
  }

  const resendEmail = async () => {
    if (cooldown > 0) return
    setError('')
    try {
      await axios.post(`${API}/api/v1/auth/resend-verification`)
      setSent(true)
      setCooldown(60)
    } catch (err) {
      setError(err.response?.data?.detail || (isAr ? 'تعذّر إرسال الرمز' : 'Could not send the code'))
    }
  }

  const sendTelegramOtp = async () => {
    if (cooldown > 0) return
    setError('')
    try {
      await axios.post(`${API}/api/v1/auth/verify-email/send-telegram-otp`)
      setSent(true)
      setCooldown(60)
    } catch (err) {
      setError(err.response?.data?.detail || (isAr ? 'تعذّر إرسال الرمز' : 'Could not send the code'))
    }
  }

  const checkLinked = async () => {
    setTgLinkLoading(true)
    try { await refreshUser() } finally { setTgLinkLoading(false) }
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4"
      style={{ background: 'rgba(4,5,7,0.78)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
      dir={isAr ? 'rtl' : 'ltr'}
      role="dialog"
      aria-modal="true"
    >
      <div
        onClick={e => e.stopPropagation()}
        className="relative w-full max-w-sm rounded-3xl overflow-hidden q-panel border q-line p-6"
        style={{ boxShadow: '0 30px 80px rgba(251,191,36,0.25)' }}
      >
        <button onClick={onClose} className="absolute top-3 end-3 text-gray-400 hover:text-white p-1" aria-label={isAr ? 'إغلاق' : 'Close'}>
          <X size={18} />
        </button>

        <div className="text-center mb-4">
          <div className="mx-auto w-14 h-14 rounded-2xl grid place-items-center mb-3 bg-amber-400/15 border border-amber-400/30">
            <MailCheck size={26} className="text-amber-300" />
          </div>
          <h2 className="text-lg font-black text-white">{isAr ? 'فعّل حسابك' : 'Verify Your Account'}</h2>
          <p className="text-sm text-gray-300 mt-1.5 leading-relaxed">
            {isAr
              ? 'أدخل رمز التفعيل المكوّن من 6 أرقام لتفعيل تجربتك المجانية.'
              : 'Enter the 6-digit code to activate your free trial.'}
          </p>
        </div>

        {/* اختيار القناة */}
        <div className="flex rounded-xl bg-gray-800/70 p-1 mb-4">
          <button
            onClick={() => { setChannel('email'); setError(''); setSent(false); setCooldown(0) }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition ${
              channel === 'email' ? 'bg-amber-500 text-[#1A1200]' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Mail size={13} /> {isAr ? 'البريد الإلكتروني' : 'Email'}
          </button>
          <button
            onClick={() => { setChannel('telegram'); setError(''); setSent(false); setCooldown(0) }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition ${
              channel === 'telegram' ? 'bg-amber-500 text-[#1A1200]' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Send size={13} /> {isAr ? 'تلغرام' : 'Telegram'}
          </button>
        </div>

        {channel === 'email' ? (
          <p className="text-xs text-gray-400 text-center -mt-2 mb-3">
            {isAr ? 'أرسلنا رمزاً إلى بريدك عند التسجيل — اضغط أدناه لإعادة إرساله إن لم يصلك.' : 'We sent a code to your email on signup — resend it below if it never arrived.'}
            {sent && <span className="block text-amber-400 mt-1">{isAr ? 'تم إرسال رمز جديد' : 'A new code was sent'}</span>}
          </p>
        ) : user.telegram_linked ? (
          <p className="text-xs text-gray-400 text-center -mt-2 mb-3">
            {isAr ? 'اضغط الزر أدناه ليصلك رمز التفعيل عبر تلغرام.' : 'Tap the button below to receive the code via Telegram.'}
            {sent && <span className="block text-amber-400 mt-1">{isAr ? 'تم إرسال رمز جديد عبر تلغرام' : 'A new code was sent via Telegram'}</span>}
          </p>
        ) : (
          <div className="text-center mb-3 space-y-2">
            <p className="text-xs text-gray-400">
              {isAr ? 'اربط حسابك بتلغرام أولاً لتستخدم هذه الطريقة:' : 'Link your account to Telegram first:'}
            </p>
            {tgLink ? (
              <a
                href={tgLink} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-2 rounded-lg font-semibold transition"
              >
                <ExternalLink size={12} /> {isAr ? `ربط مع @${tgBotName}` : `Link with @${tgBotName}`}
              </a>
            ) : (
              <span className="text-gray-500 text-xs">{isAr ? 'جاري التحميل...' : 'Loading...'}</span>
            )}
            <button
              onClick={checkLinked}
              disabled={tgLinkLoading}
              className="flex items-center gap-1.5 mx-auto text-gray-400 hover:text-white text-[11px] disabled:opacity-50"
            >
              <RefreshCw size={11} className={tgLinkLoading ? 'animate-spin' : ''} />
              {isAr ? 'ربطت حسابي — تحقّق مجدداً' : "I've linked it — check again"}
            </button>
          </div>
        )}

        <input
          type="text" inputMode="numeric" maxLength={6} value={otp}
          onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
          onKeyDown={e => e.key === 'Enter' && !loading && verify()}
          placeholder={isAr ? 'رمز التفعيل' : 'Verification code'}
          className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-3 text-white text-center text-lg font-mono tracking-[0.3em] focus:outline-none focus:ring-1 focus:ring-amber-500"
          dir="ltr"
        />

        {error && (
          <p className="flex items-center justify-center gap-1 text-red-400 text-xs mt-2">
            <AlertCircle size={12} />{error}
          </p>
        )}

        <button
          onClick={verify}
          disabled={loading}
          className="w-full mt-3 rounded-xl py-3 font-bold text-sm flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-[#1A1200] transition-all"
        >
          {loading ? '...' : <><CheckCircle2 size={15} />{isAr ? 'تحقّق وفعّل' : 'Verify & Activate'}</>}
        </button>

        {(channel === 'email' || user.telegram_linked) && (
          <button
            onClick={channel === 'email' ? resendEmail : sendTelegramOtp}
            disabled={cooldown > 0}
            className="w-full text-amber-400 hover:text-amber-300 disabled:text-gray-500 text-xs mt-2.5 py-1"
          >
            {cooldown > 0
              ? (isAr ? `إعادة الإرسال (${cooldown})` : `Resend (${cooldown})`)
              : (isAr ? 'إعادة إرسال الرمز' : 'Resend the code')}
          </button>
        )}
      </div>
    </div>
  )
}
