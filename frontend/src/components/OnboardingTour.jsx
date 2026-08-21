import { useState, useEffect } from 'react'
import axios from 'axios'
import { X, ChevronRight, ChevronLeft, Zap, BarChart2, Activity,
         MessageCircle, TrendingUp, Star } from 'lucide-react'
import { useLang } from '../contexts/LangContext'
import { useAuth } from '../contexts/AuthContext'

const STORAGE_KEY = 'onboarding_done_v2'   // v2 so existing users see new onboarding
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── Market options for the preference step ──────────────────────────────────
const MARKET_OPTIONS = [
  { symbol: 'XAUUSD', label: { ar: '🥇 الذهب',       en: '🥇 Gold'       }, popular: true },
  { symbol: 'BTCUSD', label: { ar: '₿ بيتكوين',      en: '₿ Bitcoin'     }, popular: true },
  { symbol: 'EURUSD', label: { ar: '💶 يورو/دولار',   en: '💶 EUR/USD'    } },
  { symbol: 'GBPUSD', label: { ar: '💷 جنيه/دولار',  en: '💷 GBP/USD'    } },
  { symbol: 'USDJPY', label: { ar: '💴 دولار/ين',    en: '💴 USD/JPY'    } },
  { symbol: 'USOIL',  label: { ar: '🛢 نفط',         en: '🛢 Crude Oil'  } },
  { symbol: 'NAS100', label: { ar: '📈 ناسداك',      en: '📈 NASDAQ'     } },
  { symbol: 'ETHUSD', label: { ar: 'Ξ إيثيريوم',    en: 'Ξ Ethereum'    } },
]

// ── Tour steps (excluding the market-pick step which is rendered separately) ─
const STEPS_AR = [
  {
    icon: <Activity size={28} className="text-blue-400" />,
    title: 'مرحباً بك في Qaffel AI! 👋',
    desc: 'منصة تداول ذكية بتحليل Smart Money Concepts + ذكاء اصطناعي. سنعدّ المنصة لك في 30 ثانية.',
  },
  // step 1 = market picker (special)
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
    desc: 'Watchlist مُعدّ بناءً على اختياراتك — ستصلك الإشارات تلقائياً. حظ موفق وتداول بحكمة!',
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
    desc: 'Your Watchlist is set based on your preferences — signals will arrive automatically. Trade smart!',
  },
]

// ── Market Picker step ───────────────────────────────────────────────────────
function MarketPickerStep({ isAr, selected, onToggle }) {
  return (
    <div className="px-5 py-4">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-blue-500/15 flex items-center justify-center flex-shrink-0">
          <Star size={24} className="text-blue-400 fill-blue-400/30" />
        </div>
        <div>
          <h3 className="font-bold text-white text-base leading-snug">
            {isAr ? 'اختر أسواقك المفضلة' : 'Choose Your Favorite Markets'}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {isAr ? 'سيتم إضافتها لـ Watchlist تلقائياً' : 'They\'ll be added to your Watchlist automatically'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {MARKET_OPTIONS.map(m => {
          const active = selected.includes(m.symbol)
          return (
            <button key={m.symbol}
              onClick={() => onToggle(m.symbol)}
              className={`relative flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                active
                  ? 'bg-blue-600/20 border-blue-500/50 text-blue-300'
                  : 'bg-gray-800/50 border-gray-700/50 text-gray-400 hover:border-gray-600 hover:text-gray-200'
              }`}>
              {m.popular && !active && (
                <span className="absolute -top-1.5 -end-1.5 text-[9px] bg-yellow-500/80 text-black px-1 rounded-full font-bold">
                  {isAr ? 'شائع' : 'Popular'}
                </span>
              )}
              <span>{m.label[isAr ? 'ar' : 'en']}</span>
              {active && <span className="ms-auto text-blue-400 text-xs">✓</span>}
            </button>
          )
        })}
      </div>

      {selected.length === 0 && (
        <p className="text-center text-xs text-gray-400 mt-3">
          {isAr ? 'اختر سوقاً واحداً على الأقل' : 'Select at least one market'}
        </p>
      )}
    </div>
  )
}

// ── Main Component ───────────────────────────────────────────────────────────
export default function OnboardingTour() {
  const { lang } = useLang()
  const { user }  = useAuth()
  const isAr = lang === 'ar'
  const steps = isAr ? STEPS_AR : STEPS_EN

  const [visible,   setVisible]   = useState(false)
  const [step,      setStep]      = useState(0)
  const [markets,   setMarkets]   = useState(['XAUUSD', 'BTCUSD'])   // defaults
  const [saving,    setSaving]    = useState(false)

  // MARKET_PICKER is inserted between step 0 (welcome) and step 1 (features)
  const MARKET_STEP = 1
  const totalSteps  = steps.length + 1   // +1 for market picker

  // Convert logical step → display index (0-based)
  const currentStepData = step < MARKET_STEP ? steps[step]
                        : step === MARKET_STEP ? null   // market picker
                        : steps[step - 1]

  const isMarketStep = step === MARKET_STEP
  const isLast       = step === totalSteps - 1

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY)
    if (!done) {
      const t = setTimeout(() => setVisible(true), 1200)
      return () => clearTimeout(t)
    }
  }, [])

  const toggleMarket = sym => {
    setMarkets(prev =>
      prev.includes(sym)
        ? prev.length > 1 ? prev.filter(s => s !== sym) : prev   // keep min 1
        : [...prev, sym]
    )
  }

  const saveWatchlist = async () => {
    if (!user) return
    try {
      setSaving(true)
      await axios.post(
        `${API}/api/v1/bot/watchlist`,
        { symbols: markets },
        { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } }
      )
    } catch (e) {
      // silent — user can set watchlist manually later
    } finally {
      setSaving(false)
    }
  }

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1')
    setVisible(false)
  }

  const next = async () => {
    // On market step → save watchlist before moving on
    if (isMarketStep) {
      await saveWatchlist()
    }
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
          {isMarketStep ? (
            <MarketPickerStep isAr={isAr} selected={markets} onToggle={toggleMarket} />
          ) : (
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
            </div>
          )}

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
              disabled={saving}
              className={`flex items-center gap-1.5 text-sm font-semibold px-4 py-1.5 rounded-lg transition-all disabled:opacity-60 ${
                isLast
                  ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white'
              }`}
            >
              {saving
                ? (isAr ? 'جاري الحفظ...' : 'Saving...')
                : isLast
                ? (isAr ? 'ابدأ الآن 🚀' : 'Get Started 🚀')
                : isMarketStep
                ? (isAr ? 'حفظ وتابع' : 'Save & Continue')
                : (isAr ? 'التالي' : 'Next')
              }
              {!isLast && !saving && (isAr ? <ChevronLeft size={16} /> : <ChevronRight size={16} />)}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
