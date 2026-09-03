import { Link } from 'react-router-dom'
import { Brain, TrendingUp, Bell, CheckCircle, Star, BarChart2 } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import useFAQSchema from '../hooks/useFAQSchema'
import useJsonLd from '../hooks/useJsonLd'

// الأسهم الإماراتية المدعومة فعلياً — نفس القائمة المُفعّلة بـmarket_configs
// (migrate_add_gulf_markets.py) وقاعدة رموز telegram-bot/bot.py.
const UAE_STOCKS = [
  { symbol: 'EMAAR',       name: 'إعمار العقارية' },
  { symbol: 'EMIRATESNBD', name: 'بنك الإمارات دبي الوطني' },
  { symbol: 'DIB',         name: 'بنك دبي الإسلامي' },
  { symbol: 'DFMGI',       name: 'مؤشر سوق دبي المالي' },
  { symbol: 'FAB',         name: 'بنك أبوظبي الأول' },
  { symbol: 'ADNOCDIST',   name: 'أدنوك للتوزيع' },
]

// ثابت خارج الكومبوننت — نفس المرجع بكل render (راجع تعليق SA_HREFLANG بـSaudiLanding.jsx)
const AE_HREFLANG = [{ hreflang: 'ar-AE', href: 'https://qaffel.com/ae' }]

const FAQS = [
  { q: 'هل Qaffel AI يدعم تحليل أسهم سوق دبي المالي وأبوظبي؟',
    a: 'نعم — Qaffel AI يحلل 6 رموز إماراتية فعلياً (إعمار، بنك الإمارات دبي الوطني، بنك دبي الإسلامي، مؤشر دبي المالي، بنك أبوظبي الأول، وأدنوك للتوزيع) بنفس منهجية ICT/SMC المستخدمة بالذهب والفوركس.' },
  { q: 'كيف أراقب سهم إماراتي وأستلم تنبيه دخول؟',
    a: 'أضف الرمز لقائمة المراقبة من التطبيق أو بوت تلغرام — بترسل لك تنبيه فوري لما يتوفر شرط دخول حقيقي (Order Block أو FVG بمنطقة سيولة مناسبة)، مع الدخول والوقف والأهداف.' },
  { q: 'هل التحليل مجاني للأسهم الإماراتية؟',
    a: 'تجربة Qaffel AI المجانية (10 تحليلات) تشمل كل الأسواق المدعومة، بما فيها الأسهم الإماراتية — بدون بطاقة ائتمان.' },
]

export default function UAELanding() {
  useSEO({
    title: 'تداول أسهم الإمارات بالذكاء الاصطناعي | Qaffel AI',
    description: 'حلل أسهم سوق دبي المالي وأبوظبي (إعمار، بنك الإمارات دبي الوطني، بنك دبي الإسلامي، بنك أبوظبي الأول وغيرها) بتقنية ICT/SMC والذكاء الاصطناعي. إشارات دخول ووقف وأهداف على تلغرام. ابدأ مجاناً.',
    canonical: 'https://qaffel.com/ae',
    extraHreflang: AE_HREFLANG,
  })
  useBreadcrumbSchema([
    { name: 'الرئيسية', path: '/' },
    { name: 'أسهم الإمارات', path: '/ae' },
  ])
  useFAQSchema('ld-faq-ae', FAQS)

  // FinancialProduct + areaServed صريح لدولة الإمارات العربية المتحدة
  useJsonLd('ld-financial-product-ae', {
    '@context': 'https://schema.org',
    '@type': 'FinancialProduct',
    name: 'تحليل وإشارات أسهم الإمارات — Qaffel AI',
    description: 'تحليل ذكاء اصطناعي (ICT/SMC) لأسهم سوق دبي المالي وأبوظبي، مع إشارات دخول/وقف/أهداف وتنبيهات تلغرام فورية.',
    provider: {
      '@type': 'Organization',
      name: 'Qaffel AI',
      url: 'https://qaffel.com',
    },
    areaServed: {
      '@type': 'Country',
      name: 'United Arab Emirates',
      alternateName: 'الإمارات العربية المتحدة',
    },
    inLanguage: 'ar',
  })

  return (
    <PublicLayout>
      {/* Hero */}
      <section className="py-20 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-red-600/8 rounded-full blur-3xl" />
        </div>
        <div className="max-w-3xl mx-auto relative">
          <div className="inline-flex items-center gap-2 bg-red-600/20 border border-red-500/30 text-red-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <BarChart2 size={12} />
            سوق دبي المالي · سوق أبوظبي
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            تداول أسهم الإمارات<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-red-400 to-blue-400">
              بالذكاء الاصطناعي
            </span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed">
            تحليل مؤسسي حقيقي (ICT/SMC) لإعمار، بنك الإمارات دبي الوطني، بنك أبوظبي الأول، وأهم أسهم سوقي دبي وأبوظبي — إشارات دخول ووقف وأهداف واضحة، مع تنبيهات فورية على تلغرام.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap mt-8">
            <Link to="/register" className="bg-red-600 hover:bg-red-500 text-white px-8 py-3 rounded-xl font-semibold transition">
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
          <h2 className="text-2xl font-bold text-center mb-3">أسهم الإمارات المدعومة حالياً</h2>
          <p className="text-gray-500 text-center text-sm mb-10">6 رموز فعلياً بالمنصة — تحليل حي، مو قائمة تسويقية</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {UAE_STOCKS.map((s) => (
              <div key={s.symbol} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center hover:border-red-500/40 transition">
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
          <h2 className="text-2xl font-bold text-center mb-10">كيف يحلل Qaffel AI سهماً إماراتياً؟</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Brain, title: 'تحليل ICT/SMC', desc: 'رصد Order Blocks وFVG ومناطق السيولة على السهم مباشرة، بنفس المنهجية المستخدمة بالذهب والفوركس.' },
              { icon: TrendingUp, title: 'إشارة كاملة', desc: 'دخول، وقف خسارة، هدفين، ونسبة مخاطرة/عائد واضحة — قبل ما تدخل الصفقة.' },
              { icon: Bell, title: 'تنبيه فوري', desc: 'أضف السهم لقائمة المراقبة واستلم تنبيه تلغرام لحظة توفر فرصة دخول حقيقية.' },
            ].map((f, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                <div className="w-10 h-10 bg-red-600/20 rounded-xl flex items-center justify-center mb-4">
                  <f.icon size={20} className="text-red-400" />
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>

          {/* ربط داخلي لشرح ICT/SMC المعمّق — نفس المفاهيم المذكورة فوق */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <span className="text-gray-500 text-sm">تعمّق أكتر بمنهجية التحليل:</span>
            <Link to="/blog/smart-money-concepts-smc-guide"
              className="text-sm text-red-400 hover:text-red-300 border border-red-500/20 hover:border-red-500/40 px-4 py-1.5 rounded-full transition-colors">
              دليل Smart Money Concepts
            </Link>
            <Link to="/blog/order-blocks-explained"
              className="text-sm text-red-400 hover:text-red-300 border border-red-500/20 hover:border-red-500/40 px-4 py-1.5 rounded-full transition-colors">
              شرح Order Blocks
            </Link>
            <Link to="/blog/fvg-fair-value-gap-trading"
              className="text-sm text-red-400 hover:text-red-300 border border-red-500/20 hover:border-red-500/40 px-4 py-1.5 rounded-full transition-colors">
              شرح FVG
            </Link>
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
                  <CheckCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
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
              <strong>إخلاء مسؤولية:</strong> جميع التحليلات والإشارات على منصة Qaffel AI لأغراض تعليمية وتحليلية فقط، ولا تُعدّ نصيحة مالية أو استثمارية. التداول في الأسواق المالية (بما فيها أسواق الإمارات) ينطوي على مخاطر حقيقية وقد تخسر جزءاً أو كل رأس مالك.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 text-center">
        <h2 className="text-2xl font-bold mb-3">مستعد تحلل أول سهم إماراتي؟</h2>
        <p className="text-gray-400 mb-6">10 تحليلات مجانية، بدون بطاقة ائتمان</p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link to="/register" className="bg-red-600 hover:bg-red-500 text-white px-8 py-3 rounded-xl font-semibold transition">
            ابدأ مجاناً
          </Link>
          <Link to="/sa" className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3 rounded-xl font-medium transition">
            → أسهم السعودية
          </Link>
        </div>
      </section>
    </PublicLayout>
  )
}
