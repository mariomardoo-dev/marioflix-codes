/* Marioflix native-HLS (Safari/iPhone).
   Fangar filmens m3u8-URL och tvingar videon att spelas med webbläsarens
   EGNA HLS-stod (Safari). Native HLS skickar INGEN Origin-header, sa
   Cinejoys CDN godkanner anropet -> strommen gar DIREKT fran CDN:en,
   helt utan /vproxy/Render. (Chrome har ingen native HLS -> den filen
   injiceras bara for Safari, se app.py.) */
(function () {
  var probe = document.createElement('video');
  if (!probe.canPlayType || !probe.canPlayType('application/vnd.apple.mpegurl')) {
    return; // ingen native HLS (Chrome etc.) -> gor inget
  }

  var m3u8 = null;
  var watchIv = null;

  function pick(text) {
    if (!text) return null;
    var m = String(text).match(/https?:\/\/[^"'\s\\]+?\.m3u8(?:[?#][^"'\s\\]*)?/i);
    return m ? m[0] : null;
  }

  function apply() {
    if (!m3u8) return;
    var v = document.querySelector('video');
    if (!v) return;
    try {
      if (v.src === m3u8) return; // redan native - inget att gora
    } catch (e) {}
    var t = 0;
    try { t = v.currentTime || 0; } catch (e) {}
    try { v.src = m3u8; v.load(); } catch (e) {}
    try { v.currentTime = t; } catch (e) {}
    try {
      var pr = v.play();
      if (pr && pr.catch) pr.catch(function () {});
    } catch (e) {}
  }

  /* hls.js satter video.src = blob (MSE) efter att vi tvingat native -
     hall native uppe tills det sitter. Startas nar en film borjar spelas. */
  function startWatch() {
    if (watchIv) return;
    var tries = 0;
    watchIv = setInterval(function () {
      if (++tries > 80) { clearInterval(watchIv); watchIv = null; return; }
      apply();
    }, 250);
  }

  function note(url) {
    var u = pick(url);
    if (u && u !== m3u8) { m3u8 = u; apply(); startWatch(); }
  }

  /* --- Kroka fetch (fångar api.shegu.st-svar som innehåller m3u8-URL:en) --- */
  var of = window.fetch;
  if (of) {
    window.fetch = function () {
      var u = (typeof arguments[0] === 'string') ? arguments[0]
              : (arguments[0] && arguments[0].url) || '';
      var p = of.apply(this, arguments);
      if (/servers|shegu|nebula|bright67|moviebox|m3u8/i.test(u)) {
        note(u);
        if (p && p.then) {
          p.then(function (r) {
            if (r && r.clone) {
              try { r.clone().text().then(function (t) { note(t); }).catch(function () {}); } catch (e) {}
            }
          }).catch(function () {});
        }
      }
      return p;
    };
  }

  /* --- Kroka XHR (hls.js använder XHR för att hämta m3u8:an) --- */
  var oo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) {
    this.__mfnU = u;
    return oo.apply(this, arguments);
  };
  var os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function () {
    var x = this;
    var u = x.__mfnU || '';
    if (/servers|shegu|nebula|bright67|moviebox|m3u8/i.test(u)) {
      note(u);
      x.addEventListener('load', function () {
        try { note(x.responseText || ''); } catch (e) {}
      });
    }
    return os.apply(this, arguments);
  };
})();
