// Marioflix: nar man trycker Play visas en ruta - inget oppnas automatiskt.
// Cinejoys video-CDN nekar var doman (Origin-kontroll), sa om man vill se
// filmen far man valja att oppna den hos cinejoy (originalet).
(function () {
  var last = location.pathname;

  function showOverlay(url) {
    if (document.getElementById('mf-video-note')) return;
    var ov = document.createElement('div');
    ov.id = 'mf-video-note';
    ov.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:2147483000;'
      + 'background:rgba(10,10,16,.94);display:flex;align-items:center;justify-content:center;'
      + 'font-family:Roboto,Arial,sans-serif;color:#fff;text-align:center;padding:24px;box-sizing:border-box;';
    ov.innerHTML = '<div style="max-width:420px">'
      + '<h2 style="margin:0 0 10px;color:#e52020;font-size:26px">Marioflix</h2>'
      + '<p style="margin:0 0 18px;font-size:15px;line-height:1.5">Filmen kan inte spelas direkt i appen '
      + '- cinejoy tillåter bara sin egen sida att streama. Vill du öppna den hos cinejoy?</p>'
      + '<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap">'
      + '<button id="mf-open" style="background:#e52020;color:#fff;border:0;font-size:15px;font-weight:600;'
      + 'padding:12px 22px;border-radius:999px;cursor:pointer">Öppna i cinejoy</button>'
      + '<button id="mf-back" style="background:#1e1e28;color:#fff;border:1px solid #333;font-size:15px;'
      + 'padding:12px 22px;border-radius:999px;cursor:pointer">Tillbaka</button>'
      + '</div></div>';
    document.body.appendChild(ov);
    document.getElementById('mf-open').addEventListener('click', function () {
      window.open(url, '_blank');
    });
    document.getElementById('mf-back').addEventListener('click', function () {
      if (history.length > 1) { history.back(); } else { location.href = '/'; }
    });
  }

  function check() {
    var p = location.pathname;
    if (/^\/watch\//.test(p) && p !== last) {
      showOverlay('https://cinejoy.to' + p + location.search);
    }
    last = p;
  }

  var origPush = history.pushState;
  var origRep = history.replaceState;
  history.pushState = function () { var r = origPush.apply(this, arguments); setTimeout(check, 50); return r; };
  history.replaceState = function () { var r = origRep.apply(this, arguments); setTimeout(check, 50); return r; };
  setInterval(check, 500);
})();
