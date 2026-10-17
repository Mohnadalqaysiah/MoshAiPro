/**
 * LandingV2 (2026-10-17) — الصفحة الرئيسية بالهوية الجديدة (qaffel-redesign-kit)، **معاينة** على /preview-home
 * و/en/preview-home قبل استبدال Landing.jsx (طلب المالك: يراها أولاً ثم نحسّن ثم نعتمدها). noindex.
 * المراحل 1–3 من AGENT_BRIEF فقط (تصميم + جوال + أداء). المرحلة 4 (آخر إشارة حقيقية) مؤجَّلة بقرار المالك 17/10،
 * والمرحلة 5 (تجربة بلا تسجيل) بعد مراجعة 30/10 — المحرك هنا أمثلة موسومة.
 * يحافظ على منطق Landing: useAuth، useLang + mirrorPath، useSEO، useTrialLimits، /subscription/plans الحية.
 */
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useTrialLimits from '../hooks/useTrialLimits'
import PublicChatBot from '../components/PublicChatBot'
import { DEMO, TICKER, BLOG, COND_KEYS, TXT, HERO_SCENE } from '../components/landing/landingV2Text'
import '../styles/landing-v2.css'

const HeroScene = lazy(() => import('../components/landing/HeroScene'))
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FONTS = 'https://fonts.googleapis.com/css2?family=Alexandria:wght@400;600;700;800;900&family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=JetBrains+Mono:wght@500;600;700&display=swap'
const TG_URL = 'https://t.me/Qaffelbot'
const SAVINGS_RE = /توفير|وفّر|وفر |save|%/i

const Check = ({ s = 14, w = 3 }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={w} aria-hidden="true"><path d="M5 12 L10 17 L19 7" /></svg>
)
const Arrow = () => (
  <svg className="arr" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 18 L9 12 L15 6" /></svg>
)
const TgIcon = ({ s = 18 }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M21 4 L3 11 L10 13 L12 20 L21 4 Z" stroke="#fff" strokeWidth="2" strokeLinejoin="round" /></svg>
)
const BrandMark = () => (
  <span className="brand-mark"><svg width="22" height="22" viewBox="0 0 36 36" fill="none" aria-hidden="true"><circle cx="17" cy="17" r="11.5" stroke="#DDE5F2" strokeWidth="3.2" /><path d="M22 22 L31 31" stroke="#3CF2C0" strokeWidth="3.2" strokeLinecap="round" /></svg></span>
)
const FEAT_ICONS = [
  <svg key="a" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="2" /><rect x="13" y="3" width="8" height="8" rx="2" /><rect x="3" y="13" width="8" height="8" rx="2" /><rect x="13" y="13" width="8" height="8" rx="2" /></svg>,
  <svg key="b" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 18 L9 12 L13 15 L20 7" /><path d="M15 7 H20 V12" /></svg>,
  <svg key="c" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 5 H20 V16 H9 L5 20 V16 H4 Z" /></svg>,
  <svg key="d" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M21 4 L3 11 L10 13 L12 20 L21 4 Z" strokeLinejoin="round" /></svg>,
  <svg key="e" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7 V12 L15 14" /></svg>,
  <svg key="f" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M3 18 L8 12 L12 15 L16 7 L21 11" /><path d="M3 21 H21" /></svg>,
]
const FEAT_COLORS = [null, null, null, 'var(--sky)', 'var(--gold)', 'var(--coral)']
const BENTO = ['b-a', 'b-b', 'b-c', 'b-d', 'b-e', 'b-f']

function useReveal(rootRef) {
  useEffect(() => {
    const RM = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (RM || !('IntersectionObserver' in window) || !rootRef.current) return
    const els = rootRef.current.querySelectorAll('.qrv')
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.remove('pre'); io.unobserve(e.target) }
    }), { threshold: 0.12 })
    els.forEach((el) => { if (el.getBoundingClientRect().top > window.innerHeight) { el.classList.add('pre'); io.observe(el) } })
    return () => io.disconnect()
  }, [rootRef])
}

export default function LandingV2() {
  const { user } = useAuth()
  const { lang, toggle } = useLang()
  const isAr = lang === 'ar'
  const T = TXT[isAr ? 'ar' : 'en']
  const demo = DEMO[isAr ? 'ar' : 'en']
  const heroText = HERO_SCENE[isAr ? 'ar' : 'en']
  const navigate = useNavigate()
  const trial = useTrialLimits()
  const fmt = (s) => (s || '').replace('{n}', trial.analyses).replace('{m}', trial.chat)
  const p = (path) => (isAr ? path : `/en${path}`)
  const rootRef = useRef(null)

  useSEO({
    title: isAr ? 'Qaffel AI | معاينة الواجهة الجديدة' : 'Qaffel AI | New home preview',
    description: isAr ? 'معاينة داخلية للصفحة الرئيسية الجديدة.' : 'Internal preview of the new home page.',
  })
  // معاينة: لا فهرسة + الخطوط مرة واحدة
  useEffect(() => {
    const robots = document.createElement('meta')
    robots.name = 'robots'; robots.content = 'noindex,nofollow'
    document.head.appendChild(robots)
    if (!document.querySelector(`link[href="${FONTS}"]`)) {
      const pc = document.createElement('link'); pc.rel = 'preconnect'; pc.href = 'https://fonts.gstatic.com'; pc.crossOrigin = ''
      const f = document.createElement('link'); f.rel = 'stylesheet'; f.href = FONTS
      document.head.append(pc, f)
    }
    return () => robots.remove()
  }, [])

  const handleToggleLang = () => {
    const target = isAr ? 'en' : 'ar'
    toggle()
    navigate(target === 'en' ? '/en/preview-home' : '/preview-home')
  }

  // ── header: زجاجي بعد التمرير، يختفي عند النزول السريع؛ الشريط السفلي بعد الـHero ──
  const [scrolled, setScrolled] = useState(false)
  const [hideHdr, setHideHdr] = useState(false)
  const [showBar, setShowBar] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const lastY = useRef(0)
  const heroRef = useRef(null)
  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY
      setScrolled(y > 20)
      if (y > lastY.current + 8 && y > 160) setHideHdr(true)
      else if (y < lastY.current - 4) setHideHdr(false)
      lastY.current = y
      const h = heroRef.current?.offsetHeight || 600
      setShowBar(y > h - 80)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  useReveal(rootRef)

  // ── engine console ──
  const [eng, setEng] = useState({ m: 0, stage: 5, tab: 'sig' })
  const timers = useRef([])
  const run = (m = eng.m) => {
    timers.current.forEach(clearTimeout); timers.current = []
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setEng((s) => ({ ...s, m, stage: 5 })); return }
    setEng((s) => ({ ...s, m, stage: 1 }))
    ;[2, 3, 4, 5].forEach((st, i) => timers.current.push(setTimeout(() => setEng((s) => ({ ...s, stage: st })), 600 * (i + 1))))
  }
  const engineRef = useRef(null)
  useEffect(() => {
    let started = false
    const io = new IntersectionObserver((es) => { if (es[0].isIntersecting && !started) { started = true; run(0) } }, { threshold: 0.3 })
    if (engineRef.current) io.observe(engineRef.current)
    return () => { io.disconnect(); timers.current.forEach(clearTimeout) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const d = demo[eng.m]
  const running = eng.stage < 5
  const sideLabel = { buy: T.buy, sell: T.sell, wait: T.wait }

  // ── strategy builder (خفيف، بلا API) ──
  const [on, setOn] = useState({ bos: true, sweep: true })
  const pct = COND_KEYS.reduce((a, [k, w]) => a + (on[k] ? w : 0), 0)
  const onNames = COND_KEYS.filter(([k]) => on[k]).map(([k]) => T.conds[k])

  // ── FAQ ──
  const [openQ, setOpenQ] = useState(0)

  // ── pricing: من /subscription/plans الحية، الباقة المعطّلة تختفي، التوفير محسوب لا ثابت ──
  const [livePlans, setLivePlans] = useState({})
  useEffect(() => {
    axios.get(`${API}/api/v1/subscription/plans`).then((r) => { if (r.data.plans) setLivePlans(r.data.plans) }).catch(() => {})
  }, [])
  const plans = useMemo(() => {
    const out = [{ key: 'trial', name: T.trialName, price: null, period: '', feats: T.trialFeats.map(fmt), href: '/register', hot: false }]
    const w = Number(livePlans.weekly?.price_usd), m = Number(livePlans.monthly?.price_usd), y = Number(livePlans.yearly?.price_usd)
    const saveM = w && m ? Math.round((1 - m / (w * 52 / 12)) * 100) : 0
    const saveY = m && y ? Math.round((1 - y / (m * 12)) * 100) : 0
    for (const [key, period, save] of [['weekly', T.perWeek, 0], ['monthly', T.perMonth, saveM], ['yearly', T.perYear, saveY]]) {
      const lp = livePlans[key]
      if (!lp || lp.enabled === false || !lp.price_usd) continue
      const feats = ((isAr ? lp.features : lp.features_en) || lp.features || []).filter((f) => !SAVINGS_RE.test(f))
      out.push({ key, name: (isAr ? lp.name : lp.name_en) || lp.name || key, price: lp.price_usd, period, feats,
                 href: '/pricing', hot: key === 'monthly', save: save >= 5 ? save : 0 })
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [livePlans, isAr, trial.analyses, trial.chat])

  const tfBars = (k) => Array.from({ length: 12 }, (_, i) => 20 + Math.round(70 * Math.abs(Math.sin((i + 1) * (k + 1.3)))))
  const navLinks = [['#engine', T.nav.engine], ['#features', T.nav.features], [p('/strategy-builder'), T.nav.builder, true], ['#pricing', T.nav.pricing], ['#faq', T.nav.faq]]

  return (
    <div className="qx" dir={isAr ? 'rtl' : 'ltr'} ref={rootRef}>
      <span className="preview">{T.preview}</span>

      {/* ── header ── */}
      <header className={`hdr ${scrolled ? 'scrolled' : ''} ${hideHdr && !menuOpen ? 'hide' : ''}`}>
        <div className="wrap">
          <div style={{ display: 'flex', alignItems: 'center', gap: 40 }}>
            <Link to={p('/preview-home')} className="brand" aria-label="Qaffel AI"><BrandMark /><span dir="ltr">Qaffel <span className="grad">AI</span></span></Link>
            <nav className="nav" aria-label={T.menu}>
              {navLinks.map(([href, label, route]) => route
                ? <Link key={href} to={href}>{label}</Link>
                : <a key={href} href={href}>{label}</a>)}
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
          {navLinks.map(([href, label, route]) => route ? <Link key={href} to={href}>{label}</Link> : <a key={href} href={href}>{label}</a>)}
          <Link to={p('/about')}>{T.nav.about}</Link>
          <Link to="/contact">{T.nav.contact}</Link>
          <Link to="/referral">{T.nav.referral}</Link>
          <a href="/games/challenge">{T.nav.games}</a>
          {!user && <Link to="/login">{T.login}</Link>}
        </div>
      </header>

      <main id="top">
        {/* ── hero ── */}
        <section className="hero" ref={heroRef} aria-label="Qaffel AI">
          <div className="wrap hero-grid">
            <div className="hero-copy qrv">
              <span className="pill"><b>AI</b><span className="dot" /> {T.heroPill}</span>
              <h1>{T.h1a}<br />{T.h1b}<span className="grad">{T.h1c}</span></h1>
              <p className="lead">{T.heroLead}</p>
              <div className="hero-ctas">
                <Link to={user ? '/dashboard' : '/register'} className="btn btn-mint">{user ? T.dashboard : fmt(T.heroCta)}<Arrow /></Link>
                <a href="#engine" className="btn btn-line">{T.heroCta2}</a>
              </div>
              <div className="hero-note">{T.notes.map((n) => <span key={n}><Check s={15} w={2.4} />{n}</span>)}</div>
            </div>
            {/* (2026-10-17) المشهد الجديد: دماغ AI يحلل شارت شموع ويصدر الإشارة — يرسم المراحل والقرار وإشعار تيليجرام بنفسه */}
            <Suspense fallback={<div className="hs-fallback" />}><HeroScene text={heroText} /></Suspense>
          </div>
        </section>

        {/* ── ticker ── */}
        <div className="ticker" aria-label={T.marketsAria}>
          <div className="track">
            {[...TICKER, ...TICKER].map(([s, ar, en, c], i) => (
              <div className="tick" key={i} aria-hidden={i >= TICKER.length}><i style={{ '--c': c }} /><span className="mono">{s}</span><span>{isAr ? ar : en}</span></div>
            ))}
          </div>
        </div>

        {/* ── engine ── */}
        <section className="s" id="engine" ref={engineRef}>
          <div className="wrap">
            <div className="s-head qrv">
              <span className="eyebrow">{T.engineEyebrow}</span>
              <h2 className="h2">{T.engineH}</h2>
              <p className="lead">{T.engineLead}</p>
            </div>
            <div className="console qrv">
              <div className="panel c-left">
                <div className="mk-list" role="group" aria-label={T.pickMarket}>
                  {demo.map((x, i) => (
                    <button key={x.sym} type="button" className="mk" aria-pressed={i === eng.m} onClick={() => run(i)}>
                      <span className="mono">{x.sym}</span><small>{x.name}</small>
                    </button>
                  ))}
                </div>
                <div className="pipe">
                  {T.stages.map(([a, b], i) => {
                    const n = i + 1, cls = eng.stage > n ? 'done' : eng.stage === n ? 'active' : ''
                    return (
                      <div key={a} className={`stage-row ${cls}`}>
                        <span className="st-ic">{eng.stage > n ? <Check /> : n}</span>
                        <span><b>{a}</b><small className="mono">{b}</small></span>
                      </div>
                    )
                  })}
                </div>
                <button className="btn btn-line" type="button" onClick={() => run()} style={{ alignSelf: 'stretch' }}>{running ? T.running : T.rerun}</button>
              </div>
              <div className="panel c-right">
                <div className="tabs" role="tablist">
                  <button role="tab" type="button" aria-selected={eng.tab === 'sig'} onClick={() => setEng((s) => ({ ...s, tab: 'sig' }))}>{T.tabSig}</button>
                  <button role="tab" type="button" aria-selected={eng.tab === 'agent'} onClick={() => setEng((s) => ({ ...s, tab: 'agent' }))}>{T.tabAgent}</button>
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }} aria-live="polite">
                  {eng.tab === 'agent' ? (
                    <div className="chat">
                      <div className="bub me">{T.askAgent.split('{s}')[0]}<span className="mono">{d.sym}</span>{T.askAgent.split('{s}')[1]}</div>
                      {running
                        ? <div className="bub ai typing" aria-label={T.typing}><i /><i /><i /></div>
                        : <div className="bub ai"><small><span className="dot" style={{ width: 7, height: 7 }} />{T.agentName}</small>{d.agent}</div>}
                    </div>
                  ) : running ? (
                    <div className="skel"><i style={{ height: 44, width: '60%' }} /><i style={{ height: 140 }} /><i style={{ height: 120 }} /><i style={{ height: 40, width: '70%' }} /></div>
                  ) : (
                    <div className="result" key={eng.m}>
                      <div className="sig-top">
                        <div className="sym"><span className="mono">{d.sym}</span><span className="tag">{d.name} · 1H</span></div>
                        <span className={`side ${d.kind}`}>{sideLabel[d.kind]}</span>
                      </div>
                      {d.kind === 'wait' ? (<>
                        <div className="wait-box">
                          <h3>{T.waitH}</h3><p>{T.waitP}</p>
                          <div className="checks">{d.checks.map(([c, ok]) => <span key={c} className={ok ? '' : 'no'}>{ok ? '✓' : '✕'} {c}</span>)}</div>
                        </div>
                        <p className="disc">{T.waitNote}</p>
                      </>) : (<>
                        <div className="chart" style={{ margin: 0 }}>
                          <svg viewBox="0 0 400 112" preserveAspectRatio="none" aria-hidden="true"><polyline points={d.pts} fill="none" stroke={d.kind === 'buy' ? '#3CF2C0' : '#FF6B7A'} strokeWidth="2.4" /></svg>
                        </div>
                        <div className="lv">
                          <div><span>{T.lvEntry}</span><span className="mono" style={{ color: '#fff' }}>{d.lv[0]}</span></div>
                          <div><span>{T.lvSl}</span><span className="mono" style={{ color: 'var(--coral)' }}>{d.lv[1]}</span></div>
                          <div><span>{T.lvTp1}</span><span className="mono" style={{ color: 'var(--mint)' }}>{d.lv[2]}</span></div>
                          <div><span>{T.lvTp2}</span><span className="mono" style={{ color: 'var(--mint)' }}>{d.lv[3]}</span></div>
                        </div>
                        <div className="checks">{d.checks.map(([c, ok]) => <span key={c} className={ok ? '' : 'no'}>{ok ? '✓' : '✕'} {c}</span>)}</div>
                        <p className="disc" style={{ marginTop: 'auto' }}>{T.example}</p>
                      </>)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── features (bento) ── */}
        <section className="s" id="features" style={{ paddingTop: 0 }}>
          <div className="wrap">
            <div className="s-head qrv">
              <span className="eyebrow">{T.featEyebrow}</span>
              <h2 className="h2">{T.featH1}<span className="grad">{T.featH2}</span></h2>
            </div>
            <div className="bento">
              {T.feats.map(([h, txt], i) => (
                <article key={h} className={`card ${BENTO[i]} qrv`}
                  onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`); e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`) }}>
                  <span className="ic" style={FEAT_COLORS[i] ? { color: FEAT_COLORS[i] } : undefined}>{FEAT_ICONS[i]}</span>
                  <h3>{h}</h3>
                  <p>{txt}</p>
                  {i === 0 && (
                    <div className="tf">
                      {['4H', '1H', '15m'].map((tf, k) => (
                        <div key={tf}>
                          <span className="mono">{tf}</span>
                          <div className="bars">{tfBars(k).map((hgt, j) => <i key={j} style={{ '--c': ['#3CF2C0', '#7AB0FF', '#F7C35C'][k], '--h': `${hgt}%`, '--d': `${(j * 0.12).toFixed(2)}s` }} />)}</div>
                          <small>{T.tfLabels[k]}</small>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ── strategy builder (light) ── */}
        <section className="s" id="builder" style={{ paddingTop: 0 }}>
          <div className="wrap">
            <div className="s-head qrv">
              <span className="eyebrow">{T.buildEyebrow}</span>
              <h2 className="h2">{T.buildH}</h2>
              <p className="lead">{T.buildLead}</p>
            </div>
            <div className="builder qrv">
              <div className="panel b-panel" role="group" aria-label={T.condTitle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <b style={{ color: '#fff' }}>{T.condTitle}</b><span className="mono" style={{ color: 'var(--faint)', fontSize: 13 }}>XAUUSD · 15M</span>
                </div>
                {COND_KEYS.map(([k, w]) => (
                  <button key={k} type="button" className="cond" aria-pressed={!!on[k]} onClick={() => setOn((o) => ({ ...o, [k]: !o[k] }))}>
                    <span className="lbl"><span className="box">{on[k] && <Check />}</span>{T.conds[k]}</span>
                    <span className="mono">+{w}</span>
                  </button>
                ))}
                <Link to={p('/strategy-builder')} className="btn btn-line" style={{ marginTop: 8 }}>{T.openBuilder}<Arrow /></Link>
              </div>
              <div className="phone">
                <div className="phone-head"><span className="tg"><TgIcon /></span><span><b dir="ltr">@Qaffelbot</b><small>{T.connected}</small></span></div>
                <div className="phone-body" aria-live="polite">
                  {pct >= 70
                    ? <div className="msg"><b>{T.fired}</b><span className="mono">XAUUSD · 15M</span><br />{onNames.join(' + ')}<br /><span style={{ color: 'var(--faint)', fontSize: 12 }}>{T.power} {pct}%</span></div>
                    : <p className="empty">{T.noAlert}<br />{T.noAlert2}</p>}
                </div>
                <div className="power">
                  <div className="power-top"><span>{T.power}</span><span className="mono" style={{ color: '#fff' }}>{pct}%</span></div>
                  <div className={`power-bar ${pct >= 70 ? 'ok' : ''}`}><i style={{ '--p': `${pct}%` }} /></div>
                  <small style={{ color: 'var(--faint)', fontSize: 12 }}>{T.powerNote}</small>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── pricing ── */}
        <section className="s" id="pricing" style={{ paddingTop: 0 }}>
          <div className="wrap">
            <div className="s-head center qrv">
              <span className="eyebrow">{T.priceEyebrow}</span>
              <h2 className="h2">{T.priceH}</h2>
            </div>
            <div className="plans" style={{ '--n': Math.min(plans.length, 4) }}>
              {plans.map((pl) => (
                <div key={pl.key} className={`plan ${pl.hot ? 'hot' : ''} qrv`}>
                  <h3>{pl.name}{pl.save ? <span className="badge">{T.save.replace('{p}', pl.save)}</span> : null}</h3>
                  <div className="price">
                    {pl.price == null
                      ? <span style={{ fontFamily: 'var(--f-display)', fontSize: 44, fontWeight: 800, color: '#fff' }}>{T.free}</span>
                      : <><span className="mono">${pl.price}</span><small>{pl.period}</small></>}
                  </div>
                  <ul>{pl.feats.map((f) => <li key={f}><Check s={16} w={2.6} />{f}</li>)}</ul>
                  <Link to={pl.href} className={`btn ${pl.hot ? 'btn-mint' : 'btn-line'}`}>{pl.price == null ? T.start : T.subscribe}</Link>
                </div>
              ))}
            </div>
            <p className="pricing-note">{T.priceNote}</p>
            <div className="ref qrv">
              <div><b>{T.refTitle}</b><p>{T.refLine}</p></div>
              <Link to="/referral" className="btn btn-line">{T.refBtn}</Link>
            </div>
          </div>
        </section>

        {/* ── faq ── */}
        <section className="s" id="faq" style={{ paddingTop: 0 }}>
          <div className="wrap faq-grid">
            <div className="s-head qrv" style={{ margin: 0 }}>
              <span className="eyebrow">{T.faqEyebrow}</span>
              <h2 className="h2">{T.faqH}</h2>
              <p className="lead">{T.faqLead} <a href={TG_URL} target="_blank" rel="noreferrer" dir="ltr" style={{ color: 'var(--mint)' }}>@Qaffelbot</a></p>
            </div>
            <div className="qrv">
              {T.faq.map(([q, a], i) => (
                <div key={q} className="qa" data-open={openQ === i}>
                  <button type="button" aria-expanded={openQ === i} onClick={() => setOpenQ(openQ === i ? -1 : i)}>
                    <span>{q}</span>
                    <span className="plus"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true"><path d="M12 5 V19 M5 12 H19" /></svg></span>
                  </button>
                  <div className="ans"><p>{a}</p></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── learn ── */}
        <section className="s" style={{ paddingTop: 0 }}>
          <div className="wrap">
            <div className="s-head qrv" style={{ marginBottom: 24 }}>
              <span className="eyebrow">{T.learnEyebrow}</span>
              <h2 className="h2" style={{ fontSize: 'clamp(24px,3vw,34px)' }}>{T.learnH}</h2>
            </div>
            <div className="chips qrv">{BLOG.map((b) => <Link key={b.slug} to={isAr ? `/blog/${b.slug}` : `/en/blog/${b.slug}`}>{isAr ? b.ar : b.en}</Link>)}</div>
          </div>
        </section>

        {/* ── cta ── */}
        <div className="wrap">
          <div className="cta qrv">
            <div><h2>{T.ctaH1}<span className="grad">{T.ctaH2}</span></h2><p>{fmt(T.ctaP)}</p></div>
            <Link to={user ? '/dashboard' : '/register'} className="btn btn-mint" style={{ minHeight: 60, padding: '0 34px', fontSize: 17 }}>{user ? T.dashboard : T.ctaBtn}</Link>
          </div>
        </div>
      </main>

      {/* ── footer ── */}
      <footer>
        <div className="wrap">
          <div className="f-grid">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <a href="#top" className="brand"><BrandMark /><span dir="ltr">Qaffel <span className="grad">AI</span></span></a>
              <p style={{ color: 'var(--faint)', fontSize: 14, maxWidth: '34ch' }}>{T.fAbout}</p>
            </div>
            <div><h4>{T.fPlatform}</h4><ul>
              <li><Link to="/register">{T.fRegister}</Link></li>
              <li><Link to="/pricing">{T.nav.pricing}</Link></li>
              <li><Link to={p('/strategy-builder')}>{T.nav.builder}</Link></li>
              <li><Link to={isAr ? '/blog' : '/en/blog'}>{T.nav.blog}</Link></li>
              <li><a href="/games/challenge">{T.nav.games}</a></li>
            </ul></div>
            <div><h4>{T.fCompany}</h4><ul>
              <li><Link to={p('/about')}>{T.nav.about}</Link></li>
              <li><Link to="/referral">{T.nav.referral}</Link></li>
              <li><Link to="/contact">{T.nav.contact}</Link></li>
            </ul></div>
            <div><h4>{T.fLegal}</h4><ul>
              <li><Link to="/terms">{T.fTerms}</Link></li>
              <li><Link to="/privacy">{T.fPrivacy}</Link></li>
              <li><a href="#risk">{T.fRisk}</a></li>
            </ul></div>
          </div>
          <p className="risk" id="risk">{T.risk}</p>
          <div className="copy"><span>{T.rights}</span><span dir="ltr">@Qaffelbot · @qaffel_ai</span></div>
        </div>
      </footer>

      {/* ── mobile sticky bar ── */}
      {!user && (
        <div className={`mbar ${showBar ? 'show' : ''}`}>
          <Link to="/register" className="btn btn-mint">{T.start}</Link>
          <a href={TG_URL} target="_blank" rel="noreferrer" className="tgbtn" aria-label="Telegram"><TgIcon s={20} /></a>
        </div>
      )}
      <PublicChatBot />
    </div>
  )
}
