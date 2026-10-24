/**
 * MyTradesPanel (2026-10-24) — "صفقاتي": كل ما وصل المستخدم (البوت + حسابه)، بفلاتر، وزر "تحقق" يعرض الشموع الحقيقية للصفقة.
 * حلّت محل "سجل إشاراتك" التي كانت تعرض تحليلات المستخدم وحده لا ما وصله (ملاحظة المالك 24/10).
 * الشموع من نفس مرجع حساب النتيجة (services/trade_chart.py) — فيرى العميل بعينه أين وصل السعر.
 */
import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Activity, RefreshCw, Search, X } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const ST = {
  TP2_HIT:   { ar: 'الهدف 2', en: 'TP2', icon: '🏆', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  TP1_HIT:   { ar: 'الهدف 1', en: 'TP1', icon: '✅', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  SL_HIT:    { ar: 'وقف خسارة', en: 'Stop', icon: '❌', cls: 'bg-rose-500/15 text-rose-300 border-rose-500/30' },
  BREAKEVEN: { ar: 'تأمين', en: 'Breakeven', icon: '⚖️', cls: 'bg-gray-500/15 text-gray-300 border-gray-500/30' },
  EXPIRED:   { ar: 'انتهت', en: 'Expired', icon: '⏰', cls: 'bg-gray-500/15 text-gray-400 border-gray-600/30' },
  ACTIVE:    { ar: 'مفتوحة', en: 'Open', icon: '🟢', cls: 'bg-sky-500/15 text-sky-300 border-sky-500/30' },
  PENDING:   { ar: 'مفتوحة', en: 'Open', icon: '🟢', cls: 'bg-sky-500/15 text-sky-300 border-sky-500/30' },
}
const FILTERS = [['all', 'الكل', 'All'], ['win', 'رابحة', 'Wins'], ['loss', 'خاسرة', 'Losses'],
  ['breakeven', 'تأمين', 'Breakeven'], ['open', 'مفتوحة', 'Open'], ['expired', 'منتهية', 'Expired']]
const CLOSED = ['TP1_HIT', 'TP2_HIT', 'SL_HIT', 'BREAKEVEN', 'EXPIRED']

const fmtP = (v) => v == null ? '—' : (Math.abs(v) >= 100 ? v.toFixed(2) : Math.abs(v) >= 1 ? v.toFixed(4) : v.toFixed(5))
const fmtR = (r) => r == null ? '—' : `${r > 0 ? '+' : ''}${r.toFixed(2)}R`.replace('-', '−')
const fmtD = (iso, isAr) => iso ? new Date(iso).toLocaleString(isAr ? 'ar' : 'en', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'

// ─── الشارت: شموع SVG + خطوط المستويات + لحظتا الفتح والإغلاق ────────────────
function TradeChart({ d, isAr }) {
  const W = 760, H = 340, PAD_L = 8, PAD_R = 64, PAD_T = 12, PAD_B = 24
  const c = d.candles
  const levels = [
    { v: d.tp2, label: isAr ? 'الهدف 2' : 'TP2', color: '#34d399', dash: '6 4' },
    { v: d.tp1, label: isAr ? 'الهدف 1' : 'TP1', color: '#34d399' },
    { v: d.entry, label: isAr ? 'الدخول' : 'Entry', color: '#cbd5e1' },
    { v: d.sl, label: isAr ? 'الوقف' : 'Stop', color: '#fb7185' },
  ].filter((l) => l.v != null)
  const lo = Math.min(...c.map((x) => x.l), ...levels.map((l) => l.v))
  const hi = Math.max(...c.map((x) => x.h), ...levels.map((l) => l.v))
  const span = (hi - lo) || 1
  const y = (v) => PAD_T + (hi + span * 0.04 - v) / (span * 1.08) * (H - PAD_T - PAD_B)
  const cw = (W - PAD_L - PAD_R) / c.length
  const x = (i) => PAD_L + i * cw + cw / 2
  const t0 = new Date(d.opened_at).getTime(), t1 = new Date(d.closed_at).getTime()
  const idx = (t) => { let k = c.findIndex((x) => new Date(x.t).getTime() >= t); return k < 0 ? c.length - 1 : k }
  const iOpen = idx(t0), iClose = idx(t1)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={isAr ? 'شارت الصفقة' : 'Trade chart'}>
      <rect x={x(iOpen) - cw / 2} y={PAD_T} width={Math.max(cw, x(iClose) - x(iOpen) + cw)} height={H - PAD_T - PAD_B} fill="#38bdf8" opacity="0.06" />
      {levels.map((l) => (
        <g key={l.label}>
          <line x1={PAD_L} x2={W - PAD_R} y1={y(l.v)} y2={y(l.v)} stroke={l.color} strokeWidth="1.2" strokeDasharray={l.dash || ''} opacity="0.9" />
          <text x={W - PAD_R + 4} y={y(l.v) + 4} fontSize="11" fill={l.color}>{l.label}</text>
        </g>
      ))}
      {c.map((k, i) => {
        const up = k.c >= k.o
        const col = up ? '#34d399' : '#fb7185'
        return (
          <g key={k.t}>
            <line x1={x(i)} x2={x(i)} y1={y(k.h)} y2={y(k.l)} stroke={col} strokeWidth="1" />
            <rect x={x(i) - Math.max(1, cw * 0.32)} width={Math.max(2, cw * 0.64)} y={y(Math.max(k.o, k.c))}
              height={Math.max(1, Math.abs(y(k.o) - y(k.c)))} fill={col} />
          </g>
        )
      })}
      {[[iOpen, isAr ? 'الفتح' : 'Open'], [iClose, isAr ? 'الإغلاق' : 'Close']].map(([i, lbl]) => (
        <g key={lbl}>
          <line x1={x(i)} x2={x(i)} y1={PAD_T} y2={H - PAD_B} stroke="#94a3b8" strokeDasharray="3 3" />
          <text x={x(i)} y={H - 8} fontSize="11" fill="#94a3b8" textAnchor="middle">{lbl}</text>
        </g>
      ))}
    </svg>
  )
}

// url اختياري: سجل الأداء العام يمرّر مساره (/public/track-record/{id}/chart) — نفس الشارت والمرجع
export function ChartModal({ trade, onClose, isAr, url }) {
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    axios.get(url || `${API}/api/v1/signals/${trade.id}/chart`).then((r) => setD(r.data))
      .catch((e) => setErr(e.response?.data?.detail || (isAr ? 'تعذّر تحميل الشارت' : 'Could not load chart')))
  }, [trade.id])
  const st = ST[trade.status] || {}
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="w-full max-w-3xl rounded-2xl bg-gray-900 border border-gray-700 p-4 sm:p-5" onClick={(e) => e.stopPropagation()} dir={isAr ? 'rtl' : 'ltr'}>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h3 className="text-white font-bold">{trade.market} · {trade.timeframe} · {trade.type === 'BUY' ? (isAr ? 'شراء' : 'Buy') : (isAr ? 'بيع' : 'Sell')}</h3>
            <p className="text-xs text-gray-400 mt-0.5">{st.icon} {isAr ? st.ar : st.en} · <b className="text-white">{fmtR(trade.r)}</b> · {fmtD(trade.created_at, isAr)}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400"><X size={16} /></button>
        </div>
        {!d && !err && <div className="py-16 text-center text-gray-500 text-sm flex items-center justify-center gap-2"><RefreshCw size={14} className="animate-spin" />{isAr ? 'جاري جلب الشموع…' : 'Loading candles…'}</div>}
        {err && <div className="py-12 text-center text-amber-300 text-sm">{err}</div>}
        {d && (
          <>
            <div className="rounded-xl bg-gray-950 border border-gray-800 p-2"><TradeChart d={d} isAr={isAr} /></div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 text-xs tabular-nums">
              {[[isAr ? 'الدخول' : 'Entry', d.entry, 'text-white'], [isAr ? 'الوقف' : 'Stop', d.sl, 'text-rose-300'],
                [isAr ? 'الهدف 1' : 'TP1', d.tp1, 'text-emerald-300'], [isAr ? 'الهدف 2' : 'TP2', d.tp2, 'text-emerald-300']].map(([l, v, cls]) => (
                <div key={l} className="rounded-lg bg-gray-800/60 px-3 py-2"><div className="text-gray-500">{l}</div><div className={`font-semibold ${cls}`}>{fmtP(v)}</div></div>
              ))}
            </div>
            <p className="text-[11px] text-gray-500 mt-3 leading-relaxed">
              {isAr
                ? `الشموع من ${d.source} (فاصل ${d.interval}) — نفس المصدر الذي حُسبت منه نتيجة الصفقة. المنطقة المظللة = مدة الصفقة.`
                : `Candles from ${d.source} (${d.interval}) — the same source the result was computed from. Shaded area = trade duration.`}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

export default function MyTradesPanel({ isAr = true }) {
  const [filter, setFilter] = useState('all')
  const [range, setRange] = useState({ from: '', to: '' })
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [chart, setChart] = useState(null)

  const load = (p = page, f = filter, r = range) => {
    setLoading(true)
    axios.get(`${API}/api/v1/signals/my-trades`, {
      params: { status: f, page: p, page_size: 15, date_from: r.from || undefined, date_to: r.to || undefined },
    }).then((res) => setData(res.data)).catch(() => setData({ items: [], summary: null, pages: 1 })).finally(() => setLoading(false))
  }
  useEffect(() => { load(1) }, [])
  const s = data?.summary
  const chips = useMemo(() => s ? [
    [isAr ? 'صفقة' : 'trades', s.total, 'text-white'],
    [isAr ? 'رابحة' : 'wins', s.wins, 'text-emerald-300'],
    [isAr ? 'خاسرة' : 'losses', s.losses, 'text-rose-300'],
    [isAr ? 'نسبة الربح' : 'win rate', s.win_rate != null ? `${s.win_rate}%` : '—', 'text-white'],
    [isAr ? 'صافي النتيجة' : 'net', fmtR(s.total_r), s.total_r >= 0 ? 'text-emerald-300' : 'text-rose-300'],
  ] : [], [s, isAr])

  return (
    <div className="bg-gray-800/60 border border-gray-700/80 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700/60">
        <h2 className="text-white font-semibold flex items-center gap-2">
          <Activity size={16} className="text-purple-400" />{isAr ? 'صفقاتي' : 'My trades'}
          <span className="text-xs text-gray-500 font-normal">{isAr ? '— كل ما وصلك من البوت والمنصة' : '— everything delivered to you'}</span>
        </h2>
        <button onClick={() => load(page)} className="text-gray-500 hover:text-gray-300 p-1 rounded-lg hover:bg-gray-700"><RefreshCw size={14} className={loading ? 'animate-spin' : ''} /></button>
      </div>

      {s && (
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 px-5 pt-4">
          {chips.map(([l, v, cls]) => (
            <div key={l} className="rounded-xl bg-gray-900/60 border border-gray-700/50 px-3 py-2 text-center">
              <div className={`text-base font-bold tabular-nums ${cls}`}>{v}</div><div className="text-[11px] text-gray-500">{l}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 px-5 py-3">
        {FILTERS.map(([k, ar, en]) => (
          <button key={k} onClick={() => { setFilter(k); setPage(1); load(1, k) }}
            className={`text-xs px-3 py-1.5 rounded-full border transition ${filter === k ? 'bg-purple-500/20 border-purple-400/50 text-purple-200' : 'border-gray-700 text-gray-400 hover:text-gray-200'}`}>
            {isAr ? ar : en}
          </button>
        ))}
        <div className="flex items-center gap-1.5 ms-auto text-xs text-gray-400">
          <input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1 text-gray-200" />
          <span>←</span>
          <input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1 text-gray-200" />
          <button onClick={() => { setPage(1); load(1) }} className="px-2.5 py-1 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-100">{isAr ? 'تطبيق' : 'Apply'}</button>
        </div>
      </div>

      <div className="divide-y divide-gray-700/40">
        {data?.items?.length === 0 && (
          <p className="px-5 py-10 text-center text-gray-500 text-sm">{isAr ? 'لا صفقات بهذا الفلتر بعد' : 'No trades for this filter yet'}</p>
        )}
        {data?.items?.map((t) => {
          const st = ST[t.status] || ST.EXPIRED
          const buy = t.type === 'BUY'
          return (
            <div key={t.id} className="px-5 py-3 flex flex-wrap items-center gap-x-4 gap-y-2">
              <div className="min-w-[8.5rem]">
                <div className="flex items-center gap-2">
                  <span className="text-white font-bold text-sm">{t.market}</span>
                  <span className="text-[11px] text-gray-500">{t.timeframe}</span>
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">{fmtD(t.created_at, isAr)} · {t.source === 'bot' ? (isAr ? 'من البوت' : 'via bot') : (isAr ? 'حسابك' : 'your account')}</div>
              </div>
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${buy ? 'text-emerald-300 border-emerald-500/30' : 'text-rose-300 border-rose-500/30'}`}>{buy ? '▲' : '▼'} {buy ? (isAr ? 'شراء' : 'Buy') : (isAr ? 'بيع' : 'Sell')}</span>
              <span className={`text-xs px-2.5 py-0.5 rounded-full border ${st.cls}`}>{st.icon} {isAr ? st.ar : st.en}</span>
              <div className="flex gap-3 text-[11px] text-gray-400 tabular-nums">
                <span>{isAr ? 'دخول' : 'Entry'} <b className="text-gray-200 font-mono">{fmtP(t.entry)}</b></span>
                <span>SL <b className="text-rose-300 font-mono">{fmtP(t.sl)}</b></span>
                <span>TP1 <b className="text-emerald-300 font-mono">{fmtP(t.tp1)}</b></span>
              </div>
              <b className={`ms-auto text-sm tabular-nums ${t.r > 0 ? 'text-emerald-300' : t.r < 0 ? 'text-rose-300' : 'text-gray-400'}`}>{fmtR(t.r)}</b>
              {CLOSED.includes(t.status) && (
                <button onClick={() => setChart(t)} className="text-xs flex items-center gap-1 px-2.5 py-1 rounded-lg bg-gray-700/70 hover:bg-gray-600 text-gray-100">
                  <Search size={12} />{isAr ? 'تحقق' : 'Verify'}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {data?.pages > 1 && (
        <div className="flex items-center justify-center gap-3 py-3 border-t border-gray-700/40 text-xs text-gray-400">
          <button disabled={page <= 1} onClick={() => { setPage(page - 1); load(page - 1) }} className="px-3 py-1 rounded-lg bg-gray-700 disabled:opacity-40">{isAr ? 'السابق' : 'Prev'}</button>
          <span>{page} / {data.pages}</span>
          <button disabled={page >= data.pages} onClick={() => { setPage(page + 1); load(page + 1) }} className="px-3 py-1 rounded-lg bg-gray-700 disabled:opacity-40">{isAr ? 'التالي' : 'Next'}</button>
        </div>
      )}
      {chart && <ChartModal trade={chart} onClose={() => setChart(null)} isAr={isAr} />}
    </div>
  )
}
