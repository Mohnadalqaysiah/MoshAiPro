import { useLang } from '../contexts/LangContext'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// (2026-10-11) الألعاب التعليمية صفحة HTML مستقلة في public/games/challenge.html،
// تُخدَم للزوار مباشرة على /games/challenge (للمشاركة والتسويق، nginx يطابقها
// عبر `$uri.html`). هنا نعرضها داخل AppShell بإطار من نفس الأصل، فيتشارك
// الإطار localStorage مع الصفحة المستقلة وتبقى النقاط نفسها في الحالتين.
// `?embed=1` يخفي روابط "سجّل مجانًا" الموجّهة للزوار.
export default function Games() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  // (2026-10-11) api= نفس عنوان الـAPI الذي يستخدمه التطبيق — الصفحة تحفظ
  // النقاط بالحساب ولا تخمّن العنوان داخل لوحة التحكم
  // (2026-10-12) lang= يفتح الألعاب بلغة المنصة؛ key يعيد تحميل الإطار عند تبديل اللغة
  const src = `/games/challenge?embed=1&lang=${isAr ? 'ar' : 'en'}&api=${encodeURIComponent(API)}`
  return (
    <iframe
      key={lang}
      src={src}
      title={isAr ? 'الألعاب التعليمية' : 'Learning games'}
      className="block w-full rounded-2xl border-0"
      style={{ height: 'calc(100dvh - 110px)', minHeight: 560, colorScheme: 'dark' }}
    />
  )
}
