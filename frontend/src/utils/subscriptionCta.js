/**
 * subscriptionCta — مسار الدفع الظاهر للمستخدم بحسب حالة اشتراكه
 * ================================================================
 * (2026-09-17) وُجد أن المشترك المدفوع **لا يملك أي طريق للتجديد من داخل
 * حسابه**: زر البطاقة الجانبية كان `isTrial ? '/pricing' : '/profile'`،
 * وصفحة الحساب نفسها بلا أي رابط للأسعار. فمن انتهى اشتراكه أو قارب،
 * عليه أن يعرف عنوان `/pricing` ويكتبه يدوياً — وهو تسرّب إيراد مباشر
 * يصيب **المشتركين الحاليين تحديداً**، وهم أقرب الناس للدفع.
 *
 * مصدر واحد للحالتين (البطاقة الجانبية وصفحة الحساب) عمداً: نصّان
 * منفصلان لنفس المنطق يفترقان عند أول تعديل، فيرى المستخدم دعوتين
 * متناقضتين في شاشة واحدة.
 *
 * `days` هو `user.days_left` الآتي من الخادم — يُحسب من
 * `subscription_ends_at` أو `trial_ends_at`، ولا ينزل تحت الصفر.
 */

export const RENEW_SOON_DAYS = 7;

/**
 * @returns {{label: string, to: string, tone: 'primary'|'urgent'|'muted',
 *            secondary?: {label: string, to: string}}}
 */
export function subscriptionCta(user, isAr) {
  const plan = user?.plan;
  const days = user?.days_left;

  // منتهٍ أو موقوف — الدعوة الأصرح
  if (plan === 'banned') {
    return {
      label: isAr ? 'تواصل مع الدعم' : 'Contact support',
      to: '/contact',   // لا '/support' — غير معرَّف بالمسارات
      tone: 'muted',
    };
  }

  if (plan === 'trial') {
    // التجربة انتهت فعلياً
    if (days === 0) {
      return {
        label: isAr ? 'انتهت تجربتك — اشترك الآن' : 'Trial ended — Subscribe now',
        to: '/pricing',
        tone: 'urgent',
      };
    }
    return {
      label: isAr ? 'ترقية الاشتراك' : 'Upgrade',
      to: '/pricing',
      tone: 'primary',
    };
  }

  // مشترك مدفوع
  if (days === 0) {
    return {
      label: isAr ? 'اشتراكك منتهٍ — جدّد الآن' : 'Subscription expired — Renew',
      to: '/pricing',
      tone: 'urgent',
    };
  }
  if (typeof days === 'number' && days <= RENEW_SOON_DAYS) {
    return {
      label: isAr ? `جدّد اشتراكك — بقي ${days} ${days === 1 ? 'يوم' : 'أيام'}`
                  : `Renew — ${days} day${days === 1 ? '' : 's'} left`,
      to: '/pricing',
      tone: 'urgent',
    };
  }

  // اشتراك سارٍ بمهلة مريحة: إدارة الحساب أولاً، والتجديد متاح لا مخفيّ
  return {
    label: isAr ? 'إدارة الحساب' : 'Manage account',
    to: '/profile',
    tone: 'primary',
    secondary: {
      label: isAr ? 'تجديد مبكر' : 'Renew early',
      to: '/pricing',
    },
  };
}
