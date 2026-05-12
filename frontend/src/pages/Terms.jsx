import { Link } from 'react-router-dom'
import PublicLayout from '../components/PublicLayout'
import useSEO from '../hooks/useSEO'

export default function Terms() {
  useSEO({
    title: 'الشروط والأحكام | Qaffel AI',
    description: 'الشروط والأحكام لاستخدام منصة Qaffel AI لإشارات التداول بالذكاء الاصطناعي.',
    canonical: 'https://qaffel.com/terms',
  })
  return (
    <PublicLayout>
      {/* Content */}
      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">الشروط والأحكام</h1>
        <p className="text-gray-400 mb-10 text-sm">آخر تحديث: مارس 2026</p>

        <div className="space-y-8 text-gray-300 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. قبول الشروط</h2>
            <p>باستخدامك لمنصة Qaffel AI، فإنك توافق على الالتزام بهذه الشروط والأحكام. إذا كنت لا توافق على أي جزء منها، يُرجى عدم استخدام المنصة.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. طبيعة الخدمة</h2>
            <p>توفر Qaffel AI توصيات وتحليلات تقنية مدعومة بالذكاء الاصطناعي لأغراض <strong>تعليمية وإعلامية فقط</strong>. لا تُعدّ هذه التوصيات نصيحة مالية أو استثمارية موثوقة.</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>التوصيات لا تضمن الربح أو تجنّب الخسارة</li>
              <li>المستخدم مسؤول كلياً عن قراراته الاستثمارية</li>
              <li>يُنصح باستشارة مستشار مالي مرخص قبل التداول</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">3. الاشتراكات والمدفوعات</h2>
            <p>تُقدَّم الخدمة بثلاث خطط: تجريبية مجانية، أسبوعية، وشهرية. جميع المدفوعات غير قابلة للاسترداد إلا في حالات استثنائية يُبتّ فيها من قِبَل الإدارة.</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>تُجدَّد الاشتراكات تلقائياً ما لم يُلغَ الاشتراك</li>
              <li>الأسعار قابلة للتغيير مع إشعار مسبق</li>
              <li>تُطبَّق حدود استخدام يومية حسب الخطة</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. سلوك المستخدم</h2>
            <p>يلتزم المستخدم بعدم:</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>مشاركة بيانات حسابه مع أطراف أخرى</li>
              <li>محاولة اختراق أو إساءة استخدام النظام</li>
              <li>نشر محتوى التحليلات تجارياً دون إذن مسبق</li>
              <li>إنشاء حسابات متعددة للتحايل على القيود</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. إخلاء المسؤولية</h2>
            <p>لا تتحمل Qaffel AI أي مسؤولية عن الخسائر المالية الناتجة عن اتخاذ قرارات تداول بناءً على تحليلات المنصة. أسواق المال تنطوي على مخاطر عالية وقد تخسر رأس مالك كاملاً.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. التعديلات</h2>
            <p>نحتفظ بالحق في تعديل هذه الشروط في أي وقت. سيُبلَّغ المستخدمون بالتغييرات الجوهرية عبر البريد الإلكتروني أو الإشعارات داخل المنصة.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. التواصل</h2>
            <p>لأي استفسارات قانونية تواصل معنا عبر: <Link to="/contact" className="text-blue-400 hover:underline">صفحة التواصل</Link></p>
          </section>
        </div>
      </main>
    </PublicLayout>
  )
}
