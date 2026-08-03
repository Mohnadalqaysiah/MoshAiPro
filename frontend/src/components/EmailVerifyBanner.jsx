import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { MailCheck, AlertCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function EmailVerifyBanner() {
  const { user, refreshUser } = useAuth()
  const [otp, setOtp]         = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [sent, setSent]       = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const timerRef = useRef(null)

  useEffect(() => {
    if (cooldown <= 0) { clearInterval(timerRef.current); return }
    timerRef.current = setInterval(() => setCooldown(c => c > 0 ? c - 1 : 0), 1000)
    return () => clearInterval(timerRef.current)
  }, [cooldown])

  if (!user || user.is_verified) return null

  const verify = async () => {
    if (!otp.trim()) { setError('أدخل رمز التفعيل'); return }
    setLoading(true); setError('')
    try {
      await axios.post(`${API}/api/v1/auth/verify-email`, { otp: otp.trim() })
      await refreshUser()
    } catch (err) {
      setError(err.response?.data?.detail || 'رمز غير صحيح')
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
      setError(err.response?.data?.detail || 'تعذّر إرسال الرمز')
    }
  }

  return (
    <div className="bg-yellow-900/20 border-b border-yellow-700/40 px-4 py-2.5 flex items-center justify-between flex-wrap gap-2 text-sm" dir="rtl">
      <div className="flex items-center gap-2 text-yellow-300">
        <MailCheck size={14} />
        <span>يرجى تفعيل بريدك الإلكتروني لتفعيل التجربة المجانية{sent ? ' — تم إرسال رمز جديد' : ''}</span>
      </div>

      <div className="flex items-center gap-2">
        {error && <span className="flex items-center gap-1 text-red-400 text-xs"><AlertCircle size={12}/>{error}</span>}
        <input
          type="text" inputMode="numeric" maxLength={6} value={otp}
          onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
          placeholder="رمز التفعيل"
          className="w-28 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-xs text-center font-mono focus:outline-none focus:ring-1 focus:ring-yellow-500"
          dir="ltr"
        />
        <button
          onClick={verify}
          disabled={loading}
          className="bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
        >
          {loading ? '...' : 'تحقق'}
        </button>
        <button
          onClick={resend}
          disabled={cooldown > 0}
          className="text-yellow-400 hover:text-yellow-300 disabled:text-gray-600 text-xs underline"
        >
          {cooldown > 0 ? `إعادة الإرسال (${cooldown})` : 'إعادة إرسال الرمز'}
        </button>
      </div>
    </div>
  )
}
