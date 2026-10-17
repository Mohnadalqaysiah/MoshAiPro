import { Link } from 'react-router-dom'
import { Layers, Zap, Bell, Gauge, Globe, ArrowRight, BookOpen, Blocks } from 'lucide-react'
import { useEffect } from 'react'
import PublicLayout from '../components/PublicLayout'
import StrategyBuilderDemo from '../components/StrategyBuilderDemo'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'
import useFAQSchema from '../hooks/useFAQSchema'

// (2026-10-08) StrategyBuilderDemo يستخدم class="reveal" (نفس نمط
// Landing.jsx) — تبدأ opacity:0 وما تظهر إلا لما IntersectionObserver
// يضيف .visible. بدون هالـhook هون، القسم يحجز مساحته بالصفحة بس يضل
// شفّافاً بالكامل — بالضبط الفجوة الفارغة يلي ظهرت بالصفحة.
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.reveal, .reveal-left, .reveal-stagger')
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('visible')
          e.target.querySelectorAll('.stagger-child').forEach((c, i) => {
            setTimeout(() => c.classList.add('visible'), i * 120)
          })
        }
      }),
      { threshold: 0.12 }
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [])
}

// مقالات المدونة المرتبطة مباشرة بهالميزة — نفس التصنيف "باني الاستراتيجيات"
// بالمدونة، وأقدم مقال SMC عام يفيد يفهم المصطلحات قبل ما يبني
const RELATED_POSTS = [
  { slug: 'build-your-own-trading-strategy', titleAr: 'كيف تبني استراتيجية تداول خاصة بك بدون أي برمجة', titleEn: 'How to Build Your Own Trading Strategy — No Coding Required' },
  { slug: 'ict-strategy-automation',          titleAr: 'حوّل استراتيجية ICT الخاصة بك إلى تنبيهات آلية على تلجرام', titleEn: 'Turn Your ICT Strategy Into Automated Telegram Alerts' },
  { slug: 'trading-strategy-mistakes',        titleAr: 'لماذا لا تُطلق استراتيجيتك أي تنبيه؟ خمسة أخطاء شائعة وحلولها', titleEn: 'Why Does Your Strategy Never Fire? Five Common Mistakes and Their Fixes' },
  { slug: 'smart-money-concepts-smc-guide',   titleAr: 'ما هو Smart Money Concepts SMC — الدليل الشامل للمتداول العربي', titleEn: 'What is Smart Money Concepts (SMC) — Complete Arabic Trader Guide' },
]

const T = {
  ar: {
    badge: 'أداة بناء الاستراتيجيات',
    h1a: 'ابنِ استراتيجيتك بنفسك',
    h1b: 'بلا سطر كود واحد',
    heroSub: 'اختر شروط SMC/ICT ومؤشرات فنية حقيقية — Order Block، FVG، اكتساح سيولة، RSI، EMA — واتركها تراقب السوق بدلاً عنك على مدار الساعة. بمجرد ما تتحقق كل شروطك، توصلك رسالة Telegram فورية بالتفاصيل الكاملة.',
    ctaTry: 'جرّب الآن مجاناً',
    ctaLogin: 'افتح الأداة',
    features: [
      { icon: Layers,  title: 'شروط ICT/SMC حقيقية',   desc: 'كسر هيكل، اكتساح سيولة، فجوة سعرية، كتلة أوامر — نفس الأدوات يلي يستخدمها محرك الإشارات.' },
      { icon: Gauge,   title: 'وزن كل شرط بإيدك',       desc: 'حدّد نسبة أهمية كل شرط وعتبة التفعيل — الاستراتيجية تتحقق بس لما تتجاوز الحد يلي حدّدته.' },
      { icon: Bell,    title: 'تنبيه Telegram فوري',    desc: 'المنصة تفحص السوق تلقائياً كل 5 دقائق — ولما تتحقق كل شروطك، توصلك رسالة كاملة بلا ما تفتح الشارت.' },
      { icon: Globe,   title: '25+ سوق مدعوم',          desc: 'ذهب، فضة، بيتكوين وعملات رقمية، فوركس، مؤشرات، وأسواق خليجية زي تداول وأرامكو.' },
    ],
    howTitle: 'كيف تشتغل؟',
    how: [
      { step: '01', title: 'اختر الشروط',      desc: 'من قائمة شروط SMC/ICT ومؤشرات فنية جاهزة — بلا أي كود.' },
      { step: '02', title: 'حدّد العتبة',       desc: 'وزّع الأهمية بين الشروط وحدّد نسبة التفعيل اللي تناسبك.' },
      { step: '03', title: 'فعّلها وراقب',      desc: 'المنصة تراقب السوق بدلاً عنك، وترسلك تنبيه Telegram لحظة التحقق.' },
    ],
    glossaryTitle: 'قاموس المصطلحات — لمين مش خبير',
    glossarySub: 'كل شرط من هاي الشروط حقيقي ومستخدَم فعلياً بمحرك الإشارات — مو تسويق، هاي نفس الأدوات.',
    glossary: [
      { term: 'كسر هيكل (BOS)', desc: 'لما السعر يكسر أعلى قمة سابقة (باتجاه صاعد) أو أدنى قاع سابق (باتجاه هابط) — أول إشارة إن الاتجاه تغيّر أو استمر بقوة.' },
      { term: 'اكتساح سيولة (Liquidity Sweep)', desc: 'السعر يتجاوز مستوى فيه أوامر إيقاف كثيرة (قمة أو قاع واضح) لحظياً بهدف "اصطياد" هالأوامر، وبعدها يرتد بالاتجاه المعاكس — حركة مؤسسية كلاسيكية قبل الدخول الحقيقي.' },
      { term: 'فجوة سعرية (FVG)', desc: 'منطقة بالشارت السعر فيها تحرّك بسرعة بلا تداول متوازن — السعر عادة يرجع يزورها قبل ما يكمل، فبتصير منطقة دخول محتملة.' },
      { term: 'كتلة أوامر (Order Block)', desc: 'آخر شمعة معاكسة قبل حركة قوية بالاتجاه التاني — تُعتبر أثر دخول مؤسسي كبير، ولما السعر يرجعلها بيكون احتمال الارتداد أعلى.' },
      { term: 'منطقة تفعيل زمنية (Kill Zone)', desc: 'أوقات محدّدة باليوم (افتتاح لندن، افتتاح نيويورك...) فيها السيولة والحركة أعلى — نفس الإعداد ممكن يكون أقوى لو صار بهالنافذة الزمنية.' },
      { term: 'RSI < 30 (تشبع بيعي)', desc: 'مؤشر زخم كلاسيكي — لما ينزل تحت 30 بيعني السعر انباع بقوة وممكن يكون قريب من ارتداد صاعد.' },
      { term: 'السعر فوق EMA20', desc: 'متوسط متحرك أسّي لآخر 20 شمعة — السعر فوقه عادة يشير لاتجاه صاعد قصير المدى.' },
    ],
    examplesTitle: 'أمثلة استراتيجيات جاهزة',
    examplesSub: 'نقاط بداية حقيقية — عدّلها بإيدك أو استخدمها كما هي',
    examples: [
      { name: 'الاختراق المؤسسي', conditions: ['كسر هيكل (BOS)', 'اكتساح سيولة', 'كتلة أوامر'], desc: 'تستهدف استمرار الاتجاه بعد حركة مؤسسية واضحة — مناسبة لمتابعي الترند.' },
      { name: 'التصحيح بالثقة', conditions: ['فجوة سعرية (FVG)', 'السعر فوق EMA20', 'RSI < 30'], desc: 'تدخل على تصحيح مؤقت داخل اتجاه صاعد قائم — مناسبة لمن يفضّل الدخول بسعر أفضل.' },
      { name: 'الجلسة الذهبية', conditions: ['منطقة تفعيل زمنية', 'كسر هيكل (BOS)', 'اكتساح سيولة'], desc: 'تفلتر الإشارات على أوقات السيولة العالية بس — تقلّل الإشارات الضعيفة بالأوقات الهادئة.' },
    ],
    faqTitle: 'أسئلة شائعة',
    faq: [
      { q: 'هل أحتاج خبرة برمجة؟', a: 'لا إطلاقاً. تختار الشروط من قائمة جاهزة بنقرات، والمنصة تتكفّل بباقي التحليل التقني تلقائياً.' },
      { q: 'هل تشتغل على كل الأسواق؟', a: 'نعم — أكتر من 25 سوق: ذهب، فضة، بيتكوين وعملات رقمية، فوركس، مؤشرات، وأسواق خليجية زي تداول وأرامكو.' },
      { q: 'شو الفرق بينها وبين إشارات المنصة الجاهزة؟', a: 'إشارات المنصة جاهزة ومبنية على محرك التحليل الموحّد للجميع. باني الاستراتيجيات يخليك تحدّد شروطك الخاصة وتراقب فقط الإعداد اللي يهمّك.' },
      { q: 'كم استراتيجية أقدر أبني وأشغّل بنفس الوقت؟', a: 'يعتمد على باقتك — راجع صفحة الأسعار للتفاصيل الكاملة لكل باقة.' },
      { q: 'هل بتوصلني تنبيهات على الموبايل؟', a: 'نعم، عبر بوت Telegram مباشرة — بلا حاجة لفتح التطبيق أو الشارت.' },
    ],
    relatedTitle: 'مقالات ذات صلة',
  },
  en: {
    badge: 'Strategy Builder',
    h1a: 'Build Your Own Strategy',
    h1b: 'Without Writing Code',
    heroSub: 'Pick real SMC/ICT conditions and technical indicators — Order Block, FVG, Liquidity Sweep, RSI, EMA — and let the platform watch the market for you around the clock. The moment all your conditions align, you get an instant Telegram message with full details.',
    ctaTry: 'Try It Free Now',
    ctaLogin: 'Open The Tool',
    features: [
      { icon: Layers,  title: 'Real ICT/SMC Conditions', desc: 'Break of Structure, Liquidity Sweep, Fair Value Gap, Order Block — the same tools our signal engine uses.' },
      { icon: Gauge,   title: 'Weight Every Condition',   desc: 'Set each condition\'s importance and your activation threshold — the strategy triggers only once it crosses your bar.' },
      { icon: Bell,    title: 'Instant Telegram Alert',   desc: 'The platform auto-checks the market every 5 minutes — once all your conditions align, you get a full alert without opening a chart.' },
      { icon: Globe,   title: '25+ Supported Markets',    desc: 'Gold, Silver, Bitcoin and crypto, Forex, indices, and Gulf markets like Tadawul and Aramco.' },
    ],
    howTitle: 'How It Works',
    how: [
      { step: '01', title: 'Pick Conditions',  desc: 'Choose from ready SMC/ICT conditions and technical indicators — no code needed.' },
      { step: '02', title: 'Set The Threshold', desc: 'Distribute weight across conditions and pick the activation percentage that fits you.' },
      { step: '03', title: 'Activate & Watch',  desc: 'The platform monitors the market for you and sends a Telegram alert the moment it triggers.' },
    ],
    glossaryTitle: 'Glossary — For Non-Experts',
    glossarySub: "Every condition below is real and actually used by our signal engine — not marketing, the same tools.",
    glossary: [
      { term: 'Break of Structure (BOS)', desc: "When price breaks a previous swing high (uptrend) or swing low (downtrend) — the first sign a trend has reversed or is continuing with strength." },
      { term: 'Liquidity Sweep', desc: 'Price briefly pierces a level with lots of stop orders (an obvious high or low) to "hunt" them, then reverses — a classic institutional move before the real entry.' },
      { term: 'Fair Value Gap (FVG)', desc: 'A zone on the chart where price moved fast with unbalanced trading — price often revisits it before continuing, making it a potential entry zone.' },
      { term: 'Order Block', desc: 'The last opposite-direction candle before a strong move — considered a footprint of large institutional entry; price returning to it raises the odds of a bounce.' },
      { term: 'Kill Zone', desc: 'Specific times of day (London open, New York open...) when liquidity and movement are higher — the same setup can carry more weight inside this window.' },
      { term: 'RSI < 30 (Oversold)', desc: 'A classic momentum indicator — dropping below 30 means price has been sold off hard and may be close to a bullish bounce.' },
      { term: 'Price Above EMA20', desc: "A 20-candle exponential moving average — price trading above it usually signals a short-term uptrend." },
    ],
    examplesTitle: 'Ready Strategy Examples',
    examplesSub: 'Real starting points — tweak them or use as-is',
    examples: [
      { name: 'Institutional Breakout', conditions: ['Break of Structure', 'Liquidity Sweep', 'Order Block'], desc: 'Targets trend continuation after a clear institutional move — suited for trend followers.' },
      { name: 'Confident Pullback', conditions: ['Fair Value Gap', 'Price Above EMA20', 'RSI < 30'], desc: 'Enters on a temporary pullback within an existing uptrend — suited for those who prefer a better entry price.' },
      { name: 'Golden Session', conditions: ['Kill Zone', 'Break of Structure', 'Liquidity Sweep'], desc: 'Filters signals to high-liquidity hours only — cuts weak signals during quiet hours.' },
    ],
    faqTitle: 'Frequently Asked Questions',
    faq: [
      { q: 'Do I need coding experience?', a: 'Not at all. You pick conditions from a ready list with a few clicks, and the platform handles all the technical analysis automatically.' },
      { q: 'Does it work on every market?', a: 'Yes — 25+ markets: Gold, Silver, Bitcoin and crypto, Forex, indices, and Gulf markets like Tadawul and Aramco.' },
      { q: "What's the difference versus the platform's ready signals?", a: "Ready signals are built on the shared analysis engine for everyone. Strategy Builder lets you define your own conditions and monitor only the setup that matters to you." },
      { q: 'How many strategies can I build and run at once?', a: 'Depends on your plan — check the pricing page for full details per tier.' },
      { q: 'Will I get alerts on mobile?', a: 'Yes, directly through our Telegram bot — no need to open the app or a chart.' },
    ],
    relatedTitle: 'Related Articles',
  },
}

export default function StrategyBuilderPage() {
  const { user } = useAuth()
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']
  useReveal()

  useSEO({
    title: isAr
      ? 'أداة بناء الاستراتيجيات | Qaffel AI — راقب السوق تلقائياً بشروطك'
      : 'Strategy Builder | Qaffel AI — Monitor The Market On Your Own Terms',
    description: isAr
      ? 'ابنِ استراتيجية تداول بشروط ICT/SMC حقيقية بلا أي كود، والمنصة تراقب السوق تلقائياً وترسلك تنبيه Telegram فوري لحظة تحققها.'
      : 'Build a trading strategy from real ICT/SMC conditions with no code — the platform monitors the market and sends an instant Telegram alert the moment it triggers.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: tx.badge, path: isAr ? '/strategy-builder' : '/en/strategy-builder' },
  ])
  useFAQSchema('ld-faq-strategy-builder', tx.faq)

  const ICO = ['', 'gold', 'sky', 'coral']
  return (
    <PublicLayout>

      {/* Hero */}
      <section className="qp-hero">
        <div className="qp-wrap qp-narrow">
          <span className="qp-eyebrow">{tx.badge}</span>
          <h1 className="qp-h1">{tx.h1a} <span className="qp-grad">{tx.h1b}</span></h1>
          <p className="qp-lead">{tx.heroSub}</p>
          <div className="qp-btns">
            <Link to={user ? (isAr ? '/strategies' : '/en/strategies') : (isAr ? '/register' : '/en/register')} className="qp-btn qp-mint">
              <Zap size={16} />
              {user ? tx.ctaLogin : tx.ctaTry}
              <ArrowRight size={15} className="rtl:rotate-180" />
            </Link>
            <a href="#demo" className="qp-btn qp-line">{isAr ? 'جرّب العرض التفاعلي' : 'Try the live demo'}</a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="qp-sec" style={{ paddingTop: 0 }}>
        <div className="qp-wrap qp-grid qp-g4">
          {tx.features.map((f, i) => (
            <div key={i} className="qp-card qp-hover">
              <span className={`qp-ico ${ICO[i % 4]}`} style={{ marginBottom: 14 }}><f.icon size={20} /></span>
              <h3 className="qp-h3" style={{ fontSize: 16, marginBottom: 6 }}>{f.title}</h3>
              <p className="qp-sub" style={{ fontSize: 14 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="qp-sec qp-band">
        <div className="qp-wrap">
          <div className="qp-head"><h2 className="qp-h2">{tx.howTitle}</h2></div>
          <div className="qp-grid qp-g3">
            {tx.how.map((st, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div className="qp-step" style={{ marginBottom: 16 }}>{st.step}</div>
                <h3 className="qp-h3" style={{ marginBottom: 6 }}>{st.title}</h3>
                <p className="qp-sub" style={{ fontSize: 14, maxWidth: '32ch', marginInline: 'auto' }}>{st.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Interactive demo — عنده عنوانه ومقدّمته الخاصة أصلاً */}
      <div id="demo" style={{ scrollMarginTop: 80 }}>
        <StrategyBuilderDemo isAr={isAr} />
      </div>

      {/* Glossary */}
      <section className="qp-sec">
        <div className="qp-wrap">
          <div className="qp-head">
            <span className="qp-eyebrow"><BookOpen size={14} /> {tx.glossaryTitle}</span>
            <p className="qp-sub">{tx.glossarySub}</p>
          </div>
          <div className="qp-grid qp-g2">
            {tx.glossary.map((g, i) => (
              <div key={i} className="qp-card">
                <h3 className="qp-h3" style={{ fontSize: 16, color: 'var(--mint)', marginBottom: 6 }}>{g.term}</h3>
                <p className="qp-sub" style={{ fontSize: 14 }}>{g.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Example strategies */}
      <section className="qp-sec qp-band">
        <div className="qp-wrap">
          <div className="qp-head">
            <span className="qp-eyebrow"><Blocks size={14} /> {tx.examplesTitle}</span>
            <p className="qp-sub">{tx.examplesSub}</p>
          </div>
          <div className="qp-grid qp-g3">
            {tx.examples.map((ex, i) => (
              <div key={i} className={`qp-card qp-hover ${i === 0 ? 'qp-mintline' : i === 1 ? 'qp-goldline' : ''}`} style={{ display: 'flex', flexDirection: 'column' }}>
                <h3 className="qp-h3" style={{ marginBottom: 12 }}>{ex.name}</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
                  {ex.conditions.map(c => <span key={c} className="qp-chip sm">{c}</span>)}
                </div>
                <p className="qp-sub" style={{ fontSize: 14 }}>{ex.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="qp-sec">
        <div className="qp-wrap qp-narrow">
          <div className="qp-head"><h2 className="qp-h2">{tx.faqTitle}</h2></div>
          <div className="qp-faq">
            {tx.faq.map((f, i) => (
              <details key={i}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Related articles */}
      <section className="qp-sec" style={{ paddingTop: 0 }}>
        <div className="qp-wrap qp-narrow">
          <h2 className="qp-h3" style={{ fontSize: 20, marginBottom: 16 }}>{tx.relatedTitle}</h2>
          <div className="qp-grid qp-g2" style={{ gap: 12 }}>
            {RELATED_POSTS.map(p => (
              <Link key={p.slug} to={isAr ? `/blog/${p.slug}` : `/en/blog/${p.slug}`} className="qp-card"
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '14px 18px' }}>
                <span style={{ fontSize: 14, color: '#C9D5EA' }}>{isAr ? p.titleAr : p.titleEn}</span>
                <ArrowRight size={15} className="rtl:rotate-180" style={{ color: 'var(--mint)', flexShrink: 0 }} />
              </Link>
            ))}
          </div>
        </div>
      </section>

    </PublicLayout>
  )
}
