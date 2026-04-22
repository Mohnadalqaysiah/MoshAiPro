import { useState, useEffect } from 'react'
import { X, ChevronRight, ChevronLeft, Zap, BarChart2, Activity, MessageCircle, TrendingUp } from 'lucide-react'
import { useLang } from '../contexts/LangContext'

const STORAGE_KEY = 'onboarding_done_v1'

const STEPS_AR = [
  {
    icon: <Activity size={28} className="text-blue-400" />,
    title: 'مرحباً بك في المنصة! 👋',
    desc: 'منصة تداول ذكية مبنية على تحليل Smart Money Concepts مع الذكاء الاصطناعي. دعنا نريك كيف تستخدمها في دقيقتين.',
    highlight: null,
  },
  {
    icon: <Zap size={28} className="text-yellow-400" />,
    title: 'التحليل السريع',
    desc: 'من لوحة التحكم، اضغط على أي رمز (XAUUSD، NAS100...) لتحصل فوراً على تحليل ICT كامل: اتجاه، نقطة دخول، وقف الخسارة، وأهداف الربح.',
    highlight: 'quick-analyze',
  },
  {
    icon: <Zap size={28} className="text-green-400" />,
    title: 'صفحة الإشارات',
    desc: 'في صفحة الإشارات ستجد كل التحليلات مرتبة حسب الثقة والوقت. يمكنك فلترة الإشارات حسب الرمز والاتجاه.',
    highlight: 'nav-signals',
  },
  {
    icon: <BarChart2 size={28} className="text-purple-400" />,
    title: 'الأداء التاريخي',
    desc: 'في صفحة الأداء التاريخي، ستجد إحصائيات دقيقة لكل رمز وإطار زمني: نسبة الفوز، متوسط R/R، وآخر 5 صفقات.',
    highlight: 'nav-backtesting',
  },
  {
    icon: <MessageCircle size={28} className="text-indigo-400" />,
    title: 'المساعد الذكي',
    desc: 'الزر الدائر في أسفل الشاشة هو مساعد AI يجيب على أسئلتك عن الأسواق، يحلل الرموز، ويشرح مفاهيم التداول باللغة العربية.',
    highlight: 'chatbot',
  },
  {
    icon: <TrendingUp size={28} className="text-orange-400" />,
    title: 'أنت جاهز! 🚀',
    desc: 'ابدأ بتحليل XAUUSD أو أي سوق تريده. الإشارات ترسل أيضاً على Telegram تلقائياً إذا ربطت حسابك. حظ موفق!',
    highlight: null,
  },
]

const STEPS_EN = [
  {
    icon: <Activity size={28} className="text-blue-400" />,
    title: 'Welcome to the Platform! 👋',
    desc: 'An intelligent trading platform built on Smart Money Concepts analysis with AI. Let us show you how to use it in two minutes.',
    highlight: null,
  },
  {
    icon: <Zap size={28} className="text-yellow-400" />,
    title: 'Quick Analysis',
    desc: 'From the Dashboard, click any symbol (XAUUSD, NAS100...) to instantly get a full ICT analysis: direction, entry point, stop loss, and profit targets.',
    highlight: 'quick-analyze',
  },
  {
    icon: <Zap size={28} className="text-green-400" />,
    title: 'Signals Page',
    desc: 'The Signals page shows all analyses sorted by confidence and time. You can filter by symbol and direction.',
    highlight: 'nav-signals',
  },
  {
    icon: <BarChart2 size={28} className="text-purple-400" />,
    title: 'Backtesting',
    desc: 'The Backtesting page shows detailed stats per symbol and timeframe: win rate, average R/R, and last 5 trades.',
    highlight: 'nav-backtesting',
  },
  {
    icon: <MessageCircle size={28} className="text-indigo-400" />,
    title: 'AI Assistant',
    desc: 'The floating button at the bottom is an AI assistant that answers market questions, analyzes symbols, and explains trading concepts.',
    highlight: 'chatbot',
  },
  {
    icon: <TrendingUp size={28} className="text-orange-400" />,
    title: "You're Ready! 🚀",
    desc: 'Start by analyzing XAUUSD or any market you want. Signals are also sent to Telegram automatically if you link your account. Good luck!',
    highlight: null,
  },
]

export default function OnboardingTour() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const steps = isAr ? STEPS_AR : STEPS_EN

  const [visible, setVisible] = useState(false)
  const [step, setStep]       = useState(0)

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY)
    if (!done) {
      // slight delay so dashboard loads first
      const t = setTimeout(() => setVisible(true), 1200)
      return () => clearTimeout(t)
    }
  }, [])

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1')
    setVisible(false)
  }

  const next = () => {
    if (step < steps.length - 1) setStep(s => s + 1)
    else dismiss()
  }

  const prev = () => setStep(s => Math.max(0, s - 1))

  if (!visible) return null

  const current = steps[step]
  const isLast  = step === steps.length - 1

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[9998] bg-black/50 backdrop-blur-sm"
        onClick={dismiss}
      />

      {/* Tour Card */}
      <div
        className="fixed z-[9999] bottom-6 left-1/2 -translate-x-1/2 w-full max-w-sm px-4"
        dir={isAr ? 'rtl' : 'ltr'}
        onClick={e => e.stopPropagation()}
      >
        <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl overflow-hidden animate-scale-in">
          {/* Progress bar */}
          <div className="h-1 bg-gray-800">
            <div
              className="h-full bg-blue-500 transition-all duration-500"
              style={{ width: `${((step + 1) / steps.length) * 100}%` }}
            />
          </div>

          {/* Header */}
          <div className="flex items-center justify-between px-5 pt-4 pb-0">
            <span className="text-xs text-gray-500">{step + 1} / {steps.length}</span>
            <button
              onClick={dismiss}
              className="text-gray-500 hover:text-white transition-colors p-1"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="px-5 py-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center flex-shrink-0">
                {current.icon}
              </div>
              <h3 className="font-bold text-white text-base leading-snug">{current.title}</h3>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">{current.desc}</p>
          </div>

          {/* Step dots */}
          <div className="flex justify-center gap-1.5 pb-3">
            {steps.map((_, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={`rounded-full transition-all ${
                  i === step
                    ? 'w-5 h-1.5 bg-blue-500'
                    : 'w-1.5 h-1.5 bg-gray-700 hover:bg-gray-500'
                }`}
              />
            ))}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-800">
            <button
              onClick={prev}
              disabled={step === 0}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-white disabled:opacity-30 transition-colors"
            >
              {isAr ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
              {isAr ? 'السابق' : 'Back'}
            </button>

            <button
              onClick={dismiss}
              className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
            >
              {isAr ? 'تخطي الجولة' : 'Skip tour'}
            </button>

            <button
              onClick={next}
              className={`flex items-center gap-1 text-sm font-semibold px-4 py-1.5 rounded-lg transition-all ${
                isLast
                  ? 'bg-green-600 hover:bg-green-500 text-white'
                  : 'bg-blue-600 hover:bg-blue-500 text-white'
              }`}
            >
              {isLast
                ? (isAr ? 'ابدأ الآن' : 'Get Started')
                : (isAr ? 'التالي' : 'Next')}
              {!isLast && (isAr ? <ChevronLeft size={16} /> : <ChevronRight size={16} />)}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
