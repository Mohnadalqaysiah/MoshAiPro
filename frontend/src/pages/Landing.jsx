import { Link } from 'react-router-dom'
import { TrendingUp, Shield, Zap, Bot, Bell, BarChart2, ChevronLeft, CheckCircle, Star } from 'lucide-react'

// ─── SEO meta helper (injected via Helmet-like approach) ──────────────────────
const META = {
  title: 'Mosh AI Pro — تداول بذكاء مع الذكاء الاصطناعي',
  desc:  'منصة تداول احترافية تعتمد على الذكاء الاصطناعي وتحليل ICT/SMC/Wyckoff لتوليد إشارات دقيقة للذهب والبيتكوين والفوركس.',
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-gray-950 text-white" dir="rtl">

      {/* ── Navbar ───────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-sm">M</div>
            <span className="font-bold text-lg">Mosh AI <span className="text-blue-400">Pro</span></span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">المميزات</a>
            <a href="#pricing"  className="hover:text-white transition-colors">الأسعار</a>
            <a href="#faq"      className="hover:text-white transition-colors">الأسئلة</a>
            <Link to="/contact" className="hover:text-white transition-colors">تواصل</Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login"    className="text-sm text-gray-300 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors">دخول</Link>
            <Link to="/register" className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-medium transition-colors">ابدأ مجاناً</Link>
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative py-20 md:py-32 px-4 overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl" />
        </div>
        <div className="max-w-4xl mx-auto text-center relative">
          <div className="inline-flex items-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Zap size={12} />
            يعمل بتقنية Gemini AI + ICT/SMC الاحترافية
          </div>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            تداول بذكاء مع<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-blue-400 to-purple-400">
              الذكاء الاصطناعي
            </span>
          </h1>
          <p className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            إشارات تداول دقيقة للذهب، البيتكوين والفوركس — مدعومة بتحليل ICT/SMC/Wyckoff المؤسسي وتُرسل مباشرة على Telegram.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/register" className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-xl font-semibold text-base transition-all hover:scale-105 shadow-lg shadow-blue-500/25">
              ابدأ تجربة مجانية
              <ChevronLeft size={18} />
            </Link>
            <Link to="/pricing" className="flex items-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3.5 rounded-xl font-medium text-base transition-colors">
              عرض الأسعار
            </Link>
          </div>
          <p className="text-gray-600 text-sm mt-4">10 تحليلات مجانية · بدون بطاقة ائتمان</p>
        </div>
      </section>

      {/* ── Stats ────────────────────────────────────────────────────── */}
      <section className="py-12 px-4 border-y border-gray-800/50">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { value: '4',      label: 'أسواق مدعومة' },
            { value: '15+',    label: 'مؤشر ICT/SMC' },
            { value: '24/7',   label: 'تحليل مستمر' },
            { value: '< 30ث', label: 'وقت التحليل' },
          ].map((s, i) => (
            <div key={i}>
              <div className="text-3xl font-bold text-white mb-1">{s.value}</div>
              <div className="text-gray-500 text-sm">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section id="features" className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">كل ما تحتاجه في منصة واحدة</h2>
            <p className="text-gray-400 max-w-xl mx-auto">تحليل احترافي بمستوى المؤسسات — متاح للجميع</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: <BarChart2 className="text-blue-400" size={24} />,
                title: 'تحليل ICT/SMC المتقدم',
                desc:  'Order Blocks، FVG، Liquidity Sweep، BOS/CHoCH، Premium/Discount — بنفس أدوات المتداولين المؤسسيين.',
                color: 'blue',
              },
              {
                icon: <Bot className="text-purple-400" size={24} />,
                title: 'وكيل AI للمحادثة',
                desc:  'اسأل "مُوش" عن أي زوج بالعامية — يحلل السوق ويعطيك خطة تداول كاملة مع مستويات الدخول والخروج.',
                color: 'purple',
              },
              {
                icon: <Bell className="text-green-400" size={24} />,
                title: 'تنبيهات Telegram فورية',
                desc:  'استقبل الإشارات والتنبيهات مباشرة على هاتفك عبر بوت @ai_hybridbot بمجرد ربط حسابك.',
                color: 'green',
              },
              {
                icon: <TrendingUp className="text-yellow-400" size={24} />,
                title: 'Multi-Timeframe Analysis',
                desc:  'تحليل مزدوج HTF (4H) + LTF (1H) لتأكيد الاتجاه والدخول في الوقت المناسب.',
                color: 'yellow',
              },
              {
                icon: <Shield className="text-red-400" size={24} />,
                title: 'إدارة رأس المال',
                desc:  'حساب تلقائي لحجم الصفقة بناءً على رصيدك ونسبة المخاطرة مع نظام تقييم A+/A/B/C.',
                color: 'red',
              },
              {
                icon: <Zap className="text-cyan-400" size={24} />,
                title: 'Wyckoff المؤسسي',
                desc:  'تحديد مراحل التجميع والتوزيع، Spring، UTAD، و Effort vs Result لفهم نوايا Smart Money.',
                color: 'cyan',
              },
            ].map((f, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-6 hover:border-gray-700 transition-colors">
                <div className="w-12 h-12 bg-gray-800 rounded-xl flex items-center justify-center mb-4">
                  {f.icon}
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section className="py-20 px-4 bg-gray-900/40">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-4">كيف يعمل؟</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'سجّل مجاناً', desc: 'أنشئ حسابك في 30 ثانية واحصل على 10 تحليلات مجانية لتجربة المنصة.' },
              { step: '02', title: 'اختر السوق والإطار', desc: 'اختر من XAUUSD أو BTCUSD أو EURUSD أو GBPUSD واضغط تحليل.' },
              { step: '03', title: 'استقبل الإشارة', desc: 'خلال ثوانٍ تحصل على توصية كاملة مع الدخول والوقف والأهداف وحجم الصفقة.' },
            ].map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-14 h-14 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-blue-400 font-bold text-lg">{s.step}</span>
                </div>
                <h3 className="font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────── */}
      <section id="pricing" className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-4">أسعار بسيطة وشفافة</h2>
            <p className="text-gray-400">ابدأ مجاناً ثم اشترك بما يناسبك</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                name: 'تجريبي',
                price: 'مجاني',
                period: '',
                color: 'border-gray-700',
                features: ['10 تحليلات', '20 رسالة شات', 'جميع الأسواق', 'ربط Telegram'],
                cta: 'ابدأ مجاناً',
                href: '/register',
                highlight: false,
              },
              {
                name: 'أسبوعي',
                price: '$9.99',
                period: '/ أسبوع',
                color: 'border-blue-500',
                features: ['تحليلات غير محدودة', '50 رسالة شات/يوم', 'جميع الأسواق', 'ربط Telegram', 'تحليل متعدد الفريمات'],
                cta: 'اشترك الآن',
                href: '/pricing',
                highlight: true,
              },
              {
                name: 'شهري',
                price: '$29.99',
                period: '/ شهر',
                color: 'border-purple-500',
                features: ['تحليلات غير محدودة', '200 رسالة شات/يوم', 'جميع الأسواق', 'ربط Telegram', 'أولوية الدعم'],
                cta: 'اشترك الآن',
                href: '/pricing',
                highlight: false,
              },
            ].map((p, i) => (
              <div key={i} className={`relative bg-gray-900 border-2 ${p.color} rounded-2xl p-6 ${p.highlight ? 'shadow-xl shadow-blue-500/10' : ''}`}>
                {p.highlight && (
                  <div className="absolute -top-3 right-1/2 translate-x-1/2 bg-blue-600 text-white text-xs px-3 py-1 rounded-full font-medium">
                    الأكثر طلباً
                  </div>
                )}
                <h3 className="font-bold text-white text-lg mb-1">{p.name}</h3>
                <div className="flex items-baseline gap-1 mb-5">
                  <span className="text-3xl font-bold text-white">{p.price}</span>
                  <span className="text-gray-500 text-sm">{p.period}</span>
                </div>
                <ul className="space-y-2.5 mb-6">
                  {p.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm text-gray-300">
                      <CheckCircle size={14} className="text-green-400 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to={p.href}
                  className={`block text-center py-2.5 rounded-xl font-medium text-sm transition-colors ${
                    p.highlight
                      ? 'bg-blue-600 hover:bg-blue-500 text-white'
                      : 'border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white'
                  }`}
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────────────────── */}
      <section id="faq" className="py-20 px-4 bg-gray-900/40">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">الأسئلة الشائعة</h2>
          <div className="space-y-4">
            {[
              { q: 'هل الإشارات مضمونة الربح؟', a: 'لا. التحليل مبني على بيانات تقنية حقيقية لكنه ليس نصيحة مالية. التداول ينطوي على مخاطر وأنت مسؤول عن قراراتك.' },
              { q: 'ما الأسواق المدعومة؟', a: 'حالياً: الذهب (XAUUSD)، البيتكوين (BTCUSD)، اليورو/دولار (EURUSD)، الجنيه/دولار (GBPUSD). سيتم إضافة المزيد قريباً.' },
              { q: 'كيف يعمل ربط Telegram؟', a: 'من لوحة التحكم اضغط "ربط مع Telegram" وسيتوجه لك رابط تشغيل البوت @ai_hybridbot تلقائياً.' },
              { q: 'هل يمكنني إلغاء الاشتراك؟', a: 'نعم، الاشتراك غير ملزم. ينتهي تلقائياً عند نهاية المدة ولا يتجدد.' },
              { q: 'ما طرق الدفع المتاحة؟', a: 'ندعم USDT (TRC20) حالياً. التسعير بالدولار الأمريكي.' },
            ].map((item, i) => (
              <details key={i} className="bg-gray-900 border border-gray-800 rounded-xl group">
                <summary className="flex items-center justify-between px-5 py-4 cursor-pointer list-none font-medium text-white">
                  {item.q}
                  <ChevronLeft size={16} className="text-gray-500 group-open:-rotate-90 transition-transform" />
                </summary>
                <p className="px-5 pb-4 text-gray-400 text-sm leading-relaxed border-t border-gray-800 pt-3">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <section className="py-20 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">جاهز تبدأ؟</h2>
          <p className="text-gray-400 mb-8">10 تحليلات مجانية. بدون بطاقة ائتمان.</p>
          <Link to="/register" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-10 py-4 rounded-xl font-semibold text-lg transition-all hover:scale-105 shadow-lg shadow-blue-500/25">
            ابدأ مجاناً الآن
            <ChevronLeft size={20} />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-800 py-10 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-xs">M</div>
                <span className="font-bold">Mosh AI Pro</span>
              </div>
              <p className="text-gray-600 text-xs leading-relaxed">منصة تداول ذكية مدعومة بالذكاء الاصطناعي وتحليل ICT/SMC المؤسسي.</p>
            </div>
            <div>
              <h4 className="font-semibold text-sm mb-3 text-gray-300">المنصة</h4>
              <ul className="space-y-2 text-xs text-gray-600">
                <li><Link to="/register" className="hover:text-gray-400">التسجيل</Link></li>
                <li><Link to="/login"    className="hover:text-gray-400">الدخول</Link></li>
                <li><Link to="/pricing"  className="hover:text-gray-400">الأسعار</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-sm mb-3 text-gray-300">قانوني</h4>
              <ul className="space-y-2 text-xs text-gray-600">
                <li><Link to="/terms"   className="hover:text-gray-400">الشروط والأحكام</Link></li>
                <li><Link to="/privacy" className="hover:text-gray-400">سياسة الخصوصية</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-sm mb-3 text-gray-300">تواصل</h4>
              <ul className="space-y-2 text-xs text-gray-600">
                <li><Link to="/contact" className="hover:text-gray-400">اتصل بنا</Link></li>
                <li><a href="https://t.me/ai_hybridbot" target="_blank" rel="noreferrer" className="hover:text-gray-400">Telegram Bot</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-gray-700">
            <span>© 2026 Mosh AI Pro. جميع الحقوق محفوظة.</span>
            <span className="flex items-center gap-1">
              <Star size={10} className="text-yellow-600" />
              هذا تحليل تقني فقط وليس نصيحة مالية أو استثمارية
            </span>
          </div>
        </div>
      </footer>

    </div>
  )
}
