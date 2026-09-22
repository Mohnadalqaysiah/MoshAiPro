import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

const T = {
  ar: { cta: 'المتابعة بحساب Google', loading: 'جاري التحقق...', or: 'أو', genericError: 'فشل الدخول بحساب Google' },
  en: { cta: 'Continue with Google', loading: 'Verifying...', or: 'or', genericError: 'Google sign-in failed' },
}

// أيقونة Google الرسمية متعددة الألوان (SVG) — لا مكتبة خارجية لهيك شكل واحد بسيط
function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.87 2.7-6.62z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.96v2.33A9 9 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.95 10.7A5.41 5.41 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.03l2.99-2.33z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.97l2.99 2.33C4.66 5.17 6.65 3.58 9 3.58z" />
    </svg>
  )
}

/**
 * زر "المتابعة بحساب Google" — مشترك بين Login و Register. نفس شكل
 * استجابة login/register (يرجّع user)، فاستدعاؤه من الصفحتين متماثل.
 */
export default function GoogleAuthButton({ isAr, refCode = '', onSuccess, onError, className = '' }) {
  const { loginWithGoogle } = useAuth()
  const tx = T[isAr ? 'ar' : 'en']
  const [loading, setLoading] = useState(false)

  const handleClick = async () => {
    setLoading(true)
    try {
      const user = await loginWithGoogle(refCode)
      onSuccess?.(user)
    } catch (err) {
      // المستخدم أغلق نافذة قوقل بنفسه — مو خطأ يستاهل عرضه
      if (err?.code === 'auth/popup-closed-by-user' || err?.code === 'auth/cancelled-popup-request') {
        setLoading(false)
        return
      }
      onError?.(err.response?.data?.detail || tx.genericError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={className}>
      <div className="flex items-center gap-3 my-4">
        <div className="flex-1 h-px bg-gray-800" />
        <span className="text-xs text-gray-600">{tx.or}</span>
        <div className="flex-1 h-px bg-gray-800" />
      </div>
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="w-full flex items-center justify-center gap-2.5 bg-white hover:bg-gray-100 disabled:opacity-60 text-gray-800 font-medium py-2.5 rounded-xl transition-colors text-sm"
      >
        <GoogleIcon />
        {loading ? tx.loading : tx.cta}
      </button>
    </div>
  )
}
