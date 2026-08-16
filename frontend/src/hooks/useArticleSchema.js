import useJsonLd from './useJsonLd'

const ORIGIN = 'https://qaffel.com'

// post: { titleAr/titleEn, descAr/descEn, date, slug }, isAr: bool, path: المسار الفعلي المعروض
export default function useArticleSchema(post, isAr, path) {
  const title = post ? (isAr ? post.titleAr : post.titleEn) : null
  const desc  = post ? (isAr ? post.descAr  : post.descEn)  : null

  useJsonLd('ld-article', post ? {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description: desc,
    image: `${ORIGIN}/og-image.png`,
    datePublished: post.date,
    dateModified: post.date,
    inLanguage: isAr ? 'ar' : 'en',
    author: {
      '@type': 'Organization',
      name: 'Qaffel AI',
      url: ORIGIN,
    },
    publisher: {
      '@type': 'Organization',
      name: 'Qaffel AI',
      logo: {
        '@type': 'ImageObject',
        url: `${ORIGIN}/brand/logo-icon-only.png`,
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `${ORIGIN}${path}`,
    },
  } : null)
}
