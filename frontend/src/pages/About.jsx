import { Link } from 'react-router-dom'
import { Users, Brain, Globe, Shield, Award, TrendingUp, Star } from 'lucide-react'
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
      { icon: TrendingUp, title: 'إشارات وتوصيات دقيقة', items: ['إشارات شراء/بيع مع مستويات الدخول', 'حساب وقف الخسارة والأهداف', 'تحديد حجم الصفقة المناسب', 'متابعة نتيجة كل إشارة حتى إغلاقها'] },
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
      { icon: TrendingUp, title: 'Accurate Signals & Recommendations', items: ['Buy/sell signals with entry levels', 'Stop-loss and target calculation', 'Proper position sizing', 'Tracking every signal’s outcome until it closes'] },
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

      {/* Story */}
      <section className="qp-sec" style={{ paddingTop: 0 }}>
        <div className="qp-wrap">
          <div className="qp-grid qp-g2" style={{ alignItems: 'center', gap: 'clamp(24px,5vw,56px)' }}>
            <div>
              <h2 className="qp-h2" style={{ marginBottom: 16 }}>{tx.storyTitle}</h2>
              {tx.storyP.map((p, i) => (
                <p key={i} className="qp-sub" style={{ marginBottom: 14 }}>{p}</p>
              ))}
            </div>
            <div className="qp-grid qp-g2 keep2" style={{ gridTemplateColumns: 'repeat(2,minmax(0,1fr))' }}>
              {tx.storyCards.map((item, i) => (
                <div key={i} className="qp-card qp-hover" style={{ textAlign: 'center' }}>
                  <span className={`qp-ico ${ICO[i % 4]}`} style={{ margin: '0 auto 12px' }}><item.icon size={20} /></span>
                  <p style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>{item.label}</p>
                  <p className="qp-faint" style={{ fontSize: 13, marginTop: 4 }}>{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* What we offer */}
      <section className="qp-sec qp-band">
        <div className="qp-wrap">
          <div className="qp-head"><h2 className="qp-h2">{tx.offerTitle}</h2></div>
          <div className="qp-grid qp-g3">
            {tx.offerCols.map((col, i) => (
              <div key={i} className="qp-card qp-hover">
                <span className={`qp-ico ${ICO[i % 4]}`} style={{ marginBottom: 16 }}><col.icon size={20} /></span>
                <h3 className="qp-h3" style={{ marginBottom: 14 }}>{col.title}</h3>
                <ul className="qp-check">
                  {col.items.map((it, j) => <li key={j}>{it}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="qp-sec">
        <div className="qp-wrap">
          <div className="qp-head"><h2 className="qp-h2">{tx.valuesTitle}</h2></div>
          <div className="qp-grid qp-g2">
            {tx.values.map((v, i) => (
              <div key={i} className="qp-card qp-hover" style={{ display: 'flex', gap: 16 }}>
                <span className={`qp-ico ${ICO[i % 4]}`}><v.icon size={20} /></span>
                <div>
                  <h3 className="qp-h3" style={{ marginBottom: 6 }}>{v.title}</h3>
                  <p className="qp-sub" style={{ fontSize: 14 }}>{v.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Disclaimer */}
      <div className="qp-wrap qp-narrow">
        <div className="qp-note">
          <Star size={16} />
          <p><strong style={{ color: '#fff' }}>{tx.disclaimerLabel}</strong> {tx.disclaimer}</p>
        </div>
      </div>

      {/* CTA */}
      <section className="qp-sec">
        <div className="qp-wrap">
          <div className="qp-cta">
            <h2 className="qp-h2">{tx.ctaTitle}</h2>
            <p className="qp-lead">{tx.ctaSub}</p>
            <div className="qp-btns">
              <Link to={isAr ? '/register' : '/en/register'} className="qp-btn qp-mint">{tx.ctaStart}</Link>
              <Link to={isAr ? '/vision' : '/en/vision'} className="qp-btn qp-line">{tx.ctaVision}</Link>
            </div>
          </div>
        </div>
      </section>

    </PublicLayout>
  )
}
