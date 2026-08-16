// المسارات العامة اللي إلها فعلاً محتوى إنجليزي حقيقي (bilingual) — نفّس هوي
// اللي بيصير عليه /en/* حقيقياً.
export const EN_MIRRORED_PREFIXES = [
  '/pricing', '/referral', '/blog',
  '/about', '/vision', '/contact', '/terms', '/privacy', '/login', '/register',
]

// pathname -> { isEn, bare, isMirrored }
// bare = نفس المسار بدون بادئة /en (يعني النسخة العربية المكافئة)
export function pathLangInfo(pathname) {
  const isEn = pathname === '/en' || pathname.startsWith('/en/')
  const bare = isEn ? (pathname === '/en' ? '/' : pathname.slice(3)) : pathname
  const isMirrored =
    bare === '/' || EN_MIRRORED_PREFIXES.some(p => bare === p || bare.startsWith(p + '/'))
  return { isEn, bare, isMirrored }
}

// يرجّع مسار الوجهة المقابلة بلغة أخرى، أو null لو ما في نسخة مرآة لهالصفحة
export function mirrorPath(pathname, targetLang) {
  const { bare, isMirrored } = pathLangInfo(pathname)
  if (!isMirrored) return null
  if (targetLang === 'en') return bare === '/' ? '/en' : `/en${bare}`
  return bare
}
