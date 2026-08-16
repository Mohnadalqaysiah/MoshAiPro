import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { Mail, Lock, AlertCircle } from 'lucide-react'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import { mirrorPath } from '../utils/langRoutes'

const T = {
  ar: {
    tagline: 'منصة التداول الذكي بمدارس ICT/SMC',
    heading: 'تسجيل الدخول',
    email: 'البريد الإلكتروني',
    password: 'كلمة المرور',
    submit: 'دخول',
    submitting: 'جاري الدخول...',
    forgot: 'نسيت كلمة المرور؟',
    noAccount: 'ليس لديك حساب؟',
    register: 'سجّل مجاناً',
    genericError: 'فشل تسجيل الدخول',
  },
  en: {
    tagline: 'Smart trading powered by ICT/SMC methodology',
    heading: 'Sign In',
    email: 'Email',
    password: 'Password',
    submit: 'Sign In',
    submitting: 'Signing in...',
    forgot: 'Forgot your password?',
    noAccount: "Don't have an account?",
    register: 'Register free',
    genericError: 'Login failed',
  },
}

export default function Login() {
  const { lang, toggle } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']
  const location = useLocation()
  const navigate  = useNavigate()

  useSEO({
    title: isAr ? 'تسجيل الدخول | Qaffel AI' : 'Sign In | Qaffel AI',
    description: isAr
      ? 'سجّل دخولك إلى Qaffel AI للوصول إلى إشارات التداول الذكية للذهب والبيتكوين والفوركس.'
      : 'Sign in to Qaffel AI to access smart trading signals for Gold, Bitcoin and Forex.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'تسجيل الدخول' : 'Sign In', path: isAr ? '/login' : '/en/login' },
  ])

  const { login } = useAuth()
  const [form, setForm]     = useState({ email: '', password: '' })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleToggleLang = () => {
    const target = isAr ? 'en' : 'ar'
    const mirror = mirrorPath(location.pathname, target)
    toggle()
    if (mirror && mirror !== location.pathname) navigate(mirror)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(form.email, form.password)
      navigate(user.role === 'admin' ? '/admin' : '/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || tx.genericError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="w-full max-w-md">
        {/* Lang toggle */}
        <div className="flex justify-end mb-4">
          <button onClick={handleToggleLang}
            className="text-xs border border-gray-700 hover:border-blue-500/50 text-gray-400 hover:text-white px-3 py-1.5 rounded-lg transition-all font-medium">
            {isAr ? 'EN' : 'ع'}
          </button>
        </div>

        {/* Logo */}
        <div className="text-center mb-8">
          <img src="/brand/logo-icon-only.png" alt="Qaffel AI" className="w-14 h-14 mx-auto mb-4 rounded-2xl" />
          <h1 className="text-2xl font-bold text-white">Qaffel <span className="text-blue-400">AI</span></h1>
          <p className="text-gray-400 text-sm mt-1">{tx.tagline}</p>
        </div>

        {/* Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-6">{tx.heading}</h2>

          {error && (
            <div className="flex items-center gap-2 bg-red-900/30 border border-red-700/50 rounded-lg px-3 py-2 mb-4 text-sm text-red-400">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{tx.email}</label>
              <div className="relative">
                <Mail size={16} className={`absolute top-1/2 -translate-y-1/2 text-gray-500 ${isAr ? 'right-3' : 'left-3'}`} />
                <input
                  type="email" required
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className={`w-full bg-gray-800 border border-gray-700 rounded-xl py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${isAr ? 'pr-10 pl-4' : 'pl-10 pr-4'}`}
                  placeholder="example@email.com"
                  dir="ltr"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{tx.password}</label>
              <div className="relative">
                <Lock size={16} className={`absolute top-1/2 -translate-y-1/2 text-gray-500 ${isAr ? 'right-3' : 'left-3'}`} />
                <input
                  type="password" required
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  className={`w-full bg-gray-800 border border-gray-700 rounded-xl py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${isAr ? 'pr-10 pl-4' : 'pl-10 pr-4'}`}
                  placeholder="••••••••"
                  dir="ltr"
                />
              </div>
            </div>

            <button
              type="submit" disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm"
            >
              {loading ? tx.submitting : tx.submit}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-4">
            <Link to={isAr ? '/forgot-password' : '/forgot-password'} className="text-gray-400 hover:text-blue-400 transition">
              {tx.forgot}
            </Link>
          </p>
          <p className="text-center text-sm text-gray-500 mt-3">
            {tx.noAccount}{' '}
            <Link to={isAr ? '/register' : '/en/register'} className="text-blue-400 hover:text-blue-300">
              {tx.register}
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
