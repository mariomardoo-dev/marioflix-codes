// Marioflix: nar man trycker Play (sidan gar till /watch/...) oppnas
// videon i en NY FLIK pa cinejoy.to (originalet) - dar streamen funkar.
(function () {
  var last = location.pathname;

  function forward() {
    var p = location.pathname;
    if (/^\/watch\//.test(p) && p !== last) {
      var url = 'https://cinejoy.to' + p + location.search;
      window.open(url, '_blank');
      // aterga till detaljsidan (spelaren hos oss kan inte streama anda)
      setTimeout(function () {
        if (location.pathname === p && history.length > 1) {
          history.back();
        }
      }, 900);
    }
    last = p;
  }

  // SPA-navigering (pushState/replaceState) + pollning som sakring
  var origPush = history.pushState;
  var origRep = history.replaceState;
  history.pushState = function () { var r = origPush.apply(this, arguments); setTimeout(forward, 50); return r; };
  history.replaceState = function () { var r = origRep.apply(this, arguments); setTimeout(forward, 50); return r; };
  setInterval(forward, 500);
})();
