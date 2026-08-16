import useJsonLd from './useJsonLd'

// id: معرّف فريد للـ tag (كل صفحة إلها id مختلف حتى ما تتصادم مع FAQ الرئيسية بـ index.html)
// faqs: [{ q, a }, ...]
export default function useFAQSchema(id, faqs) {
  useJsonLd(id, faqs?.length ? {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map(f => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  } : null)
}
