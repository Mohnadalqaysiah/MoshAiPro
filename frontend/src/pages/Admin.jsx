import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import {
  Users, CreditCard, BarChart2, Settings, CheckCircle,
  XCircle, Clock, Search, Plus, Trash2, ToggleLeft, ToggleRight,
  TrendingUp, DollarSign, Activity
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ─── Plan Badge ───────────────────────────────────────────────────────────────
const PlanBadge = ({ plan }) => {
  const styles = {
    trial:   'bg-gray-700 text-gray-300',
    weekly:  'bg-blue-900/50 text-blue-300 border border-blue-700/50',
    monthly: 'bg-purple-900/50 text-purple-300 border border-purple-700/50',
    banned:  'bg-red-900/50 text-red-300 border border-red-700/50',
  }
  const labels = { trial: 'تجريبي', weekly: 'أسبوعي', monthly: 'شهري', banned: 'محظور' }
  return <span className={`text-xs px-2 py-0.5 rounded-full ${styles[plan] || styles.trial}`}>{labels[plan] || plan}</span>
}

// ─── Status Badge ─────────────────────────────────────────────────────────────
const StatusBadge = ({ status }) => {
  const s = {
    pending:  { class: 'bg-yellow-900/50 text-yellow-300', label: 'قيد المراجعة', icon: Clock },
    approved: { class: 'bg-green-900/50 text-green-300',  label: 'مقبول',         icon: CheckCircle },
    rejected: { class: 'bg-red-900/50 text-red-300',      label: 'مرفوض',         icon: XCircle },
  }[status] || {}
  const Icon = s.icon || Clock
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${s.class}`}>
      <Icon size={10} />{s.label}
    </span>
  )
}

export default function Admin() {
  const { user } = useAuth()
  const navigate  = useNavigate()
  const [tab, setTab]   = useState('stats')
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [payments, setPayments] = useState([])
  const [markets, setMarkets] = useState([])
  const [search, setSearch]   = useState('')
  const [loading, setLoading] = useState(false)

  // Market form
  const [marketForm, setMarketForm] = useState({
    symbol: '', display_name: '', category: 'forex',
    yf_symbol: '', td_symbol: '', is_premium: false, sort_order: 0
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

  const loadStats = async () => {
    const r = await axios.get(`${API}/api/v1/admin/stats`)
    setStats(r.data)
  }

  const loadUsers = async () => {
    setLoading(true)
    const r = await axios.get(`${API}/api/v1/admin/users?search=${search}&limit=100`)
    setUsers(r.data.users)
    setLoading(false)
  }

  const loadPayments = async (status = 'all') => {
    setLoading(true)
    const r = await axios.get(`${API}/api/v1/admin/payments?status_filter=${status}&limit=100`)
    setPayments(r.data.payments)
    setLoading(false)
  }

  const loadMarkets = async () => {
    setLoading(true)
    const r = await axios.get(`${API}/api/v1/admin/markets`)
    setMarkets(r.data)
    setLoading(false)
  }

  const updateUser = async (id, data) => {
    await axios.put(`${API}/api/v1/admin/users/${id}`, data)
    loadUsers()
  }

  const banUser = async (id) => {
    if (!confirm('هل أنت متأكد من حظر هذا المستخدم؟')) return
    await axios.delete(`${API}/api/v1/admin/users/${id}/ban`)
    loadUsers()
  }

  const handlePayment = async (id, action) => {
    await axios.put(`${API}/api/v1/admin/payments/${id}`, { action })
    loadPayments()
    loadStats()
  }

  const toggleMarket = async (symbol) => {
    await axios.patch(`${API}/api/v1/admin/markets/${symbol}/toggle`)
    loadMarkets()
  }

  const addMarket = async (e) => {
    e.preventDefault()
    await axios.post(`${API}/api/v1/admin/markets`, { ...marketForm, is_active: true })
    setMarketForm({ symbol: '', display_name: '', category: 'forex', yf_symbol: '', td_symbol: '', is_premium: false, sort_order: 0 })
    loadMarkets()
  }

  const deleteMarket = async (symbol) => {
    if (!confirm(`حذف ${symbol}؟`)) return
    await axios.delete(`${API}/api/v1/admin/markets/${symbol}`)
    loadMarkets()
  }

  const TABS = [
    { key: 'stats',    icon: Activity,    label: 'إحصائيات' },
    { key: 'users',    icon: Users,       label: 'المستخدمون' },
    { key: 'payments', icon: CreditCard,  label: 'المدفوعات' },
    { key: 'markets',  icon: BarChart2,   label: 'الأسواق' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-white" dir="rtl">
      {/* Sidebar */}
      <div className="flex">
        <aside className="w-56 min-h-screen bg-gray-900 border-l border-gray-800 flex flex-col">
          <div className="p-4 border-b border-gray-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-xs font-bold">M</div>
              <div>
                <div className="text-sm font-semibold">لوحة الإدارة</div>
                <div className="text-xs text-gray-400">Mosh AI Pro</div>
              </div>
            </div>
          </div>
          <nav className="flex-1 p-3 space-y-1">
            {TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  tab === t.key ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                <t.icon size={16} />
                {t.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main */}
        <main className="flex-1 p-6">

          {/* ── Stats ── */}
          {tab === 'stats' && stats && (
            <div>
              <h1 className="text-xl font-bold mb-6">نظرة عامة</h1>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {[
                  { label: 'إجمالي المستخدمين', value: stats.users.total, icon: Users, color: 'blue' },
                  { label: 'اشتراكات نشطة',     value: stats.users.weekly + stats.users.monthly, icon: TrendingUp, color: 'green' },
                  { label: 'الإيرادات (USDT)',   value: `$${stats.payments.revenue_usd}`, icon: DollarSign, color: 'purple' },
                  { label: 'دفعات معلّقة',       value: stats.payments.pending, icon: Clock, color: 'yellow' },
                ].map(s => (
                  <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <div className={`w-8 h-8 rounded-lg bg-${s.color}-900/50 flex items-center justify-center mb-3`}>
                      <s.icon size={16} className={`text-${s.color}-400`} />
                    </div>
                    <div className="text-2xl font-bold">{s.value}</div>
                    <div className="text-xs text-gray-400 mt-1">{s.label}</div>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
                {[
                  { label: 'تجريبي', value: stats.users.trial, color: 'gray' },
                  { label: 'أسبوعي', value: stats.users.weekly, color: 'blue' },
                  { label: 'شهري',   value: stats.users.monthly, color: 'purple' },
                  { label: 'محظور',  value: stats.users.banned, color: 'red' },
                  { label: 'أسواق نشطة', value: stats.markets.active, color: 'green' },
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
              <div className="flex items-center justify-between mb-4">
                <h1 className="text-xl font-bold">المستخدمون</h1>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && loadUsers()}
                      placeholder="بحث بالإيميل..."
                      className="bg-gray-800 border border-gray-700 rounded-lg pr-9 pl-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 w-48"
                      dir="ltr"
                    />
                  </div>
                  <button onClick={loadUsers} className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-2 rounded-lg">بحث</button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-400 border-b border-gray-800">
                      <th className="text-right py-2 px-3">المستخدم</th>
                      <th className="text-right py-2 px-3">الباقة</th>
                      <th className="text-right py-2 px-3">الأيام المتبقية</th>
                      <th className="text-right py-2 px-3">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {users.map(u => (
                      <tr key={u.id} className="hover:bg-gray-900/50">
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-white">{u.full_name || u.email}</div>
                          <div className="text-xs text-gray-500">{u.email}</div>
                          {u.telegram_id && <div className="text-xs text-blue-400">TG: @{u.telegram_username}</div>}
                        </td>
                        <td className="py-2.5 px-3"><PlanBadge plan={u.plan} /></td>
                        <td className="py-2.5 px-3 text-gray-300">{u.days_left ?? '-'} يوم</td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <select
                              className="text-xs bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-gray-300"
                              defaultValue=""
                              onChange={e => {
                                if (e.target.value) updateUser(u.id, { plan: e.target.value })
                              }}
                            >
                              <option value="">تغيير الباقة</option>
                              <option value="trial">تجريبي</option>
                              <option value="weekly">أسبوعي</option>
                              <option value="monthly">شهري</option>
                            </select>
                            <button
                              onClick={() => updateUser(u.id, { is_active: !u.is_active })}
                              className={`text-xs px-2 py-1 rounded-lg border ${u.is_active ? 'border-green-700 text-green-400' : 'border-red-700 text-red-400'}`}
                            >
                              {u.is_active ? 'نشط' : 'معلّق'}
                            </button>
                            <button onClick={() => banUser(u.id)} className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded-lg border border-red-800/50">حظر</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {users.length === 0 && !loading && <p className="text-center text-gray-500 py-8">لا يوجد مستخدمون</p>}
              </div>
            </div>
          )}

          {/* ── Payments ── */}
          {tab === 'payments' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h1 className="text-xl font-bold">المدفوعات</h1>
                <div className="flex gap-2">
                  {['pending', 'approved', 'rejected', 'all'].map(s => (
                    <button key={s} onClick={() => loadPayments(s)}
                      className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500"
                    >
                      {{ pending: '⏳ معلّقة', approved: '✅ مقبولة', rejected: '❌ مرفوضة', all: 'الكل' }[s]}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-3">
                {payments.map(p => (
                  <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium text-white">{p.user_email || p.user_id}</div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          {p.plan === 'weekly' ? 'أسبوعي' : 'شهري'} · ${p.amount_usd} USDT · {p.network}
                        </div>
                        <div className="text-xs font-mono text-blue-400 mt-1 break-all">{p.tx_id}</div>
                        <div className="text-xs text-gray-500 mt-1">{p.created_at?.slice(0, 16)}</div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StatusBadge status={p.status} />
                        {p.status === 'pending' && (
                          <>
                            <button onClick={() => handlePayment(p.id, 'approve')}
                              className="text-xs bg-green-700 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg">
                              قبول
                            </button>
                            <button onClick={() => handlePayment(p.id, 'reject')}
                              className="text-xs bg-red-800 hover:bg-red-700 text-white px-3 py-1.5 rounded-lg">
                              رفض
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {payments.length === 0 && !loading && <p className="text-center text-gray-500 py-8">لا توجد مدفوعات</p>}
              </div>
            </div>
          )}

          {/* ── Markets ── */}
          {tab === 'markets' && (
            <div>
              <h1 className="text-xl font-bold mb-4">إدارة الأسواق</h1>

              {/* Add form */}
              <form onSubmit={addMarket} className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
                <h3 className="text-sm font-semibold mb-3 text-gray-300">إضافة زوج جديد</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    { key: 'symbol',       placeholder: 'XAUUSD',   label: 'الرمز' },
                    { key: 'display_name', placeholder: 'Gold / XAU/USD', label: 'الاسم' },
                    { key: 'yf_symbol',    placeholder: 'GC=F',     label: 'yfinance' },
                    { key: 'td_symbol',    placeholder: 'XAU/USD',  label: 'TwelveData' },
                  ].map(f => (
                    <div key={f.key}>
                      <label className="text-xs text-gray-400 mb-1 block">{f.label}</label>
                      <input
                        required={['symbol', 'display_name'].includes(f.key)}
                        value={marketForm[f.key]}
                        onChange={e => setMarketForm(m => ({ ...m, [f.key]: e.target.value }))}
                        placeholder={f.placeholder}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        dir="ltr"
                      />
                    </div>
                  ))}
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">الفئة</label>
                    <select
                      value={marketForm.category}
                      onChange={e => setMarketForm(m => ({ ...m, category: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white"
                    >
                      <option value="forex">فوركس</option>
                      <option value="crypto">كريبتو</option>
                      <option value="commodity">سلع</option>
                      <option value="index">مؤشرات</option>
                    </select>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                    <input type="checkbox" checked={marketForm.is_premium}
                      onChange={e => setMarketForm(m => ({ ...m, is_premium: e.target.checked }))}
                      className="rounded"
                    />
                    مدفوع فقط
                  </label>
                  <button type="submit" className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg">
                    <Plus size={14} />
                    إضافة
                  </button>
                </div>
              </form>

              {/* Markets list */}
              <div className="space-y-2">
                {markets.map(m => (
                  <div key={m.symbol} className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => toggleMarket(m.symbol)}>
                        {m.is_active
                          ? <ToggleRight size={22} className="text-green-400" />
                          : <ToggleLeft  size={22} className="text-gray-600" />
                        }
                      </button>
                      <div>
                        <div className="font-mono font-semibold text-white text-sm">{m.symbol}</div>
                        <div className="text-xs text-gray-400">{m.display_name} · {m.category}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {m.is_premium && <span className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded-full">مدفوع</span>}
                      {!m.is_active && <span className="text-xs bg-red-900/30 text-red-400 px-2 py-0.5 rounded-full">مغلق</span>}
                      <button onClick={() => deleteMarket(m.symbol)} className="text-gray-600 hover:text-red-400">
                        <Trash2 size={14} />
                      </button>
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
