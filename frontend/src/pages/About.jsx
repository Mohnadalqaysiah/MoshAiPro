import { Link } from 'react-router-dom'
import { Users, Brain, Globe, Shield, Award, TrendingUp, CheckCircle, Star } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

const T = {
  ar: {
    badge: 'من نحن',
    h1a: 'نُمكّن المتداولين من',
    h1b: 'اتخاذ قرارات أذكى',
    heroSub: 'Qaffel AI منصة عربية متخصصة في تحليل الأسواق المالية بالذكاء الاصطناعي، تجمع بين تقنيات التحليل المؤسسي الاحترافي وسهولة الوصول للجميع.',
    storyTitle: 'قصتنا',
    storyP: [
      'وُلدت فكرة Qaffel AI من رحم التحدي الذي يعيشه المتداول العربي يومياً — أدوات تحليل احترافية موجودة لكنها بالإنجليزية وتحتاج خبرة عميقة، أو إشارات مجهولة المصدر لا يمكن الوثوق بها.',
      'قرّرنا بناء منصة تجمع أقوى منهجيات التحليل المؤسسي — ICT وSMC وWyckoff — مع قدرات الذكاء الاصطناعي الحديث، لتقديم تحليل شفاف وقابل للتفسير بالعربية مباشرة على هاتفك.',
      'نؤمن أن كل متداول — سواء كان محترفاً أو مبتدئاً — يستحق أدوات من المستوى المؤسسي، بسعر عادل وبلغته الأم.',
    ],
    storyCards: [
      { icon: Brain,      label: 'ذكاء اصطناعي متقدم', desc: 'Gemini AI + ICT/SMC' },
      { icon: Globe,      label: 'منصة عربية أصيلة',    desc: 'دعم كامل بالعربية' },
      { icon: Shield,     label: 'تحليل شفاف وموثوق',   desc: 'بدون إشارات مجهولة' },
      { icon: TrendingUp, label: 'أسواق متعددة',        desc: 'ذهب · بيتكوين · فوركس' },
    ],
    offerTitle: 'ماذا نقدّم؟',
    offerCols: [
      { icon: Brain, title: 'تحليل بالذكاء الاصطناعي', items: ['تحليل ICT/SMC المتقدم', 'تحديد Order Blocks و FVGs', 'رصد Liquidity و Smart Money', 'تحليل Wyckoff المؤسسي'] },
      { icon: TrendingUp, title: 'إشارات وتوصيات دقيقة', items: ['إشارات شراء/بيع مع مستويات الدخول', 'حساب وقف الخسارة والأهداف', 'تحديد حجم الصفقة المناسب', 'تقييم جودة الإشارة (A+ إلى C)'] },
      { icon: Users, title: 'تجربة مستخدم متميزة', items: ['واجهة عربية سهلة الاستخدام', 'تنبيهات فورية على Telegram', 'وكيل AI للمحادثة والاستفسار', 'دعم فني متواصل'] },
    ],
    valuesTitle: 'قيمنا',
    values: [
      { icon: Shield, title: 'الشفافية أولاً', desc: 'نؤمن بأن التحليل يجب أن يكون مفهوماً وقابلاً للتحقق. كل إشارة نقدمها مبنية على بيانات حقيقية وأسباب موثقة.' },
      { icon: Award,  title: 'الجودة لا الكمية', desc: 'نفضّل إشارة واحدة عالية الجودة على عشر إشارات مشكوك فيها. التقييم الصادق يحمي رأس مالك.' },
      { icon: Users,  title: 'مجتمع أولاً', desc: 'نبني منصة يشعر فيها كل متداول عربي بأنه في المكان الصحيح — حيث الدعم والتعليم متاحان للجميع.' },
      { icon: Brain,  title: 'الابتكار المستمر', desc: 'نواصل تطوير نماذجنا وإضافة أسواق وأدوات جديدة لتبقى في طليعة أدوات التداول الذكي.' },
    ],
    disclaimerLabel: 'إخلاء مسؤولية:',
    disclaimer: 'جميع التحليلات والإشارات المقدمة على منصة Qaffel AI هي لأغراض تعليمية وتحليلية فقط، ولا تُعدّ نصيحة مالية أو استثمارية. التداول في الأسواق المالية ينطوي على مخاطر حقيقية وقد تخسر جزءاً أو كل رأس مالك. أنت المسؤول الكامل عن قراراتك الاستثمارية.',
    ctaTitle: 'مستعد تبدأ رحلتك؟',
    ctaSub: '10 تحليلات مجانية، بدون بطاقة ائتمان',
    ctaStart: 'ابدأ مجاناً',
    ctaVision: 'رؤيتنا',
  },
  en: {
    badge: 'About Us',
    h1a: 'We empower traders to',
    h1b: 'make smarter decisions',
    heroSub: 'Qaffel AI is an Arabic-first platform specialized in AI-powered financial market analysis, combining professional institutional analysis techniques with accessibility for everyone.',
    storyTitle: 'Our Story',
    storyP: [
      'Qaffel AI was born out of the daily challenge faced by Arab traders — professional analysis tools that exist only in English and require deep expertise, or signals of unknown origin that can\'t be trusted.',
      'We decided to build a platform that combines the strongest institutional analysis methodologies — ICT, SMC, and Wyckoff — with modern AI capabilities, to deliver transparent, explainable analysis in Arabic, straight to your phone.',
      'We believe every trader — professional or beginner — deserves institutional-grade tools, at a fair price, in their native language.',
    ],
    storyCards: [
      { icon: Brain,      label: 'Advanced AI',        desc: 'Gemini AI + ICT/SMC' },
      { icon: Globe,      label: 'Arabic-native platform', desc: 'Full Arabic support' },
      { icon: Shield,     label: 'Transparent & trusted', desc: 'No anonymous signals' },
      { icon: TrendingUp, label: 'Multiple markets',    desc: 'Gold · Bitcoin · Forex' },
    ],
    offerTitle: 'What We Offer',
    offerCols: [
      { icon: Brain, title: 'AI-Powered Analysis', items: ['Advanced ICT/SMC analysis', 'Identifying Order Blocks & FVGs', 'Tracking Liquidity & Smart Money', 'Institutional Wyckoff analysis'] },
      { icon: TrendingUp, title: 'Accurate Signals & Recommendations', items: ['Buy/sell signals with entry levels', 'Stop-loss and target calculation', 'Proper position sizing', 'Signal quality rating (A+ to C)'] },
      { icon: Users, title: 'A Superior User Experience', items: ['Easy-to-use Arabic interface', 'Instant Telegram alerts', 'AI chat agent for questions', 'Ongoing technical support'] },
    ],
    valuesTitle: 'Our Values',
    values: [
      { icon: Shield, title: 'Transparency First', desc: 'We believe analysis should be understandable and verifiable. Every signal we provide is built on real data and documented reasoning.' },
      { icon: Award,  title: 'Quality Over Quantity', desc: 'We prefer one high-quality signal over ten questionable ones. Honest evaluation protects your capital.' },
      { icon: Users,  title: 'Community First', desc: 'We build a platform where every Arab trader feels they belong — where support and education are available to everyone.' },
      { icon: Brain,  title: 'Continuous Innovation', desc: 'We keep improving our models and adding new markets and tools to stay at the forefront of smart trading tools.' },
    ],
    disclaimerLabel: 'Disclaimer:',
    disclaimer: 'All analysis and signals provided on the Qaffel AI platform are for educational and analytical purposes only, and do not constitute financial or investment advice. Trading in financial markets involves real risk and you may lose part or all of your capital. You are solely responsible for your investment decisions.',
    ctaTitle: 'Ready to start your journey?',
    ctaSub: '10 free analyses, no credit card required',
    ctaStart: 'Start Free',
    ctaVision: 'Our Vision',
  },
}

export default function About() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']

  useSEO({
    title: isAr
      ? 'من نحن | Qaffel AI — منصة إشارات تداول بالذكاء الاصطناعي'
      : 'About Us | Qaffel AI — AI-Powered Trading Signals Platform',
    description: isAr
      ? 'تعرّف على Qaffel AI — فريق من خبراء التداول والذكاء الاصطناعي يبني أفضل منصة إشارات ICT/SMC للمتداولين العرب.'
      : 'Learn about Qaffel AI — a team of trading and AI experts building the best ICT/SMC signals platform for Arab traders.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'من نحن' : 'About Us', path: isAr ? '/about' : '/en/about' },
  ])

  return (
    <PublicLayout>

      {/* Hero */}
      <section className="py-20 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/8 rounded-full blur-3xl" />
        </div>
        <div className="max-w-3xl mx-auto relative">
          <div className="inline-flex items-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Users size={12} />
            {tx.badge}
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            {tx.h1a}<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-blue-400 to-purple-400">
              {tx.h1b}
            </span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed">
            {tx.heroSub}
          </p>
        </div>
      </section>

      {/* Story */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-2xl font-bold mb-4">{tx.storyTitle}</h2>
              {tx.storyP.map((p, i) => (
                <p key={i} className="text-gray-400 leading-relaxed mb-4 last:mb-0">{p}</p>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-4">
              {tx.storyCards.map((item, i) => (
                <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                  <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                    <item.icon size={20} className="text-blue-400" />
                  </div>
                  <p className="text-white text-sm font-medium">{item.label}</p>
                  <p className="text-gray-500 text-xs mt-1">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* What we offer */}
      <section className="py-16 px-6 bg-gray-900/40">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-10">{tx.offerTitle}</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {tx.offerCols.map((col, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center mb-4">
                  <col.icon size={20} className="text-blue-400" />
                </div>
                <h3 className="font-semibold text-white mb-3">{col.title}</h3>
                <ul className="space-y-2">
                  {col.items.map((it, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-gray-400">
                      <CheckCircle size={13} className="text-green-400 mt-0.5 flex-shrink-0" />
                      {it}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-10">{tx.valuesTitle}</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {tx.values.map((v, i) => (
              <div key={i} className="flex gap-4 bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <v.icon size={20} className="text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">{v.title}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{v.desc}</p>
                </div>
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
              <strong>{tx.disclaimerLabel}</strong> {tx.disclaimer}
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 text-center">
        <h2 className="text-2xl font-bold mb-3">{tx.ctaTitle}</h2>
        <p className="text-gray-400 mb-6">{tx.ctaSub}</p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link to={isAr ? '/register' : '/en/register'} className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-semibold transition">
            {tx.ctaStart}
          </Link>
          <Link to={isAr ? '/vision' : '/en/vision'} className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3 rounded-xl font-medium transition">
            {tx.ctaVision}
          </Link>
        </div>
      </section>

    </PublicLayout>
  )
}
