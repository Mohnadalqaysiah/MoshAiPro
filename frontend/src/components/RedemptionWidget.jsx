import { useState, useEffect } from 'react'
import axios from 'axios'
import { Gift, ChevronDown, ChevronUp, Star, Zap, Calendar, CheckCircle, AlertTriangle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TYPE_ICON = { analysis: <Zap size={14} className="text-yellow-400"/>, days: <Calendar size={14} className="text-blue-400"/> }
const TYPE_COLOR = {
  analysis: 'border-yellow-700/40 bg-yellow-900/10',
  days:     'border-blue-700/40 bg-blue-900/10',
}

export default function RedemptionWidget() {
  const [open, setOpen]     = useState(false)
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [redeeming, setRedeeming] = useState(null)
  const [msg, setMsg]       = useState(null)

  const load = async () => {
    try {
      const r = await axios.get(`${API}/api/v1/affiliate/redemption-tiers`)
      setData(r.data)
    } catch {}
  }

  useEffect(() => { if (open && !data) load() }, [open])

  const redeem = async (tier) => {
    if (!tier.can_redeem) return
    setRedeeming(tier.id); setMsg(null)
    try {
      const r = await axios.post(`${API}/api/v1/affiliate/redeem-tier`, { tier_id: tier.id })
      setMsg({ type:'ok', text: r.data.message })
      await load()
    } catch (e) {
      setMsg({ type:'err', text: e.response?.data?.detail || 'خطأ في الاستبدال' })
    } finally { setRedeeming(null) }
  }

  const points = data?.points ?? 0

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-800/50 transition">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-yellow-900/30 border border-yellow-700/40 flex items-center justify-center">
            <Gift size={15} className="text-yellow-400"/>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold text-white">استبدال النقاط</p>
            <p className="text-xs text-gray-400">{points > 0 ? `لديك ${points} نقطة` : 'اجمع نقاطاً واستبدلها بمكافآت'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {points > 0 && (
            <span className="bg-yellow-500/20 text-yellow-400 text-xs font-bold px-2.5 py-1 rounded-full border border-yellow-500/30">
              {points} نقطة
            </span>
          )}
          {open ? <ChevronUp size={16} className="text-gray-400"/> : <ChevronDown size={16} className="text-gray-400"/>}
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-3 border-t border-gray-800/50">
          {/* Points Bar */}
          {data && (
            <div className="pt-4">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs text-gray-400">رصيد النقاط</span>
                <span className="text-sm font-bold text-yellow-400">{points} نقطة</span>
              </div>
              {/* Progress to first redeemable tier */}
              {(() => {
                const nextTier = data.tiers.find(t => !t.can_redeem)
                if (!nextTier) return null
                const pct = Math.min(100, (points / nextTier.points) * 100)
                return (
                  <div>
                    <div className="w-full bg-gray-800 rounded-full h-1.5 mb-1">
                      <div className="bg-yellow-500 h-1.5 rounded-full transition-all" style={{width:`${pct}%`}}/>
                    </div>
                    <p className="text-xs text-gray-500">تحتاج {nextTier.points_needed} نقطة للمستوى التالي</p>
                  </div>
                )
              })()}
            </div>
          )}

          {msg && (
            <div className={`flex items-center gap-2 text-xs rounded-lg px-3 py-2 ${msg.type==='ok'?'bg-green-900/30 text-green-400':'bg-red-900/30 text-red-400'}`}>
              {msg.type==='ok'?<CheckCircle size={12}/>:<AlertTriangle size={12}/>} {msg.text}
            </div>
          )}

          {/* Tiers Grid */}
          {loading && <p className="text-xs text-gray-500 text-center py-4">جاري التحميل...</p>}
          {data && (
            <div className="grid grid-cols-1 gap-2">
              {data.tiers.map(tier => (
                <div key={tier.id}
                  className={`flex items-center justify-between rounded-xl px-4 py-3 border transition ${
                    tier.can_redeem ? TYPE_COLOR[tier.reward_type] : 'border-gray-800 bg-gray-800/20 opacity-60'
                  }`}>
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center">
                      {TYPE_ICON[tier.reward_type] || <Star size={14} className="text-gray-400"/>}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{tier.label}</p>
                      <p className="text-xs text-gray-500">{tier.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-gray-300">
                      {tier.points} <span className="text-gray-500 font-normal">نقطة</span>
                    </span>
                    <button
                      disabled={!tier.can_redeem || redeeming === tier.id}
                      onClick={() => redeem(tier)}
                      className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition ${
                        tier.can_redeem
                          ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
                          : 'bg-gray-800 text-gray-400 cursor-not-allowed'
                      }`}>
                      {redeeming === tier.id ? '...' : tier.can_redeem ? 'استبدل' : `ناقص ${tier.points_needed}`}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-gray-400 text-center pt-1">
            اجمع نقاطاً بدعوة أصدقاء للمنصة
          </p>
        </div>
      )}
    </div>
  )
}
