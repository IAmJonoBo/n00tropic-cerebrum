self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', () => {
  if (self.clients && typeof self.clients.claim === 'function') {
    self.clients.claim()
  }
})

self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request))
})
