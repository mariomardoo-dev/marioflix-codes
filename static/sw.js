self.addEventListener('install', function (e) {
  self.skipWaiting();
});
self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', function (e) {
  if (e.request.url.indexOf('/static/app.html') !== -1) {
    e.respondWith(
      fetch(e.request).catch(function () {
        return caches.match(e.request);
      })
    );
  }
});
