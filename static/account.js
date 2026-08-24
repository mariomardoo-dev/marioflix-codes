/* Marioflix konto på webben (som Android):
   - Settings > Account: visar "Din kod" + "Logga ut"-knapp
   - Logga ut -> /logout (raderar cookien -> tillbaka till login)
   - 24/7-inloggning: /account-info kollas var 45:e sekund;
     om koden raderats/frigjorts (401) -> slängs man ut direkt. */
(function () {
  var CODE = '';

  /* "Logga ut · KOD" i kugghjulsmenyn (profilmenyn) */
  function addItem() {
    var menu = document.querySelector('div.profile-portal-menu') || document.querySelector('div.mobile-profile-menu');
    if (!menu || menu.querySelector('#mf-signout-item')) return;
    var btn = document.createElement('button');
    btn.id = 'mf-signout-item';
    btn.type = 'button';
    btn.textContent = 'Logga ut \u00b7 ' + CODE;
    btn.className = 'flex items-center gap-3 px-4 py-2.5 text-sm text-white/90 hover:bg-white/10 transition-colors text-left w-full';
    btn.style.cssText = 'color:#ff6b6b;background:none;border:0;font:inherit;text-align:left;cursor:pointer;';
    btn.addEventListener('click', function () { window.location.href = '/logout'; });
    menu.appendChild(btn);
  }

  /* Settings-sidan: Account-rutan far kod-info + "Logga ut"-knapp */
  function addAccountInfo() {
    var h2s = document.querySelectorAll('h2');
    var acc = null;
    h2s.forEach(function (h) {
      if (!acc && (h.textContent || '').trim().toLowerCase() === 'account') acc = h;
    });
    if (!acc || !acc.parentElement) return;
    var box = acc.parentElement;
    if (box.querySelector('#mf-account-info')) return;
    var info = document.createElement('div');
    info.id = 'mf-account-info';
    info.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 18px;background:rgba(229,32,32,.08);border:1px solid rgba(229,32,32,.35);border-radius:12px;margin-top:12px;color:#fff;';
    info.innerHTML = '<span style="font-size:13px;color:#aaa;">Din kod</span>'
      + '<span style="font-size:15px;font-weight:700;letter-spacing:1px;">' + CODE + '</span>';
    box.appendChild(info);
    var out = document.createElement('button');
    out.id = 'mf-logout-btn';
    out.type = 'button';
    out.textContent = 'Logga ut';
    out.style.cssText = 'margin-top:10px;width:100%;background:rgba(229,32,32,.15);color:#ff6b6b;border:1px solid rgba(229,32,32,.5);border-radius:12px;padding:12px;font-size:15px;font-weight:600;cursor:pointer;';
    out.addEventListener('click', function () { window.location.href = '/logout'; });
    box.appendChild(out);
  }

  function updateUI() {
    var item = document.getElementById('mf-signout-item');
    if (item) item.textContent = 'Logga ut \u00b7 ' + CODE;
    var info = document.getElementById('mf-account-info');
    if (info) {
      var spans = info.querySelectorAll('span');
      if (spans.length > 1) spans[spans.length - 1].textContent = CODE;
    }
  }

  /* 24/7-koll: raderad/frigjord kod -> utkastad direkt */
  function check() {
    fetch('/account-info')
      .then(function (r) {
        if (!r.ok) { window.location.href = '/'; return null; }
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.ok) return;
        CODE = d.code;
        updateUI();
        run();
      });
  }

  function run() {
    addItem();
    addAccountInfo();
  }
  run();
  var scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(function () { scheduled = false; run(); }, 250);
  }
  new MutationObserver(schedule).observe(document.documentElement, { childList: true, subtree: true });
  check();
  setInterval(check, 45000);
})();
