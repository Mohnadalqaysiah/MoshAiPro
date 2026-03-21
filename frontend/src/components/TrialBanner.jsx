import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Clock, Zap } from 'lucide-react'

export default function TrialBanner() {
  const { user } = useAuth()
  if (!user || user.plan !== 'trial') return null

  const daysLeft      = user.days_left ?? 0
  const analysesLeft  = user.trial_analyses_left ?? 0
  const chatLeft      = user.trial_chat_left ?? 0
  const isExpired     = daysLeft === 0 || (analysesLeft === 0 && chatLeft === 0)

  if (isExpired) return (
    <div className="bg-red-900/30 border-b border-red-700/50 px-4 py-2.5 flex items-center justify-between text-sm" dir="rtl">
      <div className="flex items-center gap-2 text-red-300">
        <Clock size={14} />
        <span>انتهت فترة التجربة. اشترك للاستمرار.</span>
      </div>
      <Link to="/pricing" className="flex items-center gap-1.5 bg-red-600 hover:bg-red-500 text-white px-3 py-1 rounded-lg text-xs font-semibold">
        <Zap size={12} />
        اشترك الآن
      </Link>
    </div>
  )

  return (
    <div className="bg-blue-900/20 border-b border-blue-700/30 px-4 py-2 flex items-center justify-between text-xs" dir="rtl">
      <div className="flex items-center gap-4 text-gray-300">
        <span className="flex items-center gap-1"><Clock size={12} className="text-blue-400" />{daysLeft} أيام متبقية</span>
        <span>· {analysesLeft} تحليل</span>
        <span>· {chatLeft} رسالة شات</span>
      </div>
      <Link to="/pricing" className="text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1">
        <Zap size={11} />
        ترقية
      </Link>
    </div>
  )
}
