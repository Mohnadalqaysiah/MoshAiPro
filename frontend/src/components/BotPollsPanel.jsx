import { useState, useEffect } from 'react'
import axios from 'axios'
import { RefreshCw, Send, FlaskConical, Plus, X } from 'lucide-react'

// (2026-11-14) تصويت تيليجرام جماعي من البوت — backend/app/services/bot_polls.py. المالك: "بدنا نرسل تصويت جماعي بالبوت".
// إنشاء ← "جرّبه عليّ" ← "أرسل" (مرة واحدة). النتائج مقسومة مدفوع/تجربة، وإجابة تجربة الأدمن لا تُحتسب.
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const AUD = { paid: 'المشتركون الدافعون', trial: 'مستخدمو التجربة', all: 'الكل' }
const DEFAULT_Q = 'ما أكثر شيء يزعجك في إشارات Qaffel؟'
const DEFAULT_OPTS = ['📶 كثرة الإشارات', '🎯 دقة الإشارات', '⏰ توقيتها لا يناسبني', '🤔 لا أعرف كيف أدير الصفقة', '✅ لا شيء، راضٍ']

function Bars({ options, part, color }) {
  if (!part || !part.voters) return <div className="text-xs text-gray-500">لا إجابات بعد</div>
  return (
    <div className="space-y-1.5">
      {options.map((o, i) => (
        <div key={i}>
          <div className="flex justify-between text-xs text-gray-300"><span>{o}</span><span>{part.counts[i]} · {part.pct[i]}%</span></div>
          <div className="h-1.5 bg-gray-800 rounded"><div className={`h-1.5 rounded ${color}`} style={{ width: `${part.pct[i]}%` }} /></div>
        </div>
      ))}
    </div>
  )
}

export default function BotPollsPanel() {
  const [list, setList] = useState(null)
  const [form, setForm] = useState({ question: DEFAULT_Q, options: DEFAULT_OPTS, allows_multiple: false, audience: 'paid' })
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState('')
  const [open, setOpen] = useState(null)       // نتائج تصويت مفتوح

  const load = () => axios.get(`${API}/api/v1/admin/bot-polls`).then(r => setList(r.data)).catch(() => {})
  useEffect(() => { load() }, [])
  const err = e => setMsg({ ok: false, text: e.response?.data?.detail || 'خطأ' })

  const create = async () => {
    setBusy('create'); setMsg(null)
    try {
      await axios.post(`${API}/api/v1/admin/bot-polls`, { ...form, options: form.options.filter(o => o.trim()) })
      setMsg({ ok: true, text: '✅ أُنشئ التصويت — جرّبه عليك أولاً ثم أرسله' })
      load()
    } catch (e) { err(e) } finally { setBusy('') }
  }
  const test = async id => {
    setBusy('test' + id); setMsg(null)
    try { const r = await axios.post(`${API}/api/v1/admin/bot-polls/${id}/test`); setMsg({ ok: r.data.ok, text: r.data.message }) }
    catch (e) { err(e) } finally { setBusy('') }
  }
  const send = async p => {
    const n = list?.audience_counts?.[p.audience] ?? '?'
    if (!window.confirm(`إرسال التصويت إلى ${AUD[p.audience]} (${n} مستلم)؟\nلا يمكن التراجع، ولا يُرسل نفس التصويت مرتين.`)) return
    setBusy('send' + p.id); setMsg(null)
    try { const r = await axios.post(`${API}/api/v1/admin/bot-polls/${p.id}/send`); setMsg({ ok: true, text: r.data.message }); load() }
    catch (e) { err(e) } finally { setBusy('') }
  }
  const results = async id => {
    try { const r = await axios.get(`${API}/api/v1/admin/bot-polls/${id}`); setOpen(r.data) } catch (e) { err(e) }
  }

  const setOpt = (i, v) => setForm(f => ({ ...f, options: f.options.map((o, j) => (j === i ? v : o)) }))

  return (
    <div className="space-y-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-base font-bold text-white mb-1">📊 تصويت جديد عبر البوت</h2>
        <p className="text-xs text-gray-400 mb-4">
          يصل كل مستلم تصويت تيليجرام في محادثة البوت. يُستبعد من حظر البوت ومن أطفأ الإشعارات. لا يُرسل شيء قبل زر "أرسل".
        </p>
        <label className="block text-xs text-gray-400 mb-1">السؤال ({form.question.length}/300)</label>
        <input value={form.question} maxLength={300} onChange={e => setForm(f => ({ ...f, question: e.target.value }))}
          className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white mb-3" />
        <label className="block text-xs text-gray-400 mb-1">الخيارات (2–10، كل خيار حتى 100 حرف)</label>
        <div className="space-y-2 mb-2">
          {form.options.map((o, i) => (
            <div key={i} className="flex gap-2">
              <input value={o} maxLength={100} onChange={e => setOpt(i, e.target.value)}
                className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white" />
              <button type="button" onClick={() => setForm(f => ({ ...f, options: f.options.filter((_, j) => j !== i) }))}
                className="text-gray-500 hover:text-red-400 px-2" disabled={form.options.length <= 2}><X size={14} /></button>
            </div>
          ))}
        </div>
        {form.options.length < 10 && (
          <button type="button" onClick={() => setForm(f => ({ ...f, options: [...f.options, ''] }))}
            className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 mb-3"><Plus size={12} /> خيار</button>
        )}
        <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
          <label className="flex items-center gap-2 text-gray-300">
            <input type="checkbox" checked={form.allows_multiple} onChange={e => setForm(f => ({ ...f, allows_multiple: e.target.checked }))} />
            يسمح باختيار أكثر من خيار
          </label>
          <label className="flex items-center gap-2 text-gray-300">
            الجمهور:
            <select value={form.audience} onChange={e => setForm(f => ({ ...f, audience: e.target.value }))}
              className="bg-gray-950 border border-gray-700 rounded-lg px-2 py-1 text-sm">
              {Object.entries(AUD).map(([k, v]) => (
                <option key={k} value={k}>{v}{list?.audience_counts ? ` (${list.audience_counts[k]})` : ''}</option>
              ))}
            </select>
          </label>
        </div>
        <button onClick={create} disabled={busy === 'create'}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium">
          {busy === 'create' ? 'جاري الإنشاء...' : 'إنشاء التصويت'}
        </button>
        {msg && <div className={`mt-3 text-sm ${msg.ok ? 'text-green-400' : 'text-red-400'}`}>{msg.text}</div>}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-200">التصويتات</h3>
          <button onClick={load} className="text-xs text-gray-400 hover:text-white flex items-center gap-1"><RefreshCw size={12} /> تحديث</button>
        </div>
        {!list ? <div className="text-xs text-gray-500">جاري التحميل...</div> : list.polls.length === 0 ? (
          <div className="text-xs text-gray-500">لا تصويتات بعد</div>
        ) : (
          <div className="space-y-2">
            {list.polls.map(p => (
              <div key={p.id} className="border border-gray-800 rounded-lg p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-sm text-white">#{p.id} · {p.question}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {AUD[p.audience]} · {p.sent_at
                        ? `أُرسل ${new Date(p.sent_at).toLocaleString('ar')} · وصل ${p.sent}/${p.total}${p.failed ? ` · فشل ${p.failed}` : ''}${p.done_at ? '' : ' · جاري الإرسال…'}`
                        : 'مسودة — لم يُرسل'}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => test(p.id)} disabled={busy === 'test' + p.id}
                      className="text-xs px-2.5 py-1 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 flex items-center gap-1">
                      <FlaskConical size={12} /> جرّبه عليّ
                    </button>
                    {!p.sent_at && (
                      <button onClick={() => send(p)} disabled={busy === 'send' + p.id}
                        className="text-xs px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1">
                        <Send size={12} /> أرسل
                      </button>
                    )}
                    <button onClick={() => results(p.id)}
                      className="text-xs px-2.5 py-1 rounded-lg border border-blue-700 text-blue-300 hover:bg-blue-900/30">النتائج</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {open && (
        <div className="bg-gray-900 border border-blue-800/50 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">نتائج #{open.id} · {open.question}</h3>
            <div className="flex gap-3">
              <button onClick={() => results(open.id)} className="text-xs text-gray-400 hover:text-white flex items-center gap-1"><RefreshCw size={12} /> تحديث</button>
              <button onClick={() => setOpen(null)} className="text-gray-400 hover:text-white"><X size={16} /></button>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {[['all', 'الكل', 'bg-blue-500'], ['paid', 'الدافعون', 'bg-emerald-500'], ['trial', 'التجربة', 'bg-amber-500']].map(([k, label, color]) => (
              <div key={k}>
                <div className="text-xs text-gray-400 mb-2">
                  {label}: صوّت {open.tally[k].voters}
                  {k !== 'all' && open.sent_by_tier?.[k] ? ` من ${open.sent_by_tier[k]}` : ''}
                </div>
                <Bars options={open.options} part={open.tally[k]} color={color} />
              </div>
            ))}
          </div>
          {open.voters?.length > 0 && (
            <div className="mt-4 max-h-72 overflow-auto">
              <table className="w-full text-xs">
                <thead className="text-gray-500"><tr><th className="text-right p-1">المستخدم</th><th className="text-right p-1">الفئة</th><th className="text-right p-1">اختياره</th></tr></thead>
                <tbody>
                  {open.voters.map((v, i) => (
                    <tr key={i} className="border-t border-gray-800 text-gray-300">
                      <td className="p-1">{v.name || v.email || (v.telegram_username ? '@' + v.telegram_username : `#${v.user_id ?? '—'}`)}</td>
                      <td className="p-1">{v.tier === 'paid' ? 'دافع' : 'تجربة'}</td>
                      <td className="p-1">{v.choices.join('، ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
