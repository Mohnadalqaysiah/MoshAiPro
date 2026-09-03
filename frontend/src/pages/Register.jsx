import { useState, useMemo } from 'react'
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { Mail, Lock, User, Phone, AlertCircle, CheckCircle, ShieldCheck, Gift } from 'lucide-react'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import { mirrorPath } from '../utils/langRoutes'
import Logo from '../components/Logo'

// Simple math captcha — generates client-side, no external API needed
function useCaptcha() {
  const captcha = useMemo(() => {
    const a = Math.floor(Math.random() * 9) + 1
    const b = Math.floor(Math.random() * 9) + 1
    return { question: `${a} + ${b}`, answer: String(a + b) }
  }, [])
  return captcha
}

const T = {
  ar: {
    tagline: 'ابدأ تجربتك المجانية',
    referredVia: 'تم التسجيل عبر رابط إحالة — كود:',
    freeTitle: '✨ ما تحصل عليه مجاناً:',
    freeBenefits: ['7 أيام تجريبية', '10 تحليلات ICT/SMC كاملة', '20 رسالة مع وكيل الذكاء الاصطناعي', 'وصول لجميع الأزواج'],
    heading: 'إنشاء حساب جديد',
    fullName: 'الاسم الكامل',
    fullNamePh: 'محمد أحمد',
    email: 'البريد الإلكتروني',
    phone: 'رقم الهاتف',
    optional: '(اختياري)',
    password: 'كلمة المرور',
    passwordHint: '(8 أحرف+)',
    captchaLabel: 'تحقق بشري — أجب عن السؤال:',
    captchaQ: 'كم يساوي:',
    captchaPh: 'الإجابة...',
    submit: 'ابدأ التجربة المجانية',
    submitting: 'جاري التسجيل...',
    haveAccount: 'لديك حساب؟',
    login: 'سجّل دخول',
    errPasswordShort: 'كلمة المرور يجب أن تكون 8 أحرف على الأقل',
    errCaptcha: 'إجابة التحقق غير صحيحة — يرجى المحاولة مجدداً',
    errGeneric: 'فشل إنشاء الحساب',
  },
  en: {
    tagline: 'Start your free trial',
    referredVia: 'Signed up via referral link — code:',
    freeTitle: '✨ What you get for free:',
    freeBenefits: ['7-day trial', '10 full ICT/SMC analyses', '20 messages with the AI agent', 'Access to all pairs'],
    heading: 'Create a New Account',
    fullName: 'Full Name',
    fullNamePh: 'John Smith',
    email: 'Email',
    phone: 'Phone Number',
    optional: '(optional)',
    password: 'Password',
    passwordHint: '(8+ characters)',
    captchaLabel: 'Human check — answer the question:',
    captchaQ: 'What is:',
    captchaPh: 'Answer...',
    submit: 'Start Free Trial',
    submitting: 'Signing up...',
    haveAccount: 'Already have an account?',
    login: 'Sign in',
    errPasswordShort: 'Password must be at least 8 characters',
    errCaptcha: 'Incorrect answer — please try again',
    errGeneric: 'Failed to create account',
  },
}

export default function Register() {
  const { lang, toggle } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']
  const location = useLocation()

  useSEO({
    title: isAr
      ? 'إنشاء حساب مجاني | Qaffel AI — ابدأ بـ 10 تحليلات مجانية'
      : 'Create Free Account | Qaffel AI',
    description: isAr
      ? 'أنشئ حسابك المجاني بـ Qaffel AI واحصل على 10 تحليلات و20 رسالة شات AI مجاناً — بدون بطاقة ائتمان. إشارات تداول ذكية للذهب والبيتكوين والفوركس.'
      : 'Create your free Qaffel AI account: 10 analyses and 20 AI chat messages free, no credit card. Smart signals for Gold, Bitcoin and Forex.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'إنشاء حساب' : 'Register', path: isAr ? '/register' : '/en/register' },
  ])
  const { register } = useAuth()
  const navigate = useNavigate()
  const captcha = useCaptcha()
  const [searchParams] = useSearchParams()
  const ref = searchParams.get('ref') || ''

  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '' })
  const [captchaVal, setCaptchaVal] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleToggleLang = () => {
    const target = isAr ? 'en' : 'ar'
    const mirror = mirrorPath(location.pathname, target)
    toggle()
    if (mirror && mirror !== location.pathname) navigate(mirror)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    if (form.password.length < 8) { setError(tx.errPasswordShort); return }
    if (captchaVal.trim() !== captcha.answer) { setError(tx.errCaptcha); return }
    setError('')
    setLoading(true)
    try {
      await register(form.email, form.password, form.full_name, ref)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || tx.errGeneric)
    } finally {
      setLoading(false)
    }
  }

  const iconSide = isAr ? 'right-3' : 'left-3'
  const inputPad = isAr ? 'pr-10 pl-4' : 'pl-10 pr-4'

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4 py-10" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="w-full max-w-md">
        <div className="flex justify-end mb-4">
          <button onClick={handleToggleLang}
            className="text-xs border border-gray-700 hover:border-blue-500/50 text-gray-400 hover:text-white px-3 py-1.5 rounded-lg transition-all font-medium">
            {isAr ? 'EN' : 'ع'}
          </button>
        </div>

        <div className="text-center mb-8">
          <Logo className="w-14 h-14 mx-auto mb-4 rounded-2xl" />
          <h1 className="text-2xl font-bold text-white">Qaffel <span className="text-blue-400">AI</span></h1>
          <p className="text-gray-400 text-sm mt-1">{tx.tagline}</p>
        </div>

        {/* Referral banner */}
        {ref && (
          <div className="bg-green-900/20 border border-green-700/30 rounded-xl p-3 mb-4 flex items-center gap-2">
            <Gift size={16} className="text-green-400 flex-shrink-0" />
            <p className="text-green-300 text-xs">{tx.referredVia} <span className="font-mono font-bold">{ref}</span></p>
          </div>
        )}

        {/* Trial benefits */}
        <div className="bg-blue-900/20 border border-blue-700/30 rounded-xl p-4 mb-6">
          <p className="text-blue-300 text-xs font-semibold mb-2">{tx.freeTitle}</p>
          {tx.freeBenefits.map(f => (
            <div key={f} className="flex items-center gap-2 text-xs text-gray-300 mt-1">
              <CheckCircle size={12} className="text-green-400 flex-shrink-0" />
              <span>{f}</span>
            </div>
          ))}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-6">{tx.heading}</h2>

          {error && (
            <div className="flex items-center gap-2 bg-red-900/30 border border-red-700/50 rounded-lg px-3 py-2 mb-4 text-sm text-red-400">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{tx.fullName}</label>
              <div className="relative">
                <User size={16} className={`absolute top-1/2 -translate-y-1/2 text-gray-500 ${iconSide}`} />
                <input type="text" required value={form.full_name}
                  onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  className={`w-full bg-gray-800 border border-gray-700 rounded-xl py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${inputPad}`}
                  placeholder={tx.fullNamePh} />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{tx.email}</label>
              <div className="relative">
                <Mail size={16} className={`absolute top-1/2 -translate-y-1/2 text-gray-500 ${iconSide}`} />
                <input type="email" required value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className={`w-full bg-gray-800 border border-gray-700 rounded-xl py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${inputPad}`}
                  placeholder="example@email.com" dir="ltr" />
              </div>
            </div>

            {/* Phone (optional) */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{tx.phone} <span className="text-gray-400 text-xs">{tx.optional}</span></label>
              <div className="relative">
                <Phone size={16} className={`absolute top-1/2 -translate-y-1/2 text-gray-500 ${iconSide}`} />
                <input type="tel" value={form.phone}
                  onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                  className={`w-full bg-gray-800 border border-gray-700 rounded-xl py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${inputPad}`}
                  placeholder="+966 5x xxx xxxx" dir="ltr" />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">{tx.password} <span className="text-gray-400 text-xs">{tx.passwordHint}</span></label>
              <div className="relative">
                <Lock size={16} className={`absolute top-1/2 -translate-y-1/2 text-gray-500 ${iconSide}`} />
                <input type="password" required minLength={8} value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  className={`w-full bg-gray-800 border border-gray-700 rounded-xl py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${inputPad}`}
                  placeholder="••••••••" dir="ltr" />
              </div>
            </div>

            {/* Captcha */}
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <ShieldCheck size={15} className="text-blue-400" />
                <p className="text-xs text-gray-400 font-medium">{tx.captchaLabel}</p>
              </div>
              <p className="text-white text-base font-bold mb-3 text-center">
                {tx.captchaQ} <span className="text-blue-400 text-lg">{captcha.question}</span> ?
              </p>
              <input
                type="number" required value={captchaVal}
                onChange={e => setCaptchaVal(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={tx.captchaPh} dir="ltr" />
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm">
              {loading ? tx.submitting : tx.submit}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            {tx.haveAccount}{' '}
            <Link to={isAr ? '/login' : '/en/login'} className="text-blue-400 hover:text-blue-300">{tx.login}</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
