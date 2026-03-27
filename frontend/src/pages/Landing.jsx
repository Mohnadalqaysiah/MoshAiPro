import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import {
  TrendingUp, Shield, Zap, Bot, Bell, BarChart2,
  ChevronLeft, ChevronRight, CheckCircle, Star,
  LayoutDashboard, ArrowUpRight, Cpu, Lock, Target, Menu, X
} from 'lucide-react'
import PublicChatBot from '../components/PublicChatBot'
import DemoSection from '../components/DemoSection'
import AffiliateSection from '../components/AffiliateSection'

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
  useReveal()

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
              { href: '#features', label: t.nav.features },
              { href: '#pricing',  label: t.nav.pricing },
              { href: '#faq',      label: t.nav.faq },
            ].map(({ href, label }) => (
              <a key={href} href={href}
                className="hover:text-white transition-colors relative group">
                {label}
                <span className="absolute -bottom-0.5 right-0 w-0 h-px bg-blue-400 group-hover:w-full transition-all duration-300" />
              </a>
            ))}
            <Link to="/about"   className="hover:text-white transition-colors">{t.nav.about}</Link>
            <Link to="/contact" className="hover:text-white transition-colors">{t.nav.contact}</Link>
          </nav>

          <div className="flex items-center gap-2">
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
              { href: '#features', label: t.nav.features },
              { href: '#pricing',  label: t.nav.pricing },
              { href: '#faq',      label: t.nav.faq },
            ].map(({ href, label }) => (
              <a key={href} href={href}
                onClick={() => setMobileOpen(false)}
                className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                {label}
              </a>
            ))}
            <Link to="/about"   onClick={() => setMobileOpen(false)} className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">{t.nav.about}</Link>
            <Link to="/contact" onClick={() => setMobileOpen(false)} className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">{t.nav.contact}</Link>
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

      {/* ── Pricing ────────────────────────────────────────────────────── */}
      <section id="pricing" className="py-24 px-4 bg-gradient-to-b from-transparent via-blue-950/10 to-transparent">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16 reveal">
            <p className="text-green-400 text-sm font-semibold mb-3 uppercase tracking-widest">
              {isAr ? 'الأسعار' : 'Pricing'}
            </p>
            <h2 className="text-3xl font-black mb-4 section-title">{t.pricingTitle}</h2>
            <p className="text-gray-400">{t.pricingSub}</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {t.plans.map((p, i) => (
              <div key={i}
                className={`reveal card-hover relative rounded-2xl p-6 border transition-all ${
                  p.highlight
                    ? 'bg-gradient-to-b from-blue-600/20 to-indigo-600/10 border-blue-500/50 shadow-2xl shadow-blue-500/15'
                    : 'glass border-white/8'
                }`}
                style={{ transitionDelay: `${i * 100}ms` }}>
                {p.badge && (
                  <div className="absolute -top-3 right-1/2 translate-x-1/2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-xs px-4 py-1 rounded-full font-bold shadow-lg shadow-blue-500/30">
                    {p.badge}
                  </div>
                )}
                {p.highlight && (
                  <div className="absolute inset-0 rounded-2xl animate-shimmer opacity-20 pointer-events-none" />
                )}
                <h3 className="font-black text-white text-lg mb-1">{p.name}</h3>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className={`text-4xl font-black ${p.highlight ? 'gradient-text' : 'text-white'}`}>{p.price}</span>
                  <span className="text-gray-500 text-sm">{p.period}</span>
                </div>
                <ul className="space-y-3 mb-6">
                  {p.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm text-gray-300">
                      <CheckCircle size={14} className="text-green-400 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link to={p.href}
                  className={`block text-center py-3 rounded-xl font-bold text-sm transition-all ${
                    p.highlight
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40'
                      : 'glass hover:bg-white/8 text-gray-300 hover:text-white border border-white/10'
                  }`}>
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
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
        <div className="orb w-[600px] h-[400px] bg-blue-600/12 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
        <div className="max-w-2xl mx-auto text-center relative reveal">
          <div className="inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Star size={11} className="fill-yellow-400 text-yellow-400" />
            {isAr ? 'ابدأ رحلتك اليوم' : 'Start your journey today'}
          </div>
          <h2 className="text-3xl md:text-5xl font-black mb-5 leading-tight">
            <span className="gradient-text">{t.ctaTitle}</span>
          </h2>
          <p className="text-gray-400 mb-10 text-lg leading-relaxed">{t.ctaSub}</p>
          <Link to="/register"
            className="group inline-flex items-center gap-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-12 py-4 rounded-2xl font-black text-lg transition-all shadow-2xl shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-1">
            {t.ctaBtn}
            <ChevronCta size={22} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <p className="text-gray-600 text-sm mt-4">{t.hero.note}</p>
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
              <p className="text-gray-600 text-xs leading-relaxed">
                {isAr
                  ? 'منصة تداول ذكية مدعومة بالذكاء الاصطناعي وتحليل ICT/SMC المؤسسي.'
                  : 'Smart trading platform powered by AI and institutional ICT/SMC analysis.'}
              </p>
            </div>
            {[
              { title: t.footer.platform, links: [
                { to: '/register', label: t.footer.register },
                { to: '/login',    label: t.footer.login },
                { to: '/pricing',  label: t.footer.pricing },
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
