import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { X, ChevronRight, ChevronLeft, Sparkles, Layers, SlidersHorizontal, Play, Bot, FolderOpen } from 'lucide-react'

const STORAGE_KEY = 'strategy_tour_done_v1'

const STEPS = [
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
    desc: 'كل شرط له وزن (Weight) يُحتسب بالسكور الكلي فقط لو تحقق فعليًا. اضبط الحد الأدنى لتفعيل الاستراتيجية من نفس التبويب.',
  },
  {
    icon: <Play size={28} className="text-teal-400" />,
    title: 'المحاكاة (Simulation)',
    desc: 'جرّب استراتيجيتك مقابل بيانات سوق حقيقية فورًا — قبل ما تحفظ أو تفعّل أي شي.',
  },
  {
    icon: <Bot size={28} className="text-green-400" />,
    title: 'المراقبة الحية وTelegram',
    desc: 'بعد التفعيل، الخادم يفحص استراتيجيتك تلقائيًا كل 5 دقائق ويرسلك تنبيه Telegram حقيقي عند تحقق الشروط.',
  },
  {
    icon: <FolderOpen size={28} className="text-gold" />,
    title: 'جاهز؟ 🚀',
    desc: 'الحفظ والتفعيل والمراقبة الحقيقية حصرية للمشتركين. جرّب البناء والمحاكاة الآن مجانًا، واشترك متى قررت تفعيلها فعليًا.',
  },
]

export default function StrategyBuilderTour({ isPaid, forceOpen, onForceClose }) {
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
        dir="rtl"
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
                عرض باقات الاشتراك
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
              <ChevronRight size={16} /> السابق
            </button>
            <button onClick={dismiss} className="text-xs text-gray-400 hover:text-gray-400 transition-colors">تخطي</button>
            <button onClick={next}
              className={`flex items-center gap-1.5 text-sm font-semibold px-4 py-1.5 rounded-lg transition-all ${
                isLast
                  ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white'
                  : 'bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white'
              }`}
            >
              {isLast ? 'ابدأ البناء 🚀' : 'التالي'}
              {!isLast && <ChevronLeft size={16} />}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
