import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import { Star, Zap, Link2, Users, Target, Trophy, MessageCircle, TrendingUp, Award, Shield } from 'lucide-react'

const BADGES = [
  {
    id: 'first_analysis',
    icon: Zap,
    color: 'text-yellow-400', bg: 'bg-yellow-500/15 border-yellow-500/30',
    glow: '0 0 16px rgba(234,179,8,0.25)',
    titleAr: 'أول خطوة',       titleEn: 'First Step',
    descAr: 'أجريت أول تحليل', descEn: 'Ran your first analysis',
    check: u => u.analyses_total >= 1,
  },
  {
    id: 'ten_analyses',
    icon: Target,
    color: 'text-blue-400', bg: 'bg-blue-500/15 border-blue-500/30',
    glow: '0 0 16px rgba(59,130,246,0.25)',
    titleAr: 'محلل نشط',             titleEn: 'Active Analyst',
    descAr: '10 تحليلات مكتملة',    descEn: '10 analyses done',
    check: u => u.analyses_total >= 10,
  },
  {
    id: 'fifty_analyses',
    icon: TrendingUp,
    color: 'text-cyan-400', bg: 'bg-cyan-500/15 border-cyan-500/30',
    glow: '0 0 16px rgba(6,182,212,0.25)',
    titleAr: 'متداول ذكي',           titleEn: 'Smart Trader',
    descAr: '50 تحليلاً مكتملاً',   descEn: '50 analyses done',
    check: u => u.analyses_total >= 50,
  },
  {
    id: 'hundred_analyses',
    icon: Trophy,
    color: 'text-purple-400', bg: 'bg-purple-500/15 border-purple-500/30',
    glow: '0 0 16px rgba(168,85,247,0.25)',
    titleAr: 'محترف',               titleEn: 'Pro Trader',
    descAr: '100 تحليل مكتمل',      descEn: '100 analyses done',
    check: u => u.analyses_total >= 100,
  },
  {
    id: 'telegram_linked',
    icon: Link2,
    color: 'text-indigo-400', bg: 'bg-indigo-500/15 border-indigo-500/30',
    glow: '0 0 16px rgba(99,102,241,0.25)',
    titleAr: 'متصل',              titleEn: 'Connected',
    descAr: 'ربط حساب Telegram', descEn: 'Linked Telegram',
    check: u => !!u.telegram_linked,
  },
  {
    id: 'ai_user',
    icon: MessageCircle,
    color: 'text-green-400', bg: 'bg-green-500/15 border-green-500/30',
    glow: '0 0 16px rgba(34,197,94,0.25)',
    titleAr: 'يستخدم الذكاء',    titleEn: 'AI User',
    descAr: 'استخدم المساعد الذكي', descEn: 'Used AI assistant',
    check: u => u.chat_total >= 1,
  },
  {
    id: 'subscriber',
    icon: Star,
    color: 'text-orange-400', bg: 'bg-orange-500/15 border-orange-500/30',
    glow: '0 0 16px rgba(249,115,22,0.25)',
    titleAr: 'مشترك',           titleEn: 'Subscriber',
    descAr: 'اشترك في المنصة', descEn: 'Subscribed to platform',
    check: u => ['weekly', 'monthly'].includes(u.plan),
  },
  {
    id: 'referrer',
    icon: Users,
    color: 'text-teal-400', bg: 'bg-teal-500/15 border-teal-500/30',
    glow: '0 0 16px rgba(20,184,166,0.25)',
    titleAr: 'سفير',             titleEn: 'Ambassador',
    descAr: 'دعا مستخدماً جديداً', descEn: 'Referred a new user',
    check: u => (u.referral_count || 0) >= 1,
  },
  {
    id: 'power_user',
    icon: Award,
    color: 'text-rose-400', bg: 'bg-rose-500/15 border-rose-500/30',
    glow: '0 0 16px rgba(244,63,94,0.25)',
    titleAr: 'مستخدم متقدم',          titleEn: 'Power User',
    descAr: '50+ تحليل + AI + ربط',   descEn: '50+ analyses + AI + linked',
    check: u => u.analyses_total >= 50 && u.chat_total >= 5 && !!u.telegram_linked,
  },
  {
    id: 'veteran',
    icon: Shield,
    color: 'text-amber-400', bg: 'bg-amber-500/15 border-amber-500/30',
    glow: '0 0 16px rgba(245,158,11,0.30)',
    titleAr: 'محلل خبير',             titleEn: 'Expert Analyst',
    descAr: '200+ تحليل',              descEn: '200+ analyses done',
    check: u => u.analyses_total >= 200,
  },
]

export default function AchievementBadges() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'

  if (!user) return null

  const earned = BADGES.filter(b => b.check(user))
  const locked = BADGES.filter(b => !b.check(user))

  return (
    <div className="bg-gray-900/60 border border-white/8 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-yellow-500/15 flex items-center justify-center">
            <Trophy size={15} className="text-yellow-400" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">
              {isAr ? 'الإنجازات' : 'Achievements'}
            </h3>
            <p className="text-xs text-gray-500">
              {isAr
                ? `${earned.length} من ${BADGES.length} مكتسب`
                : `${earned.length} of ${BADGES.length} earned`}
            </p>
          </div>
        </div>
        {earned.length > 0 && (
          <span className="text-sm bg-yellow-500/15 text-yellow-300 border border-yellow-500/30 px-2.5 py-1 rounded-full font-bold">
            {earned.length} 🏆
          </span>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Earned badges */}
        {earned.length > 0 && (
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-2">
              {isAr ? 'مكتسبة' : 'Earned'}
            </p>
            <div className="grid grid-cols-2 gap-2">
              {earned.map(b => {
                const Icon = b.icon
                return (
                  <div
                    key={b.id}
                    className={`relative flex items-center gap-3 p-3 rounded-xl border ${b.bg}`}
                    style={{ boxShadow: b.glow }}
                  >
                    <div className={`flex-shrink-0 p-1.5 rounded-lg bg-black/20 ${b.color}`}>
                      <Icon size={16} />
                    </div>
                    <div className="min-w-0">
                      <div className={`text-xs font-bold leading-tight ${b.color}`}>
                        {isAr ? b.titleAr : b.titleEn}
                      </div>
                      <div className="text-[10px] text-gray-500 leading-tight mt-0.5">
                        {isAr ? b.descAr : b.descEn}
                      </div>
                    </div>
                    <span className="absolute top-1.5 end-1.5 text-[10px] text-gray-500">✓</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Locked badges */}
        {locked.length > 0 && (
          <div>
            <p className="text-[10px] text-gray-700 uppercase tracking-wider font-bold mb-2">
              {isAr ? 'لم تُكتسب بعد' : 'Not yet earned'}
            </p>
            <div className="grid grid-cols-2 gap-2">
              {locked.map(b => {
                const Icon = b.icon
                return (
                  <div
                    key={b.id}
                    className="flex items-center gap-3 p-3 rounded-xl border border-gray-800/50 bg-gray-800/20 opacity-40"
                  >
                    <div className="flex-shrink-0 p-1.5 rounded-lg bg-gray-800/60 text-gray-700">
                      <Icon size={16} />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-gray-400 leading-tight">
                        {isAr ? b.titleAr : b.titleEn}
                      </div>
                      <div className="text-[10px] text-gray-700 leading-tight mt-0.5">
                        {isAr ? b.descAr : b.descEn}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {earned.length === 0 && (
          <div className="text-center py-6 text-gray-400 text-sm">
            {isAr ? 'ابدأ بتحليل سوق لتكسب أول إنجاز! 🚀' : 'Analyze a market to earn your first badge! 🚀'}
          </div>
        )}
      </div>
    </div>
  )
}
