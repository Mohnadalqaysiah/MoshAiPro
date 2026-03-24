import { createContext, useContext, useState } from 'react'

const LangContext = createContext()

export const translations = {
  ar: {
    dir: 'rtl',
    nav: {
      features: 'المميزات',
      pricing:  'الأسعار',
      faq:      'الأسئلة',
      about:    'من نحن',
      contact:  'تواصل',
      login:    'دخول',
      start:    'ابدأ مجاناً',
      dashboard:'لوحة التحكم',
    },
    hero: {
      badge:    'يعمل بتقنية Gemini AI + ICT/SMC الاحترافية',
      h1a:      'تداول بذكاء مع',
      h1b:      'الذكاء الاصطناعي',
      sub:      'إشارات تداول دقيقة للذهب، البيتكوين والفوركس — مدعومة بتحليل ICT/SMC/Wyckoff المؤسسي وتُرسل مباشرة على Telegram.',
      cta1:     'ابدأ تجربة مجانية',
      cta2:     'عرض الأسعار',
      note:     '10 تحليلات مجانية · بدون بطاقة ائتمان',
    },
    stats: [
      { value: '4',     label: 'أسواق مدعومة' },
      { value: '15+',   label: 'مؤشر ICT/SMC' },
      { value: '24/7',  label: 'تحليل مستمر' },
      { value: '< 30ث', label: 'وقت التحليل' },
    ],
    featuresTitle: 'كل ما تحتاجه في منصة واحدة',
    featuresSub:   'تحليل احترافي بمستوى المؤسسات — متاح للجميع',
    features: [
      { title: 'تحليل ICT/SMC المتقدم',      desc: 'Order Blocks، FVG، Liquidity Sweep، BOS/CHoCH، Premium/Discount — بنفس أدوات المتداولين المؤسسيين.' },
      { title: 'وكيل AI للمحادثة',            desc: 'اسأل عن أي زوج — يحلل السوق ويعطيك خطة تداول كاملة مع مستويات الدخول والخروج.' },
      { title: 'تنبيهات Telegram فورية',      desc: 'استقبل الإشارات والتنبيهات مباشرة على هاتفك عبر بوت @Qaffelbot بمجرد ربط حسابك.' },
      { title: 'Multi-Timeframe Analysis',    desc: 'تحليل مزدوج HTF (4H) + LTF (1H) لتأكيد الاتجاه والدخول في الوقت المناسب.' },
      { title: 'إدارة رأس المال',             desc: 'حساب تلقائي لحجم الصفقة بناءً على رصيدك ونسبة المخاطرة مع نظام تقييم A+/A/B/C.' },
      { title: 'Wyckoff المؤسسي',             desc: 'تحديد مراحل التجميع والتوزيع، Spring، UTAD، و Effort vs Result لفهم نوايا Smart Money.' },
    ],
    howTitle: 'كيف يعمل؟',
    how: [
      { step: '01', title: 'سجّل مجاناً',         desc: 'أنشئ حسابك في 30 ثانية واحصل على 10 تحليلات مجانية لتجربة المنصة.' },
      { step: '02', title: 'اختر السوق والإطار',   desc: 'اختر من XAUUSD أو BTCUSD أو EURUSD أو GBPUSD واضغط تحليل.' },
      { step: '03', title: 'استقبل الإشارة',        desc: 'خلال ثوانٍ تحصل على توصية كاملة مع الدخول والوقف والأهداف وحجم الصفقة.' },
    ],
    pricingTitle: 'أسعار بسيطة وشفافة',
    pricingSub:   'ابدأ مجاناً ثم اشترك بما يناسبك',
    plans: [
      { name: 'تجريبي',  price: 'مجاني', period: '',        badge: null,       features: ['10 تحليلات', '20 رسالة شات', 'جميع الأسواق', 'ربط Telegram'],                                              cta: 'ابدأ مجاناً',  href: '/register', highlight: false },
      { name: 'أسبوعي', price: '$7',    period: '/ أسبوع', badge: 'الأكثر طلباً', features: ['تحليلات غير محدودة', 'شات غير محدود', 'جميع الأسواق', 'ربط Telegram', 'تحليل متعدد الفريمات'], cta: 'اشترك الآن', href: '/pricing',  highlight: true },
      { name: 'شهري',   price: '$30',   period: '/ شهر',   badge: null,       features: ['تحليلات غير محدودة', 'شات غير محدود', 'جميع الأسواق', 'ربط Telegram', 'أولوية الدعم'],                 cta: 'اشترك الآن', href: '/pricing',  highlight: false },
    ],
    faqTitle: 'الأسئلة الشائعة',
    faq: [
      { q: 'هل الإشارات مضمونة الربح؟',      a: 'لا. التحليل مبني على بيانات تقنية حقيقية لكنه ليس نصيحة مالية. التداول ينطوي على مخاطر وأنت مسؤول عن قراراتك.' },
      { q: 'ما الأسواق المدعومة؟',            a: 'حالياً: الذهب (XAUUSD)، البيتكوين (BTCUSD)، اليورو/دولار (EURUSD)، الجنيه/دولار (GBPUSD).' },
      { q: 'كيف يعمل ربط Telegram؟',         a: 'من لوحة التحكم اضغط "ربط مع Telegram" وسيتوجه لك رابط تشغيل البوت @Qaffelbot تلقائياً.' },
      { q: 'هل يمكنني إلغاء الاشتراك؟',      a: 'نعم، الاشتراك غير ملزم. ينتهي تلقائياً عند نهاية المدة ولا يتجدد.' },
      { q: 'ما طرق الدفع المتاحة؟',          a: 'ندعم USDT (TRC20) حالياً. التسعير بالدولار الأمريكي.' },
    ],
    ctaTitle: 'جاهز تبدأ؟',
    ctaSub:   '10 تحليلات مجانية. بدون بطاقة ائتمان.',
    ctaBtn:   'ابدأ مجاناً الآن',
    footer: {
      platform: 'المنصة',
      company:  'الشركة',
      legal:    'قانوني',
      contact:  'تواصل',
      register: 'التسجيل',
      login:    'الدخول',
      pricing:  'الأسعار',
      about:    'من نحن',
      vision:   'رؤيتنا',
      terms:    'الشروط والأحكام',
      privacy:  'سياسة الخصوصية',
      contactUs:'اتصل بنا',
      copy:     '© 2026 Qaffel AI. جميع الحقوق محفوظة.',
      disclaimer:'هذا تحليل تقني فقط وليس نصيحة مالية أو استثمارية',
    },
  },

  en: {
    dir: 'ltr',
    nav: {
      features: 'Features',
      pricing:  'Pricing',
      faq:      'FAQ',
      about:    'About Us',
      contact:  'Contact',
      login:    'Login',
      start:    'Start Free',
      dashboard:'Dashboard',
    },
    hero: {
      badge:    'Powered by Gemini AI + Professional ICT/SMC',
      h1a:      'Trade Smarter with',
      h1b:      'Artificial Intelligence',
      sub:      'Accurate trading signals for Gold, Bitcoin & Forex — powered by institutional ICT/SMC/Wyckoff analysis, delivered directly to Telegram.',
      cta1:     'Start Free Trial',
      cta2:     'View Pricing',
      note:     '10 free analyses · No credit card required',
    },
    stats: [
      { value: '4',      label: 'Markets Supported' },
      { value: '15+',    label: 'ICT/SMC Indicators' },
      { value: '24/7',   label: 'Continuous Analysis' },
      { value: '< 30s',  label: 'Analysis Time' },
    ],
    featuresTitle: 'Everything You Need in One Platform',
    featuresSub:   'Institutional-grade analysis — available to everyone',
    features: [
      { title: 'Advanced ICT/SMC Analysis',  desc: 'Order Blocks, FVG, Liquidity Sweep, BOS/CHoCH, Premium/Discount — the same tools used by institutional traders.' },
      { title: 'AI Chat Agent',              desc: 'Ask about any pair — it analyzes the market and gives you a complete trade plan with entry and exit levels.' },
      { title: 'Instant Telegram Alerts',   desc: 'Receive signals and alerts directly on your phone via @Qaffelbot as soon as you link your account.' },
      { title: 'Multi-Timeframe Analysis',  desc: 'Dual analysis HTF (4H) + LTF (1H) to confirm trend and time entries correctly.' },
      { title: 'Risk Management',           desc: 'Auto position sizing based on your balance and risk percentage with A+/A/B/C rating system.' },
      { title: 'Institutional Wyckoff',     desc: 'Identify accumulation/distribution phases, Spring, UTAD, and Effort vs Result to understand Smart Money intent.' },
    ],
    howTitle: 'How Does It Work?',
    how: [
      { step: '01', title: 'Register Free',        desc: 'Create your account in 30 seconds and get 10 free analyses to try the platform.' },
      { step: '02', title: 'Choose Market & Frame', desc: 'Select XAUUSD, BTCUSD, EURUSD or GBPUSD and press Analyze.' },
      { step: '03', title: 'Receive Your Signal',   desc: 'Within seconds you get a complete recommendation with entry, stop loss, targets and position size.' },
    ],
    pricingTitle: 'Simple, Transparent Pricing',
    pricingSub:   'Start free then subscribe to whatever suits you',
    plans: [
      { name: 'Trial',   price: 'Free',  period: '',          badge: null,      features: ['10 Analyses', '20 Chat Messages', 'All Markets', 'Telegram Link'],                                      cta: 'Start Free',     href: '/register', highlight: false },
      { name: 'Weekly',  price: '$7',    period: '/ week',    badge: 'Popular', features: ['Unlimited Analyses', 'Unlimited Chat', 'All Markets', 'Telegram Link', 'Multi-Timeframe Analysis'], cta: 'Subscribe Now', href: '/pricing',  highlight: true },
      { name: 'Monthly', price: '$30',   period: '/ month',   badge: null,      features: ['Unlimited Analyses', 'Unlimited Chat', 'All Markets', 'Telegram Link', 'Priority Support'],          cta: 'Subscribe Now', href: '/pricing',  highlight: false },
    ],
    faqTitle: 'Frequently Asked Questions',
    faq: [
      { q: 'Are signals guaranteed to be profitable?', a: 'No. Analysis is based on real technical data but is not financial advice. Trading involves risk and you are responsible for your decisions.' },
      { q: 'What markets are supported?',              a: 'Currently: Gold (XAUUSD), Bitcoin (BTCUSD), EUR/USD, GBP/USD. More coming soon.' },
      { q: 'How does Telegram linking work?',          a: 'From the dashboard click "Link with Telegram" and you will be redirected to activate @Qaffelbot automatically.' },
      { q: 'Can I cancel my subscription?',            a: 'Yes, subscriptions are non-binding. They expire automatically and do not renew.' },
      { q: 'What payment methods are available?',      a: 'We currently support USDT (TRC20). Pricing is in US dollars.' },
    ],
    ctaTitle: 'Ready to Start?',
    ctaSub:   '10 free analyses. No credit card required.',
    ctaBtn:   'Start Free Now',
    footer: {
      platform: 'Platform',
      company:  'Company',
      legal:    'Legal',
      contact:  'Contact',
      register: 'Sign Up',
      login:    'Login',
      pricing:  'Pricing',
      about:    'About Us',
      vision:   'Our Vision',
      terms:    'Terms & Conditions',
      privacy:  'Privacy Policy',
      contactUs:'Contact Us',
      copy:     '© 2026 Qaffel AI. All rights reserved.',
      disclaimer:'This is technical analysis only and not financial or investment advice',
    },
  },
}

export function LangProvider({ children }) {
  const [lang, setLang] = useState('ar')
  const toggle = () => setLang(l => l === 'ar' ? 'en' : 'ar')
  const t = translations[lang]
  return (
    <LangContext.Provider value={{ lang, toggle, t }}>
      {children}
    </LangContext.Provider>
  )
}

export const useLang = () => useContext(LangContext)
