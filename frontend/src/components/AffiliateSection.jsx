import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Gift, DollarSign, Users, TrendingUp, ArrowUpRight, ChevronRight, ChevronLeft, Star } from 'lucide-react'

export default function AffiliateSection({ isAr = true }) {
  const sectionRef = useRef(null)

  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    const io = new IntersectionObserver(
      (entries) => entries.forEach(e => {
        if (e.isIntersecting) e.target.classList.add('visible')
      }),
      { threshold: 0.1 }
    )
    el.querySelectorAll('.reveal, .reveal-aff').forEach(el => io.observe(el))
    return () => io.disconnect()
  }, [])

  const ChevronCta = isAr ? ChevronLeft : ChevronRight

  const cards = [
    {
      icon: <TrendingUp size={22} />,
      color: 'from-green-500/20 to-emerald-600/10 border-green-500/25 text-green-400',
      titleAr: 'كيف تربح',
      titleEn: 'How You Earn',
      descAr: 'شارك رابط الإحالة الخاص بك. كل مشترك يسجّل عبر رابطك تحصل على عمولة فورية عند قبول دفعته.',
      descEn: 'Share your unique referral link. Every subscriber who registers through your link earns you a commission when their payment is approved.',
    },
    {
      icon: <DollarSign size={22} />,
      color: 'from-purple-500/20 to-indigo-600/10 border-purple-500/25 text-purple-400',
      titleAr: 'العمولات',
      titleEn: 'Commissions',
      descAr: 'ابدأ بـ 5% على كل اشتراك. بعد 25 إحالة ناجحة تنتقل تلقائياً إلى المرحلة الثانية بعمولة 15%.',
      descEn: 'Start at 5% per subscription. After 25 successful referrals, you automatically upgrade to Tier 2 with 15% commission.',
    },
    {
      icon: <Users size={22} />,
      color: 'from-blue-500/20 to-cyan-600/10 border-blue-500/25 text-blue-400',
      titleAr: 'السحب',
      titleEn: 'Withdrawals',
      descAr: 'تراكم أرباحك في لوحة التحكم. اطلب السحب متى بلغ رصيدك الحد الأدنى — تتم المراجعة خلال 48 ساعة.',
      descEn: 'Your earnings accumulate in your dashboard. Request a withdrawal once you reach the minimum — reviewed within 48 hours.',
    },
  ]

  return (
    <section ref={sectionRef} className="py-24 px-4 relative overflow-hidden">
      {/* Background orbs */}
      <div className="orb w-[500px] h-[400px] bg-green-600/8 top-0 right-0 translate-x-1/3 -translate-y-1/4 pointer-events-none" />
      <div className="orb w-[400px] h-[300px] bg-purple-600/8 bottom-0 left-0 -translate-x-1/4 translate-y-1/4 pointer-events-none" />

      <div className="max-w-6xl mx-auto relative">

        {/* Header */}
        <div className="text-center mb-16 reveal">
          <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/20 text-green-300 text-xs px-4 py-1.5 rounded-full mb-5">
            <Gift size={12} className="text-green-400" />
            {isAr ? 'برنامج الإحالة' : 'Referral Program'}
          </div>
          <h2 className="text-3xl md:text-4xl font-black mb-4">
            <span className="bg-gradient-to-r from-green-400 via-emerald-400 to-teal-400 bg-clip-text text-transparent">
              {isAr ? 'نظام الإحالة' : 'Referral Program'}
            </span>
            <br />
            <span className="text-white">{isAr ? 'اربح معنا' : 'Earn With Us'}</span>
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto leading-relaxed">
            {isAr
              ? 'أحِل أصدقاءك إلى Qaffel AI واحصل على عمولة دورية من كل اشتراك — بدون حد أقصى للأرباح.'
              : 'Refer your friends to Qaffel AI and earn recurring commissions on every subscription — no earning cap.'}
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid md:grid-cols-3 gap-5 mb-14">
          {cards.map((c, i) => (
            <div
              key={i}
              className={`reveal relative bg-gradient-to-br ${c.color} border rounded-2xl p-6 overflow-hidden group hover:-translate-y-1 transition-all duration-300`}
              style={{ transitionDelay: `${i * 80}ms` }}
            >
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                style={{ background: 'radial-gradient(circle at 50% 0%, rgba(255,255,255,0.03) 0%, transparent 70%)' }} />
              <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${c.color} border flex items-center justify-center mb-4`}>
                {c.icon}
              </div>
              <h3 className="font-bold text-white text-base mb-2">{isAr ? c.titleAr : c.titleEn}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{isAr ? c.descAr : c.descEn}</p>
            </div>
          ))}
        </div>

        {/* Tier visual + Example calculation */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">

          {/* Tiers */}
          <div className="reveal glass border border-white/8 rounded-2xl p-6">
            <h3 className="font-bold text-white mb-5 flex items-center gap-2">
              <Star size={15} className="text-yellow-400 fill-yellow-400" />
              {isAr ? 'مراحل العمولة' : 'Commission Tiers'}
            </h3>
            <div className="space-y-4">
              {/* Tier 1 */}
              <div className="relative rounded-xl border border-blue-500/30 bg-blue-500/5 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-xs font-bold text-blue-400 bg-blue-500/15 px-2.5 py-0.5 rounded-full">
                      {isAr ? 'المرحلة 1' : 'Tier 1'}
                    </span>
                    <p className="text-gray-400 text-xs mt-1.5">{isAr ? 'من 0 إحالة' : 'Starting from 0 referrals'}</p>
                  </div>
                  <div className="text-3xl font-black text-blue-400">5%</div>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full" style={{ width: '33%' }} />
                </div>
                <p className="text-xs text-gray-600 mt-1.5">{isAr ? '0 / 25 إحالة للمرحلة التالية' : '0 / 25 referrals to next tier'}</p>
              </div>
              {/* Tier 2 */}
              <div className="relative rounded-xl border border-yellow-500/40 bg-yellow-500/5 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="text-xs font-bold text-yellow-400 bg-yellow-500/15 px-2.5 py-0.5 rounded-full">
                      {isAr ? 'المرحلة 2' : 'Tier 2'}
                    </span>
                    <p className="text-gray-400 text-xs mt-1.5">{isAr ? 'بعد 25 إحالة ناجحة' : 'After 25 successful referrals'}</p>
                  </div>
                  <div className="text-3xl font-black text-yellow-400">15%</div>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-yellow-500 to-amber-400 rounded-full" style={{ width: '100%' }} />
                </div>
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
                  <p className="text-xs text-yellow-500/80">{isAr ? 'أعلى مستوى عمولة' : 'Maximum commission level'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Example calculation */}
          <div className="reveal glass border border-white/8 rounded-2xl p-6" style={{ transitionDelay: '120ms' }}>
            <h3 className="font-bold text-white mb-5 flex items-center gap-2">
              <TrendingUp size={15} className="text-green-400" />
              {isAr ? 'مثال على الأرباح' : 'Earnings Example'}
            </h3>

            <div className="space-y-3 mb-5">
              {[
                {
                  labelAr: 'أحِل 10 مشتركين / شهر',
                  labelEn: 'Refer 10 subscribers / month',
                  valueAr: '+$30 / شهر',
                  valueEn: '+$30 / month',
                  color: 'text-green-400',
                  note: 'Tier 1 · 5%',
                },
                {
                  labelAr: 'أحِل 25 مشتركين / شهر',
                  labelEn: 'Refer 25 subscribers / month',
                  valueAr: '+$112 / شهر',
                  valueEn: '+$112 / month',
                  color: 'text-yellow-400',
                  note: 'Tier 2 · 15%',
                },
                {
                  labelAr: 'أحِل 50 مشتركين / شهر',
                  labelEn: 'Refer 50 subscribers / month',
                  valueAr: '+$300 / شهر',
                  valueEn: '+$300 / month',
                  color: 'text-purple-400',
                  note: 'Tier 2 · 15%',
                },
              ].map((row, i) => (
                <div key={i} className="flex items-center justify-between bg-white/3 rounded-xl px-4 py-3">
                  <div>
                    <p className="text-sm text-white font-medium">{isAr ? row.labelAr : row.labelEn}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{row.note}</p>
                  </div>
                  <span className={`text-base font-black ${row.color}`}>{isAr ? row.valueAr : row.valueEn}</span>
                </div>
              ))}
            </div>

            <div className="bg-green-900/15 border border-green-500/20 rounded-xl p-3 text-xs text-gray-400">
              <p className="text-green-400 font-semibold mb-1">
                {isAr ? '💡 مثال تفصيلي:' : '💡 Detailed example:'}
              </p>
              {isAr
                ? 'باقة شهرية = $30 · عمولة 5% = $1.5 لكل مشترك · 20 مشترك = $30/شهر بشكل دائم — وبعد 25 إحالة ترتفع لـ 15% = $90/شهر'
                : 'Monthly plan = $30 · 5% = $1.5/subscriber · 20 subscribers = $30/mo forever — reach 25 referrals → 15% = $90/mo'}
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="reveal text-center">
          <Link
            to="/register"
            className="group inline-flex items-center gap-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white px-10 py-4 rounded-2xl font-black text-base transition-all shadow-2xl shadow-green-500/25 hover:shadow-green-500/45 hover:-translate-y-0.5"
          >
            <Gift size={18} />
            {isAr ? 'ابدأ الربح الآن' : 'Start Earning Now'}
            <ChevronCta size={18} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <p className="text-gray-600 text-xs mt-3">
            {isAr ? 'مجاني — لا رسوم على الانضمام' : 'Free — no joining fees'}
          </p>
        </div>

      </div>
    </section>
  )
}
