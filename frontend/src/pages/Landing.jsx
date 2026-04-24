import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
import {
  TrendingUp, Shield, Zap, Bot, Bell, BarChart2,
  ChevronLeft, ChevronRight, CheckCircle, Star,
  LayoutDashboard, ArrowUpRight, Cpu, Lock, Target, Menu, X
} from 'lucide-react'
import PublicChatBot from '../components/PublicChatBot'
import DemoSection from '../components/DemoSection'
import AffiliateSection from '../components/AffiliateSection'
import PublicPerformance from '../components/PublicPerformance'

// ── Scroll reveal hook ───────────────────────────────────────────────
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.reveal, .reveal-left, .reveal-stagger')
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('visible')
          // stagger children
          e.target.querySelectorAll('.stagger-child').forEach((c, i) => {
            setTimeout(() => c.classList.add('visible'), i * 120)
          })
        }
      }),
      { threshold: 0.12 }
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [])
}

// ── Animated counter ─────────────────────────────────────────────────
function Counter({ target, suffix = '' }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return
      io.disconnect()
      let start = 0
      const end = parseInt(target.replace(/\D/g, '')) || 0
      if (!end) { el.textContent = target; return }
      const dur = 1800
      const step = Math.ceil(end / (dur / 16))
      const t = setInterval(() => {
        start = Math.min(start + step, end)
        el.textContent = start.toLocaleString('ar-EG') + suffix
        if (start >= end) clearInterval(t)
      }, 16)
    }, { threshold: 0.5 })
    io.observe(el)
    return () => io.disconnect()
  }, [target, suffix])
  return <span ref={ref}>{target}</span>
}

const FEATURE_ICONS = [
  <BarChart2 size={22} />,
  <Bot       size={22} />,
  <Bell      size={22} />,
  <TrendingUp size={22} />,
  <Shield    size={22} />,
  <Zap       size={22} />,
]
const FEATURE_COLORS = [
  'from-blue-500/20 to-blue-600/10 border-blue-500/20 text-blue-400',
  'from-purple-500/20 to-purple-600/10 border-purple-500/20 text-purple-400',
  'from-green-500/20 to-green-600/10 border-green-500/20 text-green-400',
  'from-yellow-500/20 to-yellow-600/10 border-yellow-500/20 text-yellow-400',
  'from-red-500/20 to-red-600/10 border-red-500/20 text-red-400',
  'from-cyan-500/20 to-cyan-600/10 border-cyan-500/20 text-cyan-400',
]

export default function Landing() {
  const { user } = useAuth()
  const { lang, toggle, t } = useLang()
  const isAr = lang === 'ar'
  const ChevronCta = isAr ? ChevronLeft : ChevronRight
  const [mobileOpen, setMobileOpen] = useState(false)
  const [livePlans, setLivePlans] = useState({})
  useReveal()

  useEffect(() => {
    axios.get(`${API}/api/v1/subscription/plans`)
      .then(r => { if (r.data.plans) setLivePlans(r.data.plans) })
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-[#070b14] text-white overflow-x-hidden" dir={t.dir}>

      {/* ── Navbar ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-[#070b14]/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-base shadow-lg shadow-blue-500/30 group-hover:shadow-blue-500/50 transition-shadow">
              Q
            </div>
            <span className="font-bold text-lg tracking-tight">
              Qaffel <span className="text-blue-400">AI</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-7 text-sm text-gray-400">
            {[
              { href: '#features',      label: t.nav.features },
              { href: '#testimonials',  label: isAr ? 'آراء العملاء' : 'Reviews' },
              { href: '#pricing',       label: t.nav.pricing },
              { href: '#faq',           label: t.nav.faq },
            ].map(({ href, label }) => (
              <a key={href} href={href}
                className="hover:text-white transition-colors relative group">
                {label}
                <span className="absolute -bottom-0.5 right-0 w-0 h-px bg-blue-400 group-hover:w-full transition-all duration-300" />
              </a>
            ))}
            <Link to="/about"    className="hover:text-white transition-colors">{t.nav.about}</Link>
            <Link to="/contact"  className="hover:text-white transition-colors">{t.nav.contact}</Link>
            <Link to="/referral" className="hover:text-yellow-400 text-yellow-500/80 transition-colors font-medium">
              {isAr ? '💰 الإحالات' : '💰 Referrals'}
            </Link>
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            {/* Language toggle — always visible */}
            <button onClick={toggle}
              className="text-xs border border-white/10 hover:border-blue-500/50 text-gray-400 hover:text-white px-3 py-1.5 rounded-lg transition-all font-medium">
              {isAr ? 'EN' : 'ع'}
            </button>

            {/* Desktop: login / register / dashboard */}
            {user ? (
              <Link to="/dashboard"
                className="hidden md:flex items-center gap-1.5 text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-xl font-semibold transition-all shadow-md shadow-blue-500/20 hover:shadow-blue-500/40">
                <LayoutDashboard size={14} /> {t.nav.dashboard}
              </Link>
            ) : (
              <>
                <Link to="/login"
                  className="hidden md:block text-sm text-gray-400 hover:text-white px-4 py-2 rounded-xl hover:bg-white/5 transition-colors">
                  {t.nav.login}
                </Link>
                <Link to="/register"
                  className="hidden md:block text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-xl font-semibold transition-all shadow-md shadow-blue-500/20 hover:shadow-blue-500/40">
                  {t.nav.start}
                </Link>
              </>
            )}

            {/* Hamburger — mobile only */}
            <button
              className="md:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
              onClick={() => setMobileOpen(o => !o)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {mobileOpen && (
          <div className="md:hidden border-t border-white/5 bg-[#070b14]/95 backdrop-blur-xl px-4 py-4 space-y-1">
            {[
              { href: '#features',      label: t.nav.features },
              { href: '#testimonials',  label: isAr ? 'آراء العملاء' : 'Reviews' },
              { href: '#pricing',       label: t.nav.pricing },
              { href: '#faq',           label: t.nav.faq },
            ].map(({ href, label }) => (
              <a key={href} href={href}
                onClick={() => setMobileOpen(false)}
                className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                {label}
              </a>
            ))}
            <Link to="/about"    onClick={() => setMobileOpen(false)} className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">{t.nav.about}</Link>
            <Link to="/contact"  onClick={() => setMobileOpen(false)} className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">{t.nav.contact}</Link>
            <Link to="/referral" onClick={() => setMobileOpen(false)} className="block py-2.5 px-3 rounded-lg text-sm text-yellow-400/80 hover:text-yellow-400 hover:bg-white/5 transition-colors font-medium">
              💰 {isAr ? 'برنامج الإحالات' : 'Referral Program'}
            </Link>
            <div className="pt-2 border-t border-white/5 space-y-2">
              {user ? (
                <Link to="/dashboard" onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-2 w-full py-2.5 px-3 rounded-xl text-sm bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold">
                  <LayoutDashboard size={14} /> {t.nav.dashboard}
                </Link>
              ) : (
                <>
                  <Link to="/login" onClick={() => setMobileOpen(false)}
                    className="block py-2.5 px-3 rounded-xl text-sm text-center text-gray-300 hover:text-white border border-white/10 hover:border-white/20 transition-colors">
                    {t.nav.login}
                  </Link>
                  <Link to="/register" onClick={() => setMobileOpen(false)}
                    className="block py-2.5 px-3 rounded-xl text-sm text-center bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold">
                    {t.nav.start}
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <section className="relative py-24 md:py-36 px-4 overflow-hidden bg-grid">
        {/* Orbs */}
        <div className="orb w-[500px] h-[500px] bg-blue-600/15 top-0 left-1/2 -translate-x-1/2 -translate-y-1/2" />
        <div className="orb w-[300px] h-[300px] bg-indigo-600/10 bottom-0 right-0" />
        <div className="orb w-[200px] h-[200px] bg-purple-600/10 top-1/3 left-0" />

        <div className="max-w-4xl mx-auto text-center relative animate-fade-up">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-7 animate-pulse-glow">
            <Zap size={11} className="fill-blue-400 text-blue-400" />
            {t.hero.badge}
          </div>

          <h1 className="text-4xl md:text-6xl font-black leading-tight mb-6 tracking-tight">
            <span className="text-white">{t.hero.h1a}</span>
            <br />
            <span className="gradient-text">{t.hero.h1b}</span>
          </h1>

          <p className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed font-light">
            {t.hero.sub}
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/register"
              className="group flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-9 py-3.5 rounded-2xl font-bold text-base transition-all shadow-xl shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5">
              {t.hero.cta1}
              <ChevronCta size={18} className="group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link to="/pricing"
              className="flex items-center gap-2 glass hover:bg-white/8 text-gray-300 hover:text-white px-8 py-3.5 rounded-2xl font-medium text-base transition-all">
              {t.hero.cta2}
              <ArrowUpRight size={16} />
            </Link>
          </div>
          <p className="text-gray-600 text-sm mt-5">{t.hero.note}</p>

          {/* Trust badges */}
          <div className="flex items-center justify-center gap-6 mt-10 flex-wrap">
            {[
              { icon: <Lock size={13}/>,   label: isAr ? 'مشفّر وآمن' : 'Encrypted & Secure' },
              { icon: <Cpu size={13}/>,    label: isAr ? 'مدعوم بمحرك الذكاء الاصطناعي' : 'Powered by AI Engine' },
              { icon: <Target size={13}/>, label: isAr ? 'دقة ICT/SMC مؤسسية' : 'Institutional ICT/SMC' },
            ].map((b, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs text-gray-500">
                <span className="text-blue-500">{b.icon}</span>
                {b.label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats ──────────────────────────────────────────────────────── */}
      <section className="py-14 px-4 border-y border-white/5 bg-gradient-to-r from-transparent via-blue-950/20 to-transparent">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center reveal">
          {t.stats.map((s, i) => (
            <div key={i} className="stagger-child reveal" style={{ transitionDelay: `${i*100}ms` }}>
              <div className="text-3xl font-black text-white mb-1 gradient-text">
                <Counter target={s.value} />
              </div>
              <div className="text-gray-500 text-sm">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Markets ─────────────────────────────────────────────────────── */}
      <section className="py-20 px-4 bg-white/[0.01]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12 reveal">
            <p className="text-xs text-blue-400 font-semibold uppercase tracking-widest mb-3">
              {isAr ? 'الأسواق المدعومة' : 'Supported Markets'}
            </p>
            <h2 className="text-3xl font-bold mb-3 section-title">
              {isAr ? 'تداول أقوى الأسواق العالمية' : "Trade the World's Top Markets"}
            </h2>
            <p className="text-gray-400 text-sm max-w-lg mx-auto">
              {isAr
                ? 'تحليل ICT/SMC بالذكاء الاصطناعي لأبرز الأسواق المالية العالمية في ثوانٍ'
                : 'AI-powered ICT/SMC analysis for the world\'s top financial markets in seconds'}
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { symbol: 'XAUUSD', name: isAr ? 'الذهب' : 'Gold', icon: '🥇', color: 'from-yellow-900/30 to-yellow-800/10', border: 'border-yellow-700/30', tag: isAr ? 'الأكثر تداولاً' : 'Most Traded' },
              { symbol: 'BTCUSD', name: isAr ? 'البيتكوين' : 'Bitcoin', icon: '₿', color: 'from-orange-900/30 to-orange-800/10', border: 'border-orange-700/30', tag: '' },
              { symbol: 'EURUSD', name: isAr ? 'يورو/دولار' : 'EUR/USD', icon: '€', color: 'from-blue-900/30 to-blue-800/10', border: 'border-blue-700/30', tag: '' },
              { symbol: 'GBPUSD', name: isAr ? 'جنيه/دولار' : 'GBP/USD', icon: '£', color: 'from-purple-900/30 to-purple-800/10', border: 'border-purple-700/30', tag: '' },
              { symbol: 'USDJPY', name: isAr ? 'دولار/ين' : 'USD/JPY', icon: '¥', color: 'from-red-900/30 to-red-800/10', border: 'border-red-700/30', tag: '' },
              { symbol: 'ETHUSD', name: isAr ? 'إثيريوم' : 'Ethereum', icon: 'Ξ', color: 'from-indigo-900/30 to-indigo-800/10', border: 'border-indigo-700/30', tag: '' },
              { symbol: 'USOIL', name: isAr ? 'النفط الخام' : 'Crude Oil', icon: '🛢', color: 'from-gray-800/60 to-gray-700/20', border: 'border-gray-600/30', tag: '' },
              { symbol: 'NAS100', name: isAr ? 'ناسداك' : 'NASDAQ', icon: '📈', color: 'from-teal-900/30 to-teal-800/10', border: 'border-teal-700/30', tag: isAr ? 'قريباً' : 'Soon' },
            ].map((m, i) => (
              <div key={i} className={`reveal card-hover relative bg-gradient-to-br ${m.color} border ${m.border} rounded-2xl p-5 text-center`}
                   style={{ transitionDelay: `${i * 60}ms` }}>
                {m.tag && (
                  <span className="absolute -top-2 left-1/2 -translate-x-1/2 text-xs bg-yellow-600/80 text-white px-2 py-0.5 rounded-full whitespace-nowrap">
                    {m.tag}
                  </span>
                )}
                <div className="text-3xl mb-2">{m.icon}</div>
                <div className="font-bold text-white text-sm">{m.symbol}</div>
                <div className="text-gray-400 text-xs mt-0.5">{m.name}</div>
              </div>
            ))}
          </div>
          {/* Hidden SEO keywords */}
          <p className="text-gray-700 text-xs text-center mt-8 select-none" aria-hidden="true">
            تحليل فوركس بالذكاء الاصطناعي · إشارات تداول الذهب · توصيات البيتكوين · بوت تداول تلجرام · منصة تداول ذكية عربية · تحليل XAUUSD · إشارات يومية
          </p>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16 reveal">
            <p className="text-blue-400 text-sm font-semibold mb-3 uppercase tracking-widest">
              {isAr ? 'المميزات' : 'Features'}
            </p>
            <h2 className="text-3xl md:text-4xl font-black mb-4 section-title">{t.featuresTitle}</h2>
            <p className="text-gray-400 max-w-xl mx-auto leading-relaxed">{t.featuresSub}</p>
          </div>
          <div className="grid md:grid-cols-3 gap-5">
            {t.features.map((f, i) => (
              <div key={i}
                className={`reveal card-hover relative bg-gradient-to-br ${FEATURE_COLORS[i]} border rounded-2xl p-6 overflow-hidden`}
                style={{ transitionDelay: `${i * 80}ms` }}>
                {/* shimmer */}
                <div className="absolute inset-0 animate-shimmer opacity-40 pointer-events-none" />
                <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${FEATURE_COLORS[i]} border flex items-center justify-center mb-4`}>
                  {FEATURE_ICONS[i]}
                </div>
                <h3 className="font-bold text-white text-base mb-2">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Demo Section ───────────────────────────────────────────────── */}
      <DemoSection isAr={isAr} />

      {/* ── How it works ───────────────────────────────────────────────── */}
      <section className="py-24 px-4 relative overflow-hidden">
        <div className="orb w-[400px] h-[400px] bg-indigo-600/8 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
        <div className="max-w-4xl mx-auto relative">
          <div className="text-center mb-16 reveal">
            <p className="text-purple-400 text-sm font-semibold mb-3 uppercase tracking-widest">
              {isAr ? 'كيف يعمل' : 'How It Works'}
            </p>
            <h2 className="text-3xl font-black mb-4 section-title">{t.howTitle}</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8 relative">
            {/* connector line */}
            <div className="hidden md:block absolute top-8 left-1/6 right-1/6 h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
            {t.how.map((s, i) => (
              <div key={i} className="reveal text-center" style={{ transitionDelay: `${i * 150}ms` }}>
                <div className="w-16 h-16 bg-gradient-to-br from-blue-600/30 to-indigo-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center mx-auto mb-5 animate-float glow-blue"
                  style={{ animationDelay: `${i * 1.3}s` }}>
                  <span className="text-blue-300 font-black text-xl">{s.step}</span>
                </div>
                <h3 className="font-bold text-white mb-2 text-base">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Performance ────────────────────────────────────────────────── */}
      <PublicPerformance isAr={isAr} />

      {/* ── Testimonials ───────────────────────────────────────────────── */}
      <section id="testimonials" className="py-24 px-4 relative overflow-hidden bg-white/[0.01]">
        <div className="orb w-[500px] h-[400px] bg-purple-600/7 top-1/2 right-0 translate-x-1/4 -translate-y-1/2 pointer-events-none" />
        <div className="max-w-6xl mx-auto relative">
          <div className="text-center mb-14 reveal">
            <p className="text-purple-400 text-sm font-semibold mb-3 uppercase tracking-widest">
              {isAr ? 'آراء المستخدمين' : 'User Reviews'}
            </p>
            <h2 className="text-3xl md:text-4xl font-black mb-4 section-title">{t.testimonialsTitle}</h2>
            <p className="text-gray-400">{t.testimonialsSub}</p>
            {/* Star row */}
            <div className="flex items-center justify-center gap-1 mt-4">
              {[1,2,3,4,5].map(i => (
                <Star key={i} size={18} className="text-yellow-400 fill-yellow-400" />
              ))}
              <span className="text-gray-400 text-sm ms-2">4.9/5 {isAr ? 'من' : 'from'} 400+ {isAr ? 'مستخدم' : 'users'}</span>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-5">
            {t.testimonials.map((tm, i) => (
              <div key={i}
                className="reveal card-hover relative bg-gradient-to-br from-white/4 to-white/[0.01] border border-white/8 hover:border-purple-500/25 rounded-2xl p-6 flex flex-col gap-4"
                style={{ transitionDelay: `${i * 70}ms` }}>
                {/* Quote mark */}
                <span className="absolute top-4 end-5 text-4xl text-purple-500/15 font-serif leading-none select-none">"</span>
                {/* Stars */}
                <div className="flex gap-0.5">
                  {[...Array(tm.rating)].map((_, j) => (
                    <Star key={j} size={12} className="text-yellow-400 fill-yellow-400" />
                  ))}
                </div>
                {/* Text */}
                <p className="text-gray-300 text-sm leading-relaxed flex-1">"{tm.text}"</p>
                {/* Author */}
                <div className="flex items-center gap-3 pt-3 border-t border-white/6">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-600/40 to-indigo-600/30 border border-purple-500/20 flex items-center justify-center text-base">
                    {tm.country}
                  </div>
                  <div>
                    <div className="font-bold text-white text-sm">{tm.name}</div>
                    <div className="text-xs text-gray-500">{tm.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ────────────────────────────────────────────────────── */}
      <section id="pricing" className="py-24 px-4 relative overflow-hidden">
        <div className="orb w-[600px] h-[400px] bg-blue-600/6 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <div className="max-w-5xl mx-auto relative">
          <div className="text-center mb-16 reveal">
            <p className="text-green-400 text-sm font-semibold mb-3 uppercase tracking-widest">
              {isAr ? 'الأسعار' : 'Pricing'}
            </p>
            <h2 className="text-3xl font-black mb-4 section-title">{t.pricingTitle}</h2>
            <p className="text-gray-400">{t.pricingSub}</p>
          </div>

          <div className="grid md:grid-cols-3 gap-5 items-stretch">
            {t.plans.map((p, i) => {
              const isHighlight = p.highlight
              const isFree = p.price === 'مجاني' || p.price === 'Free'
              // Merge live API price for weekly/monthly
              const planKey = p.name === 'أسبوعي' || p.name === 'Weekly' ? 'weekly'
                            : p.name === 'شهري' || p.name === 'Monthly'  ? 'monthly'
                            : null
              const livePrice = planKey && livePlans[planKey]?.price_usd
              const displayPrice = livePrice ? `$${livePrice}` : p.price
              const liveFeaturesAr = planKey && livePlans[planKey]?.features
              const liveFeaturesEn = planKey && livePlans[planKey]?.features_en
              const displayFeatures = isFree ? p.features
                : isAr ? (liveFeaturesAr || p.features)
                : (liveFeaturesEn || p.features)
              return (
                <div key={i}
                  className={`reveal relative flex flex-col rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 ${
                    isHighlight
                      ? 'border border-blue-500/60 shadow-2xl shadow-blue-500/20'
                      : 'border border-white/8 hover:border-white/15'
                  }`}
                  style={{ transitionDelay: `${i * 80}ms` }}>

                  {/* Card top color stripe */}
                  <div className={`h-1 w-full ${isHighlight ? 'bg-gradient-to-r from-blue-500 to-indigo-500' : isFree ? 'bg-gradient-to-r from-gray-600 to-gray-500' : 'bg-gradient-to-r from-purple-500 to-purple-400'}`} />

                  <div className={`flex-1 flex flex-col p-7 ${isHighlight ? 'bg-gradient-to-b from-blue-900/25 to-gray-900' : 'bg-gray-900/80'}`}>
                    {/* Badge */}
                    {p.badge && (
                      <div className="inline-flex self-start items-center gap-1.5 bg-gradient-to-r from-blue-600/30 to-indigo-600/20 border border-blue-500/40 text-blue-300 text-xs px-3 py-1 rounded-full font-bold mb-4">
                        <Star size={9} fill="currentColor" />
                        {p.badge}
                      </div>
                    )}

                    {/* Plan name */}
                    <h3 className="text-base font-bold text-gray-400 mb-1 uppercase tracking-wider">{p.name}</h3>

                    {/* Price */}
                    <div className="flex items-end gap-1.5 mb-6">
                      <span className={`text-5xl font-black leading-none ${isHighlight ? 'bg-gradient-to-r from-blue-300 to-indigo-300 bg-clip-text text-transparent' : 'text-white'}`}>
                        {displayPrice}
                      </span>
                      {p.period && <span className="text-gray-500 text-sm mb-1">{p.period}</span>}
                    </div>

                    {/* Divider */}
                    <div className={`border-t mb-5 ${isHighlight ? 'border-blue-500/20' : 'border-white/6'}`} />

                    {/* Features */}
                    <ul className="space-y-3 flex-1 mb-6">
                      {displayFeatures.map((f, j) => (
                        <li key={j} className="flex items-center gap-2.5 text-sm">
                          <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${isHighlight ? 'bg-blue-500/25' : 'bg-white/8'}`}>
                            <CheckCircle size={10} className={isHighlight ? 'text-blue-300' : 'text-green-400'} />
                          </div>
                          <span className={isHighlight ? 'text-gray-200' : 'text-gray-400'}>{f}</span>
                        </li>
                      ))}
                    </ul>

                    {/* CTA */}
                    <Link to={p.href}
                      className={`block text-center py-3 rounded-xl font-bold text-sm transition-all hover:scale-[1.02] ${
                        isHighlight
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-500/30'
                          : isFree
                          ? 'bg-gray-700/60 hover:bg-gray-700 text-gray-200 border border-white/10'
                          : 'bg-gradient-to-r from-purple-700 to-purple-600 hover:from-purple-600 hover:to-purple-500 text-white shadow-lg shadow-purple-500/20'
                      }`}>
                      {p.cta}
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Footer note */}
          <p className="text-center text-gray-600 text-xs mt-8">
            {isAr ? '✓ لا توجد رسوم خفية · ✓ إلغاء في أي وقت · ✓ دفع آمن بـ USDT' : '✓ No hidden fees · ✓ Cancel anytime · ✓ Secure USDT payment'}
          </p>
        </div>
      </section>

      {/* ── Affiliate ──────────────────────────────────────────────────── */}
      <AffiliateSection isAr={isAr} />

      {/* ── FAQ ────────────────────────────────────────────────────────── */}
      <section id="faq" className="py-24 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16 reveal">
            <p className="text-yellow-400 text-sm font-semibold mb-3 uppercase tracking-widest">
              {isAr ? 'الأسئلة الشائعة' : 'FAQ'}
            </p>
            <h2 className="text-3xl font-black mb-4 section-title">{t.faqTitle}</h2>
          </div>
          <div className="space-y-3 reveal">
            {t.faq.map((item, i) => (
              <details key={i}
                className="glass border border-white/8 rounded-2xl group hover:border-blue-500/20 transition-colors overflow-hidden">
                <summary className="flex items-center justify-between px-5 py-4 cursor-pointer list-none font-semibold text-white group-open:text-blue-400 transition-colors">
                  {item.q}
                  <ChevronLeft size={16}
                    className={`text-gray-500 group-open:-rotate-90 transition-transform duration-300 flex-shrink-0 ${!isAr ? 'rotate-180' : ''}`} />
                </summary>
                <p className="px-5 pb-5 text-gray-400 text-sm leading-relaxed border-t border-white/5 pt-4">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────── */}
      <section className="py-24 px-4 relative overflow-hidden">
        <div className="orb w-[700px] h-[500px] bg-blue-600/12 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
        {/* Subtle grid */}
        <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />
        <div className="max-w-2xl mx-auto text-center relative reveal">
          {/* Urgency badge */}
          <div className="inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 text-xs px-4 py-1.5 rounded-full mb-6 animate-pulse-glow">
            <Zap size={11} className="fill-yellow-400 text-yellow-400" />
            {t.ctaUrgency}
          </div>

          <h2 className="text-3xl md:text-5xl font-black mb-5 leading-tight">
            <span className="gradient-text">{t.ctaTitle}</span>
          </h2>
          <p className="text-gray-400 mb-8 text-lg leading-relaxed">{t.ctaSub}</p>

          {/* Social proof mini-row */}
          <div className="flex items-center justify-center gap-3 mb-8">
            {/* Avatar stack */}
            <div className="flex -space-x-2 rtl:space-x-reverse">
              {['🧑','👨‍💼','👩','🧔','👩‍💼'].map((em, i) => (
                <div key={i} className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-700 to-indigo-700 border-2 border-[#070b14] flex items-center justify-center text-sm">
                  {em}
                </div>
              ))}
            </div>
            <span className="text-gray-400 text-sm">
              {isAr ? '+2,000 متداول نشط' : '+2,000 active traders'}
            </span>
          </div>

          <Link to="/register"
            className="group inline-flex items-center gap-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-12 py-4 rounded-2xl font-black text-lg transition-all shadow-2xl shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-1">
            {t.ctaBtn}
            <ChevronCta size={22} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>

          {/* Trust badges row */}
          <div className="flex flex-wrap items-center justify-center gap-4 mt-6">
            {t.ctaTrust.map((item, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs text-gray-500">
                <CheckCircle size={12} className="text-green-500" />
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-12 px-4 bg-[#050810]">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-10">
            <div className="col-span-2 md:col-span-1">
              <Link to="/" className="flex items-center gap-2.5 mb-4">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-sm">Q</div>
                <span className="font-bold text-sm">Qaffel AI</span>
              </Link>
              <p className="text-gray-600 text-xs leading-relaxed mb-4">
                {isAr
                  ? 'منصة تداول ذكية مدعومة بالذكاء الاصطناعي وتحليل ICT/SMC المؤسسي.'
                  : 'Smart trading platform powered by AI and institutional ICT/SMC analysis.'}
              </p>
              <div className="flex items-center gap-3">
                <a href="https://www.instagram.com/qaffel_ai/" target="_blank" rel="noreferrer"
                  className="text-gray-600 hover:text-pink-400 transition-colors" aria-label="Instagram">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
                </a>
                <a href="https://t.me/Qaffelbot" target="_blank" rel="noreferrer"
                  className="text-gray-600 hover:text-blue-400 transition-colors" aria-label="Telegram">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-1.97 9.289c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.932z"/></svg>
                </a>
              </div>
            </div>
            {[
              { title: t.footer.platform, links: [
                { to: '/register', label: t.footer.register },
                { to: '/login',    label: t.footer.login },
                { to: '/pricing',  label: t.footer.pricing },
                { to: '/blog',     label: isAr ? 'المدونة' : 'Blog' },
              ]},
              { title: t.footer.company, links: [
                { to: '/about',  label: t.footer.about },
                { to: '/vision', label: t.footer.vision },
              ]},
              { title: t.footer.legal, links: [
                { to: '/terms',   label: t.footer.terms },
                { to: '/privacy', label: t.footer.privacy },
              ]},
              { title: t.footer.contact, links: [
                { to: '/contact', label: t.footer.contactUs },
                { href: 'https://t.me/Qaffelbot', label: '@Qaffelbot' },
              ]},
            ].map((col, i) => (
              <div key={i}>
                <h4 className="font-bold text-sm mb-4 text-gray-300">{col.title}</h4>
                <ul className="space-y-2.5">
                  {col.links.map((l, j) => (
                    <li key={j}>
                      {l.href
                        ? <a href={l.href} target="_blank" rel="noreferrer" className="text-xs text-gray-600 hover:text-blue-400 transition-colors">{l.label}</a>
                        : <Link to={l.to} className="text-xs text-gray-600 hover:text-blue-400 transition-colors">{l.label}</Link>
                      }
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="border-t border-white/5 pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-gray-700">
            <span>{t.footer.copy}</span>
            <span className="flex items-center gap-1.5">
              <Star size={10} className="text-yellow-600 fill-yellow-600" />
              {t.footer.disclaimer}
            </span>
          </div>
        </div>
      </footer>

      <PublicChatBot />
    </div>
  )
}
