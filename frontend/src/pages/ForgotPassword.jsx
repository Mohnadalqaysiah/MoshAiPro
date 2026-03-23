import { useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, Mail, AlertCircle, CheckCircle } from 'lucide-react'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  const handleSubmit = e => {
    e.preventDefault()
    // No email service configured — show manual support message
    setSent(true)
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4" dir="rtl">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600 mb-4">
            <TrendingUp size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Qafeel <span className="text-blue-400">AI</span></h1>
          <p className="text-gray-400 text-sm mt-1">استعادة كلمة المرور</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          {sent ? (
            <div className="text-center space-y-4">
              <CheckCircle size={48} className="text-green-400 mx-auto" />
              <h2 className="text-lg font-bold text-white">تم استلام طلبك</h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                تواصل مع الدعم الفني عبر Telegram أو البريد الإلكتروني مع ذكر بريدك المسجّل وسيتم إعادة تعيين كلمة المرور خلال 24 ساعة.
              </p>
              <a href="https://t.me/qafeel_support" target="_blank" rel="noreferrer"
                 className="inline-block mt-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition">
                تواصل عبر Telegram
              </a>
              <p className="text-xs text-gray-600">أو راسلنا: support@qaffel.com</p>
            </div>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-white mb-2">نسيت كلمة المرور؟</h2>
              <p className="text-gray-400 text-sm mb-6">أدخل بريدك الإلكتروني وسنساعدك في استعادة الوصول.</p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">البريد الإلكتروني</label>
                  <div className="relative">
                    <Mail size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input type="email" required value={email}
                      onChange={e => setEmail(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="example@email.com" dir="ltr" />
                  </div>
                </div>
                <button type="submit"
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 rounded-xl text-sm transition">
                  إرسال طلب الاستعادة
                </button>
              </form>
            </>
          )}

          <p className="text-center text-sm text-gray-500 mt-6">
            <Link to="/login" className="text-blue-400 hover:text-blue-300">العودة لتسجيل الدخول</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
