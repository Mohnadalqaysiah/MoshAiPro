import PublicLayout from '../components/PublicLayout'
import LegalDoc from '../components/LegalDoc'
import { useLang } from '../contexts/LangContext'
import useSEO from '../hooks/useSEO'
import useBreadcrumbSchema from '../hooks/useBreadcrumbSchema'

const T = {
  ar: {
    h1: 'سياسة الخصوصية',
    updated: 'آخر تحديث: مارس 2026',
    sections: [
      {
        h: '1. المعلومات التي نجمعها',
        p: 'نجمع المعلومات الضرورية لتقديم خدماتنا:',
        ul: [
          <><strong>بيانات الحساب:</strong> الاسم، البريد الإلكتروني، كلمة المرور (مشفّرة)</>,
          <><strong>بيانات الاستخدام:</strong> التحليلات المطلوبة، الأزواج المفضلة، إعدادات التداول</>,
          <><strong>بيانات تقنية:</strong> عنوان IP، نوع المتصفح، أوقات الدخول</>,
          <><strong>بيانات الدفع:</strong> لا نخزّن بيانات البطاقات — تُعالَج عبر بوابات دفع آمنة</>,
        ],
      },
      {
        h: '2. كيف نستخدم بياناتك',
        ul: ['تقديم التحليلات والتوصيات المخصصة', 'إرسال إشعارات الإشارات عبر البريد الإلكتروني أو Telegram', 'تحسين خوارزميات الذكاء الاصطناعي', 'إدارة الاشتراك والفوترة', 'مراقبة أمن الحساب ومنع الاحتيال'],
      },
      {
        h: '3. مشاركة البيانات',
        p: 'لا نبيع بياناتك الشخصية لأطراف ثالثة. قد نشاركها فقط في الحالات التالية:',
        ul: ['مزودو الخدمات التقنية (استضافة، بريد إلكتروني) بموجب اتفاقيات سرية', 'الجهات القانونية عند وجود أمر قضائي', 'حماية حقوق المنصة في حال انتهاك الشروط'],
      },
      {
        h: '4. أمان البيانات',
        p: 'نطبّق معايير أمان صارمة تشمل:',
        ul: ['تشفير HTTPS لجميع الاتصالات', 'تشفير bcrypt لكلمات المرور', 'قاعدة بيانات مؤمّنة بصلاحيات محدودة', 'نسخ احتياطية منتظمة'],
      },
      {
        h: '5. حقوقك',
        p: 'يحق لك في أي وقت:',
        ul: ['طلب نسخة من بياناتك الشخصية', 'تصحيح بيانات غير دقيقة', 'طلب حذف حسابك وبياناتك', 'إلغاء الاشتراك في الرسائل التسويقية'],
      },
      {
        h: '6. ملفات تعريف الارتباط (Cookies)',
        p: 'نستخدم cookies ضرورية للحفاظ على جلسة تسجيل الدخول وتذكّر التفضيلات. لا نستخدم cookies للإعلانات المستهدفة.',
      },
    ],
    contactLabel: 'لممارسة حقوقك أو لأي استفسار تواصل معنا عبر:',
    contactLink: 'صفحة التواصل',
  },
  en: {
    h1: 'Privacy Policy',
    updated: 'Last updated: March 2026',
    sections: [
      {
        h: '1. Information We Collect',
        p: 'We collect the information necessary to provide our services:',
        ul: [
          <><strong>Account data:</strong> Name, email, password (encrypted)</>,
          <><strong>Usage data:</strong> Requested analyses, favorite pairs, trading settings</>,
          <><strong>Technical data:</strong> IP address, browser type, login times</>,
          <><strong>Payment data:</strong> We do not store card details — these are processed via secure payment gateways</>,
        ],
      },
      {
        h: '2. How We Use Your Data',
        ul: ['Providing personalized analysis and recommendations', 'Sending signal notifications via email or Telegram', 'Improving our AI algorithms', 'Managing subscriptions and billing', 'Monitoring account security and preventing fraud'],
      },
      {
        h: '3. Data Sharing',
        p: 'We do not sell your personal data to third parties. We may only share it in the following cases:',
        ul: ['Technical service providers (hosting, email) under confidentiality agreements', 'Legal authorities when required by a court order', 'To protect the platform\'s rights in case of a terms violation'],
      },
      {
        h: '4. Data Security',
        p: 'We apply strict security standards including:',
        ul: ['HTTPS encryption for all connections', 'bcrypt encryption for passwords', 'A secured database with limited access permissions', 'Regular backups'],
      },
      {
        h: '5. Your Rights',
        p: 'You have the right, at any time, to:',
        ul: ['Request a copy of your personal data', 'Correct inaccurate data', 'Request deletion of your account and data', 'Unsubscribe from marketing messages'],
      },
      {
        h: '6. Cookies',
        p: 'We use essential cookies to maintain your login session and remember your preferences. We do not use cookies for targeted advertising.',
      },
    ],
    contactLabel: 'To exercise your rights or for any inquiry, contact us via:',
    contactLink: 'the Contact page',
  },
}

export default function Privacy() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  const tx = T[isAr ? 'ar' : 'en']

  useSEO({
    title: isAr ? 'سياسة الخصوصية | Qaffel AI' : 'Privacy Policy | Qaffel AI',
    description: isAr
      ? 'سياسة الخصوصية لمنصة Qaffel AI — كيف نجمع بياناتك ونحميها ونستخدمها.'
      : 'Privacy policy for the Qaffel AI platform — how we collect, protect, and use your data.',
  })
  useBreadcrumbSchema([
    { name: isAr ? 'الرئيسية' : 'Home', path: isAr ? '/' : '/en' },
    { name: isAr ? 'سياسة الخصوصية' : 'Privacy Policy', path: isAr ? '/privacy' : '/en/privacy' },
  ])
  return (
    <PublicLayout>
      <LegalDoc isAr={isAr} eyebrow={isAr ? 'خصوصيتك أولاً' : 'Your privacy'} h1={tx.h1} updated={tx.updated} sections={tx.sections}
        contactLabel={tx.contactLabel} contactLink={tx.contactLink} />
    </PublicLayout>
  )
}
