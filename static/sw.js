// Marioflix Service Worker: fangar ström-anrop (servers-lista + video-CDN)
// och kor dem genom var server - da skickas ingen Origin och CDN:en svarar 200.
self.addEventListener('install', function (e) {
  self.skipWaiting();
});
self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});

var STREAM_HOSTS = ['nebula.bright67.online', 'info.movieboxnoob.cc', 'api.shegu.st'];

function needsProxy(url) {
  var u = url.toLowerCase();
  if (u.indexOf('/vproxy/') !== -1) return false;
  if (u.indexOf('api.shegu.st/servers') !== -1) return true;
  return STREAM_HOSTS.some(function (h) { return u.indexOf(h) !== -1; });
}

self.addEventListener('fetch', function (e) {
  var url = e.request.url;

  // servers-listan: hamta via oss + skriv om alla stream-URL:er till /vproxy
  if (url.indexOf('api.shegu.st/servers') !== -1) {
    e.respondWith(
      fetch('/vproxy/' + url).then(function (r) {
        return r.text().then(function (t) {
          t = t.replace(/https:\/\/[a-z0-9.-]+(?=\/(?:playlist|hls|stream)\/)/gi,
                        function (m) { return '/vproxy/' + m; });
          return new Response(t, {
            status: r.status,
            headers: { 'Content-Type': 'application/json' }
          });
        });
      }).catch(function () {
        return new Response('{"error":"proxyfel"}', {
          status: 502,
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }

  // video-CDN (m3u8, segment, undertexter): kor genom oss
  if (needsProxy(url)) {
    e.respondWith(fetch('/vproxy/' + url));
  }
});
