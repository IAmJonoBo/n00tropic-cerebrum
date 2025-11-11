self.addEventListener('install', (event) => {
  self.skipWaiting()
})
self.addEventListener('activate', (event) => {
  clients.claim()
})
self.addEventListener('fetch', (event) => {
  // Placeholder: add cache strategies via Workbox or Cache API.
})
