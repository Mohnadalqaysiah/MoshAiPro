/**
 * PublicLayout — Shared header + footer for all public pages
 * (Pricing, About, Contact, Terms, Privacy, Vision)
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { LayoutDashboard, Menu, X, Star } from 'lucide-react'

// ── Social icons (inline SVG, no extra lib needed) ─────────────────────
const IconInstagram = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/>
  </svg>
)
const IconTelegram = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-1.97 9.289c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.932z"/>
  </svg>
)

export default function PublicLayout({ children, bgClass = 'bg-[#070b14]' }) {
  const { user } = useAuth()
  const { lang, toggle, t } = useLang()
  const isAr = lang === 'ar'
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className={`min-h-screen ${bgClass} text-white`} dir={isAr ? 'rtl' : 'ltr'}>

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-[#070b14]/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-base shadow-lg shadow-blue-500/30">
              Q
            </div>
            <span className="font-bold text-lg tracking-tight">
              Qaffel <span className="text-blue-400">AI</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-6 text-sm text-gray-400">
            <a href="/#features" className="hover:text-white transition-colors">{t.nav.features}</a>
            <Link to="/pricing"  className="hover:text-white transition-colors">{t.nav.pricing}</Link>
            <Link to="/referral" className="hover:text-yellow-400 text-yellow-500/70 transition-colors font-medium">
              💰 {isAr ? 'الإحالات' : 'Referrals'}
            </Link>
            <Link to="/about"   className="hover:text-white transition-colors">{t.nav.about}</Link>
            <Link to="/contact" className="hover:text-white transition-colors">{t.nav.contact}</Link>
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            <button onClick={toggle}
              className="text-xs border border-white/10 hover:border-blue-500/50 text-gray-400 hover:text-white px-3 py-1.5 rounded-lg transition-all font-medium">
              {isAr ? 'EN' : 'ع'}
            </button>
            {user ? (
              <Link to="/dashboard"
                className="hidden md:flex items-center gap-1.5 text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-4 py-2 rounded-xl font-semibold transition-all shadow-md">
                <LayoutDashboard size={14} /> {t.nav.dashboard}
              </Link>
            ) : (
              <>
                <Link to="/login"
                  className="hidden md:block text-sm text-gray-400 hover:text-white px-4 py-2 rounded-xl hover:bg-white/5 transition-colors">
                  {t.nav.login}
                </Link>
                <Link to="/register"
                  className="hidden md:block text-sm bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-2 rounded-xl font-semibold transition-all shadow-md">
                  {t.nav.start}
                </Link>
              </>
            )}
            <button className="md:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
              onClick={() => setMobileOpen(o => !o)}>
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {mobileOpen && (
          <div className="md:hidden border-t border-white/5 bg-[#070b14]/95 backdrop-blur-xl px-4 py-4 space-y-1">
            {[
              { href: '/#features', label: t.nav.features },
              { to: '/pricing',     label: t.nav.pricing },
              { to: '/about',       label: t.nav.about },
              { to: '/contact',     label: t.nav.contact },
              { to: '/referral',    label: `💰 ${isAr ? 'برنامج الإحالات' : 'Referral Program'}` },
            ].map((l, i) => l.href
              ? <a key={i} href={l.href} onClick={() => setMobileOpen(false)} className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">{l.label}</a>
              : <Link key={i} to={l.to} onClick={() => setMobileOpen(false)} className="block py-2.5 px-3 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors">{l.label}</Link>
            )}
            <div className="pt-2 border-t border-white/5 space-y-2">
              {user ? (
                <Link to="/dashboard" onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-2 w-full py-2.5 px-3 rounded-xl text-sm bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold">
                  <LayoutDashboard size={14} /> {t.nav.dashboard}
                </Link>
              ) : (
                <>
                  <Link to="/login" onClick={() => setMobileOpen(false)}
                    className="block py-2.5 px-3 rounded-xl text-sm text-center text-gray-300 border border-white/10 transition-colors">
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

      {/* ── Page Content ────────────────────────────────────────────────── */}
      <main>{children}</main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-12 px-4 bg-[#050810]">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-10">

            {/* Brand */}
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
              {/* Social Media */}
              <div className="flex items-center gap-3">
                <a href="https://www.instagram.com/qaffel_ai/" target="_blank" rel="noreferrer"
                  className="text-gray-600 hover:text-pink-400 transition-colors" aria-label="Instagram">
                  <IconInstagram />
                </a>
                <a href="https://t.me/Qaffelbot" target="_blank" rel="noreferrer"
                  className="text-gray-600 hover:text-blue-400 transition-colors" aria-label="Telegram Bot">
                  <IconTelegram />
                </a>
              </div>
            </div>

            {/* Links */}
            {[
              { title: t.footer.platform, links: [
                { to: '/register', label: t.footer.register },
                { to: '/login',    label: t.footer.login },
                { to: '/pricing',  label: t.footer.pricing },
              ]},
              { title: t.footer.company, links: [
                { to: '/about',    label: t.footer.about },
                { to: '/vision',   label: t.footer.vision },
                { to: '/referral', label: isAr ? 'برنامج الإحالات' : 'Referral Program' },
              ]},
              { title: t.footer.legal, links: [
                { to: '/terms',   label: t.footer.terms },
                { to: '/privacy', label: t.footer.privacy },
              ]},
              { title: t.footer.contact, links: [
                { to: '/contact',                       label: t.footer.contactUs },
                { href: 'https://t.me/Qaffelbot',       label: '@Qaffelbot (Telegram)' },
                { href: 'https://www.instagram.com/qaffel_ai/', label: '@qaffel_ai (Instagram)' },
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
    </div>
  )
}
