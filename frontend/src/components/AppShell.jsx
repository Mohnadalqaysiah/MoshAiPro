import { useState, useEffect, useRef, Suspense, lazy } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import {
  Activity, Zap, History, Globe, BarChart2, TrendingUp, BookOpen, Sparkles, Shield,
  Gift, LogOut, Sun, Moon, Menu, X, Send, CheckCircle, Copy, ExternalLink, Settings, Plus,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { useTheme } from '../contexts/ThemeContext'
import useSiteSettings from '../hooks/useSiteSettings'
import useMarkets from '../hooks/useMarkets'
import Logo from './Logo'

const TrialBanner        = lazy(() => import('./TrialBanner'))
const TelegramLinkBanner = lazy(() => import('./TelegramLinkBanner'))
const EmailVerifyBanner  = lazy(() => import('./EmailVerifyBanner'))
const OnboardingTour     = lazy(() => import('./OnboardingTour'))

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Categories as they exist in market_configs today (forex includes XAUUSD;
// commodity = indices + silver/platinum/copper + oil/gas). Unknown categories
// still render (uppercased 3-letter code) rather than being dropped.
const CAT_META = {
  forex:     { short: 'FX',  ar: 'فوركس وذهب',   en: 'Forex & Gold' },
  commodity: { short: 'CMD', ar: 'سلع ومؤشرات',  en: 'Commodities & Indices' },
  crypto:    { short: 'BTC', ar: 'كريبتو',       en: 'Crypto' },
  stock:     { short: 'STK', ar: 'أسهم أمريكية', en: 'US Stocks' },
  gulf:      { short: 'GCC', ar: 'أسواق خليجية', en: 'Gulf Markets' },
}
const CAT_ORDER = Object.keys(CAT_META)

const planBadge = {
  trial:   { ar: 'تجريبي', en: 'Trial',   cls: 'bg-blue-900/50 text-blue-300 border border-blue-700/50' },
  weekly:  { ar: 'أسبوعي', en: 'Weekly',  cls: 'bg-green-900/50 text-green-300 border border-green-700/50' },
  monthly: { ar: 'شهري',   en: 'Monthly', cls: 'bg-purple-900/50 text-purple-300 border border-purple-700/50' },
  banned:  { ar: 'محظور',  en: 'Banned',  cls: 'bg-red-900/50 text-red-300 border border-red-700/50' },
}

// ── Rail: market categories as "servers" ────────────────────────────────────
function Rail({ isAr }) {
  const { markets } = useMarkets()
  const navigate = useNavigate()
  const location = useLocation()
  const [params] = useSearchParams()
  const siteSettings = useSiteSettings()

  const present = [...new Set(markets.map(m => m.category || 'other'))]
  const cats = [...CAT_ORDER.filter(c => present.includes(c)), ...present.filter(c => !CAT_META[c])]
  const activeCat = location.pathname === '/dashboard'
    ? (params.get('cat') || localStorage.getItem('mosh_quick_cat') || '')
    : ''

  return (
    <nav className="hidden lg:flex flex-col items-center gap-3 py-4 q-panel border-e q-line" aria-label={isAr ? 'فئات الأسواق' : 'Market categories'}>
      <Link to="/dashboard" className="w-11 h-11 rounded-2xl q-logo grid place-items-center overflow-hidden" title={siteSettings.site_name || 'Qaffel AI'}>
        {siteSettings.site_logo_url
          ? <img src={siteSettings.site_logo_url} alt="logo" className="w-8 h-8 object-contain" />
          : <Logo className="w-8 h-8 object-contain" />}
      </Link>
      <hr className="w-6 q-line" />
      {cats.map(c => {
        const meta = CAT_META[c] || { short: c.slice(0, 3).toUpperCase(), ar: c, en: c }
        const on = activeCat === c
        return (
          <button
            key={c}
            onClick={() => navigate(`/dashboard?cat=${c}`)}
            title={isAr ? meta.ar : meta.en}
            className={`relative w-11 h-11 rounded-2xl grid place-items-center text-[11px] font-extrabold tracking-wide border transition-all hover:-translate-y-0.5
              ${on ? 'q-rail-on text-white' : 'q-glass q-glass-hover text-gray-200'}`}
          >
            {meta.short}
            {on && <span className="absolute -end-4 top-3 w-1 h-5 rounded-full bg-[var(--q-acc1)]" />}
          </button>
        )
      })}
      <Link
        to="/profile"
        title={isAr ? 'إدارة قائمة المراقبة' : 'Manage watchlist'}
        className="mt-auto w-11 h-11 rounded-2xl grid place-items-center border border-dashed q-line text-gray-400 hover:text-white q-glass-hover"
      >
        <Plus size={16} />
      </Link>
    </nav>
  )
}

// ── Live gold sparkline (real 15m closes) ───────────────────────────────────
function LiveGoldWidget({ isAr }) {
  const { isDark } = useTheme()
  const [price, setPrice] = useState(null)
  const [closes, setCloses] = useState([])
  const canvasRef = useRef(null)

  useEffect(() => {
    let alive = true
    const loadPrice = () => axios.get(`${API}/api/v1/markets/XAUUSD/price`)
      .then(r => { if (alive) setPrice(r.data?.data?.price ?? null) }).catch(() => {})
    const loadCandles = () => axios.get(`${API}/api/v1/markets/XAUUSD/candles?interval=15m&limit=40`)
      .then(r => { if (alive) setCloses((r.data?.data || []).map(c => c.close)) }).catch(() => {})
    loadPrice(); loadCandles()
    const p = setInterval(loadPrice, 60_000)
    const c = setInterval(loadCandles, 5 * 60_000)
    return () => { alive = false; clearInterval(p); clearInterval(c) }
  }, [])

  useEffect(() => {
    const cv = canvasRef.current
    if (!cv || closes.length < 2) return
    const dpr = window.devicePixelRatio || 1
    const w = cv.clientWidth, h = cv.clientHeight
    cv.width = w * dpr; cv.height = h * dpr
    const g = cv.getContext('2d'); g.scale(dpr, dpr)
    const min = Math.min(...closes), max = Math.max(...closes), span = (max - min) || 1, pad = 5
    const x = i => i / (closes.length - 1) * w
    const y = v => h - pad - (v - min) / span * (h - pad * 2)
    const up = closes[closes.length - 1] >= closes[0]
    // Dark glass: bright cyan/rose. Light glass (near-white): darker cyan-600/rose-600 so the
    // line and fill don't melt into the background.
    const col = isDark ? (up ? '34,211,238' : '251,113,133') : (up ? '8,145,178' : '225,29,72')
    g.clearRect(0, 0, w, h)
    const gr = g.createLinearGradient(0, 0, 0, h)
    gr.addColorStop(0, `rgba(${col},${isDark ? 0.45 : 0.28})`); gr.addColorStop(1, `rgba(${col},0)`)
    g.beginPath(); g.moveTo(x(0), h)
    closes.forEach((v, i) => g.lineTo(x(i), y(v)))
    g.lineTo(x(closes.length - 1), h); g.closePath(); g.fillStyle = gr; g.fill()
    g.beginPath(); closes.forEach((v, i) => i ? g.lineTo(x(i), y(v)) : g.moveTo(x(i), y(v)))
    g.strokeStyle = `rgba(${col},1)`; g.lineWidth = 2.25; g.lineJoin = 'round'; g.stroke()
    const lx = x(closes.length - 1), ly = y(closes[closes.length - 1])
    g.beginPath(); g.arc(lx, ly, 3.5, 0, Math.PI * 2); g.fillStyle = `rgba(${col},1)`; g.fill()
  }, [closes, isDark])

  const first = closes[0], last = closes[closes.length - 1]
  const chg = first && last ? ((last - first) / first) * 100 : null

  return (
    // السعر الكبير = سبوت (TV feed) — نفس اللي يشوفه المستخدم بالتحليل.
    // الخط البياني = شموع GC=F (العقود الآجلة، مصدر الكاندلز الوحيد للذهب)
    // ويختلف عن السبوت بفارق أساس $10-60، فنسمّيه بوضوح بدل ما نوهم إنه سبوت.
    <div className="rounded-2xl q-glass p-3">
      <div className="flex items-baseline justify-between text-[11px] text-gray-300">
        <span className="font-semibold">XAUUSD · {isAr ? 'سبوت' : 'spot'}</span>
        {chg != null && (
          <span
            className={`tabular-nums font-bold ${chg >= 0 ? (isDark ? 'text-emerald-400' : 'text-emerald-600') : (isDark ? 'text-rose-400' : 'text-rose-600')}`}
            title={isAr ? 'تغيّر عقود الذهب الآجلة (GC=F) خلال آخر 10 ساعات تداول' : 'Gold futures (GC=F) change over the last 10 trading hours'}
          >
            {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
          </span>
        )}
      </div>
      <div className="text-xl font-extrabold text-white tabular-nums leading-tight mt-0.5">
        {price != null ? Number(price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
      </div>
      {closes.length > 1 && (
        <>
          <canvas ref={canvasRef} className="block w-full h-11 mt-1" aria-label="Gold futures 15m sparkline" />
          <div className="text-[11px] text-gray-300 mt-1 leading-snug">{isAr ? 'الاتجاه: عقود آجلة GC=F · 15m · آخر 10 ساعات تداول' : 'Trend: GC=F futures · 15m · last 10 trading hours'}</div>
        </>
      )}
    </div>
  )
}

// ── Sidebar ─────────────────────────────────────────────────────────────────
function SidebarContent({ isAr, onNavigate }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { toggle: toggleLang } = useLang()
  const { isDark, toggle: toggleTheme } = useTheme()
  const siteSettings = useSiteSettings()

  const links = [
    { path: '/dashboard',       ar: 'الرئيسية',          en: 'Home',        icon: <Activity size={17} /> },
    { path: '/signals',         ar: 'الإشارات',          en: 'Signals',     icon: <Zap size={17} /> },
    { path: '/analyses',        ar: 'سجل التحليل',       en: 'Analyses',    icon: <History size={17} /> },
    { path: '/market-overview', ar: 'نظرة الأسواق',      en: 'Overview',    icon: <Globe size={17} /> },
    { path: '/backtesting',     ar: 'الأداء التاريخي',   en: 'Backtesting', icon: <BarChart2 size={17} /> },
    { path: '/analytics',       ar: 'التحليلات',         en: 'Analytics',   icon: <TrendingUp size={17} /> },
    { path: '/journal',         ar: 'يومية التداول',     en: 'Journal',     icon: <BookOpen size={17} /> },
    { path: '/strategies',      ar: 'بناء الاستراتيجيات', en: 'Strategies', icon: <Sparkles size={17} />, tag: isAr ? 'تجريبي' : 'Beta' },
    { path: '/affiliate',       ar: 'إحالاتي',           en: 'Referrals',   icon: <Gift size={17} /> },
  ]
  const isActive = p => location.pathname === p || (p === '/dashboard' && location.pathname === '/')
  const go = () => onNavigate && onNavigate()
  const handleLogout = () => { logout(); navigate('/login') }
  const initial = (user?.full_name || user?.email || '?').trim().charAt(0).toUpperCase()

  return (
    <div className="flex flex-col h-full gap-1.5">
      <h2 className="text-lg font-extrabold text-white px-2 pt-1 pb-3">{siteSettings.site_name || 'Qaffel AI'}</h2>

      <nav className="flex flex-col gap-0.5">
        {links.map(l => (
          <Link
            key={l.path}
            to={l.path}
            onClick={go}
            className={`flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-sm transition-colors
              ${isActive(l.path) ? 'q-nav-on text-white font-semibold' : 'text-gray-300 hover:text-white q-glass-hover'}`}
          >
            <span className="opacity-85">{l.icon}</span>
            {isAr ? l.ar : l.en}
            {l.tag && <span className="ms-auto text-[10px] px-2 py-0.5 rounded-full bg-amber-400/15 text-amber-300 font-semibold">{l.tag}</span>}
          </Link>
        ))}
        {user?.role === 'admin' && (
          <Link to="/admin" onClick={go} className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-sm text-amber-300 hover:text-amber-200 q-glass-hover">
            <Shield size={17} /> {isAr ? 'الإدارة' : 'Admin'}
          </Link>
        )}
      </nav>

      <div className="mt-auto flex flex-col gap-2 pt-3">
        <LiveGoldWidget isAr={isAr} />

        <div className="flex items-center gap-2.5 px-1 pt-1">
          <Link to="/profile" onClick={go} className="flex items-center gap-2.5 min-w-0 flex-1" title={isAr ? 'حسابي' : 'My account'}>
            <span className="w-9 h-9 rounded-xl grid place-items-center font-extrabold text-white bg-gradient-to-br from-[var(--q-acc3)] to-[var(--q-acc2)]">{initial}</span>
            <span className="min-w-0">
              <b className="block text-[13px] text-white truncate">{user?.full_name || user?.email}</b>
              <small className="block text-[11px] text-gray-400 truncate">{user?.full_name ? user.email : (isAr ? 'حسابي' : 'My account')}</small>
            </span>
          </Link>
          <button onClick={toggleTheme} title={isDark ? (isAr ? 'الوضع النهاري' : 'Light mode') : (isAr ? 'الوضع الليلي' : 'Dark mode')} className="w-8 h-8 rounded-lg q-glass grid place-items-center text-gray-300 hover:text-amber-300">
            {isDark ? <Sun size={14} /> : <Moon size={14} />}
          </button>
          <button onClick={toggleLang} title={isAr ? 'Switch to English' : 'التبديل للعربية'} className="w-8 h-8 rounded-lg q-glass grid place-items-center text-[11px] font-bold text-gray-300 hover:text-white">
            {isAr ? 'EN' : 'AR'}
          </button>
          <button onClick={handleLogout} title={isAr ? 'تسجيل الخروج' : 'Logout'} className="w-8 h-8 rounded-lg q-glass grid place-items-center text-gray-300 hover:text-rose-400">
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Profile panel widgets ───────────────────────────────────────────────────
function PerformanceMini({ isAr }) {
  const [d, setD] = useState(null)
  useEffect(() => {
    axios.get(`${API}/api/v1/signals/performance`).then(r => setD(r.data)).catch(() => {})
  }, [])
  if (!d?.rolling_30d) return null
  const r = d.rolling_30d, w = d.current_week
  const ptColor = v => v > 0 ? 'text-emerald-400' : v < 0 ? 'text-rose-400' : 'text-gray-400'
  return (
    <div className="rounded-2xl q-glass p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-[13px] font-bold text-gray-300">{isAr ? 'أداء الإشارات' : 'Signal performance'}</h3>
        <Link to="/dashboard?tab=performance" className="text-[11px] text-gray-400 hover:text-[var(--q-acc3)]">{isAr ? 'التفاصيل' : 'Details'}</Link>
      </div>
      {r.sufficient_data ? (
        <div className="grid grid-cols-2 gap-3 mt-3">
          <div>
            <div className="text-[11px] text-gray-500">{isAr ? 'نسبة النجاح' : 'Win rate'}</div>
            <div className="text-2xl font-extrabold text-white tabular-nums">{r.win_rate}%</div>
          </div>
          <div>
            <div className="text-[11px] text-gray-500">{isAr ? 'العائد / قرار' : 'Expectancy'}</div>
            <div className={`text-xl font-bold tabular-nums ${ptColor(r.expectancy)}`}>{r.expectancy > 0 ? '+' : ''}{r.expectancy}</div>
          </div>
        </div>
      ) : (
        <div className="mt-2">
          <p className="text-sm text-white">{isAr ? 'قيد جمع بيانات كافية' : 'Collecting enough data'}</p>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden my-2">
            <div className="h-full rounded-full q-conf" style={{ width: `${Math.min(100, (r.total_trades / r.min_decisions) * 100)}%` }} />
          </div>
          <p className="text-[11px] text-gray-400 tabular-nums">
            {isAr ? `${r.total_trades} من ${r.min_decisions} قرار — تُعرض النسبة عند اكتمال العينة` : `${r.total_trades} of ${r.min_decisions} decisions — shown once the sample is complete`}
          </p>
        </div>
      )}
      {w && (
        <div className="flex justify-between text-[11px] mt-3 pt-3 border-t q-line tabular-nums">
          <span className="text-gray-500">{w.week_label}</span>
          <span className="text-gray-300">{w.wins}/{w.total_trades} · <b className={ptColor(w.total_points)}>{w.total_points > 0 ? '+' : ''}{w.total_points}</b></span>
        </div>
      )}
    </div>
  )
}

function TelegramMini({ isAr }) {
  const { user } = useAuth()
  const [link, setLink] = useState('')
  const [bot, setBot] = useState('Qaffelbot')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  if (!user) return null

  const fetchLink = async () => {
    if (link) return link
    setBusy(true)
    try {
      const r = await axios.get(`${API}/api/v1/auth/telegram-link`)
      setLink(r.data.link || ''); if (r.data.bot_username) setBot(r.data.bot_username)
      return r.data.link || ''
    } catch { return '' } finally { setBusy(false) }
  }
  const open = async () => { const l = await fetchLink(); if (l) window.open(l, '_blank', 'noreferrer') }
  const copy = async () => { const l = await fetchLink(); if (!l) return; navigator.clipboard.writeText(l); setCopied(true); setTimeout(() => setCopied(false), 2000) }

  if (user.telegram_linked) {
    return (
      <div className="rounded-2xl q-glass p-4 flex items-center gap-3">
        <span className="w-9 h-9 rounded-xl bg-emerald-500/15 grid place-items-center text-emerald-400"><CheckCircle size={16} /></span>
        <div className="min-w-0">
          <p className="text-sm text-white font-semibold truncate">Telegram {isAr ? 'مرتبط' : 'linked'}{user.telegram_username ? ` — @${user.telegram_username}` : ''}</p>
          <Link to="/dashboard?tab=account" className="text-[11px] text-gray-400 hover:text-[var(--q-acc3)]">{isAr ? 'إدارة الربط' : 'Manage link'}</Link>
        </div>
      </div>
    )
  }
  return (
    <div className="rounded-2xl p-4 border q-line bg-gradient-to-br from-cyan-500/10 to-violet-600/10">
      <h3 className="text-[13px] font-bold text-white flex items-center gap-2"><Send size={14} className="text-sky-400" /> {isAr ? 'اربط حسابك مع Telegram' : 'Link your Telegram'}</h3>
      <p className="text-[12px] text-gray-300 mt-1.5 mb-3">{isAr ? `استلم الإشارات وتنبيهات TP/SL لحظياً على @${bot}.` : `Get signals and TP/SL alerts instantly on @${bot}.`}</p>
      <div className="flex gap-2">
        <button onClick={open} disabled={busy} className="flex-1 flex items-center justify-center gap-2 py-2 rounded-xl bg-[#229ED9] hover:bg-[#1f8fc5] disabled:opacity-60 text-white text-sm font-semibold">
          <ExternalLink size={14} /> {busy ? (isAr ? 'جاري...' : 'Loading…') : (isAr ? 'ربط الآن' : 'Link now')}
        </button>
        <button onClick={copy} disabled={busy} title={isAr ? 'نسخ الرابط' : 'Copy link'} className="w-10 rounded-xl q-glass grid place-items-center text-gray-300 hover:text-white">
          {copied ? <CheckCircle size={14} className="text-emerald-400" /> : <Copy size={14} />}
        </button>
      </div>
    </div>
  )
}

function ReferralMini({ isAr }) {
  const [d, setD] = useState(null)
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    axios.get(`${API}/api/v1/affiliate/points-summary`).then(r => setD(r.data)).catch(() => {})
  }, [])
  if (!d) return null
  const copy = () => { navigator.clipboard.writeText(d.referral_link); setCopied(true); setTimeout(() => setCopied(false), 2000) }
  return (
    <div className="rounded-2xl q-glass p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-[13px] font-bold text-gray-300">{isAr ? 'إحالاتي' : 'Referrals'}</h3>
        <Link to="/affiliate" className="text-[11px] text-gray-400 hover:text-[var(--q-acc3)]">{isAr ? 'البرنامج' : 'Program'}</Link>
      </div>
      <div className="mt-1 text-2xl font-extrabold text-white tabular-nums">
        {d.points} <small className="text-xs font-normal text-gray-400">{isAr ? 'نقطة' : 'points'}</small>
        <small className="text-xs font-normal text-gray-500 ms-2">· {d.total_referrals} {isAr ? 'مدعوّين' : 'invited'}</small>
      </div>
      <div className="flex gap-1.5 mt-2.5">
        <input readOnly value={d.referral_link} dir="ltr" aria-label="Referral link" className="flex-1 min-w-0 px-2.5 py-1.5 rounded-lg bg-black/30 border q-line text-[11px] text-gray-300 text-left" />
        <button onClick={copy} className="px-3 rounded-lg q-glass text-[12px] text-gray-200 hover:text-white">{copied ? (isAr ? 'تم' : 'Done') : (isAr ? 'نسخ' : 'Copy')}</button>
      </div>
    </div>
  )
}

function ProfilePanel({ isAr }) {
  const { user } = useAuth()
  if (!user) return null
  const badge = planBadge[user.plan]
  const initial = (user.full_name || user.email || '?').trim().charAt(0).toUpperCase()
  const isTrial = user.plan === 'trial'
  const days = user.days_left

  return (
    <aside className="hidden xl:flex flex-col gap-3.5 p-4 pb-24 q-panel border-s q-line">
      <div className="rounded-2xl q-glass p-4">
        <div className="relative w-24 h-24 mx-auto mb-2 grid place-items-center">
          <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full" aria-hidden="true">
            <defs><linearGradient id="q-hex" x1="0" x2="1"><stop offset="0" stopColor="#FF4FD8" /><stop offset="1" stopColor="#22D3EE" /></linearGradient></defs>
            <polygon points="50,3 91,26 91,74 50,97 9,74 9,26" fill="none" stroke="url(#q-hex)" strokeWidth="2.5" />
          </svg>
          <div className="w-[70px] h-[70px] grid place-items-center text-2xl font-extrabold text-white bg-gradient-to-br from-[var(--q-acc3)] via-[var(--q-acc2)] to-[var(--q-acc1)]"
               style={{ clipPath: 'polygon(50% 0,93% 25%,93% 75%,50% 100%,7% 75%,7% 25%)' }}>{initial}</div>
        </div>
        <div className="text-center">
          <b className="block text-lg font-extrabold text-white truncate">{user.full_name || user.email}</b>
          {user.full_name && <small className="block text-gray-400 truncate">{user.email}</small>}
        </div>
        <div className="flex justify-center flex-wrap gap-2 mt-3">
          {badge && <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${badge.cls}`}>{isAr ? badge.ar : badge.en}</span>}
          {days != null && (
            <span className="text-xs px-2.5 py-1 rounded-full bg-amber-400/12 border border-amber-400/30 text-amber-300 tabular-nums">
              {isAr ? `${days} أيام متبقية` : `${days} days left`}
            </span>
          )}
        </div>
        {isTrial && (
          <div className="grid grid-cols-2 gap-2 mt-3 text-center tabular-nums">
            <div className="rounded-xl bg-black/20 py-2"><b className="block text-white">{user.trial_analyses_left ?? 0}</b><small className="text-[11px] text-gray-400">{isAr ? 'تحليل متبقٍ' : 'analyses left'}</small></div>
            <div className="rounded-xl bg-black/20 py-2"><b className="block text-white">{user.trial_chat_left ?? 0}</b><small className="text-[11px] text-gray-400">{isAr ? 'رسالة شات' : 'chat messages'}</small></div>
          </div>
        )}
        <Link to={isTrial ? '/pricing' : '/profile'} className="mt-3 block text-center py-2.5 rounded-xl q-cta text-white font-bold text-sm">
          {isTrial ? (isAr ? 'ترقية الاشتراك' : 'Upgrade') : (isAr ? 'إدارة الحساب' : 'Manage account')}
        </Link>
      </div>

      <PerformanceMini isAr={isAr} />
      <TelegramMini isAr={isAr} />
      <ReferralMini isAr={isAr} />
    </aside>
  )
}

// ── Shell ───────────────────────────────────────────────────────────────────
export default function AppShell({ children }) {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const location = useLocation()
  const siteSettings = useSiteSettings()
  const [drawer, setDrawer] = useState(false)

  useEffect(() => { setDrawer(false) }, [location.pathname])
  useEffect(() => {
    document.body.style.overflow = drawer ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [drawer])

  return (
    <div className="min-h-screen q-ground text-gray-100" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[72px_232px_minmax(0,1fr)] xl:grid-cols-[72px_232px_minmax(0,1fr)_296px]">
        <Rail isAr={isAr} />

        <aside className="hidden lg:block p-3.5 q-panel border-e q-line">
          {/* pb-24 keeps the user row clear of the floating chat button (ChatBot: fixed bottom-5, ~56px tall) */}
          <div className="sticky top-3.5 h-[calc(100vh-28px)] pb-24"><SidebarContent isAr={isAr} /></div>
        </aside>

        <div className="min-w-0 flex flex-col">
          {/* Mobile top bar */}
          <header className="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-3 py-2.5 q-panel border-b q-line backdrop-blur-md">
            <button onClick={() => setDrawer(true)} aria-label={isAr ? 'القائمة' : 'Menu'} className="w-9 h-9 rounded-xl q-glass grid place-items-center text-gray-200"><Menu size={18} /></button>
            <Link to="/dashboard" className="flex items-center gap-2 min-w-0">
              <span className="w-8 h-8 rounded-xl q-logo grid place-items-center overflow-hidden">
                {siteSettings.site_logo_url ? <img src={siteSettings.site_logo_url} alt="logo" className="w-6 h-6 object-contain" /> : <Logo className="w-6 h-6 object-contain" />}
              </span>
              <span className="text-white font-extrabold truncate">{siteSettings.site_name || 'Qaffel AI'}</span>
            </Link>
          </header>

          {/* On xl+ the profile panel already shows trial credits + the Telegram card,
              so the two strip banners only render below that breakpoint. */}
          <Suspense fallback={null}>
            <EmailVerifyBanner />
            <div className="xl:hidden"><TrialBanner /></div>
            <div className="xl:hidden"><TelegramLinkBanner /></div>
            <OnboardingTour />
          </Suspense>

          <main className="flex-1 min-w-0 px-3 sm:px-5 py-4 sm:py-5 max-w-[1180px] w-full mx-auto">
            {children}
          </main>
        </div>

        <ProfilePanel isAr={isAr} />
      </div>

      {/* Mobile drawer */}
      {drawer && (
        <div className="lg:hidden fixed inset-0 z-40" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/60" onClick={() => setDrawer(false)} />
          <div className="absolute inset-y-0 start-0 w-[280px] max-w-[85vw] p-4 bg-gray-900 border-e q-line overflow-y-auto">
            <button onClick={() => setDrawer(false)} aria-label={isAr ? 'إغلاق' : 'Close'} className="absolute top-3 end-3 w-8 h-8 rounded-lg q-glass grid place-items-center text-gray-300"><X size={16} /></button>
            <SidebarContent isAr={isAr} onNavigate={() => setDrawer(false)} />
          </div>
        </div>
      )}
    </div>
  )
}
