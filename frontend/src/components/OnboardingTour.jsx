import { useState, useEffect } from 'react'
import axios from 'axios'
import { Link } from 'react-router-dom'
import { X, ChevronRight, ChevronLeft, Zap, BarChart2, Activity,
         MessageCircle, TrendingUp, Send, CheckCircle, Settings2 } from 'lucide-react'
import { useLang } from '../contexts/LangContext'
import { useAuth } from '../contexts/AuthContext'

const STORAGE_KEY = 'onboarding_done_v2'   // v2 so existing users see new onboarding
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// (2026-09-23) خطوة اختيار الأسواق أُزيلت من الجولة — قرار صاحب المنتج:
// التخصيص يتم حصراً من صفحة الحساب (Profile.jsx#watchlist)، والديفولت
// دائماً "كل الرموز" (notify_watchlist فاضي). كانت هاي الخطوة أصلاً معطوبة
// وما بتُحفظ فعلياً (كانت ترسل لـ endpoint غير موجود)، فإزالتها لا تغيّر
// أي سلوك حالي للمستخدمين — فقط تشيل خطوة كانت توهم بأنها تعمل.
const STEPS_AR = [
  {
    icon: <Activity size={28} className="text-blue-400" />,
    title: 'مرحباً بك في Qaffel AI! 👋',
    desc: 'منصة تداول ذكية بتحليل Smart Money Concepts + ذكاء اصطناعي. سنعدّ المنصة لك في 30 ثانية.',
  },
  {
    icon: <Zap size={28} className="text-yellow-400" />,
    title: 'التحليل السريع',
    desc: 'من لوحة التحكم، اضغط على أي رمز للحصول على تحليل ICT كامل: اتجاه، دخول، وقف، وأهداف — في ثوانٍ.',
  },
  {
    icon: <BarChart2 size={28} className="text-purple-400" />,
    title: 'تنبيهات Telegram',
    desc: 'اربط حسابك بـ @Qaffelbot ليصلك كل إشارة مباشرة على هاتفك مع الدخول والوقف والأهداف.',
  },
  {
    icon: <MessageCircle size={28} className="text-indigo-400" />,
    title: 'المساعد الذكي',
    desc: 'الزر الدائر أسفل الشاشة — اسأله أي سؤال عن الأسواق، يحلل ويشرح بالعربي مدعوماً بـ Gemini AI.',
  },
  {
    icon: <TrendingUp size={28} className="text-green-400" />,
    title: 'أنت جاهز! 🚀',
    desc: 'ستصلك إشارات كل الأسواق افتراضياً. حابب تركّز على رموز معينة؟ خصّصها لاحقاً من صفحة حسابك.',
    linkTo: '/profile#watchlist',
    linkLabel: 'تخصيص الرموز من صفحة الحساب',
  },
]

const STEPS_EN = [
  {
    icon: <Activity size={28} className="text-blue-400" />,
    title: 'Welcome to Qaffel AI! 👋',
    desc: 'Smart trading platform powered by Smart Money Concepts + AI. Let\'s set it up for you in 30 seconds.',
  },
  {
    icon: <Zap size={28} className="text-yellow-400" />,
    title: 'Quick Analysis',
    desc: 'From the Dashboard, click any symbol for a full ICT analysis: direction, entry, stop loss, and targets — in seconds.',
  },
  {
    icon: <BarChart2 size={28} className="text-purple-400" />,
    title: 'Telegram Alerts',
    desc: 'Link your account to @Qaffelbot to receive every signal directly on your phone with full trade details.',
  },
  {
    icon: <MessageCircle size={28} className="text-indigo-400" />,
    title: 'AI Assistant',
    desc: 'The floating button at the bottom — ask anything about markets. Analyzes and explains, powered by Gemini AI.',
  },
  {
    icon: <TrendingUp size={28} className="text-green-400" />,
    title: "You're Ready! 🚀",
    desc: 'You\'ll get signals for all markets by default. Want to focus on specific symbols? Customize that anytime from your account page.',
    linkTo: '/profile#watchlist',
    linkLabel: 'Customize symbols from your account',
  },
]

// ── Main Component ───────────────────────────────────────────────────────────
export default function OnboardingTour() {
  const { lang } = useLang()
  const { user }  = useAuth()
  const isAr = lang === 'ar'
  const steps = isAr ? STEPS_AR : STEPS_EN

  const [visible,   setVisible]   = useState(false)
  const [step,      setStep]      = useState(0)
  const [tgLink,    setTgLink]    = useState('')
  const [tgBot,     setTgBot]     = useState('Qaffelbot')

  const totalSteps  = steps.length
  const currentStepData = steps[step]
  const isLast       = step === totalSteps - 1
  const isTelegramStep = step === 2

  useEffect(() => {
    if (isTelegramStep && user && !user.telegram_linked && !tgLink) {
      axios.get(`${API}/api/v1/auth/telegram-link`)
        .then(r => {
          setTgLink(r.data.link)
          if (r.data.bot_username) setTgBot(r.data.bot_username)
        })
        .catch(() => {})
    }
  }, [isTelegramStep, user, tgLink])

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY)
    if (!done) {
      const t = setTimeout(() => setVisible(true), 1200)
      return () => clearTimeout(t)
    }
  }, [])

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1')
    setVisible(false)
  }

  const next = () => {
    if (step < totalSteps - 1) setStep(s => s + 1)
    else dismiss()
  }

  const prev = () => setStep(s => Math.max(0, s - 1))

  if (!visible) return null

  const progressPct = ((step + 1) / totalSteps) * 100

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-[9998] bg-black/60 backdrop-blur-sm" onClick={dismiss} />

      {/* Tour Card */}
      <div
        className="fixed z-[9999] bottom-6 left-1/2 -translate-x-1/2 w-full max-w-sm px-4"
        dir={isAr ? 'rtl' : 'ltr'}
        onClick={e => e.stopPropagation()}
      >
        <div className="bg-[#0f1724] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
          {/* Progress bar */}
          <div className="h-0.5 bg-gray-800">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Header */}
          <div className="flex items-center justify-between px-5 pt-4 pb-0">
            <span className="text-xs text-gray-500">{step + 1} / {totalSteps}</span>
            <button onClick={dismiss} className="text-gray-500 hover:text-white transition-colors p-1">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="px-5 py-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/8 flex items-center justify-center flex-shrink-0">
                {currentStepData?.icon}
              </div>
              <h3 className="font-bold text-white text-base leading-snug">
                {currentStepData?.title}
              </h3>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">
              {currentStepData?.desc}
            </p>

            {isTelegramStep && (
              user?.telegram_linked ? (
                <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-medium">
                  <CheckCircle size={14} />
                  {isAr ? 'حسابك مربوط بتيليجرام بالفعل ✅' : 'Your account is already linked ✅'}
                </div>
              ) : tgLink ? (
                <a
                  href={tgLink}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-center gap-2 w-full bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all"
                >
                  <Send size={15} />
                  {isAr ? `ربط الآن مع @${tgBot}` : `Link now with @${tgBot}`}
                </a>
              ) : (
                <div className="text-center text-xs text-gray-500 py-2">
                  {isAr ? 'جاري تجهيز الرابط...' : 'Preparing link...'}
                </div>
              )
            )}

            {currentStepData?.linkTo && (
              <Link
                to={currentStepData.linkTo}
                onClick={dismiss}
                className="flex items-center justify-center gap-1.5 w-full text-xs text-blue-400 hover:text-blue-300 border border-blue-500/20 hover:border-blue-500/40 bg-blue-500/5 px-4 py-2 rounded-xl transition-all"
              >
                <Settings2 size={13} />
                {currentStepData.linkLabel}
              </Link>
            )}
          </div>

          {/* Dots */}
          <div className="flex justify-center gap-1.5 pb-3">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <button key={i} onClick={() => setStep(i)}
                className={`rounded-full transition-all ${
                  i === step ? 'w-5 h-1.5 bg-blue-500' : 'w-1.5 h-1.5 bg-gray-700 hover:bg-gray-500'
                }`}
              />
            ))}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-white/6">
            <button
              onClick={prev}
              disabled={step === 0}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-white disabled:opacity-30 transition-colors"
            >
              {isAr ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
              {isAr ? 'السابق' : 'Back'}
            </button>

            <button onClick={dismiss} className="text-xs text-gray-400 hover:text-gray-400 transition-colors">
              {isAr ? 'تخطي' : 'Skip'}
            </button>

            <button
              onClick={next}
              className={`flex items-center gap-1.5 text-sm font-semibold px-4 py-1.5 rounded-lg transition-all ${
                isLast
                  ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white'
              }`}
            >
              {isLast
                ? (isAr ? 'ابدأ الآن 🚀' : 'Get Started 🚀')
                : (isAr ? 'التالي' : 'Next')
              }
              {!isLast && (isAr ? <ChevronLeft size={16} /> : <ChevronRight size={16} />)}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
