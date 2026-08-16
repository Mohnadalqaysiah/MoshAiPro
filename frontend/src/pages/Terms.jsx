import { Link } from 'react-router-dom'
import PublicLayout from '../components/PublicLayout'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

const T = {
  ar: {
    h1: 'الشروط والأحكام',
    updated: 'آخر تحديث: مارس 2026',
    sections: [
      {
        h: '1. قبول الشروط',
        p: 'باستخدامك لمنصة Qaffel AI، فإنك توافق على الالتزام بهذه الشروط والأحكام. إذا كنت لا توافق على أي جزء منها، يُرجى عدم استخدام المنصة.',
      },
      {
        h: '2. طبيعة الخدمة',
        p: <>توفر Qaffel AI توصيات وتحليلات تقنية مدعومة بالذكاء الاصطناعي لأغراض <strong>تعليمية وإعلامية فقط</strong>. لا تُعدّ هذه التوصيات نصيحة مالية أو استثمارية موثوقة.</>,
        ul: ['التوصيات لا تضمن الربح أو تجنّب الخسارة', 'المستخدم مسؤول كلياً عن قراراته الاستثمارية', 'يُنصح باستشارة مستشار مالي مرخص قبل التداول'],
      },
      {
        h: '3. الاشتراكات والمدفوعات',
        p: 'تُقدَّم الخدمة بثلاث خطط: تجريبية مجانية، أسبوعية، وشهرية. جميع المدفوعات غير قابلة للاسترداد إلا في حالات استثنائية يُبتّ فيها من قِبَل الإدارة.',
        ul: ['الاشتراك غير ملزم وينتهي تلقائياً بنهاية المدة (أسبوع أو شهر) دون أي تجديد أو خصم إضافي', 'لإكمال الاستخدام بعد الانتهاء، يشترك المستخدم يدوياً من جديد', 'الأسعار قابلة للتغيير مع إشعار مسبق', 'تُطبَّق حدود استخدام يومية حسب الخطة'],
      },
      {
        h: '4. سلوك المستخدم',
        p: 'يلتزم المستخدم بعدم:',
        ul: ['مشاركة بيانات حسابه مع أطراف أخرى', 'محاولة اختراق أو إساءة استخدام النظام', 'نشر محتوى التحليلات تجارياً دون إذن مسبق', 'إنشاء حسابات متعددة للتحايل على القيود'],
      },
      {
        h: '5. إخلاء المسؤولية',
        p: 'لا تتحمل Qaffel AI أي مسؤولية عن الخسائر المالية الناتجة عن اتخاذ قرارات تداول بناءً على تحليلات المنصة. أسواق المال تنطوي على مخاطر عالية وقد تخسر رأس مالك كاملاً.',
      },
      {
        h: '6. التعديلات',
        p: 'نحتفظ بالحق في تعديل هذه الشروط في أي وقت. سيُبلَّغ المستخدمون بالتغييرات الجوهرية عبر البريد الإلكتروني أو الإشعارات داخل المنصة.',
      },
    ],
    contactLabel: 'لأي استفسارات قانونية تواصل معنا عبر:',
    contactLink: 'صفحة التواصل',
  },
  en: {
    h1: 'Terms & Conditions',
    updated: 'Last updated: March 2026',
    sections: [
      {
        h: '1. Acceptance of Terms',
        p: 'By using the Qaffel AI platform, you agree to be bound by these terms and conditions. If you do not agree to any part of them, please do not use the platform.',
      },
      {
        h: '2. Nature of the Service',
        p: <>Qaffel AI provides AI-powered technical recommendations and analysis for <strong>educational and informational purposes only</strong>. These recommendations do not constitute reliable financial or investment advice.</>,
        ul: ['Recommendations do not guarantee profit or protection from loss', 'The user is fully responsible for their investment decisions', 'It is recommended to consult a licensed financial advisor before trading'],
      },
      {
        h: '3. Subscriptions & Payments',
        p: 'The service is offered in three plans: a free trial, weekly, and monthly. All payments are non-refundable except in exceptional cases decided by management.',
        ul: ['Subscriptions are non-binding and expire automatically at the end of the period (week or month) with no renewal or extra charge', 'To keep using the service afterward, the user subscribes again manually', 'Prices are subject to change with prior notice', 'Daily usage limits apply based on the plan'],
      },
      {
        h: '4. User Conduct',
        p: 'The user agrees not to:',
        ul: ['Share their account credentials with other parties', 'Attempt to hack or misuse the system', 'Commercially redistribute analysis content without prior permission', 'Create multiple accounts to circumvent usage limits'],
      },
      {
        h: '5. Disclaimer',
        p: 'Qaffel AI bears no responsibility for financial losses resulting from trading decisions made based on the platform\'s analysis. Financial markets involve high risk and you may lose your entire capital.',
      },
      {
        h: '6. Amendments',
        p: 'We reserve the right to modify these terms at any time. Users will be notified of material changes via email or in-platform notifications.',
      },
    ],
    contactLabel: 'For any legal inquiries, contact us via:',
    contactLink: 'the Contact page',
  },
}

export default function Terms() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']

  useSEO({
    title: isAr ? 'الشروط والأحكام | Qaffel AI' : 'Terms & Conditions | Qaffel AI',
    description: isAr
      ? 'الشروط والأحكام لاستخدام منصة Qaffel AI لإشارات التداول بالذكاء الاصطناعي.'
      : 'Terms and conditions for using the Qaffel AI trading signals platform.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'الشروط والأحكام' : 'Terms & Conditions', path: isAr ? '/terms' : '/en/terms' },
  ])
  return (
    <PublicLayout>
      {/* Content */}
      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">{tx.h1}</h1>
        <p className="text-gray-400 mb-10 text-sm">{tx.updated}</p>

        <div className="space-y-8 text-gray-300 leading-relaxed">
          {tx.sections.map((s, i) => (
            <section key={i}>
              <h2 className="text-xl font-semibold text-white mb-3">{s.h}</h2>
              <p>{s.p}</p>
              {s.ul && (
                <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
                  {s.ul.map((li, j) => <li key={j}>{li}</li>)}
                </ul>
              )}
            </section>
          ))}

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">{isAr ? '7. التواصل' : '7. Contact'}</h2>
            <p>{tx.contactLabel} <Link to={isAr ? '/contact' : '/en/contact'} className="text-blue-400 hover:underline">{tx.contactLink}</Link></p>
          </section>
        </div>
      </main>
    </PublicLayout>
  )
}
