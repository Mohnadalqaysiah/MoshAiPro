import { useEffect } from 'react'
import { pathLangInfo } from '../utils/langRoutes'

const ORIGIN = 'https://qaffel.com'

function setOrRemoveAlternate(hreflang, href) {
  let el = document.querySelector(`link[rel="alternate"][hreflang="${hreflang}"]`)
  if (href) {
    if (!el) {
      el = document.createElement('link')
      el.rel = 'alternate'
      el.hreflang = hreflang
      document.head.appendChild(el)
    }
    el.href = href
  } else if (el) {
    el.remove()
  }
}

export default function useSEO({ title, description, canonical }) {
  useEffect(() => {
    if (title) document.title = title

    let metaDesc = document.querySelector('meta[name="description"]')
    if (!metaDesc) {
      metaDesc = document.createElement('meta')
      metaDesc.name = 'description'
      document.head.appendChild(metaDesc)
    }
    if (description) metaDesc.content = description

    const path = window.location.pathname
    let link = document.querySelector('link[rel="canonical"]')
    if (!link) {
      link = document.createElement('link')
      link.rel = 'canonical'
      document.head.appendChild(link)
    }
    link.href = canonical || `${ORIGIN}${path}`

    // hreflang — بس للصفحات اللي فعلاً إلها نسخة إنجليزية حقيقية على /en/*
    // (مش كل الصفحات، تفادياً لتكرار مشكلة hreflang يشاور لرابط بدون محتوى)
    const { bare, isMirrored } = pathLangInfo(path)
    if (isMirrored) {
      const arUrl = `${ORIGIN}${bare}`
      const enUrl = bare === '/' ? `${ORIGIN}/en` : `${ORIGIN}/en${bare}`
      setOrRemoveAlternate('ar', arUrl)
      setOrRemoveAlternate('en', enUrl)
      setOrRemoveAlternate('x-default', arUrl)
    } else {
      setOrRemoveAlternate('ar', null)
      setOrRemoveAlternate('en', null)
      setOrRemoveAlternate('x-default', null)
    }
  }, [title, description, canonical])
}
