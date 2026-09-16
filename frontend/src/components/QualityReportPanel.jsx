/**
 * QualityReportPanel — تقرير جودة القرارات
 * ==========================================
 * رفيق لوحة التشخيص الحيّة لا بديل عنها:
 *   • تشخيص الـpipeline يجيب "لماذا لا تُولَّد إشارات الآن؟"
 *   • هذا يجيب "هل ما نقيسه صحيح، وأي شرط يستحق التشديد أو التخفيف؟"
 *
 * قرار تصميمي مقصود: الشريحة الموسومة confounded تُعرض بالجدول لكن
 * لا تتحول إلى اقتراح أبداً، ويُطبع سبب الاستبعاد صراحةً بدل إخفائها.
 * إخفاؤها يوحي بأن التحليل شامل، وعرضها بلا وسم يدعو لقرار خاطئ —
 * والثالث (عرضها موسومة) هو الوحيد الذي يعلّم القارئ متى لا يثق.
 */
import { useState } from 'react'
import axios from 'axios'
import {
  RefreshCw, Activity, XCircle, CheckCircle, AlertTriangle,
  TrendingUp, TrendingDown, ShieldAlert, Info,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const num = (v, d = 2) =>
  v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(d)
const signed = (v, d = 2) =>
  v === null || v === undefined || Number.isNaN(Number(v))
    ? '—'
    : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(d)}`
const ptsColor = (v) =>
  Number(v) > 0 ? 'text-green-400' : Number(v) < 0 ? 'text-red-400' : 'text-gray-400'

const STATUS_STYLE = {
  ok:   { cls: 'border-green-700/50 bg-green-900/15',   icon: CheckCircle,    ic: 'text-green-400' },
  warn: { cls: 'border-yellow-700/50 bg-yellow-900/15', icon: AlertTriangle,  ic: 'text-yellow-400' },
  bad:  { cls: 'border-red-700/50 bg-red-900/15',       icon: XCircle,        ic: 'text-red-400' },
}

export default function QualityReportPanel() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [days, setDays]       = useState(30)
  const [lever, setLever]     = useState('symbol')

  const run = async () => {
    setLoading(true); setError(null); setData(null)
    try {
      const r = await axios.get(`${API}/api/v1/admin/diagnostics/quality`, { params: { days } })
      setData(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const h  = data?.headline
  const gap = h?.measurement_gap

  return (
    <div className="space-y-6 max-w-6xl">
      {/* ── شريط التحكم ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <TrendingUp size={20} className="text-blue-400" /> تقرير جودة القرارات
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            تشريح النتائج المسجّلة — سلامة الأرقام أولاً، ثم أثر كل شرط
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-gray-800 border border-gray-700 rounded-xl p-1">
            {[7, 14, 30, 90].map((d) => (
              <button key={d} onClick={() => setDays(d)} disabled={loading}
                className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition ${
                  days === d ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
                }`}>
                {d} يوم
              </button>
            ))}
          </div>
          <button onClick={run} disabled={loading}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition">
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <Activity size={15} />}
            {loading ? 'جاري التحليل...' : 'تشغيل التقرير'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300 text-sm flex items-center gap-2">
          <XCircle size={16} /> {error}
        </div>
      )}

      {!data && !loading && !error && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-8 text-center">
          <Info size={26} className="text-gray-500 mx-auto mb-3" />
          <p className="text-gray-400 text-sm">
            اختر الفترة واضغط «تشغيل التقرير». كل الحسابات من قاعدة البيانات —
            لا طلبات شبكة ولا أي تأثير على المحرك.
          </p>
        </div>
      )}

      {data && (
        <div className="space-y-5">

          {/* ── التوقّع أولاً: الرقم الذي يحسم الربحية ─────────── */}
          <div className={`rounded-2xl p-5 border ${
            (h.expectancy ?? 0) >= 0.15 ? 'border-green-700/50 bg-green-900/10'
              : (h.expectancy ?? 0) > 0 ? 'border-yellow-700/50 bg-yellow-900/10'
              : 'border-red-700/50 bg-red-900/10'
          }`}>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-xs text-gray-400">توقّع النظام</span>
              <span className={`text-3xl font-bold ${
                (h.expectancy ?? 0) > 0 ? 'text-green-400' : 'text-red-400'
              }`} dir="ltr">
                {h.expectancy === null || h.expectancy === undefined
                  ? '—' : `${h.expectancy >= 0 ? '+' : ''}${num(h.expectancy, 3)}R`}
              </span>
              <span className="text-xs text-gray-400">
                لكل قرار · إجمالي {signed(h.r_total)}R · نسبة ربح {num(h.winrate, 1)}%
              </span>
            </div>
            <p className="text-[11px] text-gray-400 mt-2 leading-relaxed max-w-3xl">
              العائد مقسوماً على المخاطرة — الوقف <span className="font-mono">−1R</span> لأي رمز كان.
              هذا الرقم وحده يحسم ربحية النظام، لأن النقاط ليست عملة موحّدة:
              حركة 1% تساوي ~360 نقطة على الذهب و~0.3 على الغاز، ففارق المضاعف
              بين الرموز يبلغ 1200 ضعفاً وأي مجموع نقاط عابر للرموز متوسط
              مرجّح بأوزان اعتباطية.
            </p>
          </div>

          {/* ── المقاس مقابل القابل للتداول ────────────────────── */}
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
              <div className="text-xs text-gray-500 mb-1">الأداء المقاس (كل القرارات)</div>
              <div className={`text-2xl font-bold ${ptsColor(h.points)}`}>{signed(h.points)}</div>
              <div className="text-xs text-gray-400 mt-1">
                {h.decisions_closed} قراراً مغلقاً · نسبة ربح {num(h.winrate, 1)}%
              </div>
              <div className="text-[11px] text-gray-500 mt-2">نقاط — لا تُقارَن بين الرموز</div>
            </div>

            <div className="bg-gray-800 border border-blue-700/50 rounded-2xl p-5">
              <div className="text-xs text-blue-400 mb-1 font-semibold">
                الأداء القابل للتداول ★
              </div>
              <div className={`text-2xl font-bold ${ptsColor(h.tradable.points)}`}>
                {signed(h.tradable.points)}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {h.tradable.decisions} قراراً وصل المشتركين · توقّع{' '}
                <span dir="ltr">
                  {h.tradable.expectancy === null || h.tradable.expectancy === undefined
                    ? '—' : `${h.tradable.expectancy >= 0 ? '+' : ''}${num(h.tradable.expectancy, 3)}R`}
                </span>
              </div>
              <div className="text-[11px] text-blue-300/70 mt-2 leading-relaxed">
                هذا وحده ما يصحّ عرضه على المشتركين — الباقي أُغلق قبل أن يصل أحداً.
              </div>
            </div>

            <div className={`bg-gray-800 border rounded-2xl p-5 ${
              gap.decisions ? 'border-yellow-700/50' : 'border-gray-700'
            }`}>
              <div className="text-xs text-gray-500 mb-1">فجوة القياس</div>
              <div className={`text-2xl font-bold ${gap.decisions ? 'text-yellow-400' : 'text-gray-500'}`}>
                {signed(gap.points)}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {gap.decisions} قراراً ({num(gap.share_pct, 1)}%) لم يُبثّ قط
              </div>
            </div>
          </div>

          {/* ── سلامة الأرقام ──────────────────────────────────── */}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700">
              <h2 className="font-semibold text-sm">سلامة الأرقام — يُقرأ قبل أي استنتاج</h2>
            </div>
            <div className="p-4 space-y-2">
              {(data.integrity || []).map((it) => {
                const st = STATUS_STYLE[it.status] || STATUS_STYLE.warn
                const Icon = st.icon
                return (
                  <div key={it.key} className={`border rounded-xl p-3 ${st.cls}`}>
                    <div className="flex items-start gap-2.5">
                      <Icon size={15} className={`${st.ic} mt-0.5 shrink-0`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-baseline gap-x-2">
                          <span className="text-sm font-semibold text-gray-200">{it.label}</span>
                          <span className="text-sm font-mono text-white">{it.value}</span>
                        </div>
                        <div className="text-[11px] text-gray-400 mt-1 leading-relaxed">{it.why}</div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* ── الاقتراحات ─────────────────────────────────────── */}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700 flex items-center justify-between">
              <h2 className="font-semibold text-sm">فرضيات مرشّحة للاختبار</h2>
              <span className="text-[11px] text-gray-500">
                عينة ≥ {data.thresholds?.min_n_suggest} · وهيمنة رمز واحد ≤{' '}
                {Math.round((data.thresholds?.max_symbol_share || 0) * 100)}%
              </span>
            </div>
            <div className="p-4 space-y-2">
              {!(data.recommendations || []).length && (
                <div className="text-sm text-gray-400 flex items-start gap-2">
                  <ShieldAlert size={15} className="text-gray-500 mt-0.5 shrink-0" />
                  <span>
                    لا اقتراح نجا من الحارس بهذه الفترة. هذه نتيجة صحيحة لا عطل —
                    تعني أن العينة لا تحتمل استنتاجاً بعد. جرّب فترة أطول، أو انتظر
                    تراكم قرارات أكثر. اقتراح مبني على عينة صغيرة أسوأ من لا اقتراح.
                  </span>
                </div>
              )}
              {(data.recommendations || []).map((r, i) => (
                <div key={i} className={`border rounded-xl p-3.5 ${
                  r.action === 'تشديد'
                    ? 'border-red-700/40 bg-red-900/10'
                    : 'border-green-700/40 bg-green-900/10'
                }`}>
                  <div className="flex items-start gap-2.5">
                    {r.action === 'تشديد'
                      ? <TrendingDown size={15} className="text-red-400 mt-0.5 shrink-0" />
                      : <TrendingUp size={15} className="text-green-400 mt-0.5 shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          r.action === 'تشديد'
                            ? 'bg-red-900/40 text-red-300'
                            : 'bg-green-900/40 text-green-300'
                        }`}>{r.action}</span>
                        <span className="text-sm font-semibold text-gray-200">
                          {r.lever}: {r.value}
                        </span>
                        <span className="text-[11px] text-gray-500">
                          ن={r.n} · ربح {num(r.winrate, 1)}% · توقّع{' '}
                          <span dir="ltr">{r.expectancy >= 0 ? '+' : ''}{num(r.expectancy, 2)}R</span>
                        </span>
                        <span className={`text-[11px] px-1.5 py-0.5 rounded ${
                          r.strength === 'قوية'
                            ? 'bg-gray-700 text-gray-200'
                            : 'bg-gray-700/50 text-gray-400'
                        }`}>دلالة {r.strength}</span>
                      </div>
                      <div className="text-xs text-gray-300">{r.effect}</div>
                      {r.stability && (
                        <div className={`text-[11px] mt-1.5 rounded-lg px-2 py-1.5 leading-relaxed border ${
                          r.stability === 'مستقرة'
                            ? 'text-green-300/90 bg-green-900/15 border-green-700/40'
                            : r.stability === 'متفاوتة الشدة'
                            ? 'text-yellow-300/90 bg-yellow-900/15 border-yellow-700/40'
                            : r.stability === 'غير مستقرة'
                            ? 'text-red-300/90 bg-red-900/15 border-red-700/40'
                            : 'text-gray-400 bg-gray-900/40 border-gray-700'
                        }`}>
                          {r.stability === 'مستقرة' ? '✓'
                            : r.stability === 'متفاوتة الشدة' ? '≈'
                            : r.stability === 'غير مستقرة' ? '⛔' : '○'}{' '}
                          <span className="font-semibold">{r.stability}</span> — {r.stability_note}
                          {r.stability === 'غير مستقرة' && (
                            <> · <span className="font-semibold">لا تنفّذها</span>؛ الأرجح أنها حالة
                            سوق مؤقتة، وتفصيل النظام عليها ينقلب ضدك بأول انعكاس.</>
                          )}
                        </div>
                      )}
                      {(r.overlaps || []).length > 0 && (
                        <div className="text-[11px] text-yellow-300/90 mt-1.5 bg-yellow-900/15 border border-yellow-700/40 rounded-lg px-2 py-1.5 leading-relaxed">
                          ⚠ تصف نفس الصفقات تقريباً: {r.overlaps.join(' · ')} —
                          آثارها <span className="font-semibold">لا تُجمع</span>،
                          ونفّذ واحدة ثم أعد القياس.
                        </div>
                      )}
                      <div className="text-[11px] text-gray-500 mt-1 italic">{r.caveat}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── تشريح الروافع ──────────────────────────────────── */}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700">
              <h2 className="font-semibold text-sm mb-3">تشريح الروافع</h2>
              <div className="flex flex-wrap gap-1.5">
                {Object.keys(data.levers || {}).map((k) => (
                  <button key={k} onClick={() => setLever(k)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                      lever === k
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-900 text-gray-400 hover:text-gray-200 border border-gray-700'
                    }`}>
                    {data.lever_labels?.[k] || k}
                  </button>
                ))}
              </div>
            </div>

            {lever === 'duration' && (
              <div className="mx-4 mt-4 text-[11px] text-yellow-300/80 bg-yellow-900/15 border border-yellow-700/40 rounded-lg p-2.5 leading-relaxed">
                مدة الصفقة لا تُعرف وقت الإصدار فلا تصلح شرطاً، وارتباطها بالربح فيه
                شقّ حسابي لا استراتيجي: الهدف الأبعد يستغرق وقتاً أطول بالضرورة.
                تُعرض للتشخيص ولا تدخل الاقتراحات.
              </div>
            )}

            <div className="p-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700">
                    {['القيمة', 'عدد', 'ربح', 'خسارة', 'نسبة الربح', 'التوقّع (R)',
                      'الثبات بين النصفين', 'إجمالي R', 'R لو حُذفت', 'النقاط', 'رموز', 'الحكم'].map((x) => (
                      <th key={x} className="text-right pb-2 pr-3 font-medium whitespace-nowrap">{x}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data.levers?.[lever] || []).map((b, i) => (
                    <tr key={i} className="border-b border-gray-700/40 align-top">
                      <td className="py-2 pr-3 font-bold text-white whitespace-nowrap">{b.value}</td>
                      <td className="py-2 pr-3 text-gray-300">{b.n}</td>
                      <td className="py-2 pr-3 text-green-400">{b.wins}</td>
                      <td className="py-2 pr-3 text-red-400">{b.losses}</td>
                      <td className="py-2 pr-3 text-gray-300">{num(b.winrate, 1)}%</td>
                      <td className={`py-2 pr-3 font-mono font-bold ${ptsColor(b.expectancy)}`} dir="ltr">
                        {b.expectancy === null || b.expectancy === undefined
                          ? '—' : `${b.expectancy >= 0 ? '+' : ''}${num(b.expectancy, 2)}R`}
                      </td>
                      <td className="py-2 pr-3 whitespace-nowrap">
                        <span className={
                          b.stability === 'مستقرة' ? 'text-green-400'
                            : b.stability === 'متفاوتة الشدة' ? 'text-yellow-400'
                            : b.stability === 'غير مستقرة' ? 'text-red-400' : 'text-gray-500'
                        } title={b.stability_note}>
                          {b.stability === 'مستقرة' ? '✓'
                            : b.stability === 'متفاوتة الشدة' ? '≈'
                            : b.stability === 'غير مستقرة' ? '⛔' : '○'}{' '}
                          {b.stability_note || b.stability}
                        </span>
                      </td>
                      <td className={`py-2 pr-3 font-mono ${ptsColor(b.r_total)}`} dir="ltr">
                        {signed(b.r_total, 1)}
                      </td>
                      <td className="py-2 pr-3 font-mono text-gray-400" dir="ltr">
                        {signed(b.r_without, 1)}
                      </td>
                      <td className={`py-2 pr-3 font-mono text-[11px] ${ptsColor(b.points)}`}>
                        {signed(b.points)}
                      </td>
                      <td className="py-2 pr-3 text-gray-500">{b.symbols}</td>
                      <td className="py-2 pr-3 max-w-[260px]">
                        {b.confounded ? (
                          <span className="text-yellow-400/90 text-[11px] leading-snug block">
                            ⚠ لا يُبنى عليه — {b.confound_reasons.join(' · ')}
                          </span>
                        ) : (
                          <span className="text-gray-500 text-[11px]">صالح للقراءة</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── القرارات التي لم تُبثّ ─────────────────────────── */}
          {(data.unbroadcast_list || []).length > 0 && (
            <div className="bg-gray-800 border border-yellow-700/40 rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-700">
                <h2 className="font-semibold text-sm">قرارات مُغلقة لم تصل أحداً</h2>
                <p className="text-[11px] text-gray-500 mt-1">
                  أُغلقت قبل دورة البث، فنقاطها بالتقارير ولم يتمكن أي مشترك من تداولها.
                </p>
              </div>
              <div className="p-4 overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700">
                      {['#', 'الرمز', 'الفريم', 'النتيجة', 'عمرها', 'النقاط', 'التاريخ'].map((x) => (
                        <th key={x} className="text-right pb-2 pr-3 font-medium">{x}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.unbroadcast_list.map((u) => (
                      <tr key={u.id} className="border-b border-gray-700/40">
                        <td className="py-2 pr-3 font-mono text-gray-400">{u.id}</td>
                        <td className="py-2 pr-3 font-bold text-white">{u.market}</td>
                        <td className="py-2 pr-3 text-gray-400">{u.timeframe}</td>
                        <td className="py-2 pr-3 text-gray-300">{u.status}</td>
                        <td className="py-2 pr-3 text-gray-400">
                          {u.age_min === null ? '—' : `${num(u.age_min, 1)} د`}
                        </td>
                        <td className={`py-2 pr-3 font-mono ${ptsColor(u.points)}`}>{signed(u.points)}</td>
                        <td className="py-2 pr-3 text-gray-500 font-mono" dir="ltr">
                          {u.created_at ? u.created_at.slice(0, 16).replace('T', ' ') : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="text-xs text-gray-500 text-left" dir="ltr">
            {data.window_days}d · generated {String(data.generated_at).slice(0, 19).replace('T', ' ')} UTC
          </div>
        </div>
      )}
    </div>
  )
}
