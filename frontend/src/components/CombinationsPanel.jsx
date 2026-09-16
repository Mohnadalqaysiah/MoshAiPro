/**
 * CombinationsPanel — تقاطع الروافع
 * ===================================
 * تقرير الجودة يقيس كل رافعة منفردة، فيقول "الشراء يخسر" ولا يقول أين.
 * هذا يقيس التقاطعات، ليتبيّن هل الخلل في شرط مركّب يُصلَح أم في الاتجاه
 * كله — والفرق بينهما قرار مختلف تماماً.
 *
 * تحذير المقارنات المتعددة معروض دائماً بأعلى الصفحة لا في هامش: فحص
 * مئات التوليفات على بضع مئات القرارات يُظهر توليفات ممتازة بالصدفة
 * وحدها، وإخفاء ذلك يجعل الأداة مولّدَ أوهام مقنعة.
 */
import { useState } from 'react'
import axios from 'axios'
import { RefreshCw, Activity, XCircle, Info, ShieldAlert } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const num = (v, d = 2) =>
  v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(d)
const R = (v, d = 2) =>
  v === null || v === undefined ? '—' : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(d)}R`
const rColor = (v) =>
  Number(v) > 0 ? 'text-green-400' : Number(v) < 0 ? 'text-red-400' : 'text-gray-400'

const stabStyle = (s) =>
  s === 'مستقرة' ? 'text-green-400'
    : s === 'متفاوتة الشدة' ? 'text-yellow-400'
    : s === 'غير مستقرة' ? 'text-red-400' : 'text-gray-500'
const stabIcon = (s) =>
  s === 'مستقرة' ? '✓' : s === 'متفاوتة الشدة' ? '≈' : s === 'غير مستقرة' ? '⛔' : '○'

function ComboTable({ rows, baseline, title, hint }) {
  if (!rows?.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
        <h2 className="font-semibold text-sm mb-2">{title}</h2>
        <p className="text-sm text-gray-400">
          لا توليفة اجتازت الحارس. نتيجة صحيحة لا عطل — العينة لا تحتمل
          التقسيم لهذا العمق بعد.
        </p>
      </div>
    )
  }
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-700">
        <h2 className="font-semibold text-sm">{title}</h2>
        {hint && <p className="text-[11px] text-gray-500 mt-1 leading-relaxed">{hint}</p>}
      </div>
      <div className="p-4 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b border-gray-700">
              {['التوليفة', 'عدد', 'نصيبها', 'نسبة الربح', 'التوقّع',
                'قبل الإصلاح', 'الثبات', 'لو أبقيتها وحدها', 'لو حذفتها', 'رموز'].map((x) => (
                <th key={x} className="text-right pb-2 pr-3 font-medium whitespace-nowrap">{x}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-gray-700/40 align-top">
                <td className="py-2 pr-3 text-white font-medium max-w-[280px]">{r.label}</td>
                <td className="py-2 pr-3 text-gray-300">{r.n}</td>
                <td className="py-2 pr-3 text-gray-400">{num(r.share_pct, 0)}%</td>
                <td className="py-2 pr-3 text-gray-300">{num(r.winrate, 1)}%</td>
                <td className={`py-2 pr-3 font-mono font-bold ${rColor(r.expectancy)}`} dir="ltr">
                  {R(r.expectancy)}
                </td>
                <td className={`py-2 pr-3 font-mono ${
                  r.pre_fix_pct >= 60 ? 'text-red-400'
                    : r.pre_fix_pct > 0 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {num(r.pre_fix_pct, 0)}%
                </td>
                <td className="py-2 pr-3 whitespace-nowrap">
                  <span className={stabStyle(r.stability)} title={r.stability_note}>
                    {stabIcon(r.stability)} {r.stability_note || r.stability}
                  </span>
                </td>
                <td className="py-2 pr-3 font-mono text-gray-300" dir="ltr">
                  {r.n} → {R(r.keep_only.expectancy)}
                </td>
                <td className="py-2 pr-3 font-mono text-gray-400" dir="ltr">
                  {r.if_removed.n} → {R(r.if_removed.expectancy)}
                </td>
                <td className="py-2 pr-3 text-gray-500">
                  {r.symbols}
                  {r.top_share > 0.4 && (
                    <span className="text-yellow-500/80"> · {r.top_symbol} {Math.round(r.top_share * 100)}%</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {baseline && (
          <div className="mt-3 text-[11px] text-gray-500 border-t border-gray-700/50 pt-2">
            خط الأساس للمقارنة: {baseline.n} قراراً · {R(baseline.expectancy, 3)} · نسبة ربح {num(baseline.winrate, 1)}%
          </div>
        )}
      </div>
    </div>
  )
}

export default function CombinationsPanel() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [days, setDays]       = useState(90)

  const run = async () => {
    setLoading(true); setError(null); setData(null)
    try {
      const r = await axios.get(`${API}/api/v1/admin/diagnostics/combinations`, {
        params: { days },
      })
      setData(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Activity size={20} className="text-purple-400" /> تقاطع الروافع
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            أين يقع الخلل بالضبط — في شرط مركّب يُصلَح، أم في الرافعة كلها؟
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-gray-800 border border-gray-700 rounded-xl p-1">
            {[30, 90, 180].map((d) => (
              <button key={d} onClick={() => setDays(d)} disabled={loading}
                className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition ${
                  days === d ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'
                }`}>
                {d} يوم
              </button>
            ))}
          </div>
          <button onClick={run} disabled={loading}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition">
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <Activity size={15} />}
            {loading ? 'جاري الفحص...' : 'فحص التوليفات'}
          </button>
        </div>
      </div>

      {/* التحذير المنهجي — بالمتن لا بالهامش */}
      <div className="bg-yellow-900/15 border border-yellow-700/40 rounded-xl p-4">
        <div className="flex items-start gap-2.5">
          <ShieldAlert size={16} className="text-yellow-400 mt-0.5 shrink-0" />
          <div className="text-[12px] text-yellow-100/80 leading-relaxed">
            <span className="font-semibold text-yellow-300">اقرأ هذا قبل النتائج:</span>{' '}
            فحص مئات التوليفات على بضع مئات القرارات <span className="font-semibold">يضمن رياضياً</span>{' '}
            ظهور توليفات تبدو ممتازة بمحض الصدفة. لذلك:
            <span className="block mt-1.5">
              • لا تُنفّذ توليفة إلا إن كانت <span className="text-green-300 font-semibold">✓ مستقرة</span> —
              التوقّع العالي وحده لا يكفي ولا يُعتدّ به هنا.
            </span>
            <span className="block">
              • ولا تُنفّذ إلا إن كان لها <span className="font-semibold">تفسير</span> تقبله؛
              فالتوليفة التي لا تفسير لها هي الأرجح ضجيج مُنتقى.
            </span>
          </div>
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
            اختر الفترة واضغط «فحص التوليفات». يُفضَّل 90 يوماً — العمق يحتاج عينة.
          </p>
        </div>
      )}

      {data && (
        <div className="space-y-5">
          {data.pre_fix?.pct > 0 && (
            <div className={`rounded-xl p-4 border ${
              data.pre_fix.pct > 60
                ? 'bg-red-900/20 border-red-700/50'
                : 'bg-yellow-900/15 border-yellow-700/40'
            }`}>
              <div className="flex items-start gap-2.5">
                <ShieldAlert size={16} className="text-red-400 mt-0.5 shrink-0" />
                <div className="text-[12px] text-red-100/85 leading-relaxed">
                  <span className="font-semibold text-red-300">
                    {data.pre_fix.pct}% من هذه القرارات ({data.pre_fix.n}) سُجّلت قبل
                    إصلاح حلقة الرصد في {data.pre_fix.date}.
                  </span>
                  <span className="block mt-1.5">
                    وقتها كان المشي الزمني معطّلاً، فيعود الحكم إلى «أين السعر الآن»
                    بلا تحديد زمني — ويكفي أن يهبط السعر تحت وقف صفقة شراء لحظةً واحدة
                    خلال أيام لتُسجَّل خسارة. <span className="font-semibold">وهذا الأثر
                    غير محايد للاتجاه:</span> في سوق هابط تُصفّى صفقات الشراء كلها تقريباً
                    بينما يبلغ البيع أهدافه.
                  </span>
                  <span className="block mt-1.5">
                    فتوليفة بنسبة ربح <span className="font-mono">0.0%</span> على عشرات
                    القرارات ليست اكتشافاً استراتيجياً — هي بصمة العطل.
                    <span className="font-semibold"> ولا يكشفه فحص الثبات</span>، لأن
                    نصفَي الفترة كليهما يقعان قبل التاريخ.
                  </span>
                </div>
              </div>
            </div>
          )}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl p-4 flex flex-wrap gap-x-6 gap-y-2 text-xs">
            <span className="text-gray-400">
              توليفات مفحوصة: <span className="text-white font-mono">{data.tested}</span>
            </span>
            <span className="text-gray-400">
              اجتازت الحارس: <span className="text-white font-mono">{data.passed}</span>
            </span>
            <span className="text-gray-400">
              الشروط: عينة ≥ <span className="font-mono">{data.min_n}</span> ·
              رموز ≥ <span className="font-mono">{data.min_symbols}</span>
            </span>
            <span className="text-gray-400">
              خط الأساس:{' '}
              <span className={`font-mono font-bold ${rColor(data.baseline.expectancy)}`} dir="ltr">
                {R(data.baseline.expectancy, 3)}
              </span>{' '}
              على {data.baseline.n} قرار
            </span>
          </div>

          <ComboTable
            title="الأفضل"
            rows={data.best}
            baseline={data.baseline}
            hint="«لو أبقيتها وحدها» = عدد الإشارات المتبقية وتوقّعها لو صفّيتَ عليها فقط."
          />
          <ComboTable
            title="الأسوأ"
            rows={data.worst}
            baseline={data.baseline}
            hint="«لو حذفتها» = ما يتبقى من إشارات وتوقّعه بعد استبعاد هذه التوليفة."
          />

          <div className="text-xs text-gray-500 text-left" dir="ltr">
            {data.window_days}d · generated {String(data.generated_at).slice(0, 19).replace('T', ' ')} UTC
          </div>
        </div>
      )}
    </div>
  )
}
