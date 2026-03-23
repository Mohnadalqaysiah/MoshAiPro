import { Link } from 'react-router-dom'
import { Users, Brain, Globe, Shield, Award, TrendingUp, CheckCircle, Star } from 'lucide-react'

export default function About() {
  return (
    <div dir="rtl" className="min-h-screen bg-gray-950 text-gray-100">

      {/* Navbar */}
      <nav className="border-b border-gray-800 bg-gray-950/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-sm">Q</div>
            <span className="font-bold text-lg">Qafeel <span className="text-blue-400">AI</span></span>
          </Link>
          <div className="flex gap-4 text-sm">
            <Link to="/login"    className="text-gray-400 hover:text-white transition">تسجيل الدخول</Link>
            <Link to="/register" className="bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-lg transition">ابدأ مجاناً</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-20 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/8 rounded-full blur-3xl" />
        </div>
        <div className="max-w-3xl mx-auto relative">
          <div className="inline-flex items-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Users size={12} />
            من نحن
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            نُمكّن المتداولين من<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-blue-400 to-purple-400">
              اتخاذ قرارات أذكى
            </span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed">
            Qafeel AI منصة عربية متخصصة في تحليل الأسواق المالية بالذكاء الاصطناعي،
            تجمع بين تقنيات التحليل المؤسسي الاحترافي وسهولة الوصول للجميع.
          </p>
        </div>
      </section>

      {/* Story */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-2xl font-bold mb-4">قصتنا</h2>
              <p className="text-gray-400 leading-relaxed mb-4">
                وُلدت فكرة Qafeel AI من رحم التحدي الذي يعيشه المتداول العربي يومياً —
                أدوات تحليل احترافية موجودة لكنها بالإنجليزية وتحتاج خبرة عميقة، أو إشارات
                مجهولة المصدر لا يمكن الوثوق بها.
              </p>
              <p className="text-gray-400 leading-relaxed mb-4">
                قرّرنا بناء منصة تجمع أقوى منهجيات التحليل المؤسسي — ICT وSMC وWyckoff —
                مع قدرات الذكاء الاصطناعي الحديث، لتقديم تحليل شفاف وقابل للتفسير
                بالعربية مباشرة على هاتفك.
              </p>
              <p className="text-gray-400 leading-relaxed">
                نؤمن أن كل متداول — سواء كان محترفاً أو مبتدئاً — يستحق أدوات من المستوى
                المؤسسي، بسعر عادل وبلغته الأم.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { icon: Brain,     label: 'ذكاء اصطناعي متقدم',      desc: 'Gemini AI + ICT/SMC' },
                { icon: Globe,     label: 'منصة عربية أصيلة',         desc: 'دعم كامل بالعربية' },
                { icon: Shield,    label: 'تحليل شفاف وموثوق',        desc: 'بدون إشارات مجهولة' },
                { icon: TrendingUp,label: 'أسواق متعددة',              desc: 'ذهب · بيتكوين · فوركس' },
              ].map((item, i) => (
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
          <h2 className="text-2xl font-bold text-center mb-10">ماذا نقدّم؟</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Brain,
                title: 'تحليل بالذكاء الاصطناعي',
                items: [
                  'تحليل ICT/SMC المتقدم',
                  'تحديد Order Blocks و FVGs',
                  'رصد Liquidity و Smart Money',
                  'تحليل Wyckoff المؤسسي',
                ],
              },
              {
                icon: TrendingUp,
                title: 'إشارات وتوصيات دقيقة',
                items: [
                  'إشارات شراء/بيع مع مستويات الدخول',
                  'حساب وقف الخسارة والأهداف',
                  'تحديد حجم الصفقة المناسب',
                  'تقييم جودة الإشارة (A+ إلى C)',
                ],
              },
              {
                icon: Users,
                title: 'تجربة مستخدم متميزة',
                items: [
                  'واجهة عربية سهلة الاستخدام',
                  'تنبيهات فورية على Telegram',
                  'وكيل AI للمحادثة والاستفسار',
                  'دعم فني متواصل',
                ],
              },
            ].map((col, i) => (
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
          <h2 className="text-2xl font-bold text-center mb-10">قيمنا</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: Shield,  title: 'الشفافية أولاً',    desc: 'نؤمن بأن التحليل يجب أن يكون مفهوماً وقابلاً للتحقق. كل إشارة نقدمها مبنية على بيانات حقيقية وأسباب موثقة.' },
              { icon: Award,   title: 'الجودة لا الكمية', desc: 'نفضّل إشارة واحدة عالية الجودة على عشر إشارات مشكوك فيها. التقييم الصادق يحمي رأس مالك.' },
              { icon: Users,   title: 'مجتمع أولاً',       desc: 'نبني منصة يشعر فيها كل متداول عربي بأنه في المكان الصحيح — حيث الدعم والتعليم متاحان للجميع.' },
              { icon: Brain,   title: 'الابتكار المستمر',  desc: 'نواصل تطوير نماذجنا وإضافة أسواق وأدوات جديدة لتبقى في طليعة أدوات التداول الذكي.' },
            ].map((v, i) => (
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
              <strong>إخلاء مسؤولية:</strong> جميع التحليلات والإشارات المقدمة على منصة Qafeel AI
              هي لأغراض تعليمية وتحليلية فقط، ولا تُعدّ نصيحة مالية أو استثمارية.
              التداول في الأسواق المالية ينطوي على مخاطر حقيقية وقد تخسر جزءاً أو كل رأس مالك.
              أنت المسؤول الكامل عن قراراتك الاستثمارية.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 text-center">
        <h2 className="text-2xl font-bold mb-3">مستعد تبدأ رحلتك؟</h2>
        <p className="text-gray-400 mb-6">10 تحليلات مجانية، بدون بطاقة ائتمان</p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link to="/register" className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-semibold transition">
            ابدأ مجاناً
          </Link>
          <Link to="/vision" className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3 rounded-xl font-medium transition">
            رؤيتنا
          </Link>
        </div>
      </section>

      <footer className="border-t border-gray-800 py-8 text-center text-gray-500 text-sm">
        <p>© 2026 Qafeel AI ·
          <Link to="/terms"   className="hover:text-gray-300 mx-2">الشروط</Link>·
          <Link to="/privacy" className="hover:text-gray-300 mx-2">الخصوصية</Link>·
          <Link to="/contact" className="hover:text-gray-300 mx-2">تواصل معنا</Link>
        </p>
      </footer>
    </div>
  )
}
