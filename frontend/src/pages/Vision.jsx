import { Link } from 'react-router-dom'
import { Target, Rocket, Globe, Users, Zap, Brain, TrendingUp, Star, ChevronLeft, ChevronRight } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

const T = {
  ar: {
    badge: 'رؤيتنا ورسالتنا',
    h1a: 'نحو عالم يتداول فيه',
    h1b: 'كل عربي بثقة واحترافية',
    heroSub: 'رؤيتنا تتجاوز مجرد تقديم إشارات — نسعى لبناء جيل من المتداولين العرب المسلحين بالمعرفة والأدوات لتحقيق الاستقلال المالي.',
    visionTitle: 'رؤيتنا',
    visionBody: 'أن نكون المنصة الأولى والأكثر ثقةً في العالم العربي لتحليل الأسواق المالية بالذكاء الاصطناعي — منصة يلجأ إليها كل متداول عربي قبل كل صفقة.',
    missionTitle: 'رسالتنا',
    missionBody: 'ديمقراطة التحليل المؤسسي — جعل أدوات التداول الاحترافية متاحة وبأسعار منصفة لكل متداول عربي، من المبتدئ إلى المحترف.',
    roadmapTitle: 'خارطة طريقنا',
    roadmapSub: 'ما حققناه وما نسعى إليه',
    roadmap: [
      { phase: 'المرحلة الأولى ✅', title: 'الإطلاق والتأسيس', done: true, items: ['تحليل ICT/SMC بالذكاء الاصطناعي للذهب والبيتكوين', 'وكيل AI للمحادثة التفاعلية', 'تنبيهات Telegram الفورية', 'لوحة تحكم عربية متكاملة', 'نظام اشتراكات مرن'] },
      { phase: 'المرحلة الثانية 🔄', title: 'التوسع والنضج', done: false, items: ['دعم مزيد من الأسواق (نفط، مؤشرات، عملات رقمية)', 'تطبيق موبايل iOS وAndroid', 'تحليل متعدد العملات في نفس الوقت', 'تقارير أسبوعية مفصلة بالذكاء الاصطناعي', 'نظام تنبيهات ذكي حسب مستوى السعر'] },
      { phase: 'المرحلة الثالثة 🔮', title: 'الريادة الإقليمية', done: false, items: ['منصة تعليمية لتعلم ICT/SMC بالعربية', 'ذكاء اصطناعي مخصص للأسواق العربية', 'شراكات مع وسطاء التداول الموثوقين', 'مجتمع متداولين عرب نشط', 'حلول مؤسسية للشركات والصناديق'] },
    ],
    whyTitle: 'لماذا Qaffel AI؟',
    why: [
      { icon: Brain, title: 'أقوى تقنيات التحليل', desc: 'نجمع بين ICT (Inner Circle Trader) وSMC (Smart Money Concepts) وWyckoff — ثلاث منهجيات يستخدمها كبار المتداولين المؤسسيين — في تحليل واحد متكامل مدعوم بـ Gemini AI.' },
      { icon: Globe, title: 'الأول بالعربية', desc: 'لا يوجد في السوق منصة عربية تقدم هذا المستوى من التحليل المؤسسي بالذكاء الاصطناعي. Qaffel AI يملأ هذا الفراغ بمحتوى 100% عربي وواجهة مصممة للمتداول العربي.' },
      { icon: Zap, title: 'سرعة لا مثيل لها', desc: 'تحليل كامل يشمل أكثر من 15 مؤشر ICT/SMC في أقل من 30 ثانية. ما يستغرق المتداول ساعات للوصول إليه، تحصل عليه بنقرة واحدة.' },
      { icon: TrendingUp, title: 'شفافية تامة', desc: 'كل إشارة تأتي مع شرح كامل: لماذا BUY أو SELL؟ ما هو Order Block المحدد؟ أين السيولة؟ نحن لا نعطيك سمكة — نعلمك الصيد.' },
      { icon: Users, title: 'مجتمع داعم', desc: 'انضم إلى مجتمع متنامٍ من المتداولين العرب الذين يتعلمون ويتشاركون الخبرات. نبني أكثر من منصة — نبني مجتمعاً.' },
      { icon: Target, title: 'سعر عادل ومناسب', desc: 'نؤمن أن الأدوات الاحترافية يجب أن تكون متاحة للجميع. لذا نقدم خطط اشتراك مرنة تبدأ بتجربة مجانية حقيقية بدون أي التزام.' },
    ],
    marketsTitle: 'الأسواق التي نحللها',
    marketsSub: 'نقدم تحليلاً ذكياً لأبرز الأسواق المالية العالمية',
    markets: ['الذهب XAUUSD', 'البيتكوين BTCUSD', 'اليورو دولار EURUSD', 'الجنيه دولار GBPUSD', 'الدولار ين USDJPY', 'النفط الخام', 'مؤشر داو جونز', 'ناسداك', 'إثيريوم ETHUSD'],
    keywords: 'تحليل فوركس بالذكاء الاصطناعي · إشارات تداول الذهب · توصيات البيتكوين · بوت تداول تلجرام · منصة تداول ذكية عربية',
    ctaBadge: 'ابدأ رحلتك اليوم',
    ctaTitle: 'كن جزءاً من مستقبل التداول الذكي',
    ctaSub: 'انضم للمتداولين الذين يستخدمون Qaffel AI لاتخاذ قرارات أفضل. ابدأ بـ 10 تحليلات مجانية بدون أي التزام.',
    ctaStart: 'ابدأ مجاناً الآن',
    ctaAbout: 'من نحن',
  },
  en: {
    badge: 'Vision & Mission',
    h1a: 'Toward a world where',
    h1b: 'every Arab trades with confidence',
    heroSub: 'Our vision goes beyond just providing signals — we aim to build a generation of Arab traders armed with the knowledge and tools to achieve financial independence.',
    visionTitle: 'Our Vision',
    visionBody: 'To be the first and most trusted platform in the Arab world for AI-powered financial market analysis — a platform every Arab trader turns to before every trade.',
    missionTitle: 'Our Mission',
    missionBody: 'Democratizing institutional analysis — making professional trading tools accessible and fairly priced for every Arab trader, from beginner to professional.',
    roadmapTitle: 'Our Roadmap',
    roadmapSub: 'What we\'ve achieved and where we\'re headed',
    roadmap: [
      { phase: 'Phase One ✅', title: 'Launch & Foundation', done: true, items: ['AI-powered ICT/SMC analysis for Gold and Bitcoin', 'AI agent for interactive chat', 'Instant Telegram alerts', 'Full Arabic dashboard', 'Flexible subscription system'] },
      { phase: 'Phase Two 🔄', title: 'Growth & Maturity', done: false, items: ['Support for more markets (oil, indices, crypto)', 'iOS and Android mobile app', 'Simultaneous multi-pair analysis', 'Detailed AI-powered weekly reports', 'Smart price-level alert system'] },
      { phase: 'Phase Three 🔮', title: 'Regional Leadership', done: false, items: ['Educational platform for learning ICT/SMC in Arabic', 'AI tailored to Arab markets', 'Partnerships with trusted brokers', 'An active Arab trader community', 'Institutional solutions for firms and funds'] },
    ],
    whyTitle: 'Why Qaffel AI?',
    why: [
      { icon: Brain, title: 'The Strongest Analysis Techniques', desc: 'We combine ICT (Inner Circle Trader), SMC (Smart Money Concepts) and Wyckoff — three methodologies used by top institutional traders — into one integrated analysis powered by Gemini AI.' },
      { icon: Globe, title: 'First in Arabic', desc: 'No Arabic platform on the market offers this level of AI-powered institutional analysis. Qaffel AI fills that gap with 100% Arabic content and an interface designed for Arab traders.' },
      { icon: Zap, title: 'Unmatched Speed', desc: 'A complete analysis covering 15+ ICT/SMC indicators in under 30 seconds. What takes a trader hours to work out, you get in one click.' },
      { icon: TrendingUp, title: 'Complete Transparency', desc: 'Every signal comes with a full explanation: why BUY or SELL? Which specific Order Block? Where is the liquidity? We don\'t just give you a fish — we teach you to fish.' },
      { icon: Users, title: 'A Supportive Community', desc: 'Join a growing community of Arab traders learning and sharing experience. We\'re building more than a platform — we\'re building a community.' },
      { icon: Target, title: 'Fair, Accessible Pricing', desc: 'We believe professional tools should be accessible to everyone. That\'s why we offer flexible plans starting with a real free trial and no commitment.' },
    ],
    marketsTitle: 'Markets We Analyze',
    marketsSub: 'Smart analysis for the world\'s leading financial markets',
    markets: ['Gold XAUUSD', 'Bitcoin BTCUSD', 'Euro/Dollar EURUSD', 'Pound/Dollar GBPUSD', 'Dollar/Yen USDJPY', 'Crude Oil', 'Dow Jones Index', 'Nasdaq', 'Ethereum ETHUSD'],
    keywords: 'AI forex analysis · Gold trading signals · Bitcoin recommendations · Telegram trading bot · Arabic smart trading platform',
    ctaBadge: 'Start Your Journey Today',
    ctaTitle: 'Be Part of the Future of Smart Trading',
    ctaSub: 'Join traders using Qaffel AI to make better decisions. Start with 10 free analyses, no commitment required.',
    ctaStart: 'Start Free Now',
    ctaAbout: 'About Us',
  },
}

export default function Vision() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']
  const ChevronCta = isAr ? ChevronLeft : ChevronRight

  useSEO({
    title: isAr
      ? 'رؤيتنا | Qaffel AI — مستقبل التداول الذكي'
      : 'Our Vision | Qaffel AI — The Future of Smart Trading',
    description: isAr
      ? 'رؤية Qaffel AI لجعل تحليل Smart Money Concepts متاحاً لكل متداول عربي بقوة الذكاء الاصطناعي.'
      : 'Qaffel AI\'s vision to make Smart Money Concepts analysis accessible to every Arab trader through the power of AI.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'رؤيتنا' : 'Our Vision', path: isAr ? '/vision' : '/en/vision' },
  ])

  return (
    <PublicLayout>

      {/* Hero */}
      <section className="py-20 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-600/8 rounded-full blur-3xl" />
        </div>
        <div className="max-w-3xl mx-auto relative">
          <div className="inline-flex items-center gap-2 bg-purple-600/20 border border-purple-500/30 text-purple-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Target size={12} />
            {tx.badge}
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            {tx.h1a}<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-purple-400 to-blue-400">
              {tx.h1b}
            </span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed">
            {tx.heroSub}
          </p>
        </div>
      </section>

      {/* Vision Statement */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/10 border border-blue-700/30 rounded-2xl p-8">
              <div className="w-12 h-12 bg-blue-600/30 rounded-xl flex items-center justify-center mb-5">
                <Target size={24} className="text-blue-400" />
              </div>
              <h2 className="text-xl font-bold text-white mb-3">{tx.visionTitle}</h2>
              <p className="text-gray-300 leading-relaxed">{tx.visionBody}</p>
            </div>
            <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/10 border border-purple-700/30 rounded-2xl p-8">
              <div className="w-12 h-12 bg-purple-600/30 rounded-xl flex items-center justify-center mb-5">
                <Rocket size={24} className="text-purple-400" />
              </div>
              <h2 className="text-xl font-bold text-white mb-3">{tx.missionTitle}</h2>
              <p className="text-gray-300 leading-relaxed">{tx.missionBody}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Roadmap */}
      <section className="py-16 px-6 bg-gray-900/40">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-3">{tx.roadmapTitle}</h2>
          <p className="text-gray-400 text-center mb-12">{tx.roadmapSub}</p>
          <div className="space-y-6">
            {tx.roadmap.map((phase, i) => (
              <div key={i} className={`border rounded-2xl p-6 ${phase.done ? 'border-green-700/40 bg-green-900/10' : 'border-gray-800 bg-gray-900'}`}>
                <div className="flex items-center gap-3 mb-4">
                  <span className={`text-xs font-bold px-3 py-1 rounded-full ${phase.done ? 'bg-green-900/50 text-green-400' : 'bg-blue-900/50 text-blue-400'}`}>
                    {phase.phase}
                  </span>
                  <h3 className="font-semibold text-white">{phase.title}</h3>
                </div>
                <ul className="grid md:grid-cols-2 gap-2">
                  {phase.items.map((item, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-gray-400">
                      <span className={`mt-1 flex-shrink-0 ${phase.done ? 'text-green-400' : 'text-blue-400'}`}>
                        {phase.done ? '✓' : '◦'}
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SEO-rich Why us section */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-12">{tx.whyTitle}</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {tx.why.map((item, i) => (
              <div key={i} className="flex gap-4 bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <item.icon size={20} className="text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SEO Keywords section - naturally embedded */}
      <section className="py-12 px-6 bg-gray-900/40">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-xl font-bold mb-4">{tx.marketsTitle}</h2>
          <p className="text-gray-400 text-sm mb-6">
            {tx.marketsSub}
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {tx.markets.map((market, i) => (
              <span key={i} className="bg-gray-800 border border-gray-700 text-gray-300 text-sm px-4 py-1.5 rounded-full">
                {market}
              </span>
            ))}
          </div>
          <p className="text-gray-600 text-xs mt-6">
            {tx.keywords}
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Star size={12} />
            {tx.ctaBadge}
          </div>
          <h2 className="text-3xl font-bold mb-4">{tx.ctaTitle}</h2>
          <p className="text-gray-400 mb-8">
            {tx.ctaSub}
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link to={isAr ? '/register' : '/en/register'}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-xl font-semibold transition-all hover:scale-105 shadow-lg shadow-blue-500/25">
              {tx.ctaStart}
              <ChevronCta size={18} />
            </Link>
            <Link to={isAr ? '/about' : '/en/about'} className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3.5 rounded-xl font-medium transition">
              {tx.ctaAbout}
            </Link>
          </div>
        </div>
      </section>

    </PublicLayout>
  )
}
