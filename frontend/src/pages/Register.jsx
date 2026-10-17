import { useState, useMemo } from 'react'
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { Mail, Lock, User, Phone, AlertCircle, CheckCircle, ShieldCheck, Gift } from 'lucide-react'
import useSEO from '../hooks/useSEO'
import useTrialLimits from '../hooks/useTrialLimits'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import { mirrorPath } from '../utils/langRoutes'
import AuthShell from '../components/AuthShell'
import GoogleAuthButton from '../components/GoogleAuthButton'

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
    freeBenefits: ['7 أيام تجريبية', '{n} تحليلات ICT/SMC كاملة', '{m} رسالة مع وكيل الذكاء الاصطناعي', 'وصول لجميع الأزواج'],
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
    freeBenefits: ['7-day trial', '{n} full ICT/SMC analyses', '{m} messages with the AI agent', 'Access to all pairs'],
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
  const trial = useTrialLimits()
  const fmtTrial = (s) => s?.replace('{n}', trial.analyses).replace('{m}', trial.chat)

  useSEO({
    title: isAr
      ? `إنشاء حساب مجاني | Qaffel AI — ابدأ بـ ${trial.analyses} تحليلات مجانية`
      : 'Create Free Account | Qaffel AI',
    description: isAr
      ? `أنشئ حسابك المجاني بـ Qaffel AI واحصل على ${trial.analyses} تحليلات و${trial.chat} رسالة شات AI مجاناً — بدون بطاقة ائتمان. إشارات تداول ذكية للذهب والبيتكوين والفوركس.`
      : `Create your free Qaffel AI account: ${trial.analyses} analyses and ${trial.chat} AI chat messages free, no credit card. Smart signals for Gold, Bitcoin and Forex.`,
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
    <AuthShell isAr={isAr} onToggleLang={handleToggleLang}
      eyebrow={tx.tagline}
      title={isAr ? 'ابدأ مجاناً،' : 'Start free,'} titleGrad={isAr ? 'بدون بطاقة ائتمان.' : 'no credit card.'}
      lead={tx.freeTitle.replace(/^✨\s*/u, '')}
      points={tx.freeBenefits.map(fmtTrial)}>
        {/* Referral banner */}
        {ref && (
          <div className="bg-green-900/20 border border-green-700/30 rounded-xl p-3 mb-4 flex items-center gap-2">
            <Gift size={16} className="text-green-400 flex-shrink-0" />
            <p className="text-green-300 text-xs">{tx.referredVia} <span className="font-mono font-bold">{ref}</span></p>
          </div>
        )}

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

          <GoogleAuthButton
            isAr={isAr}
            refCode={ref}
            onSuccess={() => navigate('/dashboard')}
            onError={(msg) => setError(msg)}
          />

          <p className="text-center text-sm text-gray-500 mt-6">
            {tx.haveAccount}{' '}
            <Link to={isAr ? '/login' : '/en/login'} className="text-blue-400 hover:text-blue-300">{tx.login}</Link>
          </p>
        </div>
    </AuthShell>
  )
}
