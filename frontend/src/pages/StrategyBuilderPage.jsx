import { Link } from 'react-router-dom'
import { Layers, Zap, Bell, Gauge, Globe, ArrowRight } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import StrategyBuilderDemo from '../components/StrategyBuilderDemo'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

const T = {
  ar: {
    badge: 'أداة بناء الاستراتيجيات',
    h1a: 'ابنِ استراتيجيتك بنفسك',
    h1b: 'بلا سطر كود واحد',
    heroSub: 'اختر شروط SMC/ICT ومؤشرات فنية حقيقية — Order Block، FVG، اكتساح سيولة، RSI، EMA — واتركها تراقب السوق بدلاً عنك على مدار الساعة. بمجرد ما تتحقق كل شروطك، توصلك رسالة Telegram فورية بالتفاصيل الكاملة.',
    ctaTry: 'جرّب الآن مجاناً',
    ctaLogin: 'افتح الأداة',
    features: [
      { icon: Layers,  title: 'شروط ICT/SMC حقيقية',   desc: 'كسر هيكل، اكتساح سيولة، فجوة سعرية، كتلة أوامر — نفس الأدوات يلي يستخدمها محرك الإشارات.' },
      { icon: Gauge,   title: 'وزن كل شرط بإيدك',       desc: 'حدّد نسبة أهمية كل شرط وعتبة التفعيل — الاستراتيجية تتحقق بس لما تتجاوز الحد يلي حدّدته.' },
      { icon: Bell,    title: 'تنبيه Telegram فوري',    desc: 'المنصة تفحص السوق تلقائياً كل 5 دقائق — ولما تتحقق كل شروطك، توصلك رسالة كاملة بلا ما تفتح الشارت.' },
      { icon: Globe,   title: '25+ سوق مدعوم',          desc: 'ذهب، فضة، بيتكوين وعملات رقمية، فوركس، مؤشرات، وأسواق خليجية زي تداول وأرامكو.' },
    ],
    howTitle: 'كيف تشتغل؟',
    how: [
      { step: '01', title: 'اختر الشروط',      desc: 'من قائمة شروط SMC/ICT ومؤشرات فنية جاهزة — بلا أي كود.' },
      { step: '02', title: 'حدّد العتبة',       desc: 'وزّع الأهمية بين الشروط وحدّد نسبة التفعيل اللي تناسبك.' },
      { step: '03', title: 'فعّلها وراقب',      desc: 'المنصة تراقب السوق بدلاً عنك، وترسلك تنبيه Telegram لحظة التحقق.' },
    ],
  },
  en: {
    badge: 'Strategy Builder',
    h1a: 'Build Your Own Strategy',
    h1b: 'Without Writing Code',
    heroSub: 'Pick real SMC/ICT conditions and technical indicators — Order Block, FVG, Liquidity Sweep, RSI, EMA — and let the platform watch the market for you around the clock. The moment all your conditions align, you get an instant Telegram message with full details.',
    ctaTry: 'Try It Free Now',
    ctaLogin: 'Open The Tool',
    features: [
      { icon: Layers,  title: 'Real ICT/SMC Conditions', desc: 'Break of Structure, Liquidity Sweep, Fair Value Gap, Order Block — the same tools our signal engine uses.' },
      { icon: Gauge,   title: 'Weight Every Condition',   desc: 'Set each condition\'s importance and your activation threshold — the strategy triggers only once it crosses your bar.' },
      { icon: Bell,    title: 'Instant Telegram Alert',   desc: 'The platform auto-checks the market every 5 minutes — once all your conditions align, you get a full alert without opening a chart.' },
      { icon: Globe,   title: '25+ Supported Markets',    desc: 'Gold, Silver, Bitcoin and crypto, Forex, indices, and Gulf markets like Tadawul and Aramco.' },
    ],
    howTitle: 'How It Works',
    how: [
      { step: '01', title: 'Pick Conditions',  desc: 'Choose from ready SMC/ICT conditions and technical indicators — no code needed.' },
      { step: '02', title: 'Set The Threshold', desc: 'Distribute weight across conditions and pick the activation percentage that fits you.' },
      { step: '03', title: 'Activate & Watch',  desc: 'The platform monitors the market for you and sends a Telegram alert the moment it triggers.' },
    ],
  },
}

export default function StrategyBuilderPage() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']

  useSEO({
    title: isAr
      ? 'أداة بناء الاستراتيجيات | Qaffel AI — راقب السوق تلقائياً بشروطك'
      : 'Strategy Builder | Qaffel AI — Monitor The Market On Your Own Terms',
    description: isAr
      ? 'ابنِ استراتيجية تداول بشروط ICT/SMC حقيقية بلا أي كود، والمنصة تراقب السوق تلقائياً وترسلك تنبيه Telegram فوري لحظة تحققها.'
      : 'Build a trading strategy from real ICT/SMC conditions with no code — the platform monitors the market and sends an instant Telegram alert the moment it triggers.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: tx.badge, path: isAr ? '/strategy-builder' : '/en/strategy-builder' },
  ])

  return (
    <PublicLayout>

      {/* Hero */}
      <section className="py-20 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-3xl" />
        </div>
        <div className="max-w-3xl mx-auto relative">
          <div className="inline-flex items-center gap-2 bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Layers size={12} />
            {tx.badge}
          </div>
          <h1 className="text-3xl md:text-5xl font-black mb-5 leading-tight">
            {tx.h1a} <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">{tx.h1b}</span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed mb-8">{tx.heroSub}</p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link
              to={user ? (isAr ? '/strategies' : '/en/strategies') : (isAr ? '/register' : '/en/register')}
              className="group flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white px-8 py-3.5 rounded-2xl font-bold transition-all shadow-xl shadow-indigo-500/20"
            >
              <Zap size={16} className="fill-white" />
              {user ? tx.ctaLogin : tx.ctaTry}
              <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform rtl:rotate-180" />
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {tx.features.map((f, i) => (
            <div key={i} className="glass border border-white/8 rounded-2xl p-5">
              <f.icon size={20} className="text-indigo-400 mb-3" />
              <h3 className="font-bold text-white text-sm mb-1.5">{f.title}</h3>
              <p className="text-gray-400 text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 px-6 bg-white/[0.01]">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-black text-center mb-10">{tx.howTitle}</h2>
          <div className="grid sm:grid-cols-3 gap-6">
            {tx.how.map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-12 h-12 mx-auto rounded-2xl bg-indigo-600/15 border border-indigo-500/25 flex items-center justify-center text-indigo-300 font-black mb-4">
                  {s.step}
                </div>
                <h3 className="font-bold text-white mb-1.5">{s.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Interactive demo — عنده عنوانه ومقدّمته الخاصة أصلاً */}
      <StrategyBuilderDemo isAr={isAr} />

    </PublicLayout>
  )
}
