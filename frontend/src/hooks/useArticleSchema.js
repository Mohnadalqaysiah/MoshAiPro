import useJsonLd from './useJsonLd'
import { AUTHOR } from '../data/author'

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
    // updated حقل اختياري يُملأ فقط عند تحديث حقيقي للمحتوى — لا يُغيَّر لإيهام الحداثة
    dateModified: post.updated || post.date,
    inLanguage: isAr ? 'ar' : 'en',
    author: { '@type': 'Person', name: (post.author || AUTHOR).name },
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
