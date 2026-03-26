import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import {
  Users, CreditCard, BarChart2, CheckCircle, XCircle, Clock,
  Search, Plus, Trash2, ToggleLeft, ToggleRight, TrendingUp,
  DollarSign, Activity, RefreshCw, Calendar,
  X, ExternalLink, Shield, AlertTriangle, Settings, Mail, Upload
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
      } else if (action === 'delete') {
        if (!confirm(`⚠️ حذف نهائي لـ ${u.email}؟ لا يمكن التراجع!`)) { setLoading(''); return }
        await axios.delete(`${API}/api/v1/admin/users/${u.id}`)
        onClose()
        onUpdate()
        return
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
              <button disabled={loading==='delete'}
                onClick={() => doAction('delete')}
                className="flex items-center gap-1 text-xs bg-red-950/60 hover:bg-red-900/60 text-red-400 px-3 py-1.5 rounded-lg transition border border-red-800/50">
                <Trash2 size={12}/> حذف نهائي
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

  const [siteSettings, setSiteSettings] = useState({})
  const [settingEdits, setSettingEdits] = useState({})
  const [settingSaving, setSettingSaving] = useState('')
  const [settingMsg, setSettingMsg] = useState(null)

  const [adminProfile, setAdminProfile] = useState({ current_password:'', new_email:'', new_password:'' })
  const [adminProfileSaving, setAdminProfileSaving] = useState(false)
  const [adminProfileMsg, setAdminProfileMsg] = useState(null)

  // Email state
  const [emailForm, setEmailForm] = useState({ subject:'', body:'', user_id:'' })
  const [emailSending, setEmailSending] = useState(false)
  const [emailMsg, setEmailMsg] = useState(null)

  // Logo upload state
  const [logoFile, setLogoFile] = useState(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [logoMsg, setLogoMsg] = useState(null)

  // Affiliate state
  const [affStats, setAffStats] = useState({ total: 0, affiliates: [] })
  const [affLoading, setAffLoading] = useState(false)
  const [affSearch, setAffSearch] = useState('')
  const [affPayout, setAffPayout] = useState({ id: null, amount: '', note: '' })
  const [affPayoutMsg, setAffPayoutMsg] = useState(null)

  useEffect(() => {
    if (user?.role !== 'admin') { navigate('/dashboard'); return }
    loadStats()
  }, [user])

  useEffect(() => {
    if (tab === 'users')     loadUsers()
    if (tab === 'payments')  loadPayments()
    if (tab === 'markets')   loadMarkets()
    if (tab === 'settings')  loadSettings()
    if (tab === 'affiliate') loadAffStats()
  }, [tab])

  const loadStats    = async () => { const r = await axios.get(`${API}/api/v1/admin/stats`); setStats(r.data) }
  const loadAffStats = async (q = '') => {
    setAffLoading(true)
    try {
      const r = await axios.get(`${API}/api/v1/admin/affiliate/stats?search=${q}&limit=100`)
      setAffStats(r.data)
    } catch (e) {}
    finally { setAffLoading(false) }
  }
  const loadUsers    = async () => { setLoading(true); const r = await axios.get(`${API}/api/v1/admin/users?search=${search}&limit=200`); setUsers(r.data.users); setLoading(false) }
  const loadPayments = async (status='all') => { setLoading(true); const r = await axios.get(`${API}/api/v1/admin/payments?status_filter=${status}&limit=100`); setPayments(r.data.payments); setLoading(false) }
  const loadMarkets  = async () => { setLoading(true); const r = await axios.get(`${API}/api/v1/admin/markets`); setMarkets(r.data); setLoading(false) }
  const loadSettings = async () => {
    const r = await axios.get(`${API}/api/v1/admin/settings`)
    setSiteSettings(r.data)
    const edits = {}
    Object.entries(r.data).forEach(([k, v]) => { edits[k] = v.value || '' })
    setSettingEdits(edits)
  }
  const saveSetting = async (key, overrideValue) => {
    setSettingSaving(key); setSettingMsg(null)
    try {
      const value = overrideValue !== undefined ? overrideValue : settingEdits[key]
      await axios.put(`${API}/api/v1/admin/settings/${key}`, { value })
      setSettingMsg({ type:'ok', text:'تم الحفظ بنجاح' })
      loadSettings()
    } catch (e) {
      setSettingMsg({ type:'err', text: e.response?.data?.detail || 'خطأ في الحفظ' })
    } finally { setSettingSaving('') }
  }

  const saveAdminProfile = async (e) => {
    e.preventDefault()
    setAdminProfileSaving(true); setAdminProfileMsg(null)
    try {
      const payload = { current_password: adminProfile.current_password }
      if (adminProfile.new_email.trim())    payload.new_email    = adminProfile.new_email.trim()
      if (adminProfile.new_password.trim()) payload.new_password = adminProfile.new_password.trim()
      await axios.put(`${API}/api/v1/admin/profile`, payload)
      setAdminProfileMsg({ type:'ok', text:'تم تحديث بيانات الحساب بنجاح' })
      setAdminProfile({ current_password:'', new_email:'', new_password:'' })
    } catch (e) {
      setAdminProfileMsg({ type:'err', text: e.response?.data?.detail || 'خطأ في الحفظ' })
    } finally { setAdminProfileSaving(false) }
  }

  const handlePayment = async (id, action) => {
    await axios.put(`${API}/api/v1/admin/payments/${id}`, { action })
    loadPayments(); loadStats()
  }

  const toggleMarket  = async (symbol) => { await axios.patch(`${API}/api/v1/admin/markets/${symbol}/toggle`); loadMarkets() }
  const deleteMarket  = async (symbol) => { if (!confirm(`حذف ${symbol}؟`)) return; await axios.delete(`${API}/api/v1/admin/markets/${symbol}`); loadMarkets() }
  const addMarket     = async (e) => { e.preventDefault(); await axios.post(`${API}/api/v1/admin/markets`, { ...marketForm, is_active:true }); setMarketForm({ symbol:'', display_name:'', category:'forex', yf_symbol:'', td_symbol:'', is_premium:false, sort_order:0 }); loadMarkets() }

  const uploadLogo = async (e) => {
    const file = e.target.files?.[0]; if (!file) return
    setLogoFile(file); setLogoUploading(true); setLogoMsg(null)
    try {
      const fd = new FormData(); fd.append('file', file)
      const r = await axios.post(`${API}/api/v1/admin/upload-logo`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setLogoMsg({ type:'ok', text:'تم رفع الشعار بنجاح' })
      setSettingEdits(s => ({ ...s, site_logo_url: r.data.url }))
      setSiteSettings(s => ({ ...s, site_logo_url: { ...(s.site_logo_url||{}), value: r.data.url } }))
    } catch (err) { setLogoMsg({ type:'err', text: err.response?.data?.detail || 'فشل رفع الشعار' }) }
    finally { setLogoUploading(false) }
  }

  const sendEmail = async (e) => {
    e.preventDefault(); setEmailSending(true); setEmailMsg(null)
    try {
      const payload = { subject: emailForm.subject, body: emailForm.body }
      if (emailForm.user_id) payload.user_id = parseInt(emailForm.user_id)
      const r = await axios.post(`${API}/api/v1/admin/email/send`, payload)
      setEmailMsg({ type:'ok', text: r.data.message })
      setEmailForm(f => ({ ...f, subject:'', body:'' }))
    } catch (err) { setEmailMsg({ type:'err', text: err.response?.data?.detail || 'فشل الإرسال' }) }
    finally { setEmailSending(false) }
  }

  const filteredUsers = users.filter(u => planFilter === 'all' || u.plan === planFilter)

  const TABS = [
    { key:'stats',     icon:Activity,   label:'إحصائيات' },
    { key:'users',     icon:Users,      label:'المستخدمون' },
    { key:'payments',  icon:CreditCard, label:'المدفوعات' },
    { key:'markets',   icon:BarChart2,  label:'الأسواق' },
    { key:'affiliate', icon:TrendingUp, label:'الأفلييت' },
    { key:'email',     icon:Mail,       label:'البريد' },
    { key:'settings',  icon:Settings,   label:'الإعدادات' },
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
                <div className="text-xs text-gray-400">Qaffel AI</div>
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
                        <td className="py-2 px-3 text-gray-500 text-xs font-mono select-all" title="User ID">#{u.id}</td>
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
                          <div className="flex items-center gap-1.5">
                            <button onClick={() => setSelectedUser(u)} className="text-xs text-blue-400 hover:text-blue-300 border border-blue-800/50 rounded px-2 py-0.5">
                              تفاصيل
                            </button>
                            <button
                              title={`إرسال إيميل لـ ${u.email}`}
                              onClick={() => {
                                setEmailForm(f => ({ ...f, user_id: String(u.id), subject: '', body: '' }))
                                setTab('email')
                              }}
                              className="text-xs text-gray-400 hover:text-blue-400 border border-gray-700 hover:border-blue-700 rounded px-1.5 py-0.5 transition"
                            >
                              <Mail size={11}/>
                            </button>
                          </div>
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

          {/* ── Email ── */}
          {tab === 'email' && (
            <div className="max-w-2xl">
              <h1 className="text-xl font-bold mb-6 flex items-center gap-2"><Mail size={20} className="text-blue-400"/> إرسال بريد إلكتروني</h1>

              {emailMsg && (
                <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mb-4 ${emailMsg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
                  {emailMsg.type==='ok'?<CheckCircle size={14}/>:<AlertTriangle size={14}/>} {emailMsg.text}
                </div>
              )}

              <form onSubmit={sendEmail} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
                {/* المستلم */}
                <div>
                  <label className="block text-sm text-gray-300 font-medium mb-1">المستلم</label>
                  <select
                    value={emailForm.user_id ? 'specific' : 'all'}
                    onChange={e => setEmailForm(f => ({ ...f, user_id: e.target.value === 'all' ? '' : (f.user_id || '') }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white mb-2"
                  >
                    <option value="all">الكل ({users.length} مستخدم)</option>
                    <option value="specific">مستخدم معين (بالـ ID)</option>
                  </select>
                  {emailForm.user_id !== '' && (
                    <div className="flex gap-2">
                      <input
                        type="number" placeholder="ID المستخدم..." value={emailForm.user_id}
                        onChange={e => setEmailForm(f => ({ ...f, user_id: e.target.value }))}
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                        dir="ltr"
                      />
                      <select
                        onChange={e => setEmailForm(f => ({ ...f, user_id: e.target.value }))}
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                      >
                        <option value="">— اختر مستخدم —</option>
                        {users.map(u => <option key={u.id} value={u.id}>{u.email} (#{u.id})</option>)}
                      </select>
                    </div>
                  )}
                </div>

                {/* الموضوع */}
                <div>
                  <label className="block text-sm text-gray-300 font-medium mb-1">الموضوع</label>
                  <input
                    required type="text" value={emailForm.subject}
                    onChange={e => setEmailForm(f => ({ ...f, subject: e.target.value }))}
                    placeholder="موضوع الرسالة..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>

                {/* المحتوى */}
                <div>
                  <label className="block text-sm text-gray-300 font-medium mb-1">
                    المحتوى <span className="text-gray-500 font-normal">(يدعم HTML)</span>
                  </label>
                  <textarea
                    required rows={8} value={emailForm.body}
                    onChange={e => setEmailForm(f => ({ ...f, body: e.target.value }))}
                    placeholder="<h2>مرحباً...</h2><p>نص الرسالة هنا</p>"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono resize-y"
                    dir="ltr"
                  />
                </div>

                <div className="flex gap-3">
                  <button type="submit" disabled={emailSending}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-6 py-2 rounded-lg text-sm transition">
                    {emailSending ? <RefreshCw size={14} className="animate-spin"/> : <Mail size={14}/>}
                    {emailSending ? 'جاري الإرسال...' : emailForm.user_id ? 'إرسال للمستخدم' : `إرسال للكل (${users.length})`}
                  </button>
                  <button type="button" onClick={() => { if (!users.length) loadUsers() }}
                    className="text-xs text-gray-400 hover:text-white px-3 py-2 rounded-lg hover:bg-gray-800">
                    تحديث قائمة المستخدمين
                  </button>
                </div>
              </form>

              {/* ── تحذيرات انتهاء الاشتراك ── */}
              <div className="mt-6 bg-gray-900 border border-yellow-800/40 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-yellow-400 mb-1">⚠️ تحذيرات انتهاء الاشتراك</h3>
                <p className="text-xs text-gray-500 mb-3">
                  إرسال إيميل تحذير تلقائي لكل مستخدم اشتراكه ينتهي قريباً وليس لديه حساب تيليجرام
                </p>
                <div className="flex gap-2 items-center">
                  <select id="exp-days" defaultValue="3"
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white">
                    {[1,2,3,5,7].map(d => <option key={d} value={d}>{d} أيام قبل الانتهاء</option>)}
                  </select>
                  <button
                    onClick={async () => {
                      const days = document.getElementById('exp-days').value
                      try {
                        const r = await axios.post(`${API}/api/v1/admin/email/subscription-warnings?days_before=${days}`)
                        setEmailMsg({ type:'ok', text:`تم إرسال التحذيرات لـ ${r.data.sent} مستخدم` })
                      } catch (e) {
                        setEmailMsg({ type:'err', text: e.response?.data?.detail || 'خطأ' })
                      }
                    }}
                    className="flex items-center gap-1 text-sm bg-yellow-700 hover:bg-yellow-600 text-white px-4 py-1.5 rounded-lg transition">
                    <Mail size={13}/> إرسال التحذيرات
                  </button>
                </div>
              </div>

              <div className="mt-4 p-4 bg-gray-900 border border-gray-800 rounded-xl text-xs text-gray-500 space-y-1">
                <p>⚙️ يتطلب ضبط متغيرات البيئة: <span className="font-mono text-gray-400">SMTP_USER</span> و <span className="font-mono text-gray-400">SMTP_PASSWORD</span></p>
                <p>📧 الإرسال يتم في الخلفية ولا يوقف الصفحة</p>
                <p>🔐 <span className="font-mono text-gray-400">SMTP_HOST</span> الافتراضي: smtp.hostinger.com (port 465)</p>
              </div>
            </div>
          )}

          {/* ── Affiliate ── */}
          {tab === 'affiliate' && (
            <div className="max-w-4xl">
              <h1 className="text-xl font-bold mb-6 flex items-center gap-2"><TrendingUp size={20} className="text-green-400"/> نظام الأفلييت</h1>

              {/* Search */}
              <div className="flex gap-3 mb-4">
                <div className="relative flex-1 max-w-sm">
                  <Search size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"/>
                  <input value={affSearch} onChange={e => setAffSearch(e.target.value)}
                    placeholder="بحث بالإيميل أو الكود..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg pr-9 pl-4 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                    onKeyDown={e => e.key === 'Enter' && loadAffStats(affSearch)} />
                </div>
                <button onClick={() => loadAffStats(affSearch)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition">
                  <RefreshCw size={14}/> بحث
                </button>
              </div>

              {affPayoutMsg && (
                <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mb-4 ${affPayoutMsg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
                  {affPayoutMsg.type==='ok'?<CheckCircle size={14}/>:<AlertTriangle size={14}/>} {affPayoutMsg.text}
                </div>
              )}

              {affLoading ? (
                <div className="flex items-center gap-2 text-gray-400 py-8 justify-center"><RefreshCw size={16} className="animate-spin"/> جاري التحميل...</div>
              ) : (
                <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-900 text-gray-400 text-xs">
                      <tr>
                        <th className="text-right px-4 py-3">المستخدم</th>
                        <th className="text-right px-4 py-3">الكود</th>
                        <th className="text-center px-4 py-3">المرحلة</th>
                        <th className="text-center px-4 py-3">الإحالات</th>
                        <th className="text-right px-4 py-3">رصيد معلّق</th>
                        <th className="text-right px-4 py-3">مدفوع</th>
                        <th className="text-center px-4 py-3">دفع</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/50">
                      {affStats.affiliates?.map(a => (
                        <tr key={a.affiliate_id} className="hover:bg-gray-700/30 transition-colors">
                          <td className="px-4 py-3 text-white text-xs">{a.user_email}</td>
                          <td className="px-4 py-3 font-mono text-blue-400 text-xs">{a.code}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${a.current_tier===2?'bg-yellow-900/40 text-yellow-400':'bg-blue-900/40 text-blue-400'}`}>
                              T{a.current_tier} · {a.commission_rate_pct}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center text-white">{a.total_referrals}</td>
                          <td className="px-4 py-3 text-green-400 font-mono">${a.pending_balance_usd?.toFixed(2)}</td>
                          <td className="px-4 py-3 text-gray-400 font-mono">${a.paid_out_usd?.toFixed(2)}</td>
                          <td className="px-4 py-3 text-center">
                            {affPayout.id === a.affiliate_id ? (
                              <div className="flex items-center gap-1 justify-center">
                                <input type="number" step="0.01" min="0.01" max={a.pending_balance_usd}
                                  value={affPayout.amount}
                                  onChange={e => setAffPayout(p => ({...p, amount: e.target.value}))}
                                  className="w-20 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                                  placeholder="$" dir="ltr" />
                                <button
                                  onClick={async () => {
                                    setAffPayoutMsg(null)
                                    try {
                                      const r = await axios.post(`${API}/api/v1/admin/affiliate/${a.affiliate_id}/payout`, {
                                        amount_usd: parseFloat(affPayout.amount), note: ''
                                      })
                                      setAffPayoutMsg({ type:'ok', text:`تم دفع $${affPayout.amount}` })
                                      setAffPayout({ id: null, amount: '', note: '' })
                                      loadAffStats(affSearch)
                                    } catch (err) {
                                      setAffPayoutMsg({ type:'err', text: err.response?.data?.detail || 'خطأ' })
                                    }
                                  }}
                                  className="px-2 py-1 bg-green-700 hover:bg-green-600 text-white text-xs rounded">
                                  ✓
                                </button>
                                <button onClick={() => setAffPayout({ id: null, amount: '', note: '' })}
                                  className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded">
                                  ✕
                                </button>
                              </div>
                            ) : (
                              <button
                                disabled={a.pending_balance_usd <= 0}
                                onClick={() => setAffPayout({ id: a.affiliate_id, amount: a.pending_balance_usd.toFixed(2), note: '' })}
                                className="px-3 py-1 bg-green-900/40 hover:bg-green-800/50 disabled:opacity-30 disabled:cursor-not-allowed text-green-400 text-xs rounded-lg transition">
                                دفع
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                      {!affStats.affiliates?.length && (
                        <tr><td colSpan={7} className="text-center py-8 text-gray-500">لا توجد بيانات</td></tr>
                      )}
                    </tbody>
                  </table>
                  <div className="px-4 py-2 border-t border-gray-700 text-xs text-gray-500">
                    إجمالي: {affStats.total} مسوّق
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Settings ── */}
          {tab === 'settings' && (
            <div>
              <h1 className="text-xl font-bold mb-6">إعدادات الموقع</h1>

              {settingMsg && (
                <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mb-4 ${settingMsg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
                  {settingMsg.type==='ok'?<CheckCircle size={14}/>:<AlertTriangle size={14}/>} {settingMsg.text}
                </div>
              )}

              <div className="grid md:grid-cols-3 gap-6 max-w-5xl">

                {/* Site Settings */}
                <div className="space-y-4">
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">إعدادات الموقع</h2>
                  {[
                    { key:'site_name',            label:'اسم الموقع', mono:false },
                    { key:'usdt_wallet',          label:'عنوان محفظة USDT (TRC20)', mono:true },
                    { key:'telegram_bot_username', label:'اسم بوت تيليجرام (بدون @)', mono:false },
                  ].map(f => {
                    const meta = siteSettings[f.key] || {}
                    return (
                      <div key={f.key} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                        <label className="block text-sm text-gray-300 font-medium mb-1">{f.label}</label>
                        {meta.description && <p className="text-xs text-gray-500 mb-2">{meta.description}</p>}
                        <div className="flex gap-2">
                          <input type="text" value={settingEdits[f.key] ?? ''}
                            onChange={e => setSettingEdits(s => ({...s, [f.key]: e.target.value}))}
                            className={`flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 ${f.mono?'font-mono':''}`}
                            dir="ltr" />
                          <button disabled={settingSaving === f.key} onClick={() => saveSetting(f.key)}
                            className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                            {settingSaving === f.key ? <RefreshCw size={13} className="animate-spin"/> : <CheckCircle size={13}/>} حفظ
                          </button>
                        </div>
                      </div>
                    )
                  })}

                  {/* Logo Upload */}
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <label className="block text-sm text-gray-300 font-medium mb-1">شعار الموقع</label>
                    <p className="text-xs text-gray-500 mb-3">PNG / JPG / SVG / WebP — يُعرض في شريط التنقل</p>

                    {/* Current logo preview */}
                    {settingEdits['site_logo_url'] && (
                      <div className="mb-3 flex items-center gap-3 bg-gray-800 rounded-lg px-3 py-2">
                        <img
                          src={settingEdits['site_logo_url'].startsWith('http') ? settingEdits['site_logo_url'] : `${API}${settingEdits['site_logo_url']}`}
                          alt="logo"
                          className="h-8 object-contain rounded"
                          onError={e => { e.target.style.display = 'none' }}
                        />
                        <span className="text-xs text-gray-400 font-mono truncate flex-1">{settingEdits['site_logo_url']}</span>
                      </div>
                    )}

                    {/* Upload button */}
                    <label className={`flex items-center justify-center gap-2 w-full cursor-pointer border-2 border-dashed rounded-lg px-4 py-3 text-sm transition
                      ${logoUploading ? 'border-blue-700 text-blue-400 cursor-wait' : 'border-gray-700 text-gray-400 hover:border-blue-600 hover:text-blue-400'}`}>
                      {logoUploading
                        ? <><RefreshCw size={14} className="animate-spin"/> جاري الرفع...</>
                        : <><Upload size={14}/> اختر صورة للرفع</>}
                      <input type="file" accept="image/*" className="hidden" onChange={uploadLogo} disabled={logoUploading} />
                    </label>

                    {logoMsg && (
                      <p className={`mt-2 text-xs flex items-center gap-1 ${logoMsg.type==='ok' ? 'text-green-400' : 'text-red-400'}`}>
                        {logoMsg.type==='ok' ? <CheckCircle size={12}/> : <AlertTriangle size={12}/>} {logoMsg.text}
                      </p>
                    )}
                  </div>

                  {/* TwelveData */}
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-300 font-medium">TwelveData (احتياطي)</p>
                        <p className="text-xs text-gray-500 mt-0.5">يُستخدم فقط عند التفعيل</p>
                      </div>
                      <button
                        onClick={() => {
                          const cur = siteSettings['twelvedata_enabled']?.value === 'true'
                          saveSetting('twelvedata_enabled', cur ? 'false' : 'true')
                        }}
                        className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition ${
                          siteSettings['twelvedata_enabled']?.value === 'true'
                            ? 'bg-green-900/40 border-green-700 text-green-400'
                            : 'bg-gray-800 border-gray-700 text-gray-400'
                        }`}>
                        {siteSettings['twelvedata_enabled']?.value === 'true'
                          ? <><ToggleRight size={14}/> مفعّل</>
                          : <><ToggleLeft size={14}/> معطّل</>}
                      </button>
                    </div>
                    <div className="flex gap-2">
                      <input type="text" value={settingEdits['twelvedata_api_key'] ?? ''}
                        onChange={e => setSettingEdits(s => ({...s, twelvedata_api_key: e.target.value}))}
                        placeholder="API Key..."
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
                        dir="ltr" />
                      <button disabled={settingSaving === 'twelvedata_api_key'} onClick={() => saveSetting('twelvedata_api_key')}
                        className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-3 py-2 rounded-lg transition">
                        {settingSaving === 'twelvedata_api_key' ? <RefreshCw size={13} className="animate-spin"/> : <CheckCircle size={13}/>} حفظ
                      </button>
                    </div>
                  </div>
                </div>

                {/* حدود الاستخدام */}
                <div className="space-y-3">
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">حدود الاستخدام</h2>
                  {[
                    { key:'trial_chat_limit',       label:'محادثات التجريبي',   badge:'تجريبي', color:'gray' },
                    { key:'trial_analysis_limit',   label:'تحليلات التجريبي',   badge:'تجريبي', color:'gray' },
                    { key:'weekly_chat_limit',      label:'محادثات الأسبوعي',   badge:'أسبوعي', color:'blue' },
                    { key:'weekly_analysis_limit',  label:'تحليلات الأسبوعي',  badge:'أسبوعي', color:'blue' },
                    { key:'monthly_chat_limit',     label:'محادثات الشهري',     badge:'شهري',   color:'purple' },
                    { key:'monthly_analysis_limit', label:'تحليلات الشهري',    badge:'شهري',   color:'purple' },
                  ].map(f => (
                    <div key={f.key} className="bg-gray-900 border border-gray-800 rounded-xl p-3 flex items-center gap-2">
                      <div className="flex-1">
                        <p className="text-xs text-gray-400 mb-1">{f.label}</p>
                        <input type="number" min="0" value={settingEdits[f.key] ?? (siteSettings[f.key]?.value || '')}
                          onChange={e => setSettingEdits(s => ({...s, [f.key]: e.target.value}))}
                          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                          dir="ltr" />
                      </div>
                      <button disabled={settingSaving === f.key} onClick={() => saveSetting(f.key)}
                        className="mt-4 flex items-center bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-2.5 py-2 rounded-lg transition">
                        {settingSaving === f.key ? <RefreshCw size={12} className="animate-spin"/> : <CheckCircle size={12}/>}
                      </button>
                    </div>
                  ))}
                </div>

                {/* Admin Account */}
                <div>
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">حساب الإدارة</h2>
                  <form onSubmit={saveAdminProfile} className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
                    <p className="text-xs text-gray-500">البريد الحالي: <span className="text-gray-300">{user?.email}</span></p>

                    <div>
                      <label className="block text-xs text-gray-400 mb-1">كلمة المرور الحالية *</label>
                      <input type="password" required value={adminProfile.current_password}
                        onChange={e => setAdminProfile(p => ({...p, current_password: e.target.value}))}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        dir="ltr" placeholder="••••••••" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">البريد الإلكتروني الجديد</label>
                      <input type="email" value={adminProfile.new_email}
                        onChange={e => setAdminProfile(p => ({...p, new_email: e.target.value}))}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        dir="ltr" placeholder="admin@qafeel.com" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">كلمة المرور الجديدة</label>
                      <input type="password" value={adminProfile.new_password}
                        onChange={e => setAdminProfile(p => ({...p, new_password: e.target.value}))}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        dir="ltr" placeholder="8 أحرف على الأقل" />
                    </div>

                    {adminProfileMsg && (
                      <div className={`flex items-center gap-2 text-xs rounded-lg px-3 py-2 ${adminProfileMsg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
                        {adminProfileMsg.type==='ok'?<CheckCircle size={12}/>:<AlertTriangle size={12}/>} {adminProfileMsg.text}
                      </div>
                    )}

                    <button type="submit" disabled={adminProfileSaving}
                      className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm py-2 rounded-lg transition">
                      {adminProfileSaving ? <RefreshCw size={13} className="animate-spin"/> : <CheckCircle size={13}/>}
                      حفظ بيانات الحساب
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  )
}
