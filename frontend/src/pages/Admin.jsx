import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import {
  Users, CreditCard, BarChart2, CheckCircle, XCircle, Clock,
  Search, Plus, Trash2, ToggleLeft, ToggleRight, TrendingUp,
  DollarSign, Activity, RefreshCw, Calendar,
  X, ExternalLink, Shield, AlertTriangle, Settings, Mail, Upload, Signal, Send,
  FileText, TrendingUp as TrendUp, Bell, Sparkles
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
  // Renewal state
  const [renewDays, setRenewDays]       = useState(30)
  const [renewPlan, setRenewPlan]       = useState('monthly')
  const [renewReason, setRenewReason]   = useState('')
  const [renewNotify, setRenewNotify]   = useState(true)

  const doAction = async (action, payload = {}) => {
    setLoading(action); setMsg(null)
    try {
      if (action === 'reset_trial') {
        await axios.post(`${API}/api/v1/admin/users/${u.id}/reset-trial`)
        setMsg({ type:'ok', text:'تم إعادة تعيين التجربة' })
      } else if (action === 'renew') {
        const res = await axios.post(`${API}/api/v1/admin/users/${u.id}/renew`, {
          days: renewDays, plan: renewPlan, reason: renewReason, notify_telegram: renewNotify,
        })
        setMsg({ type:'ok', text:`✅ تم التجديد حتى ${res.data.new_end?.slice(0,10)} | إشعار: ${res.data.notified?'أُرسل':'لا Telegram'}` })
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
              ['تفعيل البريد', u.is_verified ? '✅ مُفعّل' : '⏳ غير مُفعّل'],
              ['IP التسجيل', u.registration_ip ? (u.dup_ip_count > 1 ? `⚠️ ${u.registration_ip} (مشترك مع ${u.dup_ip_count - 1})` : u.registration_ip) : '—'],
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

            {/* Renewal */}
            <div className="bg-gray-800/50 rounded-xl p-3 border border-green-700/30">
              <p className="text-xs text-green-400 font-semibold mb-3 flex items-center gap-1">
                <RefreshCw size={12}/> إعادة تنشيط / تجديد الاشتراك
              </p>
              <div className="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">المدة (يوم)</label>
                  <input type="number" min="1" max="365" value={renewDays}
                    onChange={e => setRenewDays(Number(e.target.value))}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-green-500 text-center" dir="ltr"/>
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">الباقة</label>
                  <select value={renewPlan} onChange={e => setRenewPlan(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-green-500">
                    <option value="monthly">شهري</option>
                    <option value="weekly">أسبوعي</option>
                  </select>
                </div>
              </div>
              <div className="mb-2">
                <label className="text-xs text-gray-400 block mb-1">السبب (اختياري)</label>
                <input type="text" value={renewReason} placeholder="مكافأة / استثناء / خطأ دفع..."
                  onChange={e => setRenewReason(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-green-500"/>
              </div>
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                  <input type="checkbox" checked={renewNotify} onChange={e => setRenewNotify(e.target.checked)}
                    className="accent-green-500"/>
                  إشعار تلغرام للمستخدم
                </label>
                <button disabled={loading==='renew'}
                  onClick={() => doAction('renew')}
                  className="flex items-center gap-1 text-xs bg-green-700 hover:bg-green-600 text-white px-4 py-1.5 rounded-lg transition font-semibold">
                  {loading==='renew' ? '...' : <><RefreshCw size={11}/> تجديد</>}
                </button>
              </div>
            </div>

            {/* Extend */}
            <div>
              <p className="text-xs text-gray-400 mb-2">تمديد بسيط</p>
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
  const [settingsSubTab, setSettingsSubTab] = useState('site')
  const [showBotToken, setShowBotToken] = useState(false)
  const [showStripeSecret, setShowStripeSecret] = useState(false)
  const [showStripeWebhook, setShowStripeWebhook] = useState(false)

  const [adminProfile, setAdminProfile] = useState({ current_password:'', new_email:'', new_password:'' })
  const [adminProfileSaving, setAdminProfileSaving] = useState(false)
  const [adminProfileMsg, setAdminProfileMsg] = useState(null)

  // Email state
  const [emailForm, setEmailForm] = useState({ subject:'', body:'', user_id:'' })
  const [emailSending, setEmailSending] = useState(false)
  const [emailMsg, setEmailMsg] = useState(null)

  // Messages state
  const [messageForm, setMessageForm] = useState({ title:'', message:'', user_ids:[] })
  const [messageSending, setMessageSending] = useState(false)
  const [messageMsg, setMessageMsg] = useState(null)

  // Performance Report state
  const [reportDays, setReportDays]       = useState(7)
  const [reportData, setReportData]       = useState(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportSending, setReportSending] = useState(false)
  const [reportMsg, setReportMsg]         = useState(null)

  const loadReport = async (days) => {
    setReportLoading(true); setReportData(null); setReportMsg(null)
    try {
      const r = await axios.get(`${API}/api/v1/admin/performance-report`, { params: { days } })
      setReportData(r.data)
    } catch { setReportMsg({ type:'err', text:'فشل جلب التقرير' }) }
    finally { setReportLoading(false) }
  }

  const sendReport = async (channel) => {
    setReportSending(true); setReportMsg(null)
    try {
      const r = await axios.post(`${API}/api/v1/admin/performance-report/send`, {
        days: reportDays, channel, include_expired: true
      })
      setReportMsg({ type:'ok', text: r.data.message })
    } catch (err) { setReportMsg({ type:'err', text: err.response?.data?.detail || 'فشل الإرسال' }) }
    finally { setReportSending(false) }
  }

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

  // Signals state
  const [adminSignals, setAdminSignals] = useState([])
  const [signalsLoading, setSignalsLoading] = useState(false)
  const [outcomeForm, setOutcomeForm] = useState({})
  const [openOutcome, setOpenOutcome] = useState(null)

  // "show more" limits
  const [usersLimit,    setUsersLimit]    = useState(10)
  const [paymentsLimit, setPaymentsLimit] = useState(10)
  const [signalsLimit,  setSignalsLimit]  = useState(10)
  const [reportLimit,   setReportLimit]   = useState(10)
  const [affLimit,      setAffLimit]      = useState(10)

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
    if (tab === 'signals')   loadAdminSignals()
    if (tab === 'messages')  loadUsers()  // للحصول على قائمة المستخدمين للاختيار
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
      const raw = overrideValue !== undefined ? overrideValue : settingEdits[key]
      const value = raw !== undefined && raw !== null ? String(raw) : (siteSettings[key]?.value ?? '')
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

  const sendMessage = async (e) => {
    e.preventDefault(); setMessageSending(true); setMessageMsg(null)
    try {
      const payload = { title: messageForm.title || undefined, message: messageForm.message }
      if (messageForm.user_ids.length > 0) payload.user_ids = messageForm.user_ids.map(id => parseInt(id))
      const r = await axios.post(`${API}/api/v1/admin/telegram/send`, payload)
      setMessageMsg({ type:'ok', text: r.data.message })
      setMessageForm(f => ({ ...f, title:'', message:'', user_ids:[] }))
    } catch (err) { setMessageMsg({ type:'err', text: err.response?.data?.detail || 'فشل الإرسال' }) }
    finally { setMessageSending(false) }
  }

  const loadAdminSignals = async () => {
    setSignalsLoading(true)
    try {
      const r = await axios.get(`${API}/api/v1/admin/signals?status=all&limit=100`)
      setAdminSignals(r.data.signals || [])
    } catch (e) {}
    finally { setSignalsLoading(false) }
  }

  const submitOutcome = async (signalId) => {
    const form = outcomeForm[signalId] || {}
    if (!form.status) return
    setOutcomeForm(prev => ({ ...prev, [signalId]: { ...prev[signalId], submitting: true, msg: '' } }))
    try {
      await axios.patch(`${API}/api/v1/admin/signals/${signalId}/outcome`, {
        status: form.status,
        closed_price: form.closed_price ? parseFloat(form.closed_price) : undefined,
      })
      setOutcomeForm(prev => ({ ...prev, [signalId]: { status: '', submitting: false, msg: 'ok' } }))
      setOpenOutcome(null)
      loadAdminSignals()
    } catch (e) {
      setOutcomeForm(prev => ({ ...prev, [signalId]: { ...prev[signalId], submitting: false, msg: e.response?.data?.detail || 'خطأ' } }))
    }
  }

  const filteredUsers = users.filter(u => planFilter === 'all' || u.plan === planFilter)

  const ShowMore = ({ total, limit, onMore }) => total <= limit ? null : (
    <button onClick={onMore}
      className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 text-sm text-gray-400 hover:text-white bg-gray-800/60 hover:bg-gray-800 rounded-xl transition-colors border border-gray-700/50">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
      عرض المزيد ({total - limit} متبقية)
    </button>
  )

  const TABS = [
    { key:'stats',      icon:Activity,      label:'إحصائيات' },
    { key:'users',      icon:Users,         label:'المستخدمون' },
    { key:'payments',   icon:CreditCard,    label:'المدفوعات' },
    { key:'markets',    icon:BarChart2,     label:'الأسواق' },
    { key:'signals',    icon:TrendingUp,    label:'الإشارات' },
    { key:'reports',    icon:FileText,      label:'تقارير الأداء' },
    { key:'affiliate',  icon:TrendUp,       label:'الأفلييت' },
    { key:'messages',   icon:Send,          label:'رسائل تيليجرام' },
    { key:'email',      icon:Mail,          label:'البريد' },
    { key:'settings',   icon:Settings,      label:'الإعدادات' },
    { key:'diagnostic', icon:AlertTriangle, label:'تشخيص النظام' },
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
            <button onClick={() => navigate('/strategies')}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-amber-400/90 hover:text-amber-300 hover:bg-amber-950/30 border border-amber-900/40 mt-2">
              <Sparkles size={16}/>Strategy Builder
            </button>
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
                  <button onClick={() => { setUsersLimit(10); loadUsers() }} className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1.5 rounded-lg">بحث</button>
                  {/* Bulk Renewal */}
                  <button
                    onClick={async () => {
                      if (!confirm('تجديد جميع المستخدمين المنتهيين (30 يوم / شهري) مع إشعار تلغرام؟')) return
                      try {
                        const r = await axios.post(`${API}/api/v1/admin/users/bulk-renew`, {
                          days: 30, plan: 'monthly', reason: 'تجديد جماعي من الأدمن', notify_telegram: true,
                        })
                        alert(`✅ تم تجديد ${r.data.renewed} مستخدم | إشعارات: ${r.data.notified}`)
                        loadUsers()
                      } catch (e) {
                        alert('خطأ: ' + (e.response?.data?.detail || e.message))
                      }
                    }}
                    className="flex items-center gap-1 text-xs bg-green-800/60 hover:bg-green-700/60 text-green-300 border border-green-700/40 px-3 py-1.5 rounded-lg transition">
                    <RefreshCw size={12}/> تجديد المنتهيين
                  </button>
                  {/* Bulk Trial Reset */}
                  <button
                    onClick={async () => {
                      if (!confirm('إعادة تعيين كريدت التجربة لجميع المستخدمين التجريبيين؟\nسيحصل كل مستخدم تجريبي على الحدود المضبوطة في الإعدادات.')) return
                      const withNotify = confirm('إرسال إشعار تلغرام للمستخدمين؟')
                      try {
                        const r = await axios.post(`${API}/api/v1/admin/users/bulk-reset-trial`, { notify_telegram: withNotify })
                        alert(`✅ تم تحديث ${r.data.reset} مستخدم تجريبي (${r.data.analysis_limit} تحليل / ${r.data.chat_limit} محادثة) | إشعارات: ${r.data.notified}`)
                        loadUsers()
                      } catch (e) {
                        alert('خطأ: ' + (e.response?.data?.detail || e.message))
                      }
                    }}
                    className="flex items-center gap-1 text-xs bg-yellow-900/40 hover:bg-yellow-800/50 text-yellow-300 border border-yellow-700/40 px-3 py-1.5 rounded-lg transition">
                    <RefreshCw size={12}/> تحديث التجريبي للكل
                  </button>
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
                      <th className="text-right py-2 px-3">IP</th>
                      <th className="text-right py-2 px-3">تسجيل</th>
                      <th className="text-right py-2 px-3">إجراء</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {filteredUsers.slice(0, usersLimit).map(u => (
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
                        <td className="py-2.5 px-3 text-xs font-mono">
                          {u.registration_ip ? (
                            <span className={`flex items-center gap-1 ${u.dup_ip_count > 1 ? 'text-yellow-400' : 'text-gray-500'}`}>
                              {u.dup_ip_count > 1 && (
                                <AlertTriangle size={11} title={`مشترك مع ${u.dup_ip_count - 1} حساب آخر بنفس الـ IP`} />
                              )}
                              {u.registration_ip}
                            </span>
                          ) : <span className="text-gray-600">—</span>}
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
                <ShowMore total={filteredUsers.length} limit={usersLimit} onMore={() => setUsersLimit(l => l + 10)} />
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
                {payments.slice(0, paymentsLimit).map(p => (
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
                <ShowMore total={payments.length} limit={paymentsLimit} onMore={() => setPaymentsLimit(l => l + 10)} />
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
                      <option value="gulf">🕌 أسواق خليجية</option>
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

          {/* ── Messages ── */}
          {tab === 'messages' && (
            <div className="max-w-2xl">
              <h1 className="text-xl font-bold mb-6 flex items-center gap-2"><Mail size={20} className="text-green-400"/> إرسال رسائل تيليجرام</h1>

              {messageMsg && (
                <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mb-4 ${messageMsg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
                  {messageMsg.type==='ok'?<CheckCircle size={14}/>:<AlertTriangle size={14}/>} {messageMsg.text}
                </div>
              )}

              {/* ── قوالب جاهزة ── */}
              {(() => {
                const TEMPLATES = [
                  {
                    icon: '🔔', label: 'تحديث جديد',
                    title: '🔔 تحديث جديد — Qaffel AI',
                    message: `🔔 *تحديث جديد على المنصة!*\n\nالسلام عليكم 👋\n\nيسعدنا إطلاق تحديث جديد على منصة Qaffel AI يشمل:\n\n✅ \n✅ \n✅ \n\nجرّب الميزات الجديدة الآن 🚀`,
                  },
                  {
                    icon: '🚀', label: 'إطلاق خدمة',
                    title: '🚀 خدمة جديدة — Qaffel AI',
                    message: `🚀 *إطلاق خدمة جديدة!*\n\nالسلام عليكم 👋\n\nيسعدنا الإعلان عن إطلاق *[اسم الخدمة]* الجديدة!\n\n📌 ما الجديد؟\n— \n\n🎯 كيف تستفيد؟\n— \n\nافتح المنصة الآن وجرّبها 👇`,
                  },
                  {
                    icon: '⚠️', label: 'تنبيه مهم',
                    title: '⚠️ تنبيه مهم',
                    message: `⚠️ *تنبيه مهم من Qaffel AI*\n\nالسلام عليكم،\n\nنودّ إعلامكم بما يلي:\n\n📌 \n\nشكراً لتفهمكم 🙏`,
                  },
                  {
                    icon: '🎁', label: 'عرض خاص',
                    title: '🎁 عرض خاص محدود',
                    message: `🎁 *عرض خاص لفترة محدودة!*\n\nالسلام عليكم 👋\n\nبمناسبة [المناسبة]، نقدّم لكم:\n\n💥 *[تفاصيل العرض]*\n⏰ صالح حتى: [التاريخ]\n\nاستفد الآن 👇`,
                  },
                  {
                    icon: '📢', label: 'إعلان عام',
                    title: '📢 إعلان من Qaffel AI',
                    message: `📢 *إعلان مهم*\n\nالسلام عليكم ورحمة الله 🤲\n\n`,
                  },
                  {
                    icon: '🛠', label: 'صيانة',
                    title: '🛠 صيانة مجدولة',
                    message: `🛠 *إشعار صيانة*\n\nالسلام عليكم،\n\nنودّ إعلامكم بأن المنصة ستكون في وضع الصيانة:\n\n🕐 الوقت: \n⏱ المدة المتوقعة: \n\nنعتذر عن أي إزعاج. نعمل لتحسين تجربتكم 💪`,
                  },
                ]
                return (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-300 mb-2">⚡ قوالب جاهزة</label>
                    <div className="grid grid-cols-3 gap-2">
                      {TEMPLATES.map(t => (
                        <button key={t.label} type="button"
                          onClick={() => setMessageForm(f => ({ ...f, title: t.title, message: t.message }))}
                          className="flex flex-col items-center gap-1 px-2 py-2.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-green-600/50 rounded-xl text-xs text-gray-300 hover:text-white transition-all"
                        >
                          <span className="text-lg leading-none">{t.icon}</span>
                          <span>{t.label}</span>
                        </button>
                      ))}
                    </div>
                    <p className="text-xs text-gray-600 mt-1.5">اضغط على القالب لتعبئة الحقول — يمكنك التعديل بعدها</p>
                  </div>
                )
              })()}

              <form onSubmit={sendMessage} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">العنوان الرئيسي (اختياري)</label>
                  <input
                    type="text" value={messageForm.title}
                    onChange={e => setMessageForm(f => ({ ...f, title: e.target.value }))}
                    placeholder="مثال: Qaffel Ai"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-green-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">نص الرسالة</label>
                  <textarea
                    required rows={6} value={messageForm.message}
                    onChange={e => setMessageForm(f => ({ ...f, message: e.target.value }))}
                    placeholder="اكتب الرسالة التي تريد إرسالها..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white resize-y"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">المستخدمون (اتركه فارغاً للإرسال للجميع)</label>
                  <select
                    multiple value={messageForm.user_ids}
                    onChange={e => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value)
                      setMessageForm(f => ({ ...f, user_ids: selected }))
                    }}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white h-32"
                  >
                    {users.filter(u => u.telegram_username).map(u => (
                      <option key={u.id} value={u.id}>
                        {u.full_name || u.email} (@{u.telegram_username})
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">يمكن اختيار عدة مستخدمين (Ctrl+Click)</p>
                </div>

                <div className="flex gap-3">
                  <button type="submit" disabled={messageSending}
                    className="flex items-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white px-6 py-2 rounded-lg text-sm transition">
                    {messageSending ? <RefreshCw size={14} className="animate-spin"/> : <Mail size={14}/>}
                    {messageSending ? 'جاري الإرسال...' : messageForm.user_ids.length > 0 ? `إرسال للمحددين (${messageForm.user_ids.length})` : `إرسال للجميع (${users.filter(u => u.telegram_username).length})`}
                  </button>
                  <button type="button" onClick={() => { if (!users.length) loadUsers() }}
                    className="text-xs text-gray-400 hover:text-white px-3 py-2 rounded-lg hover:bg-gray-800">
                    تحديث قائمة المستخدمين
                  </button>
                </div>
              </form>

              <div className="mt-4 p-4 bg-gray-900 border border-gray-800 rounded-xl text-xs text-gray-500 space-y-1">
                <p>📱 يرسل الرسائل عبر تيليجرام بوت</p>
                <p>⚙️ يتطلب ضبط <span className="font-mono text-gray-400">TELEGRAM_BOT_TOKEN</span></p>
                <p>🚀 الإرسال يتم في الخلفية للمستخدمين الذين لديهم telegram_id</p>
                <p>💬 يدعم HTML formatting في الرسائل</p>
              </div>

              {/* ── Re-engagement Campaign ── */}
              <ReEngagementCampaign />
            </div>
          )}

          {/* ── Signals ── */}
          {tab === 'signals' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h1 className="text-xl font-bold flex items-center gap-2">
                  <TrendingUp size={20} className="text-blue-400"/>
                  إدارة الإشارات
                </h1>
                <button
                  onClick={loadAdminSignals}
                  className="flex items-center gap-2 text-xs bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded-lg transition"
                >
                  <RefreshCw size={13}/> تحديث
                </button>
              </div>

              {signalsLoading ? (
                <div className="text-gray-400 text-sm flex items-center gap-2">
                  <RefreshCw size={14} className="animate-spin"/> جاري التحميل...
                </div>
              ) : adminSignals.length === 0 ? (
                <p className="text-gray-500 text-center py-12">لا توجد إشارات بعد</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-400 border-b border-gray-800">
                        <th className="pb-2 text-right font-medium pr-2">ID</th>
                        <th className="pb-2 text-right font-medium">المستخدم</th>
                        <th className="pb-2 text-right font-medium">الزوج</th>
                        <th className="pb-2 text-right font-medium">النوع</th>
                        <th className="pb-2 text-right font-medium">الحالة</th>
                        <th className="pb-2 text-right font-medium">الدخول</th>
                        <th className="pb-2 text-right font-medium">SL</th>
                        <th className="pb-2 text-right font-medium">TP1</th>
                        <th className="pb-2 text-right font-medium">النقاط</th>
                        <th className="pb-2 text-right font-medium">التاريخ</th>
                        <th className="pb-2 text-right font-medium">النتيجة</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/60">
                      {adminSignals.slice(0, signalsLimit).map(s => {
                        const typeColor = s.signal_type === 'BUY'
                          ? 'bg-green-900/50 text-green-300'
                          : s.signal_type === 'SELL'
                          ? 'bg-red-900/50 text-red-300'
                          : 'bg-gray-700 text-gray-300'

                        const statusMap = {
                          ACTIVE:  'bg-green-900/40 text-green-300',
                          PENDING: 'bg-yellow-900/40 text-yellow-300',
                          TP1_HIT: 'bg-blue-900/40 text-blue-300',
                          TP2_HIT: 'bg-purple-900/40 text-purple-300',
                          SL_HIT:  'bg-red-900/40 text-red-300',
                          EXPIRED: 'bg-gray-700/60 text-gray-400',
                        }
                        const statusCls = statusMap[s.status] || 'bg-gray-700 text-gray-400'
                        const ptColor = (pts) => pts > 0 ? 'text-green-400' : pts < 0 ? 'text-red-400' : 'text-gray-400'
                        const isOpen = openOutcome === s.id
                        const form = outcomeForm[s.id] || {}

                        return (
                          <>
                            <tr key={s.id} className="hover:bg-gray-800/40 transition-colors">
                              <td className="py-2 pr-2 text-gray-500">{s.id}</td>
                              <td className="py-2 text-gray-400 max-w-[120px] truncate" title={s.user_email}>{s.user_email?.split('@')[0] ?? `#${s.user_id}`}</td>
                              <td className="py-2 font-semibold text-white">{s.market}</td>
                              <td className="py-2">
                                <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${typeColor}`}>{s.signal_type}</span>
                              </td>
                              <td className="py-2">
                                <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${statusCls}`}>{s.status}</span>
                              </td>
                              <td className="py-2 text-gray-300 font-mono">{s.entry_price?.toFixed(5) ?? '-'}</td>
                              <td className="py-2 text-red-400 font-mono">{s.stop_loss?.toFixed(5) ?? '-'}</td>
                              <td className="py-2 text-green-400 font-mono">{s.take_profit_1?.toFixed(5) ?? '-'}</td>
                              <td className={`py-2 font-semibold font-mono ${ptColor(s.points_earned)}`}>
                                {s.points_earned != null ? (s.points_earned > 0 ? '+' : '') + s.points_earned : '—'}
                              </td>
                              <td className="py-2 text-gray-500">{s.created_at?.slice(0, 10) ?? '-'}</td>
                              <td className="py-2">
                                {!['TP1_HIT','TP2_HIT','SL_HIT','EXPIRED'].includes(s.status) && (
                                  <button
                                    onClick={() => setOpenOutcome(isOpen ? null : s.id)}
                                    className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-2 py-1 rounded transition"
                                  >
                                    تحديد النتيجة
                                  </button>
                                )}
                              </td>
                            </tr>
                            {isOpen && (
                              <tr key={`form-${s.id}`} className="bg-gray-900/70">
                                <td colSpan={10} className="py-3 px-4">
                                  <div className="flex items-center gap-3 flex-wrap">
                                    <select
                                      value={form.status || ''}
                                      onChange={e => setOutcomeForm(prev => ({ ...prev, [s.id]: { ...prev[s.id], status: e.target.value } }))}
                                      className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    >
                                      <option value="">-- اختر النتيجة --</option>
                                      <option value="TP1_HIT">TP1 HIT</option>
                                      <option value="TP2_HIT">TP2 HIT</option>
                                      <option value="SL_HIT">SL HIT</option>
                                      <option value="EXPIRED">EXPIRED</option>
                                    </select>
                                    <input
                                      type="number"
                                      step="0.00001"
                                      placeholder="سعر الإغلاق (اختياري)"
                                      value={form.closed_price || ''}
                                      onChange={e => setOutcomeForm(prev => ({ ...prev, [s.id]: { ...prev[s.id], closed_price: e.target.value } }))}
                                      className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-1.5 text-xs w-40 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                      dir="ltr"
                                    />
                                    <button
                                      onClick={() => submitOutcome(s.id)}
                                      disabled={form.submitting || !form.status}
                                      className="text-xs bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg transition"
                                    >
                                      {form.submitting ? 'جاري...' : 'حفظ'}
                                    </button>
                                    <button
                                      onClick={() => setOpenOutcome(null)}
                                      className="text-xs text-gray-400 hover:text-white px-2 py-1.5 rounded-lg transition"
                                    >
                                      إلغاء
                                    </button>
                                    {form.msg && form.msg !== 'ok' && (
                                      <span className="text-xs text-red-400">{form.msg}</span>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        )
                      })}
                    </tbody>
                  </table>
                  <ShowMore total={adminSignals.length} limit={signalsLimit} onMore={() => setSignalsLimit(l => l + 10)} />
                </div>
              )}
            </div>
          )}

          {/* ── Performance Reports ── */}
          {tab === 'reports' && (
            <div className="max-w-4xl">
              <h1 className="text-xl font-bold mb-6 flex items-center gap-2">
                <FileText size={20} className="text-yellow-400"/> تقارير الأداء
              </h1>

              {reportMsg && (
                <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mb-4 ${reportMsg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
                  {reportMsg.type==='ok'?<CheckCircle size={14}/>:<AlertTriangle size={14}/>} {reportMsg.text}
                </div>
              )}

              {/* فلتر الفترة */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-5">
                <h2 className="text-sm font-semibold text-gray-300 mb-3">اختر الفترة الزمنية</h2>
                <div className="flex flex-wrap gap-2 mb-4">
                  {[
                    { label:'اليوم',     days:1 },
                    { label:'3 أيام',   days:3 },
                    { label:'أسبوع',    days:7 },
                    { label:'أسبوعان', days:14 },
                    { label:'شهر',     days:30 },
                  ].map(opt => (
                    <button key={opt.days} onClick={() => setReportDays(opt.days)}
                      className={`px-4 py-2 rounded-lg text-sm transition ${reportDays===opt.days?'bg-yellow-600 text-white':'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'}`}>
                      {opt.label}
                    </button>
                  ))}
                  <input type="number" min="1" max="90" value={reportDays}
                    onChange={e => setReportDays(Number(e.target.value))}
                    className="w-20 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white text-center"
                    placeholder="أيام"
                  />
                </div>
                <button onClick={() => loadReport(reportDays)} disabled={reportLoading}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-sm transition">
                  {reportLoading ? <RefreshCw size={14} className="animate-spin"/> : <FileText size={14}/>}
                  {reportLoading ? 'جاري التحميل...' : 'معاينة التقرير'}
                </button>
              </div>

              {/* معاينة التقرير */}
              {reportData && (
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-5">
                  <h2 className="text-sm font-semibold text-gray-300 mb-4">
                    📊 تقرير آخر {reportDays} يوم
                  </h2>

                  {/* الإحصائيات */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                    {[
                      { label:'إجمالي الصفقات', value: reportData.total,                      color:'text-white' },
                      { label:'رابحة',           value: reportData.wins,                       color:'text-green-400' },
                      { label:'خاسرة',           value: reportData.losses,                     color:'text-red-400' },
                      { label:'نسبة الربح',      value: `${reportData.win_rate}%`,             color: reportData.win_rate>=50?'text-green-400':'text-red-400' },
                    ].map(s => (
                      <div key={s.label} className="bg-gray-800 rounded-lg p-3 text-center">
                        <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                        <div className="text-xs text-gray-500 mt-1">{s.label}</div>
                      </div>
                    ))}
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3 text-center mb-5">
                    <span className="text-gray-400 text-sm">إجمالي النقاط: </span>
                    <span className={`text-xl font-bold ${reportData.total_points>=0?'text-green-400':'text-red-400'}`}>
                      {reportData.total_points>=0?'+':''}{reportData.total_points}
                    </span>
                  </div>

                  {/* جدول الصفقات */}
                  {reportData.signals.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-gray-500 border-b border-gray-800">
                            <th className="pb-2 text-right">الزوج</th>
                            <th className="pb-2 text-right">النوع</th>
                            <th className="pb-2 text-right">النتيجة</th>
                            <th className="pb-2 text-right">النقاط</th>
                            <th className="pb-2 text-right">ثقة</th>
                            <th className="pb-2 text-right">التاريخ</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportData.signals.slice(0, reportLimit).map((s,i) => {
                            const isWin = ['TP1_HIT','TP2_HIT'].includes(s.status)
                            const statusLabel = {TP1_HIT:'هدف 1 ✅',TP2_HIT:'هدف 2 🏆',SL_HIT:'وقف ❌'}[s.status]||s.status
                            return (
                              <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                                <td className="py-2 font-medium">{s.market}</td>
                                <td className="py-2"><span className={`text-xs px-2 py-0.5 rounded ${s.signal_type==='BUY'?'bg-green-900/50 text-green-300':'bg-red-900/50 text-red-300'}`}>{s.signal_type==='BUY'?'شراء':'بيع'}</span></td>
                                <td className="py-2 text-sm">{statusLabel}</td>
                                <td className={`py-2 font-bold ${isWin?'text-green-400':'text-red-400'}`}>{s.points>=0?'+':''}{s.points}</td>
                                <td className="py-2 text-gray-400">{s.ai_confidence}%</td>
                                <td className="py-2 text-gray-500 text-xs">{s.exit_date}</td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                      <ShowMore total={reportData.signals.length} limit={reportLimit} onMore={() => setReportLimit(l => l + 10)} />
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">لا توجد صفقات مغلقة في هذه الفترة</p>
                  )}

                  {/* أزرار الإرسال */}
                  <div className="flex gap-3 mt-6 pt-4 border-t border-gray-800">
                    <button onClick={() => sendReport('telegram')} disabled={reportSending}
                      className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-sm transition font-medium">
                      {reportSending ? <RefreshCw size={14} className="animate-spin"/> : <Send size={14}/>}
                      إرسال عبر تيليجرام
                    </button>
                    <button onClick={() => sendReport('email')} disabled={reportSending}
                      className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-sm transition font-medium">
                      {reportSending ? <RefreshCw size={14} className="animate-spin"/> : <Mail size={14}/>}
                      إرسال عبر الإيميل
                    </button>
                  </div>
                </div>
              )}

              {!reportData && !reportLoading && (
                <div className="text-center py-12 text-gray-600">
                  <FileText size={40} className="mx-auto mb-3 opacity-30"/>
                  <p>اختر الفترة الزمنية ثم اضغط "معاينة التقرير"</p>
                </div>
              )}
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
                      {affStats.affiliates?.slice(0, affLimit).map(a => (
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
                  <ShowMore total={affStats.affiliates?.length || 0} limit={affLimit} onMore={() => setAffLimit(l => l + 10)} />
                </div>
              )}
            </div>
          )}

          {/* ── Settings ── */}
          {tab === 'settings' && (
            <div>
              <h1 className="text-xl font-bold mb-4">إعدادات الموقع</h1>

              {/* Sub-tab nav */}
              <div className="flex gap-1 mb-6 border-b border-gray-800">
                {[
                  { id: 'site',      icon: '🌐', label: 'الموقع' },
                  { id: 'plans',     icon: '💰', label: 'الباقات' },
                  { id: 'affiliate', icon: '🔗', label: 'الإحالات' },
                  { id: 'limits',    icon: '⚙️', label: 'الحدود' },
                  { id: 'account',   icon: '👤', label: 'الحساب' },
                ].map(st => (
                  <button key={st.id} onClick={() => setSettingsSubTab(st.id)}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition -mb-px ${
                      settingsSubTab === st.id
                        ? 'border-blue-500 text-white'
                        : 'border-transparent text-gray-500 hover:text-gray-300'
                    }`}>
                    <span>{st.icon}</span> {st.label}
                  </button>
                ))}
              </div>

              {settingMsg && (
                <div className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 mb-4 ${settingMsg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
                  {settingMsg.type==='ok'?<CheckCircle size={14}/>:<AlertTriangle size={14}/>} {settingMsg.text}
                </div>
              )}

              {/* ── site ── */}
              {settingsSubTab === 'site' && (
                <div className="grid md:grid-cols-2 gap-6 max-w-3xl">
                  <div className="space-y-4">
                    <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">إعدادات الموقع</h2>
                    {[
                      { key:'site_name',             label:'اسم الموقع', mono:false },
                      { key:'usdt_wallet',           label:'عنوان محفظة USDT (TRC20)', mono:true },
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

                    {/* ── Bot Token (sensitive) ───────────────────────────── */}
                    <div className="bg-gray-900 border border-orange-900/40 rounded-xl p-4">
                      <label className="block text-sm text-gray-300 font-medium mb-1">توكن بوت تيليجرام</label>
                      <p className="text-xs text-gray-500 mb-2">يُستخدم لإرسال الإشارات والإشعارات · يُخزَّن في قاعدة البيانات ويُلغي قيمة .env</p>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <input
                            type={showBotToken ? 'text' : 'password'}
                            value={settingEdits['telegram_bot_token'] ?? ''}
                            onChange={e => setSettingEdits(s => ({...s, telegram_bot_token: e.target.value}))}
                            placeholder="123456789:AAF..."
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:ring-1 focus:ring-orange-500 pr-10"
                            dir="ltr"
                          />
                          <button type="button" onClick={() => setShowBotToken(v => !v)}
                            className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 text-xs px-1">
                            {showBotToken ? '🙈' : '👁'}
                          </button>
                        </div>
                        <button disabled={settingSaving === 'telegram_bot_token'} onClick={() => saveSetting('telegram_bot_token')}
                          className="flex items-center gap-1 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                          {settingSaving === 'telegram_bot_token' ? <RefreshCw size={13} className="animate-spin"/> : <CheckCircle size={13}/>} حفظ
                        </button>
                      </div>
                      {siteSettings['telegram_bot_token']?.value && (
                        <p className="mt-2 text-xs text-green-400 flex items-center gap-1"><CheckCircle size={11}/> توكن مخزَّن في قاعدة البيانات · يُستخدم حالياً</p>
                      )}
                    </div>

                    {/* ── Stripe (sensitive) ───────────────────────────── */}
                    <div className="bg-gray-900 border border-orange-900/40 rounded-xl p-4 space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="block text-sm text-gray-300 font-medium">تفعيل الدفع بالبطاقة</label>
                          <p className="text-xs text-gray-500">يُظهر/يُخفي زر الدفع بالبطاقة بصفحة الأسعار</p>
                        </div>
                        <button
                          onClick={() => saveSetting('stripe_enabled', (siteSettings['stripe_enabled']?.value ?? 'true') === 'false' ? 'true' : 'false')}
                          disabled={settingSaving === 'stripe_enabled'}
                          className={`w-11 h-6 rounded-full flex items-center px-0.5 transition-colors flex-shrink-0 ${
                            (siteSettings['stripe_enabled']?.value ?? 'true') !== 'false'
                              ? 'bg-green-600 justify-end'
                              : 'bg-gray-700 justify-start'
                          }`}
                        >
                          <span className="w-5 h-5 rounded-full bg-white" />
                        </button>
                      </div>

                      <div>
                        <label className="block text-sm text-gray-300 font-medium mb-1">Stripe Publishable Key</label>
                        <p className="text-xs text-gray-500 mb-2">من Stripe Dashboard → Developers → API keys (يبدأ بـ pk_)</p>
                        <div className="flex gap-2">
                          <input type="text"
                            value={settingEdits['stripe_publishable_key'] ?? ''}
                            onChange={e => setSettingEdits(s => ({...s, stripe_publishable_key: e.target.value}))}
                            placeholder="pk_live_..."
                            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:ring-1 focus:ring-orange-500"
                            dir="ltr" />
                          <button disabled={settingSaving === 'stripe_publishable_key'} onClick={() => saveSetting('stripe_publishable_key')}
                            className="flex items-center gap-1 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                            {settingSaving === 'stripe_publishable_key' ? <RefreshCw size={13} className="animate-spin"/> : <CheckCircle size={13}/>} حفظ
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm text-gray-300 font-medium mb-1">Stripe Secret Key</label>
                        <p className="text-xs text-gray-500 mb-2">من Stripe Dashboard → Developers → API keys · يُخزَّن في قاعدة البيانات ويُلغي قيمة .env</p>
                        <div className="flex gap-2">
                          <div className="relative flex-1">
                            <input
                              type={showStripeSecret ? 'text' : 'password'}
                              value={settingEdits['stripe_secret_key'] ?? ''}
                              onChange={e => setSettingEdits(s => ({...s, stripe_secret_key: e.target.value}))}
                              placeholder="sk_live_..."
                              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:ring-1 focus:ring-orange-500 pr-10"
                              dir="ltr"
                            />
                            <button type="button" onClick={() => setShowStripeSecret(v => !v)}
                              className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 text-xs px-1">
                              {showStripeSecret ? '🙈' : '👁'}
                            </button>
                          </div>
                          <button disabled={settingSaving === 'stripe_secret_key'} onClick={() => saveSetting('stripe_secret_key')}
                            className="flex items-center gap-1 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                            {settingSaving === 'stripe_secret_key' ? <RefreshCw size={13} className="animate-spin"/> : <CheckCircle size={13}/>} حفظ
                          </button>
                        </div>
                        {siteSettings['stripe_secret_key']?.value && (
                          <p className="mt-2 text-xs text-green-400 flex items-center gap-1"><CheckCircle size={11}/> مخزَّن في قاعدة البيانات · يُستخدم حالياً</p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm text-gray-300 font-medium mb-1">Stripe Webhook Signing Secret</label>
                        <p className="text-xs text-gray-500 mb-2">من Stripe Dashboard → Webhooks → Signing secret (whsec_...)</p>
                        <div className="flex gap-2">
                          <div className="relative flex-1">
                            <input
                              type={showStripeWebhook ? 'text' : 'password'}
                              value={settingEdits['stripe_webhook_secret'] ?? ''}
                              onChange={e => setSettingEdits(s => ({...s, stripe_webhook_secret: e.target.value}))}
                              placeholder="whsec_..."
                              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:ring-1 focus:ring-orange-500 pr-10"
                              dir="ltr"
                            />
                            <button type="button" onClick={() => setShowStripeWebhook(v => !v)}
                              className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 text-xs px-1">
                              {showStripeWebhook ? '🙈' : '👁'}
                            </button>
                          </div>
                          <button disabled={settingSaving === 'stripe_webhook_secret'} onClick={() => saveSetting('stripe_webhook_secret')}
                            className="flex items-center gap-1 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                            {settingSaving === 'stripe_webhook_secret' ? <RefreshCw size={13} className="animate-spin"/> : <CheckCircle size={13}/>} حفظ
                          </button>
                        </div>
                        {siteSettings['stripe_webhook_secret']?.value && (
                          <p className="mt-2 text-xs text-green-400 flex items-center gap-1"><CheckCircle size={11}/> مخزَّن في قاعدة البيانات · يُستخدم حالياً</p>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
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
                </div>
              )}

              {/* ── plans ── */}
              {settingsSubTab === 'plans' && (
                <div className="max-w-2xl space-y-3">
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    <DollarSign size={13}/> الباقات والأسعار
                  </h2>
                  <p className="text-xs text-gray-600">اتركها فارغة لاستخدام القيم الافتراضية · التغييرات تظهر فوراً في صفحات الأسعار</p>
                  {[
                    { key: 'weekly',  label: 'الأسبوعية', color: 'blue',   defaultPrice: '7',  defaultDays: '7'  },
                    { key: 'monthly', label: 'الشهرية',   color: 'purple', defaultPrice: '30', defaultDays: '30' },
                  ].map(({ key, label, color, defaultPrice, defaultDays }) => (
                    <div key={key} className={`bg-gray-900 border border-${color}-900/40 rounded-xl p-4 space-y-3`}>
                      <div className="flex items-center justify-between">
                        <h3 className={`text-xs font-bold text-${color}-400 uppercase tracking-wider`}>{label}</h3>
                        <span className="text-xs text-gray-600">الافتراضي: ${defaultPrice} / {defaultDays} يوم</span>
                      </div>

                      {/* Price + Days */}
                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex items-center gap-1">
                          <div className="flex-1">
                            <label className="text-xs text-gray-500 mb-1 block">السعر ($)</label>
                            <input type="number" min="0" step="0.01"
                              value={settingEdits[`plan_${key}_price`] ?? (siteSettings[`plan_${key}_price`]?.value || '')}
                              onChange={e => setSettingEdits(s => ({...s, [`plan_${key}_price`]: e.target.value}))}
                              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white font-mono"
                              placeholder={defaultPrice} dir="ltr" />
                          </div>
                          <button disabled={settingSaving===`plan_${key}_price`} onClick={() => saveSetting(`plan_${key}_price`)}
                            className="mt-5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-2 py-2 rounded-lg transition">
                            {settingSaving===`plan_${key}_price`?<RefreshCw size={12} className="animate-spin"/>:<CheckCircle size={12}/>}
                          </button>
                        </div>
                        <div className="flex items-center gap-1">
                          <div className="flex-1">
                            <label className="text-xs text-gray-500 mb-1 block">المدة (أيام)</label>
                            <input type="number" min="1"
                              value={settingEdits[`plan_${key}_days`] ?? (siteSettings[`plan_${key}_days`]?.value || '')}
                              onChange={e => setSettingEdits(s => ({...s, [`plan_${key}_days`]: e.target.value}))}
                              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white font-mono"
                              placeholder={defaultDays} dir="ltr" />
                          </div>
                          <button disabled={settingSaving===`plan_${key}_days`} onClick={() => saveSetting(`plan_${key}_days`)}
                            className="mt-5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-2 py-2 rounded-lg transition">
                            {settingSaving===`plan_${key}_days`?<RefreshCw size={12} className="animate-spin"/>:<CheckCircle size={12}/>}
                          </button>
                        </div>
                      </div>

                      {/* Names */}
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { fkey:`plan_${key}_name`,    label:'الاسم (ع)', dir:'rtl', ph: key==='weekly'?'الأسبوعية':'الشهرية' },
                          { fkey:`plan_${key}_name_en`, label:'Name (EN)', dir:'ltr', ph: key==='weekly'?'Weekly':'Monthly'     },
                        ].map(f => (
                          <div key={f.fkey} className="flex items-center gap-1">
                            <div className="flex-1">
                              <label className="text-xs text-gray-500 mb-1 block">{f.label}</label>
                              <input type="text"
                                value={settingEdits[f.fkey] ?? (siteSettings[f.fkey]?.value || '')}
                                onChange={e => setSettingEdits(s => ({...s, [f.fkey]: e.target.value}))}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white"
                                placeholder={f.ph} dir={f.dir} />
                            </div>
                            <button disabled={settingSaving===f.fkey} onClick={() => saveSetting(f.fkey)}
                              className="mt-5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-2 py-1.5 rounded-lg transition">
                              {settingSaving===f.fkey?<RefreshCw size={11} className="animate-spin"/>:<CheckCircle size={11}/>}
                            </button>
                          </div>
                        ))}
                      </div>

                      {/* Features — AR + EN */}
                      {[
                        { fkey:`plan_${key}_features`,    label:'المميزات (JSON عربي)', dir:'ltr', ph:'["تحليل ICT/SMC", "تنبيهات Telegram"]' },
                        { fkey:`plan_${key}_features_en`, label:'Features (JSON EN)',   dir:'ltr', ph:'["Full ICT/SMC Analysis", "Telegram Alerts"]' },
                      ].map(f => (
                        <div key={f.fkey} className="flex items-start gap-1">
                          <div className="flex-1">
                            <label className="text-xs text-gray-500 mb-1 block">{f.label}</label>
                            <textarea rows={2}
                              value={settingEdits[f.fkey] ?? (siteSettings[f.fkey]?.value || '')}
                              onChange={e => setSettingEdits(s => ({...s, [f.fkey]: e.target.value}))}
                              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white font-mono resize-none"
                              placeholder={f.ph} dir={f.dir} />
                          </div>
                          <button disabled={settingSaving===f.fkey} onClick={() => saveSetting(f.fkey)}
                            className="mt-5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-2 py-1.5 rounded-lg transition">
                            {settingSaving===f.fkey?<RefreshCw size={11} className="animate-spin"/>:<CheckCircle size={11}/>}
                          </button>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}

              {/* ── affiliate ── */}
              {settingsSubTab === 'affiliate' && (
                <div className="max-w-xl space-y-4">
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">إعدادات الإحالات</h2>

                  {/* min payout */}
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <label className="block text-sm text-gray-300 font-medium mb-1">الحد الأدنى للسحب (USDT)</label>
                    <div className="flex gap-2">
                      <input type="number" min="0" step="0.5"
                        value={settingEdits['affiliate_min_payout_usd'] ?? (siteSettings['affiliate_min_payout_usd']?.value || '10')}
                        onChange={e => setSettingEdits(s => ({...s, affiliate_min_payout_usd: e.target.value}))}
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" dir="ltr" />
                      <button disabled={settingSaving==='affiliate_min_payout_usd'} onClick={() => saveSetting('affiliate_min_payout_usd')}
                        className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                        {settingSaving==='affiliate_min_payout_usd'?<RefreshCw size={13} className="animate-spin"/>:<CheckCircle size={13}/>} حفظ
                      </button>
                    </div>
                  </div>

                  {/* Commission Tier 1 Rate */}
                  <div className="bg-gray-900 border border-blue-900/40 rounded-xl p-4">
                    <label className="block text-sm text-blue-300 font-medium mb-1">عمولة المرحلة الأولى % (Bronze)</label>
                    <p className="text-xs text-gray-500 mb-2">الافتراضي: 5%</p>
                    <div className="flex gap-2">
                      <input type="number" min="1" max="50" step="0.5"
                        value={settingEdits['affiliate_tier1_rate'] ?? (siteSettings['affiliate_tier1_rate']?.value || '5')}
                        onChange={e => setSettingEdits(s => ({...s, affiliate_tier1_rate: e.target.value}))}
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" dir="ltr" />
                      <button disabled={settingSaving==='affiliate_tier1_rate'} onClick={() => saveSetting('affiliate_tier1_rate')}
                        className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                        {settingSaving==='affiliate_tier1_rate'?<RefreshCw size={13} className="animate-spin"/>:<CheckCircle size={13}/>} حفظ
                      </button>
                    </div>
                  </div>

                  {/* Commission Tier 2 Rate */}
                  <div className="bg-gray-900 border border-yellow-900/40 rounded-xl p-4">
                    <label className="block text-sm text-yellow-300 font-medium mb-1">عمولة المرحلة الثانية % (Gold)</label>
                    <p className="text-xs text-gray-500 mb-2">الافتراضي: 15%</p>
                    <div className="flex gap-2">
                      <input type="number" min="1" max="50" step="0.5"
                        value={settingEdits['affiliate_tier2_rate'] ?? (siteSettings['affiliate_tier2_rate']?.value || '15')}
                        onChange={e => setSettingEdits(s => ({...s, affiliate_tier2_rate: e.target.value}))}
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" dir="ltr" />
                      <button disabled={settingSaving==='affiliate_tier2_rate'} onClick={() => saveSetting('affiliate_tier2_rate')}
                        className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                        {settingSaving==='affiliate_tier2_rate'?<RefreshCw size={13} className="animate-spin"/>:<CheckCircle size={13}/>} حفظ
                      </button>
                    </div>
                  </div>

                  {/* Tier 2 Threshold */}
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <label className="block text-sm text-gray-300 font-medium mb-1">عدد الإحالات للترقية للذهبي</label>
                    <p className="text-xs text-gray-500 mb-2">الافتراضي: 25 إحالة</p>
                    <div className="flex gap-2">
                      <input type="number" min="1" step="1"
                        value={settingEdits['affiliate_tier2_threshold'] ?? (siteSettings['affiliate_tier2_threshold']?.value || '25')}
                        onChange={e => setSettingEdits(s => ({...s, affiliate_tier2_threshold: e.target.value}))}
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" dir="ltr" />
                      <button disabled={settingSaving==='affiliate_tier2_threshold'} onClick={() => saveSetting('affiliate_tier2_threshold')}
                        className="flex items-center gap-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
                        {settingSaving==='affiliate_tier2_threshold'?<RefreshCw size={13} className="animate-spin"/>:<CheckCircle size={13}/>} حفظ
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-gray-600">* تأخذ التغييرات مفعولها على الاشتراكات الجديدة فقط</p>

                  {/* ── Redemption Tiers ── */}
                  <div className="mt-6">
                    <h2 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider mb-3">🏆 مستويات استبدال النقاط</h2>
                    <RedemptionTiersAdmin saveSetting={saveSetting} siteSettings={siteSettings} settingEdits={settingEdits} setSettingEdits={setSettingEdits} settingSaving={settingSaving} />
                  </div>
                </div>
              )}

              {/* ── limits ── */}
              {settingsSubTab === 'limits' && (
                <div className="max-w-md space-y-3">
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">حدود الاستخدام</h2>
                  <p className="text-xs text-gray-600">0 = غير محدود</p>
                  {[
                    { key:'trial_chat_limit',       label:'محادثات التجريبي',   color:'gray' },
                    { key:'trial_analysis_limit',   label:'تحليلات التجريبي',   color:'gray' },
                    { key:'weekly_chat_limit',      label:'محادثات الأسبوعي',   color:'blue' },
                    { key:'weekly_analysis_limit',  label:'تحليلات الأسبوعي',   color:'blue' },
                    { key:'monthly_chat_limit',     label:'محادثات الشهري',     color:'purple' },
                    { key:'monthly_analysis_limit', label:'تحليلات الشهري',     color:'purple' },
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

                  {/* Bulk Reset Trial */}
                  <div className="mt-4 bg-yellow-900/20 border border-yellow-700/40 rounded-xl p-4 space-y-3">
                    <h3 className="text-sm font-semibold text-yellow-300 flex items-center gap-2">
                      <RefreshCw size={13}/> تحديث التجريبي للكل
                    </h3>
                    <p className="text-xs text-gray-400">يعيد تعيين كريدت التجربة لجميع المستخدمين التجريبيين وفق الحدود المضبوطة أعلاه.</p>
                    <div className="flex gap-2">
                      <button
                        onClick={async () => {
                          if (!confirm('إعادة تعيين التجربة لجميع المستخدمين التجريبيين؟')) return
                          try {
                            const r = await axios.post(`${API}/api/v1/admin/users/bulk-reset-trial`, { notify_telegram: false })
                            setSettingMsg({ type:'ok', text:`✅ تم تحديث ${r.data.reset} مستخدم (${r.data.analysis_limit} تحليل / ${r.data.chat_limit} محادثة)` })
                          } catch(e) { setSettingMsg({ type:'err', text: e.response?.data?.detail || 'خطأ' }) }
                        }}
                        className="flex-1 flex items-center justify-center gap-1.5 text-xs bg-yellow-700/40 hover:bg-yellow-600/50 text-yellow-200 px-3 py-2 rounded-lg transition">
                        <RefreshCw size={12}/> بدون إشعار
                      </button>
                      <button
                        onClick={async () => {
                          if (!confirm('إعادة تعيين التجربة لجميع المستخدمين التجريبيين مع إرسال إشعار تلغرام؟')) return
                          try {
                            const r = await axios.post(`${API}/api/v1/admin/users/bulk-reset-trial`, { notify_telegram: true })
                            setSettingMsg({ type:'ok', text:`✅ تم تحديث ${r.data.reset} مستخدم | إشعارات: ${r.data.notified}` })
                          } catch(e) { setSettingMsg({ type:'err', text: e.response?.data?.detail || 'خطأ' }) }
                        }}
                        className="flex-1 flex items-center justify-center gap-1.5 text-xs bg-blue-700/40 hover:bg-blue-600/50 text-blue-200 px-3 py-2 rounded-lg transition">
                        <Bell size={12}/> مع إشعار تلغرام
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* ── account ── */}
              {settingsSubTab === 'account' && (
                <div className="max-w-sm">
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
              )}
            </div>
          )}

          {/* ── Diagnostic ── */}
          {tab === 'diagnostic' && <DiagnosticPanel />}

        </main>
      </div>
    </div>
  )
}

// ── System Diagnostic Panel ───────────────────────────────────────────────────
function DiagnosticPanel() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const run = async () => {
    setLoading(true); setError(null); setData(null)
    try {
      const res = await axios.get(`${API}/api/v1/admin/diagnostic`)
      setData(res.data)
    } catch(e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const verdictStyle = (v) => {
    if (!v) return ''
    if (v.includes('VALID'))     return 'bg-blue-900/30 border-blue-600 text-blue-300'
    if (v.includes('FILTERING')) return 'bg-orange-900/30 border-orange-600 text-orange-300'
    if (v.includes('BUG'))       return 'bg-red-900/30 border-red-600 text-red-300'
    return 'bg-gray-800 border-gray-600 text-gray-300'
  }

  const stateColor = (s) => {
    if (s === 'TRENDING')  return 'text-green-400'
    if (s === 'VOLATILE')  return 'text-yellow-400'
    if (s === 'TRAP')      return 'text-red-400'
    return 'text-gray-400'
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <AlertTriangle size={20} className="text-orange-400" /> تشخيص النظام
          </h1>
          <p className="text-gray-500 text-sm mt-1">تحليل كامل للـ pipeline — يكتشف سبب غياب الإشارات</p>
        </div>
        <button onClick={run} disabled={loading}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition">
          {loading ? <RefreshCw size={15} className="animate-spin" /> : <Activity size={15} />}
          {loading ? 'جاري التشخيص...' : 'تشغيل التشخيص'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300 text-sm flex items-center gap-2">
          <XCircle size={16} /> {error}
        </div>
      )}

      {loading && (
        <div className="bg-gray-800 border border-gray-700 rounded-2xl p-10 text-center">
          <RefreshCw size={28} className="animate-spin text-blue-400 mx-auto mb-3" />
          <p className="text-gray-400 text-sm">يحلل {10} رموز عبر كامل الـ pipeline...</p>
          <p className="text-gray-600 text-xs mt-1">قد يستغرق 15-30 ثانية</p>
        </div>
      )}

      {data && (
        <div className="space-y-5">

          {/* VERDICT */}
          <div className={`border rounded-2xl p-5 ${verdictStyle(data.step7_diagnosis?.verdict)}`}>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl font-bold">{data.step7_diagnosis?.verdict}</span>
            </div>
            <p className="text-sm opacity-80">{data.step7_diagnosis?.reason}</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-xs">
              {Object.entries(data.step7_diagnosis?.supporting_data || {}).map(([k,v]) => (
                <div key={k} className="bg-black/20 rounded-lg p-2">
                  <div className="opacity-60 mb-0.5">{k.replace(/_/g,' ')}</div>
                  <div className="font-bold">{String(v)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* STEP 1 — Market Activity */}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700 flex items-center justify-between">
              <h2 className="font-semibold text-sm">Step 1 — حالة الأسواق</h2>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${data.step1_market_activity?.market_global_state === 'ACTIVE' ? 'bg-green-900/40 text-green-400' : 'bg-red-900/40 text-red-400'}`}>
                {data.step1_market_activity?.market_global_state}
              </span>
            </div>
            <div className="p-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700">
                    {['رمز','حالة','تذبذب','BOS↑','BOS↓','Sweep','Breakout','ATR%'].map(h => (
                      <th key={h} className="text-right pb-2 pr-3 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.step1_market_activity?.symbols || {}).map(([sym, s]) => (
                    <tr key={sym} className="border-b border-gray-700/40">
                      <td className="py-2 pr-3 font-bold text-white">{sym}</td>
                      {s.error ? (
                        <td colSpan={7} className="py-2 text-red-400">{s.error}</td>
                      ) : (
                        <>
                          <td className={`py-2 pr-3 font-semibold ${stateColor(s.market_state)}`}>{s.market_state}</td>
                          <td className="py-2 pr-3 text-gray-400">{s.volatility}</td>
                          <td className="py-2 pr-3 text-green-400">{s.bos_bull}</td>
                          <td className="py-2 pr-3 text-red-400">{s.bos_bear}</td>
                          <td className={`py-2 pr-3 ${s.sweep_detected > 0 ? 'text-yellow-400' : 'text-gray-600'}`}>{s.sweep_detected}</td>
                          <td className={`py-2 pr-3 ${s.breakout_attempts >= 3 ? 'text-orange-400' : 'text-gray-500'}`}>{s.breakout_attempts}</td>
                          <td className="py-2 pr-3 text-gray-400">{s.atr_pct}%</td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* STEP 2 — Pipeline Trace */}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700">
              <h2 className="font-semibold text-sm">Step 2 — Pipeline Trace</h2>
            </div>
            <div className="p-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700">
                    {['رمز','نتيجة','مرحلة الرفض','السبب','Δ','Δ مطلوب','R/R','R/R min'].map(h => (
                      <th key={h} className="text-right pb-2 pr-3 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data.step2_pipeline_trace || []).map((t,i) => (
                    <tr key={i} className="border-b border-gray-700/40">
                      <td className="py-2 pr-3 font-bold">{t.symbol}</td>
                      <td className={`py-2 pr-3 font-semibold ${t.decision === 'PASSED' ? 'text-green-400' : 'text-red-400'}`}>{t.decision || t.error}</td>
                      <td className="py-2 pr-3 text-orange-400 text-xs">{t.failed_stage || '—'}</td>
                      <td className="py-2 pr-3 text-gray-400 max-w-[200px] truncate" title={t.reason}>{t.reason || '—'}</td>
                      <td className={`py-2 pr-3 font-mono ${(t.delta||0) >= (t.required_delta||20) ? 'text-green-400' : 'text-red-400'}`}>{t.delta ?? '—'}</td>
                      <td className="py-2 pr-3 font-mono text-gray-400">{t.required_delta ?? '—'}</td>
                      <td className={`py-2 pr-3 font-mono ${t.rr && t.min_rr && t.rr >= t.min_rr ? 'text-green-400' : 'text-red-400'}`}>{t.rr ?? '—'}</td>
                      <td className="py-2 pr-3 font-mono text-gray-400">{t.min_rr ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* STEP 3 — Rejection Analysis */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
              <h2 className="font-semibold text-sm mb-4">Step 3 — توزيع الرفض</h2>
              <div className="space-y-2 text-xs">
                {[
                  { l: 'إجمالي محلل', v: data.step3_rejection_analysis?.total_analyzed },
                  { l: 'اجتاز', v: data.step3_rejection_analysis?.total_passed, cls: 'text-green-400' },
                  { l: 'مرفوض', v: data.step3_rejection_analysis?.total_rejected, cls: 'text-red-400' },
                  { l: 'نسبة النجاح', v: data.step3_rejection_analysis?.pass_rate },
                  { l: 'متوسط Delta', v: data.step3_rejection_analysis?.avg_delta },
                  { l: 'متوسط R/R', v: data.step3_rejection_analysis?.avg_rr },
                  { l: 'أكثر سبب رفض', v: data.step3_rejection_analysis?.most_common_rejection, cls: 'text-orange-400 font-mono' },
                ].map(({l,v,cls}) => (
                  <div key={l} className="flex justify-between items-center py-1 border-b border-gray-700/40">
                    <span className="text-gray-400">{l}</span>
                    <span className={cls || 'text-white font-semibold'}>{String(v ?? '—')}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
              <h2 className="font-semibold text-sm mb-4">توزيع أسباب الرفض</h2>
              <div className="space-y-2 text-xs">
                {Object.entries(data.step3_rejection_analysis?.rejection_distribution || {}).map(([reason, pct]) => (
                  <div key={reason}>
                    <div className="flex justify-between mb-1">
                      <span className="text-gray-400 font-mono truncate max-w-[200px]">{reason}</span>
                      <span className="text-white font-semibold">{pct}</span>
                    </div>
                    <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full bg-orange-500 rounded-full" style={{width: pct}} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* STEP 4 — Stress Test */}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
            <h2 className="font-semibold text-sm mb-3">Step 4 — Stress Test (محاكاة Δ-5 / R/R-0.2)</h2>
            <div className="flex items-center gap-6 text-sm mb-3">
              <span>ستنجح لو خُففت الحدود: <strong className="text-yellow-400">{data.step4_stress_test?.signals_would_pass}</strong> / {data.step4_stress_test?.total}</span>
              <span className="text-gray-500 text-xs">{data.step4_stress_test?.quality_note}</span>
            </div>
            {(data.step4_stress_test?.details || []).length > 0 && (
              <div className="space-y-1 text-xs">
                {data.step4_stress_test.details.map((d,i) => (
                  <div key={i} className="bg-yellow-900/10 border border-yellow-700/30 rounded-lg px-3 py-2 flex flex-wrap gap-4">
                    <span className="font-bold text-yellow-400">{d.symbol}</span>
                    <span className="text-gray-400">Δ: {d.delta} → {d.relaxed_delta}</span>
                    <span className="text-gray-400">R/R: {d.rr} → {d.relaxed_rr}</span>
                    <span className="text-orange-400">يمر عبر: {d.passes_on}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* STEP 5+6 — Cooldown + Calibration */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
              <h2 className="font-semibold text-sm mb-3">Step 5 — Cooldown</h2>
              <div className="space-y-1.5 text-xs">
                {(data.step5_cooldown?.items || []).map((c,i) => (
                  <div key={i} className={`flex justify-between items-center py-1.5 border-b border-gray-700/40 ${c.active ? 'text-red-400' : 'text-gray-400'}`}>
                    <span className="font-bold">{c.symbol}</span>
                    <span>{c.active ? `🔒 ${Math.floor(c.remaining_sec/60)}د متبقي` : '✅ متاح'}</span>
                  </div>
                ))}
                <div className="pt-1 text-orange-400 font-semibold">محظور: {data.step5_cooldown?.blocked_count}</div>
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
              <h2 className="font-semibold text-sm mb-3">Step 6 — Auto Calibration</h2>
              <div className="space-y-1 text-xs mb-3">
                <div className="flex justify-between"><span className="text-gray-400">Winrate</span><span className="text-white">{((data.step6_auto_calibration?.engine_winrate||0)*100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Wins</span><span className="text-green-400">{data.step6_auto_calibration?.perf?.wins}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Losses</span><span className="text-red-400">{data.step6_auto_calibration?.perf?.losses}</span></div>
              </div>
              <div className="space-y-1.5 text-xs">
                {(data.step6_auto_calibration?.per_symbol || []).map((s,i) => (
                  <div key={i} className="flex justify-between items-center border-b border-gray-700/40 pb-1">
                    <span className="font-bold">{s.symbol}</span>
                    <span className={stateColor(s.market_state)}>{s.market_state}</span>
                    <span className="text-gray-400">Δ≥{s.delta}</span>
                    <span className="text-gray-400">RR≥{s.min_rr}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* STEP 8 — Action Plan */}
          <div className="bg-gray-800 border border-gray-700 rounded-2xl p-5">
            <h2 className="font-semibold text-sm mb-3">Step 8 — خطة العمل</h2>
            <div className="space-y-2">
              {(data.step8_action_plan?.actions || []).map((a,i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-gray-300">
                  <span className="text-blue-400 mt-0.5 shrink-0">→</span>
                  <span>{a}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Meta */}
          <div className="text-xs text-gray-600 text-left">
            Generated: {data.diagnostic_meta?.generated_at} | {data.diagnostic_meta?.elapsed_ms}ms
          </div>
        </div>
      )}
    </div>
  )
}

// ── Redemption Tiers Admin Component ──────────────────────────────────────────
function RedemptionTiersAdmin({ saveSetting, siteSettings, settingEdits, setSettingEdits, settingSaving }) {
  const DEFAULT = [
    { id:1, label:'تحليل مجاني',  points:20,   reward_type:'analysis', reward_value:1,  description:'تحليل واحد' },
    { id:2, label:'3 تحليلات',    points:50,   reward_type:'analysis', reward_value:3,  description:'3 تحليلات' },
    { id:3, label:'يوم اشتراك',   points:100,  reward_type:'days',     reward_value:1,  description:'يوم مجاني' },
    { id:4, label:'أسبوع اشتراك', points:500,  reward_type:'days',     reward_value:7,  description:'أسبوع مجاني' },
    { id:5, label:'شهر اشتراك',   points:2000, reward_type:'days',     reward_value:30, description:'شهر مجاني' },
  ]
  const key = 'redemption_tiers'
  const raw = settingEdits[key] ?? siteSettings[key]?.value ?? ''
  let tiers = DEFAULT
  try { if (raw) tiers = JSON.parse(raw) } catch {}

  const [localTiers, setLocalTiers] = useState(tiers)
  const updateTier = (idx, field, val) => {
    const t = localTiers.map((t, i) => i === idx ? { ...t, [field]: field==='points'||field==='reward_value' ? Number(val) : val } : t)
    setLocalTiers(t)
    setSettingEdits(s => ({ ...s, [key]: JSON.stringify(t) }))
  }
  const addTier = () => {
    const t = [...localTiers, { id: Date.now(), label:'جديد', points:100, reward_type:'analysis', reward_value:1, description:'' }]
    setLocalTiers(t); setSettingEdits(s => ({ ...s, [key]: JSON.stringify(t) }))
  }
  const removeTier = (idx) => {
    const t = localTiers.filter((_,i) => i !== idx)
    setLocalTiers(t); setSettingEdits(s => ({ ...s, [key]: JSON.stringify(t) }))
  }

  return (
    <div className="space-y-3">
      {localTiers.map((t, idx) => (
        <div key={t.id} className="bg-gray-900 border border-gray-800 rounded-xl p-3 grid grid-cols-5 gap-2 items-center text-xs">
          <input value={t.label} onChange={e => updateTier(idx,'label',e.target.value)}
            className="col-span-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white" placeholder="الاسم"/>
          <div className="flex items-center gap-1">
            <input type="number" value={t.points} onChange={e => updateTier(idx,'points',e.target.value)}
              className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-center" dir="ltr"/>
            <span className="text-gray-500">نقطة</span>
          </div>
          <select value={t.reward_type} onChange={e => updateTier(idx,'reward_type',e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white">
            <option value="analysis">تحليل</option>
            <option value="days">أيام</option>
          </select>
          <div className="flex items-center gap-1">
            <input type="number" value={t.reward_value} onChange={e => updateTier(idx,'reward_value',e.target.value)}
              className="w-14 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-center" dir="ltr"/>
            <span className="text-gray-500">{t.reward_type==='days'?'يوم':'×'}</span>
          </div>
          <button onClick={() => removeTier(idx)} className="text-red-500 hover:text-red-400 justify-self-end">✕</button>
        </div>
      ))}
      <div className="flex gap-2">
        <button onClick={addTier} className="text-xs text-blue-400 hover:text-blue-300 px-3 py-1.5 border border-blue-700/40 rounded-lg">+ إضافة مستوى</button>
        <button disabled={settingSaving===key} onClick={() => saveSetting(key)}
          className="flex items-center gap-1 bg-yellow-700 hover:bg-yellow-600 disabled:opacity-50 text-white text-xs px-4 py-1.5 rounded-lg transition">
          {settingSaving===key ? <RefreshCw size={11} className="animate-spin"/> : <CheckCircle size={11}/>} حفظ المستويات
        </button>
      </div>
    </div>
  )
}

// ── Re-engagement Campaign Component ──────────────────────────────────────────
const DEFAULT_REENG_MSGS = [
  {
    label: 'عرض تجديد',
    text: `🎯 مرحباً {name}!\n\nنفتقدك في Qaffel AI 💙\n\nاشتراكك انتهى — لكن لديك فرصة للعودة بـ <b>عرض خاص</b>!\n\n✅ إشارات ذهب يومية\n✅ تحليل ICT + Smart Money\n✅ تنبيهات فورية\n\nجدّد الآن وعُد للتداول الاحترافي 🚀`,
  },
  {
    label: 'تذكير بالنتائج',
    text: `📊 {name}، هل رأيت نتائجنا الأخيرة؟\n\nالأسبوع الماضي على Qaffel AI:\n🥇 XAUUSD: +$420\n🥇 BTCUSD: +2.3%\n\nاشتراكك منتهي — جدّده الآن ولا تفوّت الإشارات القادمة 🎯`,
  },
  {
    label: 'رسالة بسيطة',
    text: `👋 {name}\n\nاشتراكك في Qaffel AI انتهى.\n\nنحن هنا إذا قررت العودة — المنصة تنتظرك 💪`,
  },
]

function ReEngagementCampaign() {
  const [msg, setMsg]             = useState(DEFAULT_REENG_MSGS[0].text)
  const [intervalDays, setInterval] = useState(3)
  const [maxSends, setMaxSends]   = useState(3)
  const [expiredSince, setExpiredSince] = useState(0)
  const [includeTrial, setIncludeTrial] = useState(false)
  const [preview, setPreview]     = useState(null)
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState('')

  const doPreview = async () => {
    setLoading('preview'); setResult(null)
    try {
      const r = await axios.get(`${API}/api/v1/admin/reengagement/preview`, {
        params: { expired_since_days: expiredSince, include_trial: includeTrial }
      })
      setPreview(r.data)
    } catch (e) {
      setResult({ type:'err', text: e.response?.data?.detail || 'خطأ' })
    } finally { setLoading('') }
  }

  const doSend = async (dryRun = false) => {
    if (!dryRun && !confirm(`إرسال الرسالة لـ ${preview?.count ?? '?'} مستخدم؟`)) return
    setLoading('send'); setResult(null)
    try {
      const r = await axios.post(`${API}/api/v1/admin/reengagement/send`, {
        message: msg, interval_days: intervalDays, max_sends: maxSends,
        expired_since_days: expiredSince, include_trial: includeTrial, dry_run: dryRun,
      })
      setResult({ type:'ok', text: r.data.dry_run
        ? `معاينة: سيُرسل لـ ${r.data.would_send} مستخدم`
        : r.data.message
      })
    } catch (e) {
      setResult({ type:'err', text: e.response?.data?.detail || 'خطأ' })
    } finally { setLoading('') }
  }

  return (
    <div className="mt-8 bg-gray-900 border border-orange-800/30 rounded-2xl p-5">
      <h2 className="text-base font-bold text-orange-400 mb-1 flex items-center gap-2">
        <Send size={16}/> حملة إعادة الاستهداف — المنتهيين
      </h2>
      <p className="text-xs text-gray-500 mb-4">إرسال رسالة تيليجرام لجميع المستخدمين المنتهيين الذين لديهم حساب تيليجرام</p>

      {/* Quick templates */}
      <div className="flex gap-2 flex-wrap mb-3">
        {DEFAULT_REENG_MSGS.map(t => (
          <button key={t.label} onClick={() => setMsg(t.text)}
            className="text-xs px-3 py-1 rounded-lg border border-gray-700 text-gray-400 hover:border-orange-600 hover:text-orange-400 transition">
            {t.label}
          </button>
        ))}
      </div>

      {/* Message editor */}
      <div className="mb-3">
        <label className="block text-xs text-gray-400 mb-1">نص الرسالة <span className="text-orange-400">(يدعم {'{name}'} و HTML)</span></label>
        <textarea rows={6} value={msg} onChange={e => setMsg(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white font-mono resize-y focus:outline-none focus:ring-1 focus:ring-orange-500"
          dir="rtl"/>
      </div>

      {/* Settings row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">تكرار كل (يوم)</label>
          <input type="number" min="1" max="30" value={intervalDays}
            onChange={e => setInterval(Number(e.target.value))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white text-center" dir="ltr"/>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">حد الإرسال</label>
          <input type="number" min="1" max="10" value={maxSends}
            onChange={e => setMaxSends(Number(e.target.value))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white text-center" dir="ltr"/>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">منتهيون منذ (يوم، 0=الكل)</label>
          <input type="number" min="0" max="365" value={expiredSince}
            onChange={e => setExpiredSince(Number(e.target.value))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white text-center" dir="ltr"/>
        </div>
        <div className="flex items-end pb-1.5">
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input type="checkbox" checked={includeTrial} onChange={e => setIncludeTrial(e.target.checked)}
              className="accent-orange-500"/>
            شمل التجريبيين
          </label>
        </div>
      </div>

      {/* Feedback */}
      {result && (
        <div className={`flex items-center gap-2 text-xs rounded-lg px-3 py-2 mb-3 ${result.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
          {result.type==='ok'?<CheckCircle size={12}/>:<AlertTriangle size={12}/>} {result.text}
        </div>
      )}

      {/* Preview result */}
      {preview && (
        <div className="bg-gray-800 rounded-xl p-3 mb-3 text-xs text-gray-300">
          <p className="font-semibold text-white mb-1">معاينة: <span className="text-orange-400">{preview.count} مستخدم</span> مؤهل للإرسال</p>
          <div className="flex flex-wrap gap-1">
            {preview.users.slice(0,10).map(u => (
              <span key={u.id} className="bg-gray-700 rounded px-2 py-0.5">{u.name}</span>
            ))}
            {preview.count > 10 && <span className="text-gray-500">+{preview.count - 10} أخرين</span>}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        <button disabled={loading==='preview'} onClick={doPreview}
          className="flex items-center gap-1 text-xs border border-gray-600 text-gray-300 hover:border-gray-400 px-4 py-2 rounded-xl transition">
          {loading==='preview'?<RefreshCw size={11} className="animate-spin"/>:<Activity size={11}/>} معاينة القائمة
        </button>
        <button disabled={loading==='send'} onClick={() => doSend(true)}
          className="flex items-center gap-1 text-xs border border-orange-700/50 text-orange-400 hover:bg-orange-900/20 px-4 py-2 rounded-xl transition">
          اختبار (بدون إرسال)
        </button>
        <button disabled={loading==='send' || !msg.trim()} onClick={() => doSend(false)}
          className="flex items-center gap-1 text-xs bg-orange-700 hover:bg-orange-600 disabled:opacity-50 text-white px-5 py-2 rounded-xl transition font-semibold">
          {loading==='send'?<RefreshCw size={11} className="animate-spin"/>:<Send size={11}/>}
          إرسال الحملة
        </button>
      </div>
    </div>
  )
}
