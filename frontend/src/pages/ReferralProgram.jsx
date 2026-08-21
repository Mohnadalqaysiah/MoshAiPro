import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useLang } from '../contexts/LangContext'
import { useAuth } from '../contexts/AuthContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import { mirrorPath } from '../utils/langRoutes'
import {
  Gift, Users, DollarSign, Star, ChevronRight, ChevronLeft,
  Share2, CheckCircle, Zap, TrendingUp, Shield, Copy, ArrowUpRight
} from 'lucide-react'

// ── Scroll reveal ──────────────────────────────────────────────────────
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.rv, .rv-left')
    const io = new IntersectionObserver(
      (entries) => entries.forEach(e => {
        if (e.isIntersecting) e.target.classList.add('visible')
      }),
      { threshold: 0.12 }
    )
    els.forEach(el => io.observe(el))
    return () => io.disconnect()
  }, [])
}

// ── Animated number ────────────────────────────────────────────────────
function AnimNum({ value, prefix = '', suffix = '' }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current; if (!el) return
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return
      io.disconnect()
      let cur = 0; const end = parseInt(value) || 0
      if (!end) { el.textContent = prefix + value + suffix; return }
      const step = Math.ceil(end / (1600 / 16))
      const t = setInterval(() => {
        cur = Math.min(cur + step, end)
        el.textContent = prefix + cur.toLocaleString() + suffix
        if (cur >= end) clearInterval(t)
      }, 16)
    }, { threshold: 0.5 })
    io.observe(el)
    return () => io.disconnect()
  }, [value, prefix, suffix])
  return <span ref={ref}>{prefix}{value}{suffix}</span>
}

const T = {
  ar: {
    dir: 'rtl',
    nav: { home: 'الرئيسية', login: 'تسجيل الدخول', start: 'ابدأ مجاناً' },
    hero: {
      badge: '💰 برنامج الإحالات',
      title: 'اربح معنا من كل',
      titleHL: 'إحالة ناجحة',
      sub: 'شارك رابطك الخاص مع أصدقائك واحصل على عمولة تصل إلى 15% من كل اشتراك يشترك عبر رابطك — مدى الحياة.',
      cta: 'ابدأ الربح الآن',
      ctaSub: 'سجّل مجاناً وابدأ فوراً',
    },
    stats: [
      { v: '15', s: '%', label: 'أعلى عمولة' },
      { v: '0', s: '$', label: 'رسوم الانضمام' },
      { v: '24', s: 'ساعة', label: 'دفع سريع' },
      { v: '2', s: 'مستوى', label: 'نظام العمولات' },
    ],
    how: {
      title: 'كيف يعمل البرنامج؟',
      steps: [
        { icon: Share2,     title: 'شارك رابطك',          desc: 'سجّل حساباً واحصل على رابط إحالة فريد خاص بك.' },
        { icon: Users,      title: 'أحل أصدقاءك',          desc: 'شارك الرابط — كل من يسجّل عبره يُحسب إحالة لك.' },
        { icon: DollarSign, title: 'اجمع عمولتك',          desc: 'تحصل تلقائياً على نسبتك من كل اشتراك مدفوع.' },
      ],
    },
    tiers: {
      title: 'مستويات العمولة',
      sub: 'كلما أحلت أكثر، زادت نسبتك',
      t1: {
        name: 'البرونزي', badge: '🥉',
        rate: '5%', threshold: 'من 0 إحالة',
        perks: ['عمولة 5% على كل اشتراك', 'دفع فوري عند الطلب', 'لوحة تتبع مباشرة', 'دعم 24/7'],
      },
      t2: {
        name: 'الذهبي', badge: '🥇',
        rate: '15%', threshold: 'من 25 إحالة ناجحة',
        perks: ['عمولة 15% على كل اشتراك', 'أولوية في الدفع', 'تقارير مفصّلة', 'مدير حساب خاص'],
        highlight: true,
      },
    },
    calc: {
      title: 'احسب أرباحك',
      sub: 'مثال واقعي: 20 مشترك شهري بالباقة الشهرية',
      rows: [
        { label: '20 مشتركاً × $30/شهر', val: '$600 دخل للمنصة' },
        { label: 'عمولتك (5% برونزي)', val: '$30 / شهر', hl: true },
        { label: 'بعد 25 إحالة → ذهبي 15%', val: '$90 / شهر', hl: true, gold: true },
        { label: '50 مشتركاً × 15% ذهبي', val: '$225 / شهر', hl: true, gold: true },
      ],
    },
    faq: {
      title: 'أسئلة شائعة',
      items: [
        { q: 'هل الانضمام مجاني؟', a: 'نعم، البرنامج مجاني تماماً لجميع المستخدمين المسجّلين.' },
        { q: 'متى أستلم العمولة؟', a: 'بمجرد وصول رصيدك للحد الأدنى يمكنك طلب السحب وسيُعالج خلال 24 ساعة.' },
        { q: 'كيف أنتقل للمستوى الذهبي؟', a: '25 إحالة ناجحة (تسديد اشتراك) ترقّيك تلقائياً للمستوى الذهبي بعمولة 15%.' },
        { q: 'هل العمولة تستمر مع تجديد الاشتراكات؟', a: 'نعم، تحصل على عمولة على كل دفعة جديدة يقوم بها المستخدم المُحال.' },
      ],
    },
    cta2: {
      title: 'ابدأ الربح اليوم',
      sub: 'انضم إلى مئات المستخدمين الذين يربحون مع Qaffel AI',
      btn: 'إنشاء حساب مجاني',
      login: 'لديك حساب؟ سجّل دخولك',
    },
  },
  en: {
    dir: 'ltr',
    nav: { home: 'Home', login: 'Login', start: 'Start Free' },
    hero: {
      badge: '💰 Referral Program',
      title: 'Earn with every',
      titleHL: 'successful referral',
      sub: 'Share your unique link with friends and earn up to 15% commission on every subscription — for life.',
      cta: 'Start Earning Now',
      ctaSub: 'Register free and start immediately',
    },
    stats: [
      { v: '15', s: '%', label: 'Max Commission' },
      { v: '0', s: '$', label: 'Joining Fee' },
      { v: '24', s: 'hrs', label: 'Fast Payout' },
      { v: '2', s: 'tiers', label: 'Commission Levels' },
    ],
    how: {
      title: 'How Does It Work?',
      steps: [
        { icon: Share2,     title: 'Share Your Link',       desc: 'Register an account and get your unique referral link.' },
        { icon: Users,      title: 'Refer Friends',          desc: 'Share the link — everyone who signs up counts as your referral.' },
        { icon: DollarSign, title: 'Collect Commissions',   desc: 'Automatically earn your percentage from every paid subscription.' },
      ],
    },
    tiers: {
      title: 'Commission Tiers',
      sub: 'The more you refer, the more you earn',
      t1: {
        name: 'Bronze', badge: '🥉',
        rate: '5%', threshold: 'Starting from 0 referrals',
        perks: ['5% commission on every subscription', 'On-demand payouts', 'Live tracking dashboard', '24/7 support'],
      },
      t2: {
        name: 'Gold', badge: '🥇',
        rate: '15%', threshold: 'After 25 successful referrals',
        perks: ['15% commission on every subscription', 'Priority payouts', 'Detailed analytics', 'Dedicated account manager'],
        highlight: true,
      },
    },
    calc: {
      title: 'Calculate Your Earnings',
      sub: 'Real example: 20 monthly subscribers at $30/mo',
      rows: [
        { label: '20 subscribers × $30/mo', val: '$600 platform revenue' },
        { label: 'Your cut (5% Bronze)', val: '$30 / month', hl: true },
        { label: 'After 25 referrals → Gold 15%', val: '$90 / month', hl: true, gold: true },
        { label: '50 subscribers × 15% Gold', val: '$225 / month', hl: true, gold: true },
      ],
    },
    faq: {
      title: 'Frequently Asked Questions',
      items: [
        { q: 'Is joining free?', a: 'Yes, the program is completely free for all registered users.' },
        { q: 'When do I receive my commission?', a: 'Once your balance reaches the minimum threshold, you can request a payout processed within 24 hours.' },
        { q: 'How do I reach Gold tier?', a: '25 successful referrals (with paid subscription) automatically upgrades you to Gold tier with 15% commission.' },
        { q: 'Do I earn on subscription renewals?', a: 'Yes, you earn a commission on every new payment made by your referred users.' },
      ],
    },
    cta2: {
      title: 'Start Earning Today',
      sub: 'Join hundreds of users already earning with Qaffel AI',
      btn: 'Create Free Account',
      login: 'Already have an account? Log in',
    },
  },
}

export default function ReferralProgram() {
  const { lang, toggle } = useLang()
  const { user } = useAuth()
  const isAr = lang === 'ar'

  useSEO({
    title: isAr
      ? 'برنامج الإحالات | Qaffel AI — اربح بدعوة أصدقائك'
      : 'Referral Program | Qaffel AI — Earn by Inviting Friends',
    description: isAr
      ? 'انضم لبرنامج إحالات Qaffel AI واكسب عمولة على كل مشترك تدعوه. دخل سلبي مستمر من منصة إشارات التداول الذكية.'
      : 'Join the Qaffel AI referral program and earn a commission on every subscriber you invite. Ongoing passive income from a smart trading signals platform.',
  })
  const tx = T[isAr ? 'ar' : 'en']
  const ChevronCta = isAr ? ChevronLeft : ChevronRight
  const [openFaq, setOpenFaq] = useState(null)
  const location = useLocation()
  const navigate  = useNavigate()
  useReveal()

  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'الإحالات' : 'Referrals', path: isAr ? '/referral' : '/en/referral' },
  ])

  const handleToggleLang = () => {
    const target = isAr ? 'en' : 'ar'
    const mirror = mirrorPath(location.pathname, target)
    toggle()
    if (mirror && mirror !== location.pathname) navigate(mirror)
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-white overflow-x-hidden" dir={tx.dir}>

      {/* ── Navbar ────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-[#070b14]/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <img src="/brand/logo-icon-only.png" alt="Qaffel AI" className="w-9 h-9 rounded-xl shadow-lg shadow-blue-500/30" />
            <span className="font-bold text-lg tracking-tight">
              Qaffel <span className="text-blue-400">AI</span>
            </span>
          </Link>
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={handleToggleLang}
              className="text-xs border border-white/10 hover:border-blue-500/50 text-gray-400 hover:text-white px-3 py-1.5 rounded-lg transition-all font-medium">
              {isAr ? 'EN' : 'ع'}
            </button>
            {user ? (
              <Link to="/affiliate"
                className="text-sm bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white px-4 py-2 rounded-xl font-semibold transition-all shadow-md">
                {isAr ? 'لوحتي' : 'My Dashboard'}
              </Link>
            ) : (
              <>
                <Link to="/login" className="hidden md:block text-sm text-gray-400 hover:text-white px-4 py-2 rounded-xl hover:bg-white/5 transition-colors">
                  {tx.nav.login}
                </Link>
                <Link to="/register" className="text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-xl font-semibold transition-all shadow-md">
                  {tx.nav.start}
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="relative pt-24 pb-20 overflow-hidden">
        {/* Orbs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-orange-500/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute top-1/3 right-0 w-64 h-64 bg-blue-500/8 rounded-full blur-[80px] pointer-events-none" />

        <div className="max-w-4xl mx-auto px-4 text-center relative z-10">
          <div className="animate-fade-up inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 text-sm px-4 py-2 rounded-full mb-6 font-medium">
            <Gift size={14} /> {tx.hero.badge}
          </div>
          <h1 className="animate-fade-up delay-100 text-4xl sm:text-5xl md:text-6xl font-black leading-tight mb-6">
            {tx.hero.title}{' '}
            <span className="bg-gradient-to-r from-yellow-400 via-orange-400 to-yellow-300 bg-clip-text text-transparent">
              {tx.hero.titleHL}
            </span>
          </h1>
          <p className="animate-fade-up delay-200 text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed mb-8">
            {tx.hero.sub}
          </p>
          <div className="animate-fade-up delay-300 flex flex-col sm:flex-row items-center justify-center gap-3">
            {user ? (
              <Link to="/affiliate"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-lg shadow-yellow-500/25 hover:shadow-yellow-500/40 hover:-translate-y-0.5">
                <ArrowUpRight size={20} /> {isAr ? 'اذهب للوحة الإحالات' : 'Go to My Referrals'}
              </Link>
            ) : (
              <Link to="/register"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-lg shadow-yellow-500/25 hover:shadow-yellow-500/40 hover:-translate-y-0.5">
                {tx.hero.cta} <ChevronCta size={20} />
              </Link>
            )}
            <p className="text-sm text-gray-500">{tx.hero.ctaSub}</p>
          </div>
        </div>
      </section>

      {/* ── Stats ─────────────────────────────────────────────────────── */}
      <section className="py-12 border-y border-white/5 bg-white/[0.01]">
        <div className="max-w-4xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {tx.stats.map((s, i) => (
              <div key={i} className={`rv delay-${(i+1)*100}`}>
                <p className="text-3xl font-black text-yellow-400">
                  <AnimNum value={s.v} suffix={s.s} />
                </p>
                <p className="text-sm text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ──────────────────────────────────────────────── */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-14 rv">
            <h2 className="text-3xl font-bold mb-3">{tx.how.title}</h2>
            <div className="w-16 h-1 bg-gradient-to-r from-yellow-400 to-orange-400 rounded-full mx-auto" />
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {tx.how.steps.map(({ icon: Icon, title, desc }, i) => (
              <div key={i} className={`rv delay-${(i+1)*150} relative text-center`}>
                {/* Connector line */}
                {i < tx.how.steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 start-1/2 w-full h-px bg-gradient-to-r from-yellow-500/30 to-transparent" />
                )}
                <div className="relative z-10 w-16 h-16 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-yellow-500/20 to-orange-500/10 border border-yellow-500/20 flex items-center justify-center">
                  <Icon size={26} className="text-yellow-400" />
                  <span className="absolute -top-2 -end-2 w-6 h-6 rounded-full bg-gradient-to-br from-yellow-500 to-orange-500 flex items-center justify-center text-xs font-bold text-white">
                    {i + 1}
                  </span>
                </div>
                <h3 className="text-lg font-bold mb-2">{title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Tiers ─────────────────────────────────────────────────────── */}
      <section className="py-20 bg-white/[0.015]">
        <div className="max-w-4xl mx-auto px-4">
          <div className="text-center mb-14 rv">
            <h2 className="text-3xl font-bold mb-2">{tx.tiers.title}</h2>
            <p className="text-gray-400">{tx.tiers.sub}</p>
            <div className="w-16 h-1 bg-gradient-to-r from-yellow-400 to-orange-400 rounded-full mx-auto mt-3" />
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {[tx.tiers.t1, tx.tiers.t2].map((tier, i) => (
              <div key={i} className={`rv delay-${(i+1)*150} relative rounded-2xl border p-7 transition-all
                ${tier.highlight
                  ? 'bg-gradient-to-br from-yellow-900/30 via-orange-900/20 to-transparent border-yellow-600/40 shadow-xl shadow-yellow-500/10'
                  : 'bg-gray-900/60 border-gray-800'}`}>
                {tier.highlight && (
                  <div className="absolute -top-3 start-1/2 -translate-x-1/2 rtl:translate-x-1/2 bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-xs font-bold px-4 py-1 rounded-full">
                    {isAr ? '⭐ الأفضل' : '⭐ Best Value'}
                  </div>
                )}
                <div className="text-center mb-6">
                  <span className="text-4xl">{tier.badge}</span>
                  <h3 className="text-xl font-bold mt-2">{tier.name}</h3>
                  <p className={`text-5xl font-black mt-3 ${tier.highlight ? 'text-yellow-400' : 'text-blue-400'}`}>
                    {tier.rate}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{tier.threshold}</p>
                </div>
                <ul className="space-y-3">
                  {tier.perks.map((p, j) => (
                    <li key={j} className="flex items-center gap-2.5 text-sm text-gray-300">
                      <CheckCircle size={15} className={tier.highlight ? 'text-yellow-400' : 'text-blue-400'} />
                      {p}
                    </li>
                  ))}
                </ul>
                <Link to={user ? '/affiliate' : '/register'}
                  className={`mt-6 w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all
                    ${tier.highlight
                      ? 'bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white shadow-lg shadow-yellow-500/20'
                      : 'bg-gray-800 hover:bg-gray-700 text-white border border-gray-700'}`}>
                  {user ? (isAr ? 'اذهب للوحتي' : 'Go to My Dashboard') : (isAr ? 'ابدأ مجاناً' : 'Start Free')}
                  <ChevronCta size={16} />
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Earnings Calculator ───────────────────────────────────────── */}
      <section className="py-20">
        <div className="max-w-3xl mx-auto px-4">
          <div className="text-center mb-10 rv">
            <h2 className="text-3xl font-bold mb-2">{tx.calc.title}</h2>
            <p className="text-gray-400 text-sm">{tx.calc.sub}</p>
          </div>
          <div className="rv delay-200 bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-gray-800">
                {tx.calc.rows.map(({ label, val, hl, gold }, i) => (
                  <tr key={i} className={`px-6 py-4 ${hl ? (gold ? 'bg-yellow-900/20' : 'bg-blue-900/10') : ''}`}>
                    <td className="px-6 py-4 text-gray-400">{label}</td>
                    <td className={`px-6 py-4 font-bold text-end ${gold ? 'text-yellow-400 text-lg' : hl ? 'text-green-400 text-base' : 'text-white'}`}>
                      {val}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-center text-xs text-gray-500 mt-4">
            {isAr ? '* الحسابات تقريبية بناءً على الباقة الشهرية ($30)' : '* Calculations based on monthly plan ($30)'}
          </p>
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────────────── */}
      <section className="py-20 bg-white/[0.015]">
        <div className="max-w-3xl mx-auto px-4">
          <div className="text-center mb-12 rv">
            <h2 className="text-3xl font-bold mb-3">{tx.faq.title}</h2>
            <div className="w-16 h-1 bg-gradient-to-r from-yellow-400 to-orange-400 rounded-full mx-auto" />
          </div>
          <div className="space-y-3">
            {tx.faq.items.map(({ q, a }, i) => (
              <div key={i} className="rv bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                <button
                  className="w-full flex items-center justify-between px-5 py-4 text-start hover:bg-white/[0.02] transition-colors"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}>
                  <span className="font-medium text-white text-sm">{q}</span>
                  <ChevronCta size={16} className={`text-gray-400 transition-transform shrink-0 ${openFaq === i ? 'rotate-90' : ''}`} />
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-4 text-sm text-gray-400 leading-relaxed border-t border-gray-800 pt-3">
                    {a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────────────────── */}
      <section className="py-24 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-yellow-900/20 via-orange-900/10 to-transparent pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-yellow-500/8 rounded-full blur-[100px] pointer-events-none" />

        <div className="max-w-3xl mx-auto px-4 text-center relative z-10">
          <div className="rv">
            <span className="text-5xl mb-6 block">🎁</span>
            <h2 className="text-4xl font-black mb-4">{tx.cta2.title}</h2>
            <p className="text-gray-400 text-lg mb-8">{tx.cta2.sub}</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              {user ? (
                <Link to="/affiliate"
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-xl shadow-yellow-500/20 hover:-translate-y-1">
                  <Gift size={20} /> {isAr ? 'لوحة الإحالات' : 'Referral Dashboard'}
                </Link>
              ) : (
                <>
                  <Link to="/register"
                    className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-xl shadow-yellow-500/20 hover:-translate-y-1">
                    <Gift size={20} /> {tx.cta2.btn}
                  </Link>
                  <Link to="/login" className="text-sm text-gray-400 hover:text-white transition-colors">
                    {tx.cta2.login}
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-8 text-center text-sm text-gray-400">
        <p>© 2025 Qaffel AI — <Link to="/" className="hover:text-gray-400 transition-colors">{isAr ? 'الصفحة الرئيسية' : 'Home'}</Link></p>
      </footer>
    </div>
  )
}
