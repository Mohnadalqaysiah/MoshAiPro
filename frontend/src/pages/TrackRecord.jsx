/**
 * TrackRecord (2026-10-24) — سجل الأداء العام /results. مغلق حتى يُفعَّل `public_track_record_enabled` من اللوحة
 * (بعد "أسبوعين ممتازين متتاليين" — DECISIONS 24/10). الأدمن يعاينه: /results?preview=1
 * كل الصفقات المغلقة منذ بداية حلقة الرصد الموثوقة، الرابحة والخاسرة، وكل صفقة قابلة للتحقق بشموع حقيقية.
 */
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { Search } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import { ChartModal } from '../components/MyTradesPanel'
import useSEO from '../hooks/useSEO'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WEEKS = 26   // أقصى ما يقبله الخادم — بنافذة 8 أسابيع كانت "كل صفقة منذ البداية" ستصير غير صحيحة بعد منتصف نوفمبر
const GROUPS = { gold: 'الذهب', metals: 'الفضة والمعادن', energy: 'الطاقة', index: 'المؤشرات', forex: 'فوركس',
  crypto: 'كريبتو', gulf: 'خليجي', stock: 'أسهم أمريكية' }
const ST = { TP3_HIT: ['🏆', 'الهدف 3', '#34d399'], TP2_HIT: ['🏆', 'الهدف 2', '#34d399'], TP1_HIT: ['✅', 'الهدف 1', '#34d399'], SL_HIT: ['❌', 'وقف الخسارة', '#fb7185'],
  BREAKEVEN: ['⚖️', 'تأمين', '#94a3b8'] }
const fmtR = (r) => r == null ? '—' : `${r > 0 ? '+' : ''}${Number(r).toFixed(2)}R`.replace('-', '−')
const rColor = (r) => r > 0 ? '#34d399' : r < 0 ? '#fb7185' : '#94a3b8'

export default function TrackRecord() {
  const [params] = useSearchParams()
  const preview = params.get('preview') === '1'
  const base = preview ? `${API}/api/v1/admin/track-record` : `${API}/api/v1/public/track-record`
  const [sum, setSum] = useState(null)
  const [closed, setClosed] = useState(false)
  const [trades, setTrades] = useState(null)
  const [filt, setFilt] = useState({ group: '', result: '', page: 1 })
  const [chart, setChart] = useState(null)

  useSEO({
    title: 'سجل الأداء | Qaffel AI — كل الصفقات الرابحة والخاسرة',
    description: 'سجل أداء إشارات Qaffel AI: كل الصفقات المغلقة، الرابحة والخاسرة، أسبوعياً ولكل سوق، وكل صفقة قابلة للتحقق بالشارت الحقيقي.',
  })
  // مغلق ← noindex حتى لا تُفهرس صفحة "قريباً"
  useEffect(() => {
    let m = document.querySelector('meta[name="robots"]')
    if (closed) {
      if (!m) { m = document.createElement('meta'); m.setAttribute('name', 'robots'); document.head.appendChild(m) }
      m.setAttribute('content', 'noindex')
    }
    return () => { const x = document.querySelector('meta[name="robots"][content="noindex"]'); if (x) x.remove() }
  }, [closed])

  useEffect(() => {
    axios.get(base, { params: { weeks: WEEKS } }).then((r) => setSum(r.data))
      .catch((e) => { if (e.response?.status === 404 || e.response?.status === 401 || e.response?.status === 403) setClosed(true) })
  }, [base])
  useEffect(() => {
    if (closed) return
    axios.get(`${base}/trades`, { params: { weeks: WEEKS, group: filt.group || undefined, result: filt.result || undefined, page: filt.page, page_size: 20 } })
      .then((r) => setTrades(r.data)).catch(() => setTrades({ items: [], pages: 1 }))
  }, [base, filt, closed])

  if (closed) {
    return (
      <PublicLayout>
        <section className="qp-hero"><div className="qp-wrap qp-narrow">
          <span className="qp-eyebrow">سجل الأداء</span>
          <h1 className="qp-h1">قريباً</h1>
          <p className="qp-lead">نجهّز سجلاً كاملاً لكل صفقاتنا — الرابحة والخاسرة — قابلاً للتحقق صفقة بصفقة.</p>
          <Link to="/" className="qp-btn" style={{ marginTop: 16, display: 'inline-block' }}>الرئيسية</Link>
        </div></section>
      </PublicLayout>
    )
  }

  const w = sum?.weekly
  const cards = sum ? [
    ['صفقة مغلقة', sum.decisions], ['نسبة الربح', sum.win_rate != null ? `${sum.win_rate}%` : '—'],
    ['مجموع النتيجة', fmtR(sum.total_r)], ['متوسط الصفقة', fmtR(sum.avg_r)],
  ] : []

  return (
    <PublicLayout>
      {preview && (
        <div style={{ background: '#78350f', color: '#fde68a', textAlign: 'center', padding: '8px 12px', fontSize: 13 }}>
          معاينة الأدمن — السجل {sum?.enabled ? 'مفتوح للعامة' : 'مغلق للعامة'} (يُفتح من الإعدادات ← الحدود)
        </div>
      )}
      <section className="qp-hero">
        <div className="qp-wrap qp-narrow">
          <span className="qp-eyebrow">سجل الأداء</span>
          <h1 className="qp-h1">كل صفقاتنا<br /><span className="qp-grad">الرابحة والخاسرة</span></h1>
          <p className="qp-lead">لا نختار ما نعرضه: كل صفقة أُغلقت منذ {sum?.since || '…'} موجودة هنا، وكل واحدة يمكنك التحقق منها بالشارت الحقيقي.</p>
        </div>
      </section>

      <section className="qp-sec" style={{ paddingTop: 0 }}>
        <div className="qp-wrap">
          <div className="qp-grid qp-g4" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))' }}>
            {cards.map(([l, v]) => (
              <div key={l} className="qp-card" style={{ textAlign: 'center' }}>
                <div style={{ color: '#fff', fontWeight: 800, fontSize: 26 }}>{v}</div>
                <div className="qp-faint" style={{ fontSize: 13, marginTop: 4 }}>{l}</div>
              </div>
            ))}
          </div>

          <div className="qp-card" style={{ marginTop: 16 }}>
            <h2 className="qp-h3" style={{ marginBottom: 8 }}>كيف نحسب</h2>
            <ul className="qp-sub" style={{ lineHeight: 1.9, paddingInlineStart: 18, listStyle: 'disc' }}>
              <li>كل صفقة تُحسب <b>مرة واحدة</b> حتى لو وصلت لمئات المشتركين.</li>
              <li>الصفقة <b>رابحة</b> عند وصول الهدف الأول، و<b>خاسرة</b> عند ضرب وقف الخسارة، و"تأمين" إذا عادت للدخول بعد نقل الوقف (0R).</li>
              <li>النتيجة بمضاعف المخاطرة <b>R</b>: ‎+1R ربح بقدر ما خاطرت، ‎−1R خسارة الوقف. النقاط لا تُجمع بين الأسواق فلا نستخدمها.</li>
              <li>النتائج تقيس وصول كل صفقة إلى أهدافها أو وقفها، قبل السبريد، ولا تمثل نتيجة عميل بعينه. الصفقة التي تنتهي مدتها دون هدف أو وقف لا تُحسب ربحاً ولا خسارة.</li>
              {sum?.ladder_since && <li>منذ {sum.ladder_since} قد يكون للصفقة ثلاثة أهداف (1R ثم 2.5R ثم الهدف البعيد)، وتُحسب بأعلى هدف بلغته؛ فلا تُقارن الأسابيع قبل هذا التاريخ بما بعده مباشرة.</li>}
              <li>البيانات تبدأ من {sum?.baseline || '…'} — تاريخ بدء نظام الرصد الحالي. لا نعرض ما قبله لأننا لا نستطيع ضمان دقته.</li>
            </ul>
          </div>
        </div>
      </section>

      {w?.weeks?.length > 0 && (
        <section className="qp-sec qp-band">
          <div className="qp-wrap">
            <div className="qp-head"><h2 className="qp-h2">أسبوعاً بأسبوع، لكل سوق</h2></div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 560 }}>
                <thead>
                  <tr style={{ color: '#94a3b8' }}>
                    <th style={{ textAlign: 'start', padding: 8 }}>الأسبوع</th>
                    {w.groups.map((g) => <th key={g.key} style={{ padding: 8 }}>{g.name}</th>)}
                    <th style={{ padding: 8 }}>المجموع</th>
                  </tr>
                </thead>
                <tbody>
                  {[...w.weeks].reverse().map((row) => (
                    <tr key={row.week} style={{ borderTop: '1px solid rgba(148,163,184,.15)' }}>
                      <td style={{ padding: 8, color: '#cbd5e1', whiteSpace: 'nowrap' }}>{row.from}{row.current ? ' (جارٍ)' : ''}</td>
                      {[...w.groups.map((g) => g.key), '_total'].map((k) => {
                        const c = row.cells[k]
                        return (
                          <td key={k} style={{ padding: 8, textAlign: 'center' }}>
                            {c && c.n ? (<><b style={{ color: rColor(c.r) }}>{fmtR(c.r)}</b>
                              <div style={{ color: '#64748b', fontSize: 11 }}>✅{c.wins} ❌{c.losses}</div></>) : <span style={{ color: '#475569' }}>—</span>}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      <section className="qp-sec">
        <div className="qp-wrap">
          <div className="qp-head"><h2 className="qp-h2">الصفقات</h2></div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            <select value={filt.group} onChange={(e) => setFilt({ ...filt, group: e.target.value, page: 1 })} className="qp-input" style={{ maxWidth: 200 }}>
              <option value="">كل الأسواق</option>
              {Object.entries(GROUPS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            {[['', 'الكل'], ['win', 'رابحة'], ['loss', 'خاسرة'], ['breakeven', 'تأمين']].map(([k, l]) => (
              <button key={k} onClick={() => setFilt({ ...filt, result: k, page: 1 })} className={filt.result === k ? 'qp-btn' : 'qp-btn-ghost'}
                style={{ padding: '6px 14px', fontSize: 13, minHeight: 36 }}>{l}</button>
            ))}
          </div>
          <div className="qp-card" style={{ padding: 0 }}>
            {trades?.items?.length === 0 && <p className="qp-faint" style={{ padding: 24, textAlign: 'center' }}>لا صفقات بهذا الفلتر</p>}
            {trades?.items?.map((t) => {
              const [ic, lbl, col] = ST[t.tp3_hit ? 'TP3_HIT' : t.status] || ['', t.status, '#94a3b8']
              return (
                <div key={t.id} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px 16px', padding: '12px 16px', borderTop: '1px solid rgba(148,163,184,.12)' }}>
                  <div style={{ minWidth: 140 }}>
                    <b style={{ color: '#fff' }}>{t.market}</b> <span className="qp-faint" style={{ fontSize: 12 }}>{t.timeframe}</span>
                    <div className="qp-faint" style={{ fontSize: 12 }}>{new Date(t.created_at).toLocaleDateString('ar', { day: 'numeric', month: 'short' })} · {GROUPS[t.group] || ''}</div>
                  </div>
                  <span style={{ color: t.type === 'BUY' ? '#34d399' : '#fb7185', fontSize: 13 }}>{t.type === 'BUY' ? '▲ شراء' : '▼ بيع'}</span>
                  <span style={{ color: col, fontSize: 13 }}>{ic} {lbl}</span>
                  <b style={{ marginInlineStart: 'auto', color: rColor(t.r) }}>{fmtR(t.r)}</b>
                  <button onClick={() => setChart(t)} className="qp-btn-ghost" style={{ padding: '4px 10px', fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <Search size={12} />تحقق
                  </button>
                </div>
              )
            })}
          </div>
          {trades?.pages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 12 }} className="qp-faint">
              <button disabled={filt.page <= 1} onClick={() => setFilt({ ...filt, page: filt.page - 1 })} className="qp-btn-ghost" style={{ padding: '4px 12px' }}>السابق</button>
              <span>{filt.page} / {trades.pages}</span>
              <button disabled={filt.page >= trades.pages} onClick={() => setFilt({ ...filt, page: filt.page + 1 })} className="qp-btn-ghost" style={{ padding: '4px 12px' }}>التالي</button>
            </div>
          )}
          <p className="qp-faint" style={{ fontSize: 12, marginTop: 20, lineHeight: 1.8 }}>
            الأداء السابق لا يضمن النتائج المستقبلية. التحليلات لأغراض تعليمية وليست نصيحة استثمارية، والتداول ينطوي على مخاطر قد تفقدك جزءاً من رأس مالك أو كله.
          </p>
        </div>
      </section>
      {chart && <ChartModal trade={chart} onClose={() => setChart(null)} isAr url={`${base}/${chart.id}/chart`} />}
    </PublicLayout>
  )
}
