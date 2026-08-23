(function () {
  function clean() {
    // 1. Gom Cinejoy logotypbilder (logomark + wordmark)
    document.querySelectorAll('img[src*="/brand/"], img[src*="cinejoy"]').forEach(function (img) {
      img.style.display = 'none';
    });

    // 2. Gom lankar som pekar pa cinejoy.to (t.ex. kontaktlanken)
    document.querySelectorAll('a[href*="cinejoy"]').forEach(function (a) {
      a.style.display = 'none';
    });

    // 2.5 Byt namn pa undertext-fonten "Cinejoy" till "Mario special"
    document.querySelectorAll('button.segment-btn, button[class*="segment"]').forEach(function (el) {
      if ((el.textContent || '').trim() === 'Cinejoy') {
        el.textContent = 'Mario special';
      }
    });

    // 3. Gom text-bara element som innehaller "cinejoy" (fottext, vattenmarkeringar osv.)
    document.querySelectorAll('p, span, div, a, h1, h2, h3, li').forEach(function (el) {
      if (el.children.length === 0 && /cinejoy/i.test(el.textContent || '')) {
        el.style.display = 'none';
      }
    });

    // 4. Byt ut loggan i toppmenyn mot "Marioflix"
    document.querySelectorAll('a').forEach(function (a) {
      if (a.querySelector('img[src*="/brand/"]')) {
        a.querySelectorAll('img').forEach(function (img) { img.style.display = 'none'; });
        if (!a.querySelector('.mf-brand')) {
          var span = document.createElement('span');
          span.className = 'mf-brand';
          span.textContent = 'Marioflix';
          span.style.cssText = 'font-size:22px;font-weight:700;color:#ffffff;letter-spacing:0.5px;white-space:nowrap;';
          a.appendChild(span);
        }
      }
    });

    // 5. Andra flik-/fonster-titeln
    if (/cinejoy/i.test(document.title)) {
      document.title = 'Marioflix';
    }

    // 6. Ta bort Discord-lankar
    document.querySelectorAll('a[href*="discord"], a[href*="discord.gg"]').forEach(function (a) {
      a.style.display = 'none';
    });

    // 7. Ta bort Cinejoys eget login (Log in / Sign In / Sign out / Login) var den an finns
    document.querySelectorAll('button, a').forEach(function (el) {
      var t = (el.textContent || '').trim();
      if (/^(log\s*in|sign\s*in|sign\s*out|sign\s*up|login|create\s+account)$/i.test(t)) {
        el.style.display = 'none';
      }
    });

    // 8. Ta bort "Manage" (konto) ur kugghjulsmenyerna - men BEHALL "Settings"!
    document.querySelectorAll('button, a').forEach(function (el) {
      var t = (el.textContent || '').trim();
      if (t === 'Manage') {
        var inMenu = el.closest('div.profile-portal-menu, div.mobile-profile-menu');
        var menuLike = /px-4 py-2\.5|px-4 py-3/.test(el.className);
        if (inMenu || menuLike) {
          el.style.display = 'none';
        }
      }
    });

    // 9. Ta bort "Not signed in" / "Create an account..."-texterna
    document.querySelectorAll('p, span, div, h1, h2, h3, li').forEach(function (el) {
      var t = (el.textContent || '').trim();
      if (el.children.length === 0 && /not signed in|create an account|sync your data/i.test(t)) {
        el.style.display = 'none';
      }
    });

    // 10. Ta bort "installera/ladda ner appen"-banderoller
    document.querySelectorAll('div, section, aside, span, button, a, p, h1, h2, h3').forEach(function (el) {
      var t = (el.textContent || '').trim();
      if (t.length < 160 && /install.{0,25}app|app.{0,25}install|download.{0,12}app|get the app/i.test(t)) {
        el.style.display = 'none';
      }
    });
  }

  clean();

  var scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(function () { scheduled = false; clean(); }, 200);
  }
  new MutationObserver(schedule).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
})();
