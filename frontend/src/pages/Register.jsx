import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { TrendingUp, Mail, Lock, User, Phone, AlertCircle, CheckCircle, ShieldCheck } from 'lucide-react'

// Simple math captcha — generates client-side, no external API needed
function useCaptcha() {
  const captcha = useMemo(() => {
    const a = Math.floor(Math.random() * 9) + 1
    const b = Math.floor(Math.random() * 9) + 1
    return { question: `${a} + ${b}`, answer: String(a + b) }
  }, [])
  return captcha
}

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const captcha = useCaptcha()

  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '' })
  const [captchaVal, setCaptchaVal] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    if (form.password.length < 8) { setError('كلمة المرور يجب أن تكون 8 أحرف على الأقل'); return }
    if (captchaVal.trim() !== captcha.answer) { setError('إجابة التحقق غير صحيحة — يرجى المحاولة مجدداً'); return }
    setError('')
    setLoading(true)
    try {
      await register(form.email, form.password, form.full_name)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'فشل إنشاء الحساب')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4 py-10" dir="rtl">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600 mb-4">
            <TrendingUp size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Qafeel <span className="text-blue-400">AI</span></h1>
          <p className="text-gray-400 text-sm mt-1">ابدأ تجربتك المجانية</p>
        </div>

        {/* Trial benefits */}
        <div className="bg-blue-900/20 border border-blue-700/30 rounded-xl p-4 mb-6">
          <p className="text-blue-300 text-xs font-semibold mb-2">✨ ما تحصل عليه مجاناً:</p>
          {['7 أيام تجريبية', '10 تحليلات ICT/SMC كاملة', '20 رسالة مع وكيل الذكاء الاصطناعي', 'وصول لجميع الأزواج'].map(f => (
            <div key={f} className="flex items-center gap-2 text-xs text-gray-300 mt-1">
              <CheckCircle size={12} className="text-green-400 flex-shrink-0" />
              <span>{f}</span>
            </div>
          ))}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-6">إنشاء حساب جديد</h2>

          {error && (
            <div className="flex items-center gap-2 bg-red-900/30 border border-red-700/50 rounded-lg px-3 py-2 mb-4 text-sm text-red-400">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">الاسم الكامل</label>
              <div className="relative">
                <User size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input type="text" required value={form.full_name}
                  onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="محمد أحمد" />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">البريد الإلكتروني</label>
              <div className="relative">
                <Mail size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input type="email" required value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="example@email.com" dir="ltr" />
              </div>
            </div>

            {/* Phone (optional) */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">رقم الهاتف <span className="text-gray-600 text-xs">(اختياري)</span></label>
              <div className="relative">
                <Phone size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input type="tel" value={form.phone}
                  onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="+966 5x xxx xxxx" dir="ltr" />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">كلمة المرور <span className="text-gray-600 text-xs">(8 أحرف+)</span></label>
              <div className="relative">
                <Lock size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input type="password" required minLength={8} value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="••••••••" dir="ltr" />
              </div>
            </div>

            {/* Captcha */}
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <ShieldCheck size={15} className="text-blue-400" />
                <p className="text-xs text-gray-400 font-medium">تحقق بشري — أجب عن السؤال:</p>
              </div>
              <p className="text-white text-base font-bold mb-3 text-center">
                كم يساوي: <span className="text-blue-400 text-lg">{captcha.question}</span> ؟
              </p>
              <input
                type="number" required value={captchaVal}
                onChange={e => setCaptchaVal(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="الإجابة..." dir="ltr" />
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm">
              {loading ? 'جاري التسجيل...' : 'ابدأ التجربة المجانية'}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            لديك حساب؟{' '}
            <Link to="/login" className="text-blue-400 hover:text-blue-300">سجّل دخول</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
