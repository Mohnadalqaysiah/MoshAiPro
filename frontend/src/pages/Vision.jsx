import { Link } from 'react-router-dom'
import { Target, Rocket, Globe, Users, Zap, Brain, TrendingUp, Star, ChevronLeft } from 'lucide-react'
import PublicLayout from '../components/PublicLayout'
import useSEO from '../hooks/useSEO'

export default function Vision() {
  useSEO({
    title: 'رؤيتنا | Qaffel AI — مستقبل التداول الذكي',
    description: 'رؤية Qaffel AI لجعل تحليل Smart Money Concepts متاحاً لكل متداول عربي بقوة الذكاء الاصطناعي.',
    canonical: 'https://qaffel.com/vision',
  })
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
            رؤيتنا ورسالتنا
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            نحو عالم يتداول فيه<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-l from-purple-400 to-blue-400">
              كل عربي بثقة واحترافية
            </span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed">
            رؤيتنا تتجاوز مجرد تقديم إشارات — نسعى لبناء جيل من المتداولين العرب
            المسلحين بالمعرفة والأدوات لتحقيق الاستقلال المالي.
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
              <h2 className="text-xl font-bold text-white mb-3">رؤيتنا</h2>
              <p className="text-gray-300 leading-relaxed">
                أن نكون المنصة الأولى والأكثر ثقةً في العالم العربي لتحليل الأسواق المالية
                بالذكاء الاصطناعي — منصة يلجأ إليها كل متداول عربي قبل كل صفقة.
              </p>
            </div>
            <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/10 border border-purple-700/30 rounded-2xl p-8">
              <div className="w-12 h-12 bg-purple-600/30 rounded-xl flex items-center justify-center mb-5">
                <Rocket size={24} className="text-purple-400" />
              </div>
              <h2 className="text-xl font-bold text-white mb-3">رسالتنا</h2>
              <p className="text-gray-300 leading-relaxed">
                ديمقراطة التحليل المؤسسي — جعل أدوات التداول الاحترافية متاحة وبأسعار
                منصفة لكل متداول عربي، من المبتدئ إلى المحترف.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Roadmap */}
      <section className="py-16 px-6 bg-gray-900/40">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-3">خارطة طريقنا</h2>
          <p className="text-gray-400 text-center mb-12">ما حققناه وما نسعى إليه</p>
          <div className="space-y-6">
            {[
              {
                phase: 'المرحلة الأولى ✅',
                title: 'الإطلاق والتأسيس',
                done: true,
                items: [
                  'تحليل ICT/SMC بالذكاء الاصطناعي للذهب والبيتكوين',
                  'وكيل AI للمحادثة التفاعلية',
                  'تنبيهات Telegram الفورية',
                  'لوحة تحكم عربية متكاملة',
                  'نظام اشتراكات مرن',
                ],
              },
              {
                phase: 'المرحلة الثانية 🔄',
                title: 'التوسع والنضج',
                done: false,
                items: [
                  'دعم مزيد من الأسواق (نفط، مؤشرات، عملات رقمية)',
                  'تطبيق موبايل iOS وAndroid',
                  'تحليل متعدد العملات في نفس الوقت',
                  'تقارير أسبوعية مفصلة بالذكاء الاصطناعي',
                  'نظام تنبيهات ذكي حسب مستوى السعر',
                ],
              },
              {
                phase: 'المرحلة الثالثة 🔮',
                title: 'الريادة الإقليمية',
                done: false,
                items: [
                  'منصة تعليمية لتعلم ICT/SMC بالعربية',
                  'ذكاء اصطناعي مخصص للأسواق العربية',
                  'شراكات مع وسطاء التداول الموثوقين',
                  'مجتمع متداولين عرب نشط',
                  'حلول مؤسسية للشركات والصناديق',
                ],
              },
            ].map((phase, i) => (
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
          <h2 className="text-2xl font-bold text-center mb-12">لماذا Qaffel AI؟</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              {
                icon: Brain,
                title: 'أقوى تقنيات التحليل',
                desc: 'نجمع بين ICT (Inner Circle Trader) وSMC (Smart Money Concepts) وWyckoff — ثلاث منهجيات يستخدمها كبار المتداولين المؤسسيين — في تحليل واحد متكامل مدعوم بـ Gemini AI.',
              },
              {
                icon: Globe,
                title: 'الأول بالعربية',
                desc: 'لا يوجد في السوق منصة عربية تقدم هذا المستوى من التحليل المؤسسي بالذكاء الاصطناعي. Qaffel AI يملأ هذا الفراغ بمحتوى 100% عربي وواجهة مصممة للمتداول العربي.',
              },
              {
                icon: Zap,
                title: 'سرعة لا مثيل لها',
                desc: 'تحليل كامل يشمل أكثر من 15 مؤشر ICT/SMC في أقل من 30 ثانية. ما يستغرق المتداول ساعات للوصول إليه، تحصل عليه بنقرة واحدة.',
              },
              {
                icon: TrendingUp,
                title: 'شفافية تامة',
                desc: 'كل إشارة تأتي مع شرح كامل: لماذا BUY أو SELL؟ ما هو Order Block المحدد؟ أين السيولة؟ نحن لا نعطيك سمكة — نعلمك الصيد.',
              },
              {
                icon: Users,
                title: 'مجتمع داعم',
                desc: 'انضم إلى مجتمع متنامٍ من المتداولين العرب الذين يتعلمون ويتشاركون الخبرات. نبني أكثر من منصة — نبني مجتمعاً.',
              },
              {
                icon: Target,
                title: 'سعر عادل ومناسب',
                desc: 'نؤمن أن الأدوات الاحترافية يجب أن تكون متاحة للجميع. لذا نقدم خطط اشتراك مرنة تبدأ بتجربة مجانية حقيقية بدون أي التزام.',
              },
            ].map((item, i) => (
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
          <h2 className="text-xl font-bold mb-4">الأسواق التي نحللها</h2>
          <p className="text-gray-400 text-sm mb-6">
            نقدم تحليلاً ذكياً لأبرز الأسواق المالية العالمية
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              'الذهب XAUUSD', 'البيتكوين BTCUSD', 'اليورو دولار EURUSD',
              'الجنيه دولار GBPUSD', 'الدولار ين USDJPY', 'النفط الخام',
              'مؤشر داو جونز', 'ناسداك', 'إثيريوم ETHUSD',
            ].map((market, i) => (
              <span key={i} className="bg-gray-800 border border-gray-700 text-gray-300 text-sm px-4 py-1.5 rounded-full">
                {market}
              </span>
            ))}
          </div>
          <p className="text-gray-600 text-xs mt-6">
            تحليل فوركس بالذكاء الاصطناعي · إشارات تداول الذهب · توصيات البيتكوين · بوت تداول تلجرام · منصة تداول ذكية عربية
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs px-4 py-1.5 rounded-full mb-6">
            <Star size={12} />
            ابدأ رحلتك اليوم
          </div>
          <h2 className="text-3xl font-bold mb-4">كن جزءاً من مستقبل التداول الذكي</h2>
          <p className="text-gray-400 mb-8">
            انضم للمتداولين الذين يستخدمون Qaffel AI لاتخاذ قرارات أفضل.
            ابدأ بـ 10 تحليلات مجانية بدون أي التزام.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link to="/register"
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-xl font-semibold transition-all hover:scale-105 shadow-lg shadow-blue-500/25">
              ابدأ مجاناً الآن
              <ChevronLeft size={18} />
            </Link>
            <Link to="/about" className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3.5 rounded-xl font-medium transition">
              من نحن
            </Link>
          </div>
        </div>
      </section>

    </PublicLayout>
  )
}
