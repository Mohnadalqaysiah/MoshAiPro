import { useEffect } from 'react'

// حقن/تحديث <script type="application/ld+json"> واحد لكل id ثابت.
// data = null يشيل الـ tag (لصفحة ما إلها schema من هالنوع).
export default function useJsonLd(id, data) {
  useEffect(() => {
    let script = document.getElementById(id)
    if (!data) {
      script?.remove()
      return
    }
    if (!script) {
      script = document.createElement('script')
      script.type = 'application/ld+json'
      script.id = id
      document.head.appendChild(script)
    }
    script.textContent = JSON.stringify(data)
    return () => { document.getElementById(id)?.remove() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, JSON.stringify(data)])
}
