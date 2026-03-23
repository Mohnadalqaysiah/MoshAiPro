import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import {
  Users, CreditCard, BarChart2, CheckCircle, XCircle, Clock,
  Search, Plus, Trash2, ToggleLeft, ToggleRight, TrendingUp,
  DollarSign, Activity, ChevronDown, RefreshCw, Calendar, Phone,
  MessageCircle, X, ExternalLink, Shield, AlertTriangle
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const PlanBadge = ({ plan }) => {
  const s = { trial:'bg-gray-700 text-gray-300', weekly:'bg-blue-900/50 text-blue-300 border border-blue-700/50', monthly:'bg-purple-900/50 text-purple-300 border border-purple-700/50', banned:'bg-red-900/50 text-red-300 border border-red-700/50' }
  const l = { trial:'تجريبي', weekly:'أسبوعي', monthly:'شهري', banned:'محظور' }
  return <span className={`text-xs px-2 py-0.5 rounded-full ${s[plan]||s.trial}`}>{l[plan]||plan}</span>
}

const StatusBadge = ({ status }) => {
  const s = { pending:{cls:'bg-yellow-900/50 text-yellow-300',l:'معلّق',I:Clock}, approved:{cls:'bg-green-900/50 text-green-300',l:'مقبول',I:CheckCircle}, rejected:{cls:'bg-red-900/50 text-red-300',l:'مرفوض',I:XCircle} }[status]||{}
  const I = s.I||Clock
  return <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${s.cls}`}><I size={10}/>{s.l}</span>
}

// ── User Detail Modal ──────────────────────────────────────────────────────────
function UserModal({ user: u, onClose, onUpdate }) {
  const [extraDays, setExtraDays] = useState(7)
  const [loading, setLoading] = useState('')
  const [msg, setMsg] = useState(null)

  const doAction = async (action, payload = {}) => {
    setLoading(action); setMsg(null)
    try {
      if (action === 'reset_trial') {
        await axios.post(`${API}/api/v1/admin/users/${u.id}/reset-trial`)
        setMsg({ type:'ok', text:'تم إعادة تعيين التجربة' })
      } else if (action === 'extend') {
        await axios.put(`${API}/api/v1/admin/users/${u.id}`, { extra_days: extraDays })
        setMsg({ type:'ok', text:`تم تمديد الاشتراك ${extraDays} يوم` })
      } else if (action === 'ban') {
        if (!confirm('حظر هذا المستخدم؟')) { setLoading(''); return }
        await axios.delete(`${API}/api/v1/admin/users/${u.id}/ban`)
        setMsg({ type:'ok', text:'تم الحظر' })
      } else if (action === 'plan') {
        await axios.put(`${API}/api/v1/admin/users/${u.id}`, payload)
        setMsg({ type:'ok', text:'تم تغيير الباقة' })
      } else if (action === 'toggle') {
        await axios.put(`${API}/api/v1/admin/users/${u.id}`, { is_active: !u.is_active })
        setMsg({ type:'ok', text: u.is_active ? 'تم تعليق الحساب' : 'تم تفعيل الحساب' })
      }
      onUpdate()
    } catch (e) {
      setMsg({ type:'err', text: e.response?.data?.detail || 'خطأ' })
    } finally { setLoading('') }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <h2 className="font-bold text-white">تفاصيل المستخدم</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={18}/></button>
        </div>
        <div className="p-5 space-y-5">
          {/* Info */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              ['الاسم', u.full_name || '—'],
              ['البريد', u.email],
              ['الهاتف', u.phone_number || '—'],
              ['الباقة', <PlanBadge key="p" plan={u.plan}/>],
              ['الحالة', u.is_active ? '✅ نشط' : '⛔ معلّق'],
              ['Telegram', u.telegram_username ? `@${u.telegram_username}` : '—'],
              ['الأيام المتبقية', `${u.days_left ?? '—'} يوم`],
              ['تاريخ التسجيل', u.created_at?.slice(0,10) || '—'],
              ['آخر زيارة', u.last_seen_at?.slice(0,10) || '—'],
              ['انتهاء الاشتراك', u.subscription_ends_at?.slice(0,10) || '—'],
              ['تحليلات تجريبية', u.trial_analyses_left],
              ['محادثات تجريبية', u.trial_chat_left],
              ['إجمالي التحليلات', u.analyses_total],
              ['إجمالي المحادثات', u.chat_total],
            ].map(([k, v]) => (
              <div key={k} className="bg-gray-800 rounded-lg px-3 py-2">
                <div className="text-xs text-gray-400 mb-0.5">{k}</div>
                <div className="text-white font-medium text-xs">{v}</div>
              </div>
            ))}
          </div>

          {msg && (
            <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 ${msg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
              {msg.type==='ok'?<CheckCircle size={14}/>:<AlertTriangle size={14}/>} {msg.text}
            </div>
          )}

          {/* Actions */}
          <div className="space-y-3">
            {/* Change Plan */}
            <div>
              <p className="text-xs text-gray-400 mb-2">تغيير الباقة</p>
              <div className="flex gap-2 flex-wrap">
                {['trial','weekly','monthly'].map(p => (
                  <button key={p} disabled={loading==='plan'||u.plan===p}
                    onClick={() => doAction('plan',{plan:p})}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition ${u.plan===p?'border-blue-500 text-blue-400 bg-blue-900/20':'border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white'}`}>
                    {p==='trial'?'تجريبي':p==='weekly'?'أسبوعي':'شهري'}
                  </button>
                ))}
              </div>
            </div>

            {/* Extend */}
            <div>
              <p className="text-xs text-gray-400 mb-2">تمديد الاشتراك</p>
              <div className="flex gap-2">
                <input type="number" min="1" max="365" value={extraDays}
                  onChange={e => setExtraDays(Number(e.target.value))}
                  className="w-20 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 text-center"
                  dir="ltr" />
                <span className="text-sm text-gray-400 self-center">يوم</span>
                <button disabled={loading==='extend'}
                  onClick={() => doAction('extend')}
                  className="flex items-center gap-1 text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg transition">
                  <Calendar size={12}/> تمديد
                </button>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-2 flex-wrap">
              <button disabled={loading==='reset_trial'}
                onClick={() => doAction('reset_trial')}
                className="flex items-center gap-1 text-xs bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded-lg transition">
                <RefreshCw size={12}/> إعادة التجربة
              </button>
              <button disabled={loading==='toggle'}
                onClick={() => doAction('toggle')}
                className={`flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg transition ${u.is_active?'bg-orange-800/50 hover:bg-orange-700/50 text-orange-300':'bg-green-800/50 hover:bg-green-700/50 text-green-300'}`}>
                {u.is_active ? '⏸ تعليق' : '▶ تفعيل'}
              </button>
              <button disabled={loading==='ban'}
                onClick={() => doAction('ban')}
                className="flex items-center gap-1 text-xs bg-red-900/50 hover:bg-red-800/50 text-red-300 px-3 py-1.5 rounded-lg transition border border-red-700/50">
                <Shield size={12}/> حظر دائم
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Admin Component ───────────────────────────────────────────────────────
export default function Admin() {
  const { user } = useAuth()
  const navigate  = useNavigate()
  const [tab, setTab]         = useState('stats')
  const [stats, setStats]     = useState(null)
  const [users, setUsers]     = useState([])
  const [payments, setPayments] = useState([])
  const [markets, setMarkets] = useState([])
  const [search, setSearch]   = useState('')
  const [planFilter, setPlanFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)

  const [marketForm, setMarketForm] = useState({
    symbol:'', display_name:'', category:'forex', yf_symbol:'', td_symbol:'', is_premium:false, sort_order:0
  })

  useEffect(() => {
    if (user?.role !== 'admin') { navigate('/dashboard'); return }
    loadStats()
  }, [user])

  useEffect(() => {
    if (tab === 'users')    loadUsers()
    if (tab === 'payments') loadPayments()
    if (tab === 'markets')  loadMarkets()
  }, [tab])

  const loadStats    = async () => { const r = await axios.get(`${API}/api/v1/admin/stats`); setStats(r.data) }
  const loadUsers    = async () => { setLoading(true); const r = await axios.get(`${API}/api/v1/admin/users?search=${search}&limit=200`); setUsers(r.data.users); setLoading(false) }
  const loadPayments = async (status='all') => { setLoading(true); const r = await axios.get(`${API}/api/v1/admin/payments?status_filter=${status}&limit=100`); setPayments(r.data.payments); setLoading(false) }
  const loadMarkets  = async () => { setLoading(true); const r = await axios.get(`${API}/api/v1/admin/markets`); setMarkets(r.data); setLoading(false) }

  const handlePayment = async (id, action) => {
    await axios.put(`${API}/api/v1/admin/payments/${id}`, { action })
    loadPayments(); loadStats()
  }

  const toggleMarket  = async (symbol) => { await axios.patch(`${API}/api/v1/admin/markets/${symbol}/toggle`); loadMarkets() }
  const deleteMarket  = async (symbol) => { if (!confirm(`حذف ${symbol}؟`)) return; await axios.delete(`${API}/api/v1/admin/markets/${symbol}`); loadMarkets() }
  const addMarket     = async (e) => { e.preventDefault(); await axios.post(`${API}/api/v1/admin/markets`, { ...marketForm, is_active:true }); setMarketForm({ symbol:'', display_name:'', category:'forex', yf_symbol:'', td_symbol:'', is_premium:false, sort_order:0 }); loadMarkets() }

  const filteredUsers = users.filter(u => planFilter === 'all' || u.plan === planFilter)

  const TABS = [
    { key:'stats',    icon:Activity,   label:'إحصائيات' },
    { key:'users',    icon:Users,      label:'المستخدمون' },
    { key:'payments', icon:CreditCard, label:'المدفوعات' },
    { key:'markets',  icon:BarChart2,  label:'الأسواق' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-white" dir="rtl">
      {selectedUser && (
        <UserModal
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
          onUpdate={() => { loadUsers(); loadStats(); setSelectedUser(null) }}
        />
      )}

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-52 min-h-screen bg-gray-900 border-l border-gray-800 flex flex-col flex-shrink-0">
          <div className="p-4 border-b border-gray-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-xs font-bold">Q</div>
              <div>
                <div className="text-sm font-semibold">لوحة الإدارة</div>
                <div className="text-xs text-gray-400">Qafeel AI</div>
              </div>
            </div>
          </div>
          <nav className="flex-1 p-3 space-y-1">
            {TABS.map(t => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${tab===t.key?'bg-blue-600 text-white':'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
                <t.icon size={16}/>{t.label}
              </button>
            ))}
          </nav>
          <div className="p-3 border-t border-gray-800">
            <button onClick={() => navigate('/dashboard')} className="w-full flex items-center gap-2 text-xs text-gray-500 hover:text-white px-3 py-2 rounded-lg hover:bg-gray-800">
              <ExternalLink size={13}/> المنصة
            </button>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 p-6 overflow-x-auto">

          {/* ── Stats ── */}
          {tab === 'stats' && stats && (
            <div>
              <h1 className="text-xl font-bold mb-6">نظرة عامة</h1>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {[
                  { label:'إجمالي المستخدمين', value:stats.users.total,                        icon:Users,       color:'blue' },
                  { label:'اشتراكات نشطة',     value:stats.users.weekly+stats.users.monthly,   icon:TrendingUp,  color:'green' },
                  { label:'الإيرادات (USDT)',   value:`$${stats.payments.revenue_usd}`,         icon:DollarSign,  color:'purple' },
                  { label:'دفعات معلّقة',       value:stats.payments.pending,                  icon:Clock,       color:'yellow' },
                ].map(s => (
                  <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <div className={`w-8 h-8 rounded-lg bg-${s.color}-900/50 flex items-center justify-center mb-3`}>
                      <s.icon size={16} className={`text-${s.color}-400`}/>
                    </div>
                    <div className="text-2xl font-bold">{s.value}</div>
                    <div className="text-xs text-gray-400 mt-1">{s.label}</div>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
                {[
                  { label:'تجريبي', value:stats.users.trial,   color:'gray' },
                  { label:'أسبوعي', value:stats.users.weekly,  color:'blue' },
                  { label:'شهري',   value:stats.users.monthly, color:'purple' },
                  { label:'محظور',  value:stats.users.banned,  color:'red' },
                  { label:'أسواق نشطة', value:stats.markets.active, color:'green' },
                ].map(s => (
                  <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
                    <div className={`text-xl font-bold text-${s.color}-400`}>{s.value}</div>
                    <div className="text-xs text-gray-500 mt-1">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Users ── */}
          {tab === 'users' && (
            <div>
              <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <h1 className="text-xl font-bold">المستخدمون <span className="text-sm text-gray-500 font-normal">({filteredUsers.length})</span></h1>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Plan filter */}
                  <div className="flex gap-1">
                    {['all','trial','weekly','monthly','banned'].map(p => (
                      <button key={p} onClick={() => setPlanFilter(p)}
                        className={`text-xs px-2.5 py-1 rounded-lg border transition ${planFilter===p?'border-blue-500 text-blue-400 bg-blue-900/20':'border-gray-700 text-gray-500 hover:border-gray-600 hover:text-gray-300'}`}>
                        {p==='all'?'الكل':p==='trial'?'تجريبي':p==='weekly'?'أسبوعي':p==='monthly'?'شهري':'محظور'}
                      </button>
                    ))}
                  </div>
                  {/* Search */}
                  <div className="relative">
                    <Search size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"/>
                    <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key==='Enter'&&loadUsers()}
                      placeholder="بحث..." className="bg-gray-800 border border-gray-700 rounded-lg pr-8 pl-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 w-40" dir="ltr"/>
                  </div>
                  <button onClick={loadUsers} className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1.5 rounded-lg">بحث</button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-400 border-b border-gray-800">
                      <th className="text-right py-2 px-3">#</th>
                      <th className="text-right py-2 px-3">المستخدم</th>
                      <th className="text-right py-2 px-3">الباقة</th>
                      <th className="text-right py-2 px-3">متبقي</th>
                      <th className="text-right py-2 px-3">Telegram</th>
                      <th className="text-right py-2 px-3">تسجيل</th>
                      <th className="text-right py-2 px-3">إجراء</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {filteredUsers.map(u => (
                      <tr key={u.id} className="hover:bg-gray-900/50 cursor-pointer" onClick={() => setSelectedUser(u)}>
                        <td className="py-2 px-3 text-gray-600 text-xs">{u.id}</td>
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-white text-sm">{u.full_name || '—'}</div>
                          <div className="text-xs text-gray-500 font-mono">{u.email}</div>
                        </td>
                        <td className="py-2.5 px-3"><PlanBadge plan={u.plan}/></td>
                        <td className="py-2.5 px-3 text-gray-300 text-xs">
                          {u.plan==='trial' ? `${u.trial_analyses_left}/${u.trial_chat_left}` : `${u.days_left??'—'}ي`}
                        </td>
                        <td className="py-2.5 px-3 text-xs">
                          {u.telegram_id ? <span className="text-blue-400">✓ مرتبط</span> : <span className="text-gray-600">—</span>}
                        </td>
                        <td className="py-2.5 px-3 text-xs text-gray-500">{u.created_at?.slice(0,10)||'—'}</td>
                        <td className="py-2.5 px-3" onClick={e => e.stopPropagation()}>
                          <button onClick={() => setSelectedUser(u)} className="text-xs text-blue-400 hover:text-blue-300 border border-blue-800/50 rounded px-2 py-0.5">
                            تفاصيل
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredUsers.length === 0 && !loading && <p className="text-center text-gray-500 py-8">لا يوجد مستخدمون</p>}
              </div>
            </div>
          )}

          {/* ── Payments ── */}
          {tab === 'payments' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h1 className="text-xl font-bold">المدفوعات</h1>
                <div className="flex gap-2">
                  {['pending','approved','rejected','all'].map(s => (
                    <button key={s} onClick={() => loadPayments(s)}
                      className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition">
                      {s==='pending'?'⏳ معلّقة':s==='approved'?'✅ مقبولة':s==='rejected'?'❌ مرفوضة':'الكل'}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-3">
                {payments.map(p => (
                  <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-white text-sm">{p.user_name || p.user_email}</div>
                        <div className="text-xs text-gray-500 mb-1">{p.user_email}</div>
                        <div className="text-xs text-gray-400">
                          {p.plan==='weekly'?'أسبوعي':'شهري'} · <span className="text-green-400 font-bold">${p.amount_usd} USDT</span> · {p.network}
                        </div>
                        <div className="text-xs font-mono text-blue-400 mt-1 break-all">{p.tx_id}</div>
                        <div className="text-xs text-gray-600 mt-1">{p.created_at?.slice(0,16)}</div>
                        {p.admin_note && <div className="text-xs text-yellow-400 mt-1">ملاحظة: {p.admin_note}</div>}
                      </div>
                      <div className="flex flex-col items-end gap-2 flex-shrink-0">
                        <StatusBadge status={p.status}/>
                        {p.status === 'pending' && (
                          <div className="flex gap-2">
                            <button onClick={() => handlePayment(p.id,'approve')}
                              className="text-xs bg-green-700 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg">
                              ✅ قبول
                            </button>
                            <button onClick={() => handlePayment(p.id,'reject')}
                              className="text-xs bg-red-800 hover:bg-red-700 text-white px-3 py-1.5 rounded-lg">
                              ❌ رفض
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {payments.length===0 && !loading && <p className="text-center text-gray-500 py-8">لا توجد مدفوعات</p>}
              </div>
            </div>
          )}

          {/* ── Markets ── */}
          {tab === 'markets' && (
            <div>
              <h1 className="text-xl font-bold mb-4">إدارة الأسواق</h1>
              <form onSubmit={addMarket} className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
                <h3 className="text-sm font-semibold mb-3 text-gray-300">إضافة زوج جديد</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    { key:'symbol',       ph:'XAUUSD',   lb:'الرمز' },
                    { key:'display_name', ph:'Gold / XAU/USD', lb:'الاسم' },
                    { key:'yf_symbol',    ph:'GC=F',     lb:'yfinance' },
                    { key:'td_symbol',    ph:'XAU/USD',  lb:'TwelveData' },
                  ].map(f => (
                    <div key={f.key}>
                      <label className="text-xs text-gray-400 mb-1 block">{f.lb}</label>
                      <input required={['symbol','display_name'].includes(f.key)} value={marketForm[f.key]}
                        onChange={e => setMarketForm(m => ({...m,[f.key]:e.target.value}))}
                        placeholder={f.ph} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none" dir="ltr"/>
                    </div>
                  ))}
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">الفئة</label>
                    <select value={marketForm.category} onChange={e => setMarketForm(m => ({...m,category:e.target.value}))}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white">
                      <option value="forex">فوركس</option>
                      <option value="crypto">كريبتو</option>
                      <option value="commodity">سلع</option>
                      <option value="index">مؤشرات</option>
                    </select>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                    <input type="checkbox" checked={marketForm.is_premium} onChange={e => setMarketForm(m => ({...m,is_premium:e.target.checked}))} className="rounded"/>
                    مدفوع فقط
                  </label>
                  <button type="submit" className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg">
                    <Plus size={14}/> إضافة
                  </button>
                </div>
              </form>

              <div className="space-y-2">
                {markets.map(m => (
                  <div key={m.symbol} className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => toggleMarket(m.symbol)}>
                        {m.is_active ? <ToggleRight size={22} className="text-green-400"/> : <ToggleLeft size={22} className="text-gray-600"/>}
                      </button>
                      <div>
                        <div className="font-mono font-semibold text-white text-sm">{m.symbol}</div>
                        <div className="text-xs text-gray-400">{m.display_name} · {m.category}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {m.is_premium && <span className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded-full">مدفوع</span>}
                      {!m.is_active && <span className="text-xs bg-red-900/30 text-red-400 px-2 py-0.5 rounded-full">مغلق</span>}
                      <button onClick={() => deleteMarket(m.symbol)} className="text-gray-600 hover:text-red-400"><Trash2 size={14}/></button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  )
}
