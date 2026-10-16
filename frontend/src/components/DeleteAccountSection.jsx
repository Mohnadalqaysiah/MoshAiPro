/**
 * DeleteAccountSection (2026-10-16) — "منطقة الخطر" بصفحة الحساب: حذف الحساب من العميل نفسه.
 * الخادم (POST /api/v1/auth/delete-account) يمسح الهوية ويوقف الحساب؛ لا تراجع. DECISIONS.md 16/10.
 */
import { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { Trash2, AlertTriangle, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function DeleteAccountSection({ isAr }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  if (!user || user.role === 'admin') return null
  const hasPassword = user.has_password !== false
  const paid = ['weekly', 'monthly'].includes(user.plan) && (user.days_left ?? 0) > 0
  const word = isAr ? 'حذف' : 'DELETE'
  const ready = hasPassword ? password.length > 0 : confirm.trim() === word

  const submit = async () => {
    setBusy(true); setErr('')
    try {
      await axios.post(`${API}/api/v1/auth/delete-account`, hasPassword ? { password } : { confirm: confirm.trim() })
      logout()
      navigate('/', { replace: true })
    } catch (e) {
      setErr(e.response?.data?.detail || (isAr ? 'تعذّر حذف الحساب' : 'Could not delete the account'))
    } finally { setBusy(false) }
  }

  return (
    <div className="bg-red-950/20 border border-red-900/50 rounded-xl p-6">
      <h2 className="text-base font-semibold text-red-400 mb-2 flex items-center gap-2">
        <AlertTriangle size={16} /> {isAr ? 'منطقة الخطر' : 'Danger zone'}
      </h2>
      <p className="text-sm text-gray-400 mb-4 leading-relaxed">
        {isAr
          ? 'حذف الحساب نهائي ولا يمكن التراجع عنه: تُمسح بياناتك الشخصية (البريد، الاسم، الهاتف، ربط تلجرام) واستراتيجياتك ومفضلتك، ولن تصلك أي رسالة بعدها.'
          : 'Deleting your account is permanent: your personal data (email, name, phone, Telegram link), strategies and watchlist are erased, and you will receive no further messages.'}
      </p>
      <button onClick={() => { setOpen(true); setErr('') }}
        className="flex items-center gap-2 bg-red-600/90 hover:bg-red-600 px-5 py-2 rounded-lg text-sm font-medium transition text-white">
        <Trash2 size={14} /> {isAr ? 'حذف حسابي' : 'Delete my account'}
      </button>

      {open && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/70" onClick={() => !busy && setOpen(false)}>
          <div dir={isAr ? 'rtl' : 'ltr'} onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-gray-900 border border-red-900/60 rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white flex items-center gap-2"><AlertTriangle size={18} className="text-red-400" />
                {isAr ? 'تأكيد حذف الحساب' : 'Confirm account deletion'}</h3>
              <button onClick={() => !busy && setOpen(false)} className="text-gray-500 hover:text-white"><X size={18} /></button>
            </div>
            <ul className="text-sm text-gray-300 space-y-1.5 list-disc ps-5">
              <li>{isAr ? 'لا يمكن استرجاع الحساب بعد الحذف.' : 'The account cannot be restored.'}</li>
              <li>{isAr ? 'إذا سجّلت لاحقاً بنفس البريد، لن تحصل على تجربة مجانية جديدة.' : 'Signing up again with the same email will not give a new free trial.'}</li>
              {paid && (
                <li className="text-amber-300">
                  {isAr
                    ? `اشتراكك الحالي (متبقٍ ${user.days_left} يوم) ينتهي فوراً بالحذف، ولا يُسترد المبلغ.`
                    : `Your current subscription (${user.days_left} days left) ends immediately and is not refunded.`}
                </li>
              )}
            </ul>
            {hasPassword ? (
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">{isAr ? 'اكتب كلمة المرور للتأكيد' : 'Enter your password to confirm'}</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} dir="ltr"
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500" />
              </div>
            ) : (
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  {isAr ? <>اكتب كلمة <b className="text-white">«حذف»</b> للتأكيد</> : <>Type <b className="text-white">DELETE</b> to confirm</>}
                </label>
                <input value={confirm} onChange={(e) => setConfirm(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500" />
              </div>
            )}
            {err && <div className="text-sm text-red-400">{err}</div>}
            <div className="flex gap-2 justify-end pt-1">
              <button onClick={() => setOpen(false)} disabled={busy} className="px-4 py-2 rounded-lg text-sm bg-gray-800 text-gray-300 hover:bg-gray-700">
                {isAr ? 'إلغاء' : 'Cancel'}
              </button>
              <button onClick={submit} disabled={!ready || busy}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 text-white hover:bg-red-500 disabled:opacity-40 flex items-center gap-2">
                <Trash2 size={14} /> {busy ? (isAr ? 'جاري الحذف...' : 'Deleting...') : (isAr ? 'احذف حسابي نهائياً' : 'Delete permanently')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
