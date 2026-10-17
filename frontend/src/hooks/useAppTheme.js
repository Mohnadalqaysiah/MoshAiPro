import { useEffect } from 'react'
import '../styles/app-v2.css'

// (2026-10-17) هوية لوحة التحكم الجديدة — معاينة قبل التفعيل للجميع (طلب المالك).
// ?newui=1 يفعّلها لهذا المتصفح فقط (localStorage)، ?newui=0 يلغيها. المشتركون لا يرونها حتى تُقلب القيمة الافتراضية.
const KEY = 'qaffel_newui'
const DEFAULT_ON = false

export function isNewUI() {
  try {
    const q = new URLSearchParams(window.location.search).get('newui')
    if (q === '1' || q === '0') localStorage.setItem(KEY, q)
    const v = localStorage.getItem(KEY)
    return v === null ? DEFAULT_ON : v === '1'
  } catch { return DEFAULT_ON }
}

// يضيف .qapp على <html> طوال وجود الصفحة (AppShell، باني الاستراتيجيات) — المتغيرات على :root فتصل للنوافذ المنبثقة أيضاً
export default function useAppTheme() {
  useEffect(() => {
    if (!isNewUI()) return
    const root = document.documentElement
    root.classList.add('qapp')
    return () => root.classList.remove('qapp')
  }, [])
}
