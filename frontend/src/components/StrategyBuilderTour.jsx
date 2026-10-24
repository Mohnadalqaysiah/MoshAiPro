import { useState, useEffect } from 'react'
import { useLang } from '../contexts/LangContext'
import { Link } from 'react-router-dom'
import { X, ChevronRight, ChevronLeft, Sparkles, Layers, SlidersHorizontal, ShieldCheck, Bot, FolderOpen } from 'lucide-react'

const STORAGE_KEY = 'strategy_tour_done_v1'

const STEPS_AR = [
  {
    icon: <Sparkles size={28} className="text-amber-400" />,
    title: 'أهلاً بك في Strategy Builder 🎯',
    desc: 'بنى استراتيجيتك الخاصة من شروط ICT/SMC ومؤشرات فنية حقيقية — بدون كتابة كود. جولة سريعة بـ 6 خطوات.',
  },
  {
    icon: <Layers size={28} className="text-purple-400" />,
    title: 'المكتبة والـ Canvas',
    desc: 'اختر شروط من المكتبة يمين الشاشة (ابحث أو تصفّح الفئات)، وأضفها لمجموعات بمنتصف الشاشة. كل مجموعة لها منطق AND / OR / X of Y خاص فيها.',
  },
  {
    icon: <SlidersHorizontal size={28} className="text-blue-400" />,
    title: 'المنطق والسكور',
    desc: 'كل شرط له وزن يُحتسب بالسكور فقط لو تحقق فعلياً. وانتبه: التنبيه يحتاج شرطين معاً — أن يكتمل منطق كل مجموعة (الكل / واحد على الأقل / X من Y)، وأن تبلغ الدرجة الحد الأدنى. فقد ترى درجة فوق حدّك بلا تنبيه لأن مجموعة لم تكتمل.',
  },
  {
    icon: <ShieldCheck size={28} className="text-teal-400" />,
    title: 'كل شرط بالمكتبة شغّال فعلياً',
    desc: 'مكتبة الشروط مقصودة قصدًا على الشروط المربوطة بمحرك التحليل الحقيقي فقط — أي شرط تضيفه بيُحتسب فعليًا بالمراقبة الحية، بدون أي شرط زخرفي.',
  },
  {
    icon: <Bot size={28} className="text-green-400" />,
    title: 'المراقبة الحية وTelegram',
    desc: 'بعد التفعيل، الخادم يفحص استراتيجيتك تلقائيًا كل 5 دقائق ويرسلك تنبيه Telegram حقيقي عند تحقق الشروط.',
  },
  {
    icon: <FolderOpen size={28} className="text-gold" />,
    title: 'جاهز؟ 🚀',
    desc: 'الحفظ والتفعيل والمراقبة الحقيقية حصرية للمشتركين. جرّب البناء الآن مجانًا، واشترك متى قررت تفعيلها فعليًا.',
  },
]

const STEPS_EN = [
  {
    icon: <Sparkles size={28} className="text-amber-400" />,
    title: 'Welcome to Strategy Builder 🎯',
    desc: 'Build your own strategy from real ICT/SMC conditions and technical indicators — no code. A quick 6-step tour.',
  },
  {
    icon: <Layers size={28} className="text-purple-400" />,
    title: 'Library and canvas',
    desc: 'Pick conditions from the library (search or browse categories) and add them to groups in the middle of the screen. Each group has its own AND / OR / X of Y logic.',
  },
  {
    icon: <SlidersHorizontal size={28} className="text-blue-400" />,
    title: 'Logic and score',
    desc: 'Each condition has a weight that counts toward the score only when it is actually met. Note: an alert needs both — every group logic is complete (all / at least one / X of Y) AND the score reaches your minimum. You may see a score above your threshold with no alert because a group is incomplete.',
  },
  {
    icon: <ShieldCheck size={28} className="text-teal-400" />,
    title: 'Every library condition is live',
    desc: 'The library is deliberately limited to conditions wired to the real analysis engine — anything you add is genuinely evaluated by live monitoring. No decorative conditions.',
  },
  {
    icon: <Bot size={28} className="text-green-400" />,
    title: 'Live monitoring and Telegram',
    desc: 'Once activated, the server checks your strategy every 5 minutes and sends you a real Telegram alert when the conditions are met.',
  },
  {
    icon: <FolderOpen size={28} className="text-gold" />,
    title: 'Ready? 🚀',
    desc: 'Saving, activation and live monitoring are for subscribers. Try building now for free, and subscribe whenever you decide to activate it.',
  },
]

export default function StrategyBuilderTour({ isPaid, forceOpen, onForceClose }) {
  const isAr = (useLang()?.lang || 'ar') === 'ar'
  const STEPS = isAr ? STEPS_AR : STEPS_EN
  const [visible, setVisible] = useState(false)
  const [step, setStep] = useState(0)

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY)
    if (!done) {
      const t = setTimeout(() => setVisible(true), 900)
      return () => clearTimeout(t)
    }
  }, [])

  useEffect(() => {
    if (forceOpen) { setStep(0); setVisible(true) }
  }, [forceOpen])

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1')
    setVisible(false)
    onForceClose?.()
  }

  const next = () => {
    if (step < STEPS.length - 1) setStep((s) => s + 1)
    else dismiss()
  }
  const prev = () => setStep((s) => Math.max(0, s - 1))

  if (!visible) return null

  const isLast = step === STEPS.length - 1
  const data = STEPS[step]
  const progressPct = ((step + 1) / STEPS.length) * 100

  return (
    <>
      <div className="fixed inset-0 z-[9998] bg-black/60 backdrop-blur-sm" onClick={dismiss} />
      <div
        className="fixed z-[9999] bottom-6 left-1/2 -translate-x-1/2 w-full max-w-sm px-4"
        dir={isAr ? 'rtl' : 'ltr'}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-[#0f1724] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
          <div className="h-0.5 bg-gray-800">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          <div className="flex items-center justify-between px-5 pt-4 pb-0">
            <span className="text-xs text-gray-500">{step + 1} / {STEPS.length}</span>
            <button onClick={dismiss} className="text-gray-500 hover:text-white transition-colors p-1">
              <X size={16} />
            </button>
          </div>

          <div className="px-5 py-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/8 flex items-center justify-center flex-shrink-0">
                {data.icon}
              </div>
              <h3 className="font-bold text-white text-base leading-snug">{data.title}</h3>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">{data.desc}</p>
            {isLast && !isPaid && (
              <Link to="/pricing" onClick={dismiss} className="block text-center text-xs font-semibold text-amber-400 hover:text-amber-300 border border-amber-500/40 rounded-lg py-2 mt-1">
                {isAr ? 'عرض باقات الاشتراك' : 'View subscription plans'}
              </Link>
            )}
          </div>

          <div className="flex justify-center gap-1.5 pb-3">
            {STEPS.map((_, i) => (
              <button key={i} onClick={() => setStep(i)}
                className={`rounded-full transition-all ${i === step ? 'w-5 h-1.5 bg-amber-500' : 'w-1.5 h-1.5 bg-gray-700 hover:bg-gray-500'}`}
              />
            ))}
          </div>

          <div className="flex items-center justify-between px-5 py-3 border-t border-white/6">
            <button onClick={prev} disabled={step === 0}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-white disabled:opacity-30 transition-colors">
              <ChevronRight size={16} /> {isAr ? 'السابق' : 'Back'}
            </button>
            <button onClick={dismiss} className="text-xs text-gray-400 hover:text-gray-400 transition-colors">{isAr ? 'تخطي' : 'Skip'}</button>
            <button onClick={next}
              className={`flex items-center gap-1.5 text-sm font-semibold px-4 py-1.5 rounded-lg transition-all ${
                isLast
                  ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white'
                  : 'bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white'
              }`}
            >
              {isLast ? (isAr ? 'ابدأ البناء 🚀' : 'Start building 🚀') : (isAr ? 'التالي' : 'Next')}
              {!isLast && <ChevronLeft size={16} />}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
