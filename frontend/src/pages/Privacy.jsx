import { Link } from 'react-router-dom'

export default function Privacy() {
  return (
    <div dir="rtl" className="min-h-screen bg-gray-950 text-gray-100">
      {/* Navbar */}
      <nav className="border-b border-gray-800 bg-gray-950/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Qaffel AI
          </Link>
          <div className="flex gap-4 text-sm">
            <Link to="/login" className="text-gray-400 hover:text-white transition">تسجيل الدخول</Link>
            <Link to="/register" className="bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-lg transition">ابدأ مجاناً</Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">سياسة الخصوصية</h1>
        <p className="text-gray-400 mb-10 text-sm">آخر تحديث: مارس 2026</p>

        <div className="space-y-8 text-gray-300 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. المعلومات التي نجمعها</h2>
            <p>نجمع المعلومات الضرورية لتقديم خدماتنا:</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li><strong>بيانات الحساب:</strong> الاسم، البريد الإلكتروني، كلمة المرور (مشفّرة)</li>
              <li><strong>بيانات الاستخدام:</strong> التحليلات المطلوبة، الأزواج المفضلة، إعدادات التداول</li>
              <li><strong>بيانات تقنية:</strong> عنوان IP، نوع المتصفح، أوقات الدخول</li>
              <li><strong>بيانات الدفع:</strong> لا نخزّن بيانات البطاقات — تُعالَج عبر بوابات دفع آمنة</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. كيف نستخدم بياناتك</h2>
            <ul className="list-disc list-inside mt-2 space-y-1 text-gray-400">
              <li>تقديم التحليلات والتوصيات المخصصة</li>
              <li>إرسال إشعارات الإشارات عبر البريد الإلكتروني أو Telegram</li>
              <li>تحسين خوارزميات الذكاء الاصطناعي</li>
              <li>إدارة الاشتراك والفوترة</li>
              <li>مراقبة أمن الحساب ومنع الاحتيال</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">3. مشاركة البيانات</h2>
            <p>لا نبيع بياناتك الشخصية لأطراف ثالثة. قد نشاركها فقط في الحالات التالية:</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>مزودو الخدمات التقنية (استضافة، بريد إلكتروني) بموجب اتفاقيات سرية</li>
              <li>الجهات القانونية عند وجود أمر قضائي</li>
              <li>حماية حقوق المنصة في حال انتهاك الشروط</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. أمان البيانات</h2>
            <p>نطبّق معايير أمان صارمة تشمل:</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>تشفير HTTPS لجميع الاتصالات</li>
              <li>تشفير bcrypt لكلمات المرور</li>
              <li>قاعدة بيانات مؤمّنة بصلاحيات محدودة</li>
              <li>نسخ احتياطية منتظمة</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. حقوقك</h2>
            <p>يحق لك في أي وقت:</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>طلب نسخة من بياناتك الشخصية</li>
              <li>تصحيح بيانات غير دقيقة</li>
              <li>طلب حذف حسابك وبياناتك</li>
              <li>إلغاء الاشتراك في الرسائل التسويقية</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. ملفات تعريف الارتباط (Cookies)</h2>
            <p>نستخدم cookies ضرورية للحفاظ على جلسة تسجيل الدخول وتذكّر التفضيلات. لا نستخدم cookies للإعلانات المستهدفة.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. التواصل</h2>
            <p>لممارسة حقوقك أو لأي استفسار تواصل معنا عبر: <Link to="/contact" className="text-blue-400 hover:underline">صفحة التواصل</Link></p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 text-center text-gray-500 text-sm">
        <p>© 2026 Qaffel AI · <Link to="/terms" className="hover:text-gray-300">الشروط والأحكام</Link> · <Link to="/contact" className="hover:text-gray-300">تواصل معنا</Link></p>
      </footer>
    </div>
  )
}
