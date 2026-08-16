import useJsonLd from './useJsonLd'

const ORIGIN = 'https://qaffel.com'

// items: [{ name: 'الرئيسية', path: '/' }, { name: 'المدونة', path: '/blog' }, ...]
// path يجب أن يكون المسار الفعلي المعروض حالياً (يشمل بادئة /en لو الصفحة إنجليزية)
export default function useBreadcrumbSchema(items) {
  useJsonLd('ld-breadcrumb', items?.length ? {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: `${ORIGIN}${item.path}`,
    })),
  } : null)
}
