// Qaffel AI Service Worker — PWA + Offline Shell
const CACHE = 'qaffel-v1'
const SHELL = ['/', '/dashboard', '/signals', '/journal']

self.addEventListener('install', e => {
  self.skipWaiting()
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => {}))
  )
})

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', e => {
  const { request } = e
  // Only handle GET requests, skip API calls (always fresh)
  if (request.method !== 'GET') return
  if (request.url.includes('/api/')) return

  e.respondWith(
    fetch(request)
      .then(res => {
        // Cache HTML navigations (app shell)
        if (request.mode === 'navigate') {
          const clone = res.clone()
          caches.open(CACHE).then(c => c.put(request, clone))
        }
        return res
      })
      .catch(() => caches.match(request).then(cached => cached || caches.match('/')))
  )
})

// Push Notifications
self.addEventListener('push', e => {
  const data = e.data?.json() || {}
  e.waitUntil(
    self.registration.showNotification(data.title || 'Qaffel AI', {
      body:    data.body  || 'إشارة جديدة متاحة',
      icon:    '/favicon.svg',
      badge:   '/favicon.svg',
      tag:     data.tag   || 'signal',
      data:    { url: data.url || '/dashboard' },
      actions: [
        { action: 'open',    title: 'عرض الإشارة' },
        { action: 'dismiss', title: 'إغلاق'       },
      ],
    })
  )
})

self.addEventListener('notificationclick', e => {
  e.notification.close()
  if (e.action === 'dismiss') return
  const url = e.notification.data?.url || '/dashboard'
  e.waitUntil(
    clients.matchAll({ type: 'window' }).then(wins => {
      const existing = wins.find(w => w.url.includes(url))
      if (existing) return existing.focus()
      return clients.openWindow(url)
    })
  )
})
