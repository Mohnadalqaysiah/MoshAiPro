import { Link } from 'react-router-dom'
import { Brain, TrendingUp, Bell, CheckCircle, Star, BarChart2, Shield } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import useFAQSchema from '../hooks/useFAQSchema'
import useJsonLd from '../hooks/useJsonLd'

// الأسهم السعودية المدعومة فعلياً — نفس القائمة المُفعّلة بـmarket_configs
// (migrate_add_gulf_markets.py) وقاعدة رموز telegram-bot/bot.py. لا تُضف
// رمز هون قبل ما يتفعّل فعلياً بالباك اند.
const SAUDI_STOCKS = [
  { symbol: 'ARAMCO', name: 'أرامكو السعودية' },
  { symbol: 'RAJHI',  name: 'مصرف الراجحي' },
  { symbol: 'SABIC',  name: 'سابك' },
  { symbol: 'STC',    name: 'الاتصالات السعودية STC' },
  { symbol: 'SNB',    name: 'البنك الأهلي السعودي' },
  { symbol: 'MAADEN', name: 'معادن' },
  { symbol: 'ALMARAI',name: 'المراعي' },
  { symbol: 'BAHRI',  name: 'البحري' },
  { symbol: 'ALINMA', name: 'مصرف الإنماء' },
  { symbol: 'TASI',   name: 'المؤشر العام تاسي' },
]

// ثابت خارج الكومبوننت — نفس المرجع بكل render، يمنع إعادة تشغيل useEffect
// بـuseSEO بدون داعي (راجع src/hooks/useSEO.js لتعليق extraHreflang)
const SA_HREFLANG = [{ hreflang: 'ar-SA', href: 'https://qaffel.com/sa' }]

const FAQS = [
  { q: 'هل Qaffel AI يدعم تحليل الأسهم السعودية مثل أرامكو والراجحي؟',
    a: 'نعم — Qaffel AI يحلل 10 رموز سعودية فعلياً (أرامكو، الراجحي، سابك، الاتصالات السعودية، البنك الأهلي، معادن، المراعي، البحري، مصرف الإنماء، ومؤشر تاسي) بنفس منهجية ICT/SMC المستخدمة بالذهب والفوركس.' },
  { q: 'كيف أراقب سهم سعودي معيّن وأستلم تنبيه عند فرصة دخول؟',
    a: 'أضف الرمز لقائمة المراقبة (Watchlist) من التطبيق أو بوت تلغرام، وحدد الفريم الزمني — بترسل لك تنبيه فوري لما يتوفر شرط دخول حقيقي (Order Block أو FVG بمنطقة سيولة مناسبة)، مع الدخول والوقف والأهداف.' },
  { q: 'هل التحليل مجاني للأسهم السعودية؟',
    a: 'تجربة Qaffel AI المجانية (10 تحليلات) تشمل كل الأسواق المدعومة، بما فيها الأسهم السعودية — بدون بطاقة ائتمان.' },
]

export default function SaudiLanding() {
  useSEO({
    title: 'تداول الأسهم السعودية بالذكاء الاصطناعي | Qaffel AI',
    description: 'حلل أسهم السوق السعودي (أرامكو، الراجحي، سابك، الاتصالات السعودية، البنك الأهلي وغيرها) بتقنية ICT/SMC والذكاء الاصطناعي. إشارات دخول ووقف وأهداف مباشرة على تلغرام. ابدأ مجاناً.',
    canonical: 'https://qaffel.com/sa',
    extraHreflang: SA_HREFLANG,
  })
  useBreadcrumbSchema([
    { name: 'الرئيسية', path: '/' },
    { name: 'الأسهم السعودية', path: '/sa' },
  ])
  useFAQSchema('ld-faq-sa', FAQS)

  // FinancialProduct + areaServed صريح للمملكة العربية السعودية
  useJsonLd('ld-financial-product-sa', {
    '@context': 'https://schema.org',
    '@type': 'FinancialProduct',
    name: 'تحليل وإشارات الأسهم السعودية — Qaffel AI',
    description: 'تحليل ذكاء اصطناعي (ICT/SMC) لأسهم السوق السعودي، مع إشارات دخول/وقف/أهداف وتنبيهات تلغرام فورية.',
    provider: {
      '@type': 'Organization',
      name: 'Qaffel AI',
      url: 'https://qaffel.com',
    },
    areaServed: {
      '@type': 'Country',
      name: 'Saudi Arabia',
      alternateName: 'المملكة العربية السعودية',
    },
    inLanguage: 'ar',
  })

  return (
    <PublicLayout>
      {/* Hero */}
      <section className="py-20 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-green-600/8 rounded-full blur-3xl" />
        </div>
        <div className="max-w-3xl mx-auto relative">
          <div className="inline-flex items-center gap-2 bg-green-600/20 border border-green-500/30 text-green-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <BarChart2 size={12} />
            السوق السعودي (تداول)
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            تداول الأسهم السعودية<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-green-400 to-blue-400">
              بالذكاء الاصطناعي
            </span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed">
            تحليل مؤسسي حقيقي (ICT/SMC) لأرامكو، الراجحي، سابك، وأهم أسهم السوق السعودي — إشارات دخول ووقف وأهداف واضحة، مع تنبيهات فورية على تلغرام.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap mt-8">
            <Link to="/register" className="bg-green-600 hover:bg-green-500 text-white px-8 py-3 rounded-xl font-semibold transition">
              ابدأ مجاناً — 10 تحليلات
            </Link>
            <Link to="/pricing" className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3 rounded-xl font-medium transition">
              الباقات
            </Link>
          </div>
        </div>
      </section>

      {/* الأسهم المدعومة */}
      <section className="py-16 px-6 bg-gray-900/40">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-3">الأسهم السعودية المدعومة حالياً</h2>
          <p className="text-gray-500 text-center text-sm mb-10">10 رموز فعلياً بالمنصة — تحليل حي، مو قائمة تسويقية</p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {SAUDI_STOCKS.map((s) => (
              <div key={s.symbol} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center hover:border-green-500/40 transition">
                <p className="text-white text-sm font-semibold">{s.name}</p>
                <p className="text-gray-500 text-xs mt-1 font-mono">{s.symbol}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* كيف يعمل */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-10">كيف يحلل Qaffel AI سهماً سعودياً؟</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Brain, title: 'تحليل ICT/SMC', desc: 'رصد Order Blocks وFVG ومناطق السيولة على السهم مباشرة، بنفس المنهجية المستخدمة بالذهب والفوركس.' },
              { icon: TrendingUp, title: 'إشارة كاملة', desc: 'دخول، وقف خسارة، هدفين، ونسبة مخاطرة/عائد واضحة — قبل ما تدخل الصفقة.' },
              { icon: Bell, title: 'تنبيه فوري', desc: 'أضف السهم لقائمة المراقبة واستلم تنبيه تلغرام لحظة توفر فرصة دخول حقيقية.' },
            ].map((f, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                <div className="w-10 h-10 bg-green-600/20 rounded-xl flex items-center justify-center mb-4">
                  <f.icon size={20} className="text-green-400" />
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-6 bg-gray-900/40">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-10">أسئلة شائعة</h2>
          <div className="space-y-4">
            {FAQS.map((f, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="font-semibold text-white mb-2 flex items-start gap-2">
                  <CheckCircle size={16} className="text-green-400 mt-0.5 flex-shrink-0" />
                  {f.q}
                </h3>
                <p className="text-gray-400 text-sm leading-relaxed pr-6">{f.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="py-8 px-6">
        <div className="max-w-3xl mx-auto bg-yellow-950/30 border border-yellow-700/30 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <Star size={16} className="text-yellow-400 mt-0.5 flex-shrink-0" />
            <p className="text-yellow-300/80 text-sm leading-relaxed">
              <strong>إخلاء مسؤولية:</strong> جميع التحليلات والإشارات على منصة Qaffel AI لأغراض تعليمية وتحليلية فقط، ولا تُعدّ نصيحة مالية أو استثمارية. التداول في الأسواق المالية (بما فيها السوق السعودي) ينطوي على مخاطر حقيقية وقد تخسر جزءاً أو كل رأس مالك.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 text-center">
        <h2 className="text-2xl font-bold mb-3">مستعد تحلل أول سهم سعودي؟</h2>
        <p className="text-gray-400 mb-6">10 تحليلات مجانية، بدون بطاقة ائتمان</p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link to="/register" className="bg-green-600 hover:bg-green-500 text-white px-8 py-3 rounded-xl font-semibold transition">
            ابدأ مجاناً
          </Link>
          <Link to="/ae" className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3 rounded-xl font-medium transition">
            أسهم الإمارات ←
          </Link>
        </div>
      </section>
    </PublicLayout>
  )
}
