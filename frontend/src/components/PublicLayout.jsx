/**
 * PublicLayout — Shared header + footer for all public pages
 * (Pricing, About, Contact, Terms, Privacy, Vision, Strategy Builder, Blog…)
 *
 * (2026-10-17) بالهوية الجديدة (نفس الصفحة الرئيسية الجديدة): الهيدر والفوتر يعيدان استخدام أنماط .qx
 * من landing-v2.css، والمحتوى داخل .qpub (public-v2.css) يعيد تعيين متغيرات الألوان فيتحوّل تلقائياً.
 */
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { mirrorPath } from '../utils/langRoutes'
import { TXT } from './landing/landingV2Text'
import '../styles/landing-v2.css'
import '../styles/public-v2.css'

// ── Social icons (inline SVG, no extra lib needed) ─────────────────────
const IconInstagram = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" width="18" height="18" aria-hidden="true">
    <rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4.2" /><circle cx="17.4" cy="6.6" r="1" fill="currentColor" stroke="none" />
  </svg>
)
const IconTelegram = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round" width="18" height="18" aria-hidden="true">
    <path d="M21 4 L3 11 L10 13 L12 20 L21 4 Z" /><path d="M10 13 L21 4" />
  </svg>
)
const BrandMark = () => (
  <span className="brand-mark"><svg width="22" height="22" viewBox="0 0 36 36" fill="none" aria-hidden="true"><circle cx="17" cy="17" r="11.5" stroke="#DDE5F2" strokeWidth="3.2" /><path d="M22 22 L31 31" stroke="#3CF2C0" strokeWidth="3.2" strokeLinecap="round" /></svg></span>
)

export default function PublicLayout({ children }) {
  const { user } = useAuth()
  const { lang, toggle, t } = useLang()
  const isAr = lang === 'ar'
  const T = TXT[isAr ? 'ar' : 'en']
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()
  const navigate  = useNavigate()
  const p = (path) => (isAr ? path : `/en${path}`)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  useEffect(() => { setMenuOpen(false) }, [location.pathname])

  // لو الصفحة الحالية إلها نسخة إنجليزية حقيقية على /en/*، بدّل اللغة عبر
  // التنقل لرابطها المكافئ (مو مجرد تبديل محلي) — عشان الرابط يعكس المحتوى فعلاً
  const handleToggleLang = () => {
    const target = isAr ? 'en' : 'ar'
    const mirror = mirrorPath(location.pathname, target)
    toggle()
    if (mirror && mirror !== location.pathname) navigate(mirror)
  }

  const bare = location.pathname.replace(/^\/en(?=\/|$)/, '') || '/'
  const isOn = (to) => { const b = to.replace(/^\/en(?=\/|$)/, ''); return bare === b || bare.startsWith(b + '/') }

  // [المسار, النص, رابط عادي خارج React؟]
  const navLinks = [
    [p('/strategy-builder'), T.nav.builder],
    ...(isAr ? [['/results', T.nav.results]] : []),   // سجل الأداء عربي فقط، ولا /en/results
    [p('/pricing'), T.nav.pricing],
    ['/referral', T.nav.referral],
    [p('/blog'), T.nav.blog],
    [p('/about'), T.nav.about],
    [p('/contact'), T.nav.contact],
  ]
  const moreLinks = [
    [p('/vision'), t.footer.vision],
    ['/games/challenge', T.nav.games, true],
  ]
  const navItem = ([to, label, native]) => native
    ? <a key={to} href={to}>{label}</a>
    : <Link key={to} to={to} className={isOn(to) ? 'on' : undefined} aria-current={isOn(to) ? 'page' : undefined}>{label}</Link>

  return (
    <div className="qpub" dir={isAr ? 'rtl' : 'ltr'}>

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="qx qx-bar" dir={isAr ? 'rtl' : 'ltr'}>
        <header className={`hdr ${scrolled || menuOpen ? 'scrolled' : ''}`}>
          <div className="wrap">
            <div style={{ display: 'flex', alignItems: 'center', gap: 36 }}>
              <Link to={isAr ? '/' : '/en'} className="brand" aria-label="Qaffel AI"><BrandMark /><span dir="ltr">Qaffel <span className="grad">AI</span></span></Link>
              <nav className="nav" aria-label={T.menu} style={{ gap: 24 }}>
                {navLinks.map(navItem)}
              </nav>
            </div>
            <div className="hdr-actions">
              <button className="lang" type="button" onClick={handleToggleLang} aria-label={isAr ? 'English' : 'العربية'}>{isAr ? 'EN' : 'ع'}</button>
              {user ? (
                <Link to="/dashboard" className="btn btn-mint">{T.dashboard}</Link>
              ) : (<>
                <Link to="/login" className="login" style={{ fontSize: 15, color: 'var(--muted)', padding: '10px 12px' }}>{T.login}</Link>
                <Link to="/register" className="btn btn-mint">{T.start}</Link>
              </>)}
              <button type="button" className="burger" aria-label={T.menu} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">{menuOpen ? <path d="M6 6 L18 18 M18 6 L6 18" /> : <path d="M4 7 H20 M4 12 H20 M4 17 H20" />}</svg>
              </button>
            </div>
          </div>
          <div className={`mnav ${menuOpen ? 'open' : ''}`} onClick={() => setMenuOpen(false)}>
            {[...navLinks, ...moreLinks].map(navItem)}
            {!user && <Link to="/login">{T.login}</Link>}
          </div>
        </header>
      </div>

      {/* ── Page Content ────────────────────────────────────────────────── */}
      <main>{children}</main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <div className="qx qx-foot" dir={isAr ? 'rtl' : 'ltr'}>
        <footer>
          <div className="wrap">
            <div className="f-grid f5">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <Link to={isAr ? '/' : '/en'} className="brand"><BrandMark /><span dir="ltr">Qaffel <span className="grad">AI</span></span></Link>
                <p style={{ color: 'var(--faint)', fontSize: 14, maxWidth: '34ch' }}>{T.fAbout}</p>
                <div className="socials">
                  <a href="https://t.me/Qaffelbot" target="_blank" rel="noreferrer" aria-label="Telegram"><IconTelegram /></a>
                  <a href="https://www.instagram.com/qaffel_ai/" target="_blank" rel="noreferrer" aria-label="Instagram"><IconInstagram /></a>
                </div>
              </div>
              <div><h4>{T.fPlatform}</h4><ul>
                <li><Link to="/register">{T.fRegister}</Link></li>
                <li><Link to="/login">{T.login}</Link></li>
                <li><Link to={p('/pricing')}>{T.nav.pricing}</Link></li>
                <li><Link to={p('/strategy-builder')}>{T.nav.builder}</Link></li>
                {isAr && <li><Link to="/results">{T.nav.results}</Link></li>}
                <li><a href="/games/challenge">{T.nav.games}</a></li>
              </ul></div>
              <div><h4>{T.fCompany}</h4><ul>
                <li><Link to={p('/about')}>{T.nav.about}</Link></li>
                <li><Link to={p('/vision')}>{t.footer.vision}</Link></li>
                <li><Link to={p('/blog')}>{T.nav.blog}</Link></li>
                <li><Link to="/referral">{T.nav.referral}</Link></li>
              </ul></div>
              <div><h4>{T.fLegal}</h4><ul>
                <li><Link to={p('/terms')}>{T.fTerms}</Link></li>
                <li><Link to={p('/privacy')}>{T.fPrivacy}</Link></li>
                <li><a href="#risk">{T.fRisk}</a></li>
              </ul></div>
              <div><h4>{t.footer.contact}</h4><ul>
                <li><Link to={p('/contact')}>{t.footer.contactUs}</Link></li>
                <li><a href="mailto:support@qaffel.com" dir="ltr">support@qaffel.com</a></li>
                <li><a href="https://t.me/Qaffelbot" target="_blank" rel="noreferrer" dir="ltr">@Qaffelbot</a></li>
              </ul></div>
            </div>
            <p className="risk" id="risk">{T.risk}</p>
            <div className="copy"><span>{T.rights}</span><span dir="ltr">@Qaffelbot · @qaffel_ai</span></div>
          </div>
        </footer>
      </div>
    </div>
  )
}
