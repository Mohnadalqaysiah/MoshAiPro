import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Sparkles } from 'lucide-react'

/* ─────────────────────────────────────────────────────────────────────────
   أيقونات الأسواق — SVG مرسومة (لا إيموجي). كل أيقونة تعبّر عن الأصل نفسه:
   سبائك للذهب، عملة ₿، عملتان متداخلتان لأزواج الفوركس (الأساس/المقابل)،
   بلّورة إيثيريوم، قطرة للنفط، شموع للمؤشر.
────────────────────────────────────────────────────────────────────────── */
const Grad = ({ id, a, b }) => (
  <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stopColor={a} />
    <stop offset="1" stopColor={b} />
  </linearGradient>
)

function GoldIcon({ uid }) {
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" aria-hidden="true">
      <defs><Grad id={`g${uid}`} a="#FDE68A" b="#D97706" /></defs>
      <g transform="translate(24 24) scale(1.3) translate(-24 -26)">
        <polygon points="17,25 20,18 28,18 31,25" fill={`url(#g${uid})`} />
        <polygon points="7,34 10,27 18,27 21,34" fill={`url(#g${uid})`} />
        <polygon points="27,34 30,27 38,27 41,34" fill={`url(#g${uid})`} />
        <path d="M20 18.6h8M10 27.6h8M30 27.6h8" stroke="#FFFBEB" strokeOpacity=".75" strokeWidth="1.2" strokeLinecap="round" />
      </g>
    </svg>
  )
}

function CoinIcon({ uid, glyph, a, b }) {
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" aria-hidden="true">
      <defs><Grad id={`c${uid}`} a={a} b={b} /></defs>
      <circle cx="24" cy="24" r="16" fill={`url(#c${uid})`} />
      <circle cx="24" cy="24" r="12.5" fill="none" stroke="#fff" strokeOpacity=".35" strokeWidth="1" />
      <text x="24" y="30.5" textAnchor="middle" fontSize="19" fontWeight="800" fill="#fff" fontFamily="system-ui, sans-serif">{glyph}</text>
    </svg>
  )
}

// عملتان متداخلتان: الأساس (ملوّنة) ثم المقابل
function PairIcon({ uid, base, quote, a, b }) {
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" aria-hidden="true">
      <defs>
        <Grad id={`pa${uid}`} a={a} b={b} />
        <Grad id={`pb${uid}`} a="#94A3B8" b="#475569" />
      </defs>
      <circle cx="32" cy="31" r="12.5" fill={`url(#pb${uid})`} />
      <text x="32" y="36.5" textAnchor="middle" fontSize="15" fontWeight="800" fill="#fff" fillOpacity=".92" fontFamily="system-ui, sans-serif">{quote}</text>
      <circle cx="17" cy="17" r="13" fill={`url(#pa${uid})`} stroke="#0B1020" strokeWidth="1.8" />
      <text x="17" y="22.5" textAnchor="middle" fontSize="16" fontWeight="800" fill="#fff" fontFamily="system-ui, sans-serif">{base}</text>
    </svg>
  )
}

function EthIcon({ uid }) {
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" aria-hidden="true">
      <defs><Grad id={`e${uid}`} a="#C7D2FE" b="#6366F1" /></defs>
      <polygon points="24,5 12,24 24,30" fill="#C7D2FE" />
      <polygon points="24,5 36,24 24,30" fill="#818CF8" />
      <polygon points="12,27 24,33 24,43" fill="#A5B4FC" />
      <polygon points="36,27 24,33 24,43" fill={`url(#e${uid})`} />
    </svg>
  )
}

function OilIcon({ uid }) {
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" aria-hidden="true">
      <defs><Grad id={`o${uid}`} a="#CBD5E1" b="#334155" /></defs>
      <path d="M24 5C24 5 11 20 11 29a13 13 0 0 0 26 0C37 20 24 5 24 5Z" fill={`url(#o${uid})`} />
      <path d="M17 30a7 7 0 0 0 5 6.6" stroke="#fff" strokeOpacity=".55" strokeWidth="2" strokeLinecap="round" fill="none" />
    </svg>
  )
}

function IndexIcon({ uid }) {
  return (
    <svg viewBox="0 0 48 48" width="100%" height="100%" aria-hidden="true">
      <defs><Grad id={`i${uid}`} a="#6EE7B7" b="#059669" /></defs>
      <g stroke="#6EE7B7" strokeWidth="1.8" strokeLinecap="round">
        <line x1="12" y1="18" x2="12" y2="39" /><line x1="24" y1="10" x2="24" y2="33" /><line x1="36" y1="5" x2="36" y2="27" />
      </g>
      <rect x="8.5" y="24" width="7" height="10" rx="1.5" fill={`url(#i${uid})`} />
      <rect x="20.5" y="16" width="7" height="12" rx="1.5" fill={`url(#i${uid})`} />
      <rect x="32.5" y="9" width="7" height="13" rx="1.5" fill={`url(#i${uid})`} />
    </svg>
  )
}

const MARKETS = [
  { symbol: 'XAUUSD', cat: 'metals',  ar: 'الذهب',        en: 'Gold',       accent: '#F5B942', hot: true,  icon: (u) => <GoldIcon uid={u} /> },
  { symbol: 'BTCUSD', cat: 'crypto',  ar: 'البيتكوين',    en: 'Bitcoin',    accent: '#F7931A', icon: (u) => <CoinIcon uid={u} glyph="₿" a="#FDBA74" b="#EA580C" /> },
  { symbol: 'EURUSD', cat: 'forex',   ar: 'يورو/دولار',   en: 'EUR/USD',    accent: '#5B8CFF', icon: (u) => <PairIcon uid={u} base="€" quote="$" a="#93C5FD" b="#2563EB" /> },
  { symbol: 'GBPUSD', cat: 'forex',   ar: 'جنيه/دولار',   en: 'GBP/USD',    accent: '#A78BFA', icon: (u) => <PairIcon uid={u} base="£" quote="$" a="#C4B5FD" b="#7C3AED" /> },
  { symbol: 'USDJPY', cat: 'forex',   ar: 'دولار/ين',     en: 'USD/JPY',    accent: '#FB7185', icon: (u) => <PairIcon uid={u} base="$" quote="¥" a="#FDA4AF" b="#E11D48" /> },
  { symbol: 'ETHUSD', cat: 'crypto',  ar: 'إثيريوم',      en: 'Ethereum',   accent: '#818CF8', icon: (u) => <EthIcon uid={u} /> },
  { symbol: 'USOIL',  cat: 'energy',  ar: 'النفط الخام',  en: 'Crude Oil',  accent: '#94A3B8', icon: (u) => <OilIcon uid={u} /> },
  { symbol: 'NAS100', cat: 'indices', ar: 'ناسداك',       en: 'NASDAQ 100', accent: '#34D399', soon: true, icon: (u) => <IndexIcon uid={u} /> },
]

const CATS = {
  all:     { ar: 'الكل',     en: 'All' },
  metals:  { ar: 'معادن',    en: 'Metals' },
  crypto:  { ar: 'كريبتو',   en: 'Crypto' },
  forex:   { ar: 'فوركس',    en: 'Forex' },
  energy:  { ar: 'طاقة',     en: 'Energy' },
  indices: { ar: 'مؤشرات',   en: 'Indices' },
}

const CSS = `
  .mk-card { --a: #fff; position: relative; transition: transform .25s ease, border-color .25s ease, opacity .25s ease, box-shadow .25s ease; }
  .mk-card::before { content:''; position:absolute; inset:0; border-radius:inherit; pointer-events:none;
    background: radial-gradient(120% 90% at 50% 0%, color-mix(in srgb, var(--a) 18%, transparent), transparent 62%); opacity:.55; transition: opacity .25s ease }
  .mk-card:hover { transform: translateY(-4px); border-color: color-mix(in srgb, var(--a) 55%, transparent); box-shadow: 0 14px 40px -12px color-mix(in srgb, var(--a) 45%, transparent) }
  .mk-card:hover::before { opacity:1 }
  .mk-card:hover .mk-arrow { opacity:1; transform: translate(0,0) }
  .mk-arrow { opacity:0; transform: translate(-4px,4px); transition: all .25s ease }
  .mk-dim { opacity:.22; transform: scale(.97); pointer-events:none; filter: saturate(.4) }
  @media (prefers-reduced-motion: reduce) { .mk-card, .mk-arrow { transition: none } }
`

export default function MarketsShowcase({ isAr, ctaTo }) {
  const [cat, setCat] = useState('all')
  const present = ['all', ...new Set(MARKETS.map(m => m.cat))]

  return (
    <div>
      <style>{CSS}</style>

      {/* فلتر الفئات — يخفّت غير المطابق بدل إزالته (لا قفز بالتخطيط) */}
      <div className="flex flex-wrap items-center justify-center gap-2 mb-8" role="tablist">
        {present.map(c => (
          <button
            key={c}
            role="tab"
            aria-selected={cat === c}
            onClick={() => setCat(c)}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
              cat === c
                ? 'bg-white text-gray-900 border-white'
                : 'text-gray-400 border-white/10 hover:text-white hover:border-white/25'
            }`}
          >
            {CATS[c][isAr ? 'ar' : 'en']}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {MARKETS.map((m) => {
          const dim = cat !== 'all' && m.cat !== cat
          const uid = m.symbol
          const inner = (
            <>
              {m.hot && (
                <span className="absolute -top-2.5 start-4 z-10 flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full text-amber-950"
                  style={{ background: 'linear-gradient(90deg,#FCD34D,#F59E0B)' }}>
                  <Sparkles size={10} /> {isAr ? 'الأكثر تداولاً' : 'Most Traded'}
                </span>
              )}
              {m.soon && (
                <span className="absolute -top-2.5 start-4 z-10 text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/10 text-gray-300 border border-white/15">
                  {isAr ? 'قريباً' : 'Soon'}
                </span>
              )}

              <div
                className="relative w-[76px] h-[76px] rounded-2xl p-2 mb-4 mx-auto"
                style={{ background: `linear-gradient(145deg, ${m.accent}26, ${m.accent}08)`, border: `1px solid ${m.accent}40` }}
              >
                {m.icon(uid)}
              </div>

              <div className="relative text-center">
                <div className="font-mono font-bold text-white text-[15px] tracking-wide" dir="ltr">{m.symbol}</div>
                <div className="text-gray-400 text-xs mt-0.5">{isAr ? m.ar : m.en}</div>
                <div className="mt-3 inline-flex items-center gap-1 text-[10.5px] px-2 py-0.5 rounded-full"
                  style={{ color: m.accent, background: `${m.accent}14`, border: `1px solid ${m.accent}30` }}>
                  {CATS[m.cat][isAr ? 'ar' : 'en']}
                </div>
              </div>

              {!m.soon && (
                <ArrowUpRight size={15} className="mk-arrow absolute top-3.5 end-3.5 text-white/70" />
              )}
            </>
          )

          const cls = `mk-card rounded-2xl p-5 pt-6 border border-white/10 bg-white/[0.025] block ${dim ? 'mk-dim' : ''}`
          const style = { '--a': m.accent }

          return m.soon ? (
            <div key={m.symbol} className={cls} style={style} aria-disabled="true">{inner}</div>
          ) : (
            <Link key={m.symbol} to={ctaTo} className={cls} style={style} tabIndex={dim ? -1 : 0}
              aria-label={`${m.symbol} — ${isAr ? m.ar : m.en}`}>
              {inner}
            </Link>
          )
        })}
      </div>
    </div>
  )
}
