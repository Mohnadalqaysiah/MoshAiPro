import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// (2026-09-27) VAPID applicationServerKey يوصل base64url من الخادم —
// pushManager.subscribe يحتاجه Uint8Array. تحويل قياسي (MDN).
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)))
}

export function isPushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

export async function getExistingSubscription() {
  if (!isPushSupported()) return null
  try {
    const reg = await navigator.serviceWorker.ready
    return await reg.pushManager.getSubscription()
  } catch {
    return null
  }
}

export async function subscribeToPush() {
  if (!isPushSupported()) throw new Error('غير مدعوم بهذا المتصفح')

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('تم رفض الإذن')

  const { data } = await axios.get(`${API}/api/v1/auth/push/vapid-public-key`)
  if (!data.enabled) throw new Error('إشعارات المتصفح غير مفعّلة بالمنصة حالياً')

  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(data.key),
  })

  const json = sub.toJSON()
  await axios.post(`${API}/api/v1/auth/push/subscribe`, {
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
  })
  return sub
}

export async function unsubscribeFromPush() {
  const sub = await getExistingSubscription()
  if (!sub) return
  try {
    await axios.post(`${API}/api/v1/auth/push/unsubscribe`, { endpoint: sub.endpoint })
  } catch { /* noop */ }
  await sub.unsubscribe()
}
