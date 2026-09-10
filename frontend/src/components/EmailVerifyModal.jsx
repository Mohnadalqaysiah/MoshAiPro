import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { MailCheck, X, AlertCircle, CheckCircle2 } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function EmailVerifyModal({ open, onClose }) {
  const { user, refreshUser } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'

  const [otp, setOtp]           = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [sent, setSent]         = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const timerRef = useRef(null)

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

  const resend = async () => {
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
          <h2 className="text-lg font-black text-white">{isAr ? 'فعّل بريدك الإلكتروني' : 'Verify Your Email'}</h2>
          <p className="text-sm text-gray-300 mt-1.5 leading-relaxed">
            {isAr
              ? 'أرسلنا رمزاً مكوّناً من 6 أرقام إلى بريدك. أدخله لتفعيل تجربتك المجانية.'
              : 'We sent a 6-digit code to your email. Enter it to activate your free trial.'}
            {sent && <span className="block text-amber-400 text-xs mt-1">{isAr ? 'تم إرسال رمز جديد' : 'A new code was sent'}</span>}
          </p>
        </div>

        <input
          type="text" inputMode="numeric" maxLength={6} value={otp}
          onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
          onKeyDown={e => e.key === 'Enter' && !loading && verify()}
          placeholder={isAr ? 'رمز التفعيل' : 'Verification code'}
          className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-3 text-white text-center text-lg font-mono tracking-[0.3em] focus:outline-none focus:ring-1 focus:ring-amber-500"
          dir="ltr"
          autoFocus
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

        <button
          onClick={resend}
          disabled={cooldown > 0}
          className="w-full text-amber-400 hover:text-amber-300 disabled:text-gray-500 text-xs mt-2.5 py-1"
        >
          {cooldown > 0
            ? (isAr ? `إعادة الإرسال (${cooldown})` : `Resend (${cooldown})`)
            : (isAr ? 'إعادة إرسال الرمز' : 'Resend the code')}
        </button>
      </div>
    </div>
  )
}
