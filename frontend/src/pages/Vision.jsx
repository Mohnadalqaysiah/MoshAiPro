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

  const ICO = ['', 'gold', 'sky', 'coral']
  return (
    <PublicLayout>

      {/* Hero */}
      <section className="qp-hero">
        <div className="qp-wrap qp-narrow">
          <span className="qp-eyebrow">{tx.badge}</span>
          <h1 className="qp-h1">{tx.h1a}<br /><span className="qp-grad">{tx.h1b}</span></h1>
          <p className="qp-lead">{tx.heroSub}</p>
        </div>
      </section>

      {/* Vision Statement */}
      <section className="qp-sec" style={{ paddingTop: 0 }}>
        <div className="qp-wrap">
          <div className="qp-grid qp-g2">
            <div className="qp-card qp-mintline" style={{ padding: 'clamp(24px,3.4vw,36px)' }}>
              <span className="qp-ico lg" style={{ marginBottom: 18 }}><Target size={24} /></span>
              <h2 className="qp-h3" style={{ fontSize: 22, marginBottom: 10 }}>{tx.visionTitle}</h2>
              <p className="qp-sub" style={{ color: '#C9D5EA' }}>{tx.visionBody}</p>
            </div>
            <div className="qp-card qp-goldline" style={{ padding: 'clamp(24px,3.4vw,36px)' }}>
              <span className="qp-ico lg gold" style={{ marginBottom: 18 }}><Rocket size={24} /></span>
              <h2 className="qp-h3" style={{ fontSize: 22, marginBottom: 10 }}>{tx.missionTitle}</h2>
              <p className="qp-sub" style={{ color: '#C9D5EA' }}>{tx.missionBody}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Roadmap */}
      <section className="qp-sec qp-band">
        <div className="qp-wrap qp-narrow">
          <div className="qp-head">
            <h2 className="qp-h2">{tx.roadmapTitle}</h2>
            <p className="qp-sub">{tx.roadmapSub}</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {tx.roadmap.map((phase, i) => (
              <div key={i} className={`qp-card ${phase.done ? 'qp-mintline' : ''}`}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                  <span className={`qp-pill ${phase.done ? 'done' : 'next'}`}>{phase.phase.replace(/\s*[✅🔄🔮]\s*$/u, '')}</span>
                  <h3 className="qp-h3">{phase.title}</h3>
                </div>
                <ul className={`qp-check ${phase.done ? '' : 'todo'}`} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 10 }}>
                  {phase.items.map((item, j) => <li key={j}>{item}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why us */}
      <section className="qp-sec">
        <div className="qp-wrap">
          <div className="qp-head"><h2 className="qp-h2">{tx.whyTitle}</h2></div>
          <div className="qp-grid qp-g2">
            {tx.why.map((item, i) => (
              <div key={i} className="qp-card qp-hover" style={{ display: 'flex', gap: 16 }}>
                <span className={`qp-ico ${ICO[i % 4]}`}><item.icon size={20} /></span>
                <div>
                  <h3 className="qp-h3" style={{ marginBottom: 6 }}>{item.title}</h3>
                  <p className="qp-sub" style={{ fontSize: 14 }}>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Markets */}
      <section className="qp-sec qp-band" style={{ paddingBlock: 'clamp(40px,6vw,64px)' }}>
        <div className="qp-wrap qp-narrow" style={{ textAlign: 'center' }}>
          <h2 className="qp-h3" style={{ fontSize: 22, marginBottom: 10 }}>{tx.marketsTitle}</h2>
          <p className="qp-sub" style={{ marginBottom: 22 }}>{tx.marketsSub}</p>
          <div className="qp-chips">
            {tx.markets.map((market, i) => <span key={i} className="qp-chip">{market}</span>)}
          </div>
          <p className="qp-faint" style={{ fontSize: 12, marginTop: 22 }}>{tx.keywords}</p>
        </div>
      </section>

      {/* CTA */}
      <section className="qp-sec">
        <div className="qp-wrap">
          <div className="qp-cta">
            <span className="qp-eyebrow">{tx.ctaBadge}</span>
            <h2 className="qp-h2" style={{ marginTop: 14 }}>{tx.ctaTitle}</h2>
            <p className="qp-lead">{tx.ctaSub}</p>
            <div className="qp-btns">
              <Link to={isAr ? '/register' : '/en/register'} className="qp-btn qp-mint">{tx.ctaStart}<ChevronCta size={18} /></Link>
              <Link to={isAr ? '/about' : '/en/about'} className="qp-btn qp-line">{tx.ctaAbout}</Link>
            </div>
          </div>
        </div>
      </section>

    </PublicLayout>
  )
}
