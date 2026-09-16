/**
 * CouponsPanel — إدارة كوبونات الخصم
 * ====================================
 * الخصم يُحسب على الخادم دائماً؛ هذه اللوحة تحرّر القواعد لا الأسعار.
 *
 * كوبون استُخدم مرة واحدة على الأقل لا يُحذف — يُوقَف. الحذف يُسقط سجلات
 * الاستخدام معه (CASCADE) فتضيع محاسبة خصومات مُنحت فعلاً، والإيقاف يحقق
 * الغرض نفسه ويُبقي الأثر. الخادم يرفض الحذف أيضاً، والواجهة تُخفي الزر
 * حتى لا يبدو الإجراء متاحاً ثم يفشل.
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  Ticket, Plus, Trash2, RefreshCw, CheckCircle, XCircle, X, Users, Copy,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const PLAN_OPTIONS = [
  { key: 'weekly',  label: 'الأسبوعية' },
  { key: 'monthly', label: 'الشهرية' },
  { key: 'yearly',  label: 'السنوية' },
]

const EMPTY = {
  code: '', discount_percent: 30, is_active: true,
  max_uses: '', per_user_limit: 1, expires_at: '', plans: [], note: '',
}

export default function CouponsPanel() {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [form, setForm]       = useState(null)      // null = مغلق
  const [saving, setSaving]   = useState(false)
  const [uses, setUses]       = useState(null)      // سجل استخدام كوبون
  const [copied, setCopied]   = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const r = await axios.get(`${API}/api/v1/admin/coupons`)
      setRows(r.data.coupons || [])
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  const openNew  = () => setForm({ ...EMPTY })
  const openEdit = (c) => setForm({
    id: c.id,
    code: c.code,
    discount_percent: c.discount_percent,
    is_active: c.is_active,
    max_uses: c.max_uses ?? '',
    per_user_limit: c.per_user_limit ?? 1,
    expires_at: c.expires_at ? c.expires_at.slice(0, 10) : '',
    plans: c.plans || [],
    note: c.note || '',
  })

  const save = async () => {
    setSaving(true); setError('')
    const body = {
      code: form.code.trim().toUpperCase(),
      discount_percent: Number(form.discount_percent),
      is_active: !!form.is_active,
      max_uses: form.max_uses === '' ? null : Number(form.max_uses),
      per_user_limit: Number(form.per_user_limit || 0),
      expires_at: form.expires_at ? `${form.expires_at}T23:59:59+00:00` : null,
      plans: form.plans?.length ? form.plans : null,
      note: form.note || null,
    }
    try {
      if (form.id) await axios.patch(`${API}/api/v1/admin/coupons/${form.id}`, body)
      else         await axios.post(`${API}/api/v1/admin/coupons`, body)
      setForm(null)
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setSaving(false)
    }
  }

  const remove = async (c) => {
    if (!window.confirm(`حذف الكوبون ${c.code}؟`)) return
    try {
      await axios.delete(`${API}/api/v1/admin/coupons/${c.id}`)
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
  }

  const showUses = async (c) => {
    try {
      const r = await axios.get(`${API}/api/v1/admin/coupons/${c.id}/redemptions`)
      setUses({ coupon: c, ...r.data })
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
  }

  const copy = (code) => {
    navigator.clipboard.writeText(code)
    setCopied(code); setTimeout(() => setCopied(''), 1500)
  }

  const togglePlan = (k) => setForm(f => ({
    ...f,
    plans: f.plans.includes(k) ? f.plans.filter(x => x !== k) : [...f.plans, k],
  }))

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Ticket size={20} className="text-pink-400" /> كوبونات الخصم
            <span className="text-sm text-gray-500 font-normal">({rows.length})</span>
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            نسبة مئوية تُخصم من سعر الباقة. الحساب يتم على الخادم في كل مسارات الدفع.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} disabled={loading}
            className="p-2.5 text-gray-400 hover:text-white rounded-xl hover:bg-gray-800 transition">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
          <button onClick={openNew}
            className="flex items-center gap-2 bg-pink-600 hover:bg-pink-500 text-white px-4 py-2.5 rounded-xl font-semibold text-sm transition">
            <Plus size={15} /> كوبون جديد
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-3 text-red-300 text-sm flex items-start gap-2">
          <XCircle size={15} className="mt-0.5 shrink-0" /> {error}
        </div>
      )}

      {/* الجدول */}
      <div className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden">
        <div className="p-4 overflow-x-auto">
          {!rows.length && !loading && (
            <p className="text-gray-400 text-sm text-center py-8">
              لا كوبونات بعد. اضغط «كوبون جديد».
            </p>
          )}
          {!!rows.length && (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-700">
                  {['الرمز', 'الخصم', 'الحالة', 'الاستخدام', 'لكل مستخدم',
                    'الباقات', 'ينتهي', 'ملاحظة', ''].map(h => (
                    <th key={h} className="text-right pb-2 pr-3 font-medium whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map(c => (
                  <tr key={c.id} className="border-b border-gray-700/40">
                    <td className="py-2.5 pr-3">
                      <button onClick={() => copy(c.code)}
                        className="font-mono font-bold text-white hover:text-pink-300 inline-flex items-center gap-1.5 transition"
                        title="نسخ">
                        {c.code}
                        {copied === c.code
                          ? <CheckCircle size={11} className="text-green-400" />
                          : <Copy size={11} className="text-gray-500" />}
                      </button>
                    </td>
                    <td className="py-2.5 pr-3 text-pink-300 font-semibold">
                      −{c.discount_percent}%
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className={`text-[11px] px-2 py-0.5 rounded-full ${
                        c.is_active ? 'bg-green-900/40 text-green-300' : 'bg-gray-700 text-gray-400'
                      }`}>
                        {c.is_active ? 'فعّال' : 'موقوف'}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <button onClick={() => showUses(c)}
                        className="text-gray-300 hover:text-white inline-flex items-center gap-1 transition"
                        title="من استخدمه">
                        <Users size={11} />
                        {c.used_count}{c.max_uses ? ` / ${c.max_uses}` : ''}
                      </button>
                    </td>
                    <td className="py-2.5 pr-3 text-gray-400">
                      {c.per_user_limit === 0 ? 'بلا حد' : c.per_user_limit}
                    </td>
                    <td className="py-2.5 pr-3 text-gray-400">
                      {c.plans?.length
                        ? c.plans.map(k => PLAN_OPTIONS.find(p => p.key === k)?.label || k).join(' · ')
                        : 'الكل'}
                    </td>
                    <td className="py-2.5 pr-3 text-gray-400 font-mono" dir="ltr">
                      {c.expires_at ? c.expires_at.slice(0, 10) : '—'}
                    </td>
                    <td className="py-2.5 pr-3 text-gray-500 max-w-[160px] truncate" title={c.note}>
                      {c.note || '—'}
                    </td>
                    <td className="py-2.5 pr-3 whitespace-nowrap">
                      <button onClick={() => openEdit(c)}
                        className="text-blue-400 hover:text-blue-300 ml-3">تعديل</button>
                      {c.used_count === 0 ? (
                        <button onClick={() => remove(c)}
                          className="text-red-500 hover:text-red-400" title="حذف">
                          <Trash2 size={13} />
                        </button>
                      ) : (
                        <span className="text-gray-600 text-[10px]" title="استُخدم فعلاً — أوقفه بدل حذفه">
                          مستخدَم
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* نموذج الإنشاء/التعديل */}
      {form && (
        <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/70 p-4 overflow-y-auto"
          onClick={() => setForm(null)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg mt-12 mb-12">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
              <h3 className="font-bold">{form.id ? 'تعديل كوبون' : 'كوبون جديد'}</h3>
              <button onClick={() => setForm(null)}
                className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800">
                <X size={16} />
              </button>
            </div>

            <div className="p-5 space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">الرمز</label>
                  <input value={form.code} dir="ltr"
                    onChange={e => setForm(f => ({ ...f, code: e.target.value.toUpperCase() }))}
                    placeholder="SAVE30"
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white font-mono focus:outline-none focus:border-pink-600" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">نسبة الخصم %</label>
                  <input type="number" min="1" max="100" value={form.discount_percent} dir="ltr"
                    onChange={e => setForm(f => ({ ...f, discount_percent: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-pink-600" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">
                    أقصى استخدام كلي <span className="text-gray-600">(فارغ = بلا حد)</span>
                  </label>
                  <input type="number" min="1" value={form.max_uses} dir="ltr"
                    onChange={e => setForm(f => ({ ...f, max_uses: e.target.value }))}
                    placeholder="بلا حد"
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-pink-600" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">
                    لكل مستخدم <span className="text-gray-600">(0 = بلا حد)</span>
                  </label>
                  <input type="number" min="0" value={form.per_user_limit} dir="ltr"
                    onChange={e => setForm(f => ({ ...f, per_user_limit: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-pink-600" />
                </div>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">
                  تاريخ الانتهاء <span className="text-gray-600">(اختياري)</span>
                </label>
                <input type="date" value={form.expires_at} dir="ltr"
                  onChange={e => setForm(f => ({ ...f, expires_at: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-pink-600" />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">
                  الباقات <span className="text-gray-600">(بلا اختيار = كل الباقات)</span>
                </label>
                <div className="flex gap-2 flex-wrap">
                  {PLAN_OPTIONS.map(p => (
                    <button key={p.key} onClick={() => togglePlan(p.key)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition border ${
                        form.plans.includes(p.key)
                          ? 'bg-pink-600 border-pink-500 text-white'
                          : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200'
                      }`}>
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">ملاحظة داخلية</label>
                <input value={form.note}
                  onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                  placeholder="حملة سبتمبر مثلاً"
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-pink-600" />
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active}
                  onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                  className="accent-pink-600" />
                <span className="text-gray-300">فعّال</span>
              </label>

              {form.id && (
                <p className="text-[11px] text-gray-500 leading-relaxed border-t border-gray-800 pt-3">
                  عدّاد الاستخدام لا يُعدَّل من هنا — هو سجل وقائع لا إعداد،
                  وتصفيره يفصله عن سجل الاستخدامات فيتناقض الرقمان.
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-gray-700">
              <button onClick={() => setForm(null)}
                className="px-4 py-2 rounded-xl text-sm text-gray-400 hover:text-white transition">
                إلغاء
              </button>
              <button onClick={save} disabled={saving || !form.code.trim()}
                className="flex items-center gap-2 bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white px-5 py-2 rounded-xl font-semibold text-sm transition">
                {saving ? <RefreshCw size={13} className="animate-spin" /> : <CheckCircle size={13} />}
                حفظ
              </button>
            </div>
          </div>
        </div>
      )}

      {/* سجل الاستخدام */}
      {uses && (
        <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/70 p-4 overflow-y-auto"
          onClick={() => setUses(null)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl mt-12 mb-12">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
              <h3 className="font-bold">
                استخدامات <span className="font-mono text-pink-300">{uses.coupon.code}</span>
                <span className="text-gray-500 font-normal text-sm"> ({uses.total})</span>
              </h3>
              <button onClick={() => setUses(null)}
                className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800">
                <X size={16} />
              </button>
            </div>
            <div className="p-5 overflow-x-auto">
              {!uses.total && (
                <p className="text-gray-400 text-sm text-center py-6">لم يُستخدم بعد.</p>
              )}
              {!!uses.total && (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-700">
                      {['المستخدم', 'الباقة', 'قبل', 'بعد', 'التاريخ'].map(h => (
                        <th key={h} className="text-right pb-2 pr-3 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {uses.redemptions.map(r => (
                      <tr key={r.id} className="border-b border-gray-800">
                        <td className="py-2 pr-3">
                          <div className="text-white">{r.full_name || '—'}</div>
                          <div className="text-gray-500" dir="ltr">{r.email}</div>
                        </td>
                        <td className="py-2 pr-3 text-gray-400">{r.plan || '—'}</td>
                        <td className="py-2 pr-3 text-gray-500 line-through">${r.price_before}</td>
                        <td className="py-2 pr-3 text-emerald-400 font-semibold">${r.price_after}</td>
                        <td className="py-2 pr-3 text-gray-500 font-mono" dir="ltr">
                          {r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
