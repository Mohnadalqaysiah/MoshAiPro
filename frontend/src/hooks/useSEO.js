import { useEffect } from 'react'

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

    let link = document.querySelector('link[rel="canonical"]')
    if (!link) {
      link = document.createElement('link')
      link.rel = 'canonical'
      document.head.appendChild(link)
    }
    link.href = canonical || `https://qaffel.com${window.location.pathname}`
  }, [title, description, canonical])
}
