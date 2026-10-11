import { useLang } from '../contexts/LangContext'

// (2026-10-11) الألعاب التعليمية صفحة HTML مستقلة في public/games/challenge.html،
// تُخدَم للزوار مباشرة على /games/challenge (للمشاركة والتسويق، nginx يطابقها
// عبر `$uri.html`). هنا نعرضها داخل AppShell بإطار من نفس الأصل، فيتشارك
// الإطار localStorage مع الصفحة المستقلة وتبقى النقاط نفسها في الحالتين.
// `?embed=1` يخفي روابط "سجّل مجانًا" الموجّهة للزوار.
export default function Games() {
  const { lang } = useLang()
  const isAr = lang === 'ar'
  return (
    <iframe
      src="/games/challenge?embed=1"
      title={isAr ? 'الألعاب التعليمية' : 'Learning games'}
      className="block w-full rounded-2xl border-0"
      style={{ height: 'calc(100dvh - 110px)', minHeight: 560, colorScheme: 'dark' }}
    />
  )
}
