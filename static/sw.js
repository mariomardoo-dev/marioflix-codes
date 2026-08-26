// Marioflix Service Worker: fangar bara VIDEO-strommen (nebula/moviebox-CDN)
// och kor den genom var server - da skickas ingen Origin och CDN:en svarar 200.
// Allt annat (film-data, servers-lista) gar direkt fran enheten sa cinejoys
// bot-skydd inte stoppar det.
// UNDANTAG: Safari (native HLS) skickar ingen Origin sjalv -> hoppa over
// interception sa videon gar DIREKT fran CDN:en (ingen Render-bandbredd).
self.addEventListener('install', function (e) {
  self.skipWaiting();
});
self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});

var STREAM_HOSTS = ['nebula.bright67.online', 'info.movieboxnoob.cc'];

// Safari = native HLS (spelar videon utan Origin) -> ingen /vproxy behovs.
var NATIVE_HLS = /safari/i.test(self.navigator.userAgent)
  && !/chrome|crios|fxios|edgi|android/i.test(self.navigator.userAgent);

function needsProxy(url) {
  var u = url.toLowerCase();
  if (u.indexOf('/vproxy/') !== -1) return false;
  return STREAM_HOSTS.some(function (h) { return u.indexOf(h) !== -1; });
}

self.addEventListener('fetch', function (e) {
  var url = e.request.url;
  // bara video-CDN (m3u8, segment, undertexter): kor genom oss
  // (Safari native HLS hoppar over - den gar direkt).
  if (!NATIVE_HLS && needsProxy(url)) {
    e.respondWith(fetch('/vproxy/' + url));
  }
});
