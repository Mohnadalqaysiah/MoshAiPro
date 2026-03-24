import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { TrendingUp, Shield, Zap, Bot, Bell, BarChart2, ChevronLeft, ChevronRight, CheckCircle, Star, LayoutDashboard } from 'lucide-react'
import PublicChatBot from '../components/PublicChatBot'

const FEATURE_ICONS = [
  <BarChart2 className="text-blue-400"   size={24} />,
  <Bot       className="text-purple-400" size={24} />,
  <Bell      className="text-green-400"  size={24} />,
  <TrendingUp className="text-yellow-400" size={24} />,
  <Shield    className="text-red-400"    size={24} />,
  <Zap       className="text-cyan-400"   size={24} />,
]

export default function Landing() {
  const { user } = useAuth()
  const { lang, toggle, t } = useLang()
  const isAr = lang === 'ar'
  const ChevronCta = isAr ? ChevronLeft : ChevronRight

  return (
    <div className="min-h-screen bg-gray-950 text-white" dir={t.dir}>

      {/* ── Navbar ───────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-sm">Q</div>
            <span className="font-bold text-lg">Qaffel <span className="text-blue-400">AI</span></span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">{t.nav.features}</a>
            <a href="#pricing"  className="hover:text-white transition-colors">{t.nav.pricing}</a>
            <a href="#faq"      className="hover:text-white transition-colors">{t.nav.faq}</a>
            <Link to="/about"   className="hover:text-white transition-colors">{t.nav.about}</Link>
            <Link to="/contact" className="hover:text-white transition-colors">{t.nav.contact}</Link>
          </nav>

          <div className="flex items-center gap-2">
            {/* Language toggle */}
            <button
              onClick={toggle}
              className="text-xs border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-white px-2.5 py-1 rounded-lg transition-colors font-medium"
            >
              {isAr ? 'EN' : 'ع'}
            </button>

            {user ? (
              <Link to="/dashboard" className="flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                <LayoutDashboard size={14} /> {t.nav.dashboard}
              </Link>
            ) : (
              <>
                <Link to="/login"    className="text-sm text-gray-300 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors">{t.nav.login}</Link>
                <Link to="/register" className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-medium transition-colors">{t.nav.start}</Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative py-20 md:py-32 px-4 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl" />
        </div>
        <div className="max-w-4xl mx-auto text-center relative">
          <div className="inline-flex items-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Zap size={12} />
            {t.hero.badge}
          </div>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            {t.hero.h1a}<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-blue-400 to-purple-400">
              {t.hero.h1b}
            </span>
          </h1>
          <p className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            {t.hero.sub}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/register" className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-xl font-semibold text-base transition-all hover:scale-105 shadow-lg shadow-blue-500/25">
              {t.hero.cta1}
              <ChevronCta size={18} />
            </Link>
            <Link to="/pricing" className="flex items-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3.5 rounded-xl font-medium text-base transition-colors">
              {t.hero.cta2}
            </Link>
          </div>
          <p className="text-gray-600 text-sm mt-4">{t.hero.note}</p>
        </div>
      </section>

      {/* ── Stats ────────────────────────────────────────────────────── */}
      <section className="py-12 px-4 border-y border-gray-800/50">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {t.stats.map((s, i) => (
            <div key={i}>
              <div className="text-3xl font-bold text-white mb-1">{s.value}</div>
              <div className="text-gray-500 text-sm">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section id="features" className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">{t.featuresTitle}</h2>
            <p className="text-gray-400 max-w-xl mx-auto">{t.featuresSub}</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {t.features.map((f, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-6 hover:border-gray-700 transition-colors">
                <div className="w-12 h-12 bg-gray-800 rounded-xl flex items-center justify-center mb-4">
                  {FEATURE_ICONS[i]}
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section className="py-20 px-4 bg-gray-900/40">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-4">{t.howTitle}</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {t.how.map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-14 h-14 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-blue-400 font-bold text-lg">{s.step}</span>
                </div>
                <h3 className="font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────── */}
      <section id="pricing" className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-4">{t.pricingTitle}</h2>
            <p className="text-gray-400">{t.pricingSub}</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {t.plans.map((p, i) => (
              <div key={i} className={`relative bg-gray-900 border-2 ${p.highlight ? 'border-blue-500 shadow-xl shadow-blue-500/10' : 'border-gray-700'} rounded-2xl p-6`}>
                {p.badge && (
                  <div className="absolute -top-3 right-1/2 translate-x-1/2 bg-blue-600 text-white text-xs px-3 py-1 rounded-full font-medium">
                    {p.badge}
                  </div>
                )}
                <h3 className="font-bold text-white text-lg mb-1">{p.name}</h3>
                <div className="flex items-baseline gap-1 mb-5">
                  <span className="text-3xl font-bold text-white">{p.price}</span>
                  <span className="text-gray-500 text-sm">{p.period}</span>
                </div>
                <ul className="space-y-2.5 mb-6">
                  {p.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm text-gray-300">
                      <CheckCircle size={14} className="text-green-400 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to={p.href}
                  className={`block text-center py-2.5 rounded-xl font-medium text-sm transition-colors ${
                    p.highlight
                      ? 'bg-blue-600 hover:bg-blue-500 text-white'
                      : 'border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white'
                  }`}
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────────────────── */}
      <section id="faq" className="py-20 px-4 bg-gray-900/40">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">{t.faqTitle}</h2>
          <div className="space-y-4">
            {t.faq.map((item, i) => (
              <details key={i} className="bg-gray-900 border border-gray-800 rounded-xl group">
                <summary className="flex items-center justify-between px-5 py-4 cursor-pointer list-none font-medium text-white">
                  {item.q}
                  <ChevronLeft size={16} className={`text-gray-500 group-open:-rotate-90 transition-transform ${!isAr ? 'rotate-180' : ''}`} />
                </summary>
                <p className="px-5 pb-4 text-gray-400 text-sm leading-relaxed border-t border-gray-800 pt-3">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <section className="py-20 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">{t.ctaTitle}</h2>
          <p className="text-gray-400 mb-8">{t.ctaSub}</p>
          <Link to="/register" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-10 py-4 rounded-xl font-semibold text-lg transition-all hover:scale-105 shadow-lg shadow-blue-500/25">
            {t.ctaBtn}
            <ChevronCta size={20} />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-800 py-10 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-8">
            <div className="col-span-2 md:col-span-1">
              <Link to="/" className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-xs">Q</div>
                <span className="font-bold">Qaffel AI</span>
              </Link>
              <p className="text-gray-600 text-xs leading-relaxed">
                {isAr
                  ? 'منصة تداول ذكية مدعومة بالذكاء الاصطناعي وتحليل ICT/SMC المؤسسي.'
                  : 'Smart trading platform powered by AI and institutional ICT/SMC analysis.'}
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-sm mb-3 text-gray-300">{t.footer.platform}</h4>
              <ul className="space-y-2 text-xs text-gray-600">
                <li><Link to="/register" className="hover:text-gray-400">{t.footer.register}</Link></li>
                <li><Link to="/login"    className="hover:text-gray-400">{t.footer.login}</Link></li>
                <li><Link to="/pricing"  className="hover:text-gray-400">{t.footer.pricing}</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-sm mb-3 text-gray-300">{t.footer.company}</h4>
              <ul className="space-y-2 text-xs text-gray-600">
                <li><Link to="/about"  className="hover:text-gray-400">{t.footer.about}</Link></li>
                <li><Link to="/vision" className="hover:text-gray-400">{t.footer.vision}</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-sm mb-3 text-gray-300">{t.footer.legal}</h4>
              <ul className="space-y-2 text-xs text-gray-600">
                <li><Link to="/terms"   className="hover:text-gray-400">{t.footer.terms}</Link></li>
                <li><Link to="/privacy" className="hover:text-gray-400">{t.footer.privacy}</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-sm mb-3 text-gray-300">{t.footer.contact}</h4>
              <ul className="space-y-2 text-xs text-gray-600">
                <li><Link to="/contact" className="hover:text-gray-400">{t.footer.contactUs}</Link></li>
                <li><a href="https://t.me/Qaffelbot" target="_blank" rel="noreferrer" className="hover:text-gray-400">@Qaffelbot</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-gray-700">
            <span>{t.footer.copy}</span>
            <span className="flex items-center gap-1">
              <Star size={10} className="text-yellow-600" />
              {t.footer.disclaimer}
            </span>
          </div>
        </div>
      </footer>

      <PublicChatBot />
    </div>
  )
}
