// Marioflix Service Worker: fangar bara VIDEO-strommen (nebula/moviebox-CDN)
// och kor den genom var server - da skickas ingen Origin och CDN:en svarar 200.
// Allt annat (film-data, servers-lista) gar direkt fran enheten sa cinejoys
// bot-skydd inte stoppar det.
self.addEventListener('install', function (e) {
  self.skipWaiting();
});
self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});

var STREAM_HOSTS = ['nebula.bright67.online', 'info.movieboxnoob.cc'];

function needsProxy(url) {
  var u = url.toLowerCase();
  if (u.indexOf('/vproxy/') !== -1) return false;
  return STREAM_HOSTS.some(function (h) { return u.indexOf(h) !== -1; });
}

self.addEventListener('fetch', function (e) {
  var url = e.request.url;
  // bara video-CDN (m3u8, segment, undertexter): kor genom oss
  if (needsProxy(url)) {
    e.respondWith(fetch('/vproxy/' + url));
  }
});
