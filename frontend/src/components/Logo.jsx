/**
 * Logo — أيقونة Qaffel AI بصيغ حديثة مع fallback.
 *
 * (2026-09-04) logo-icon-only.png الأصلي كان 512×512 و404KB، يُعرض بحد
 * أقصى 56px (w-14) بكل استخدامات الموقع — Lighthouse رصدها كأكبر مساهم
 * بـLCP. استُبدلت بنسخة 192px (تغطي حتى 3x DPR للاستخدام الأكبر + هامش)
 * بصيغ AVIF (~3.4KB) وWebP (~8.2KB)، مع PNG 192px (~69KB) كـfallback
 * لمتصفحات قديمة ما تدعم الصيغتين. <picture> يخلي المتصفح يختار أخف
 * صيغة مدعومة تلقائياً بدون JS.
 */
export default function Logo({ className = '', alt = 'Qaffel AI' }) {
  return (
    <picture>
      <source srcSet="/brand/logo-icon-only.avif" type="image/avif" />
      <source srcSet="/brand/logo-icon-only.webp" type="image/webp" />
      <img src="/brand/logo-icon-only-192.png" alt={alt} className={className} />
    </picture>
  )
}
