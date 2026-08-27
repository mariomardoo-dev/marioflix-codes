# Marioflix-koder - liten server som haller koderna.
# Koderna ligger i codes.json (i repot) - admin-sidan andrar filen direkt
# och committar den till GitHub sa koderna overlever alla uppdateringar.
# En-kod-en-enhet: forsta enheten som loggar in med en kod binds till den.
# /cinejoy = proxy som visar cinejoy rent (utan cinejoy-marken).
# OBS: kraver GITHUB_TOKEN i Render-miljon for permanent sparande.
import base64
import json
import os
import re
import threading
import time
import urllib.request

import requests
from flask import Flask, Response, jsonify, redirect, request, send_file

try:
    import fcntl
except ImportError:
    fcntl = None

app = Flask(__name__)

ADMIN_PW_ENV = "ADMIN_PW"
CODES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codes.json")

GITHUB_REPO = "mariomardoo-dev/marioflix-codes"
GITHUB_CODES_URL = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/codes.json"


def fetch_repo_codes():
    """Vid VARJE start: hamta senaste codes.json fran GitHub (kallan till
    sanningen). Render-atervinning tappar annars koder som lagts in efter
    forra deployen - med denna hamtas alltid allt vid omstart."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return False
    try:
        req = urllib.request.Request(
            GITHUB_CODES_URL,
            headers={"Authorization": "token " + token, "User-Agent": "Marioflix"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        content = base64.b64decode(data["content"]).decode("utf-8")
        parsed = json.loads(content)
        if isinstance(parsed, dict) and isinstance(parsed.get("codes"), list):
            with open(CODES_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            return True
    except Exception:
        pass
    return False


# Kor en gang vid start (Render startar om app.py vid varje boot/atervinning)
fetch_repo_codes()

# Laas for codes.json: admin och /check far ALDRIG skriva over varandra
# (read-modify-write-race). flock over processer (Render/gunicorn) +
# thread-lock som fallback (Windows/lokalt).
_codes_thread_lock = threading.Lock()
_codes_lock_file = {"f": None}


@app.before_request
def codes_write_lock():
    if request.path in ("/admin", "/check", "/codes-raw"):
        _codes_thread_lock.acquire()
        if fcntl is not None:
            try:
                f = open(CODES_FILE + ".lock", "w")
                fcntl.flock(f, fcntl.LOCK_EX)
                _codes_lock_file["f"] = f
            except Exception:
                _codes_lock_file["f"] = None


@app.after_request
def codes_write_unlock(resp):
    if request.path in ("/admin", "/check", "/codes-raw"):
        f = _codes_lock_file.get("f")
        if f is not None:
            try:
                fcntl.flock(f, fcntl.LOCK_UN)
                f.close()
            except Exception:
                pass
            _codes_lock_file["f"] = None
        _codes_thread_lock.release()
    return resp

# --- Proxy till cinejoy ---
PROXY_BASE = "/cinejoy"
CINEJOY = "https://cinejoy.to"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def is_native_hls_browser():
    """Safari (iPhone/Mac) spelar HLS nativt - skickar ingen Origin-header.
    Da kan videon ga DIREKT fran CDN:en (utan /vproxy/Render = ingen
    bandbredd). Chrome/Edge/Firefox har ingen native HLS -> de behover
    fortfarande /vproxy-tunneln."""
    ua = request.headers.get("User-Agent", "")
    l = ua.lower()
    if "safari" not in l:
        return False
    if "chrome" in l or "crios" in l or "android" in l:
        return False
    return True


def load_data():
    try:
        with open(CODES_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d.get("codes", []), d.get("used", {}), d.get("notes", {})
    except Exception:
        return [], {}, {}


def save_data(codes, used, notes):
    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump({"codes": codes, "used": used, "notes": notes}, f, indent=2)


def push_to_github(codes, used, notes):
    """Committar kodfilen till repot - da overlever koderna alla deployar.
    Retry 3 ggr med 2 s paus: GitHub contents-API:et kan visa gammal sha
    direkt efter en commit (kand cache-lag) -> PUT 409 annars."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return False
    url = "https://api.github.com/repos/mariomardoo-dev/marioflix-codes/contents/codes.json"
    body = json.dumps({"codes": codes, "used": used, "notes": notes}, indent=2)
    for _attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={"Authorization": "token " + token, "User-Agent": "Marioflix",
                         "Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                old = json.loads(r.read().decode())
            data = json.dumps({
                "message": "koder uppdaterade fran admin",
                "content": base64.b64encode(body.encode()).decode(),
                "sha": old["sha"],
            }).encode()
            req2 = urllib.request.Request(
                url, data=data,
                headers={"Authorization": "token " + token, "User-Agent": "Marioflix",
                         "Accept": "application/vnd.github+json"},
                method="PUT",
            )
            with urllib.request.urlopen(req2, timeout=15) as r2:
                if r2.status in (200, 201):
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def load_codes():
    return load_data()[0]


@app.route("/check")
def check():
    code = request.args.get("code", "").strip().lower()
    device = request.args.get("device", "").strip()
    codes, used, _notes = load_data()
    if code not in codes:
        return jsonify({"ok": False, "reason": "fel"})
    if not device:
        # ingen enhet skickad (gammal stil) - bara medlemskoll
        return jsonify({"ok": True})
    prev = used.get(code)
    if prev is None:
        # forsta gangen: binda koden till denna enhet
        used[code] = device
        save_data(codes, used, _notes)
        push_to_github(codes, used, _notes)
        resp = jsonify({"ok": True, "first": True})
        resp.set_cookie("mf_auth", code + "|" + device, httponly=True,
                        samesite="Lax", max_age=60 * 60 * 24 * 365 * 10, path="/")
        return resp
    if prev == device:
        resp = jsonify({"ok": True})
        resp.set_cookie("mf_auth", code + "|" + device, httponly=True,
                        samesite="Lax", max_age=60 * 60 * 24 * 365 * 10, path="/")
        return resp
    return jsonify({"ok": False, "reason": "upptagen"})


APP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "app.html")


def is_authed():
    """Koll att besokaren loggat in med en kod som ar bunden till enheten."""
    c = request.cookies.get("mf_auth", "")
    if "|" not in c:
        return False
    code, device = c.split("|", 1)
    codes, used, _notes = load_data()
    return used.get(code) == device


@app.before_request
def login_gate():
    """Inloggning framfor allt (som mobilen): streamingsidan kraver kod."""
    p = request.path
    # alltid oppet: inloggningssidan, admin, nedladdningar, video-streams
    if p.startswith("/static/") or p.startswith("/vproxy/") or p.startswith("/cast-proxy/"):
        return None
    if p in ("/check", "/admin", "/codes-raw", "/apk", "/apk-tv", "/apk-tvtest", "/sw.js", "/manifest.json", "/download-tv", "/favicon.ico", "/account-info", "/logout", "/status"):
        return None
    if is_authed():
        return None
    return send_file(APP_FILE)


@app.after_request
def extend_session(resp):
    """Alltid inloggad (24/7): fornya cookien vid varje besok tills man loggar ut.
    Skippar /check (satter redan ratt cookie - far ALDRIG skriva over med gammal)
    och /logout (raderar)."""
    if request.path in ("/logout", "/check"):
        return resp
    c = request.cookies.get("mf_auth", "")
    if c and "|" in c and resp.status_code < 400:
        resp.set_cookie("mf_auth", c, httponly=True, samesite="Lax",
                        max_age=60 * 60 * 24 * 365 * 10, path="/")
    return resp


def proxy_fetch(path):
    """Hamta en sida/fil fran cinejoy. Allt serveras fran var rot sa sajtens
    egna lankar (api, _app, routes) funkar utan omskrivning."""
    url = CINEJOY + "/" + path if path else CINEJOY + "/"
    try:
        resp = requests.get(url, timeout=30,
                            headers={"User-Agent": UA}, allow_redirects=False)
    except Exception:
        return "Kunde inte na cinejoy", 502

    # redirects: rota om till var doman (samma sokkvag) - ingen loop
    if resp.status_code in (301, 302, 303, 307, 308):
        loc = resp.headers.get("Location", "")
        if loc.startswith(CINEJOY):
            loc = loc[len(CINEJOY):] or "/"
        elif loc.startswith("//"):
            loc = "https:" + loc
        r = Response("", status=resp.status_code)
        r.headers["Location"] = loc
        return r

    ctype = resp.headers.get("Content-Type", "")
    body = resp.content
    native = is_native_hls_browser()
    if "html" in ctype or "json" in ctype or "javascript" in ctype:
        text = body.decode("utf-8", errors="replace")
        # absoluta cinejoy-lankar -> var rot (gor att allt haller sig pa var doman)
        text = text.replace("https://cinejoy.to", "")
        text = text.replace("http://cinejoy.to", "")
        # VIDEO: ström-URL:er (nebula-CDN) -> var /vproxy sa Origin-blocket kringgas.
        # Server-till-server skickar ingen Origin -> CDN:en svarar 200.
        # UNDANTAG: Safari (native HLS) skickar ingen Origin sjalv -> behall
        # URL:en DIREKT sa videon gar rakt fran CDN:en (sparar Render-bandbredd).
        if not native:
            text = text.replace("https://nebula.bright67.online", "/vproxy/https://nebula.bright67.online")
            text = text.replace("http://nebula.bright67.online", "/vproxy/https://nebula.bright67.online")
        # no-referrer (skadar inte; vissa CDN:er svarar battre utan Referer)
        text = text.replace("<head>", '<head><meta name="referrer" content="no-referrer">', 1)
        # injicera stadaren (gommer cinejoy-marken) + Service Worker (Chrome)
        # eller native-HLS (Safari). SW:en kor videon genom var server (Render);
        # native-HLS kor den direkt fran CDN:en (ingen Render-bandbredd).
        if native:
            scripts = ('<script src="/static/cleanup.js"></script>'
                       '<script src="/static/account.js"></script>'
                       '<script src="/static/native-hls.js"></script>')
        else:
            scripts = ('<script src="/static/cleanup.js"></script>'
                       '<script src="/static/account.js"></script>'
                       '<script>if("serviceWorker" in navigator){'
                       'navigator.serviceWorker.register("/sw.js").then(function(){'
                       'if(!navigator.serviceWorker.controller&&!sessionStorage.getItem("mf-sw")){'
                       'sessionStorage.setItem("mf-sw","1");location.reload();}});}</script>')
        if "</head>" in text:
            text = text.replace("</head>", scripts + "</head>", 1)
        elif "</body>" in text:
            text = text.replace("</body>", scripts + "</body>", 1)
        # Cinejoy-namnet ar bannat - byt ut det dar cleanup.js inte nar
        # (titel + meta-taggar i html, PWA-manifestet som serveras som json).
        if "html" in ctype:
            # PWA: tvinga VAR manifest (Marioflix + egen ikon) - cinejoys far aldrig synas
            text = re.sub(r'<link[^>]*rel="manifest"[^>]*>',
                          '<link rel="manifest" href="/static/manifest.webmanifest">', text, flags=re.I)
            text = re.sub(r'<link[^>]*rel="(?:shortcut )?icon"[^>]*>',
                          '<link rel="icon" href="/static/icon-192.png">', text, flags=re.I)
            text = re.sub(r'<link[^>]*rel="apple-touch-icon"[^>]*>',
                          '<link rel="apple-touch-icon" href="/static/icon-192.png">', text, flags=re.I)
            text = re.sub(r"(<title[^>]*>)[^<]*</title>", r"\1Marioflix</title>", text, flags=re.I)
            text = re.sub(r'(<meta[^>]*content=")([^"]*)(")',
                          lambda m: m.group(1) + m.group(2).replace("Cinejoy", "Marioflix") + m.group(3), text)
        elif "json" in ctype:
            text = text.replace("Cinejoy", "Marioflix")
        body = text.encode("utf-8")

    r = Response(body, status=resp.status_code)
    r.headers["Content-Type"] = ctype
    return r


@app.route("/")
def index():
    """Roten = cinejoy (rent, genom proxyn)."""
    return proxy_fetch("")


@app.route("/download-tv")
def download_tv():
    """Kodskydd for TV-apps-nedladdning (fore inloggning): ratt kod -> ok, sedan /apk-tv."""
    if request.args.get("code", "").strip().lower() == "m123":
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401


@app.route("/status")
def status():
    """Bindningsstatus UTAN att binda (for apparnas utkastnings-koll):
    fel=raderad, ledig=slappt, upptagen=annan enhet, bunden=min enhet."""
    code = request.args.get("code", "").strip().lower()
    device = request.args.get("device", "").strip()
    codes, used, _notes = load_data()
    if code not in codes:
        return jsonify({"ok": False, "reason": "fel"})
    if not device:
        return jsonify({"ok": True, "reason": "medlem"})
    prev = used.get(code)
    if prev is None:
        return jsonify({"ok": False, "reason": "ledig"})
    if prev == device:
        return jsonify({"ok": True, "reason": "bunden"})
    return jsonify({"ok": False, "reason": "upptagen"})


@app.route("/account-info")
def account_info():
    """Kontoinfo for inloggad session (koden). 401 om utloggad/raderad kod."""
    c = request.cookies.get("mf_auth", "")
    if "|" not in c:
        return jsonify({"ok": False}), 401
    code, device = c.split("|", 1)
    codes, used, _notes = load_data()
    if used.get(code) == device:
        return jsonify({"ok": True, "code": code})
    return jsonify({"ok": False}), 401


@app.route("/logout")
def logout():
    """Loggar ut: raderar cookien -> tillbaka till login."""
    resp = redirect("/")
    resp.delete_cookie("mf_auth", path="/")
    return resp


@app.route("/favicon.ico")
def favicon():
    """Var ikon overallt - cinejoys favicon far aldrig visas."""
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "static", "icon-192.png"),
                     mimetype="image/png")


@app.route("/manifest.json")
def manifest_json():
    """Var egen PWA-manifest (Marioflix + egen ikon) - cinejoys manifest visas aldrig."""
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "static", "manifest.webmanifest"),
                     mimetype="application/manifest+json")


@app.route("/<path:path>")
def catch_all(path):
    """Allt annat (api, _app, routes, manifest osv) skickas till cinejoy."""
    return proxy_fetch(path)


@app.route("/vproxy/<path:url>")
def vproxy(url):
    """Streamar videon (nebula-CDN) server-till-server - inget Origin skickas,
    sa CDN:en svarar 200. m3u8:er skrivs om sa segmenten ocksa gar via oss."""
    try:
        upstream = requests.get(url, timeout=60,
                                headers={"User-Agent": UA}, stream=True, allow_redirects=True)
    except Exception:
        return "Streamfel", 502
    if upstream.status_code != 200:
        return "Streamfel", upstream.status_code
    ctype = upstream.headers.get("Content-Type", "")
    if "mpegurl" in ctype or url.endswith(".m3u8"):
        base = url[:url.rfind("/") + 1]
        body = upstream.content.decode("utf-8", errors="replace")
        lines = []
        for line in body.splitlines():
            if line and not line.startswith("#"):
                if line.startswith("http"):
                    line = "/vproxy/" + line
                elif line.startswith("/"):
                    line = "/vproxy/https://nebula.bright67.online" + line
                else:
                    line = "/vproxy/" + base + line
            lines.append(line)
        return Response("\n".join(lines), content_type="application/vnd.apple.mpegurl")
    r = Response(upstream.iter_content(chunk_size=65536),
                 content_type=ctype or "application/octet-stream")
    length = upstream.headers.get("Content-Length")
    if length:
        r.headers["Content-Length"] = length
    r.headers["Accept-Ranges"] = "bytes"
    return r


@app.route("/cast-proxy/<path:url>")
def cast_proxy(url):
    """Google Cast-hjalp: nebula-CDN:en serverar ALLT som image/jpeg - aven
    m3u8-spellistorna. Cast-mottagaren (TV:n) kraver ratt Content-Type pa
    spellistan och vaxrar spela annars (ikon visas men ingen film).
    Bara MANIFESTEN gar via oss (pytte, KB) - segmenten skrivs om till
    DIREKTA nebula-URL:er sa ingen Render-bandbredd forbrukas."""
    try:
        upstream = requests.get(url, timeout=30,
                                headers={"User-Agent": UA}, stream=True, allow_redirects=True)
    except Exception:
        return "Streamfel", 502
    if upstream.status_code != 200:
        return "Streamfel", upstream.status_code
    body = upstream.content
    if body[:20].lstrip().upper().startswith(b"#EXTM3U"):
        base = url[:url.rfind("/") + 1]
        split = url.split("/", 3)
        scheme_host = split[0] + "//" + split[2] if len(split) > 2 else ""
        text = body.decode("utf-8", errors="replace")

        # KONFIRMATIONSTEST (2.23): ALLT gar via oss (manifest OCH segment) sa
        # att segmenten kan serveras med ratt Content-Type. (Fore detta gick
        # segmenten direkt fran CDN:en med text/html/image-jpeg som receivern
        # avvisade aven med FMP4-hinten.)
        def rw(u):
            if u.startswith("http"):
                return "/cast-proxy/" + u
            if u.startswith("/"):
                return "/cast-proxy/" + scheme_host + u
            return "/cast-proxy/" + base + u

        lines = []
        for line in text.splitlines():
            if line and not line.startswith("#"):
                lines.append(rw(line))
            else:
                lines.append(line)
        out = "\n".join(lines)
        # URI="..." i #-rader (EXT-X-MAP init, EXT-X-MEDIA audio) - ocksa via oss
        out = re.sub(r'URI="([^"]+)"',
                     lambda mm: 'URI="' + rw(mm.group(1)) + '"', out)
        return Response(out, content_type="application/vnd.apple.mpegurl")
    # Inte ett manifest (segment/init): sniffa fMP4 -> video/mp4 (annars
    # text/html/image-jpeg fran CDN:en som receivern avvisar). KONFIRMATIONSTEST.
    # fMP4-box = [4-byte storlek][4-byte typ] - typen ligger pa byte 4-8.
    head = body[:16]
    if head[4:8] in (b"ftyp", b"moov", b"moof", b"styp", b"sidx", b"free",
                     b"mdat", b"skip", b"wide", b"mfra"):
        return Response(body, content_type="video/mp4")
    ctype = upstream.headers.get("Content-Type", "application/octet-stream")
    return Response(body, content_type=ctype)


@app.route("/sw.js")
def sw_file():
    """Service Worker fran roten - scope blir / sa den styr alla sidor."""
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "sw.js"),
                     mimetype="application/javascript")


@app.route("/codes-raw")
def codes_raw():
    """Returnerar hela kodfilen (sakerhetskopia) - skydd med admin-losenord."""
    if request.args.get("pw", "") != os.environ.get(ADMIN_PW_ENV, ""):
        return "Fel losenord.", 401
    with open(CODES_FILE, encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "application/json; charset=utf-8"}


@app.route("/apk")
def apk():
    """Serverar Android-appen - ren nedladdningslank utan namn i adressen."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Marioflix.apk")
    if not os.path.exists(path):
        return "APK saknas", 404
    return send_file(path, as_attachment=True, download_name="Marioflix.apk")


@app.route("/apk-tvtest")
def apk_tvtest():
    """Serverar TV TEST-appen (Marioflix TvTest) - ren nedladdningslank."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Marioflix-TvTest.apk")
    if not os.path.exists(path):
        return "APK saknas", 404
    return send_file(path, as_attachment=True, download_name="Marioflix-TvTest.apk")


@app.route("/apk-tv")
def apk_tv():
    """Serverar TV-appen (Marioflix-Tv) - ren nedladdningslank."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Marioflix-Tv.apk")
    if not os.path.exists(path):
        return "APK saknas", 404
    return send_file(path, as_attachment=True, download_name="Marioflix-Tv.apk")


@app.route("/admin")
def admin():
    if request.args.get("pw", "") != os.environ.get(ADMIN_PW_ENV, ""):
        return "Fel losenord.", 401

    msg = ""
    codes, used, notes = load_data()
    add = request.args.get("add")
    remove = request.args.get("remove")
    release = request.args.get("release")
    note_code = request.args.get("note_code")
    note_value = request.args.get("note_value", "").strip()
    add_note = request.args.get("note", "").strip()  # notis i samma steg som ny kod
    saved_note = ""
    if add is not None:
        add = add.strip().lower()
        if add and add not in codes:
            codes.append(add)
            if add_note:
                notes[add] = add_note
            save_data(codes, used, notes)
            saved_note = " (sparat permanent)" if push_to_github(codes, used, notes) else " (OBS: sparat tills nasta uppdatering - lagg till GITHUB_TOKEN i Render)"
            msg = "Kod '" + add + "' tillagd" + (" med notis." if add_note else ".") + saved_note
        else:
            msg = "Koden finns redan (eller tom)."
    elif remove is not None:
        remove = remove.strip().lower()
        codes = [c for c in codes if c != remove]
        used.pop(remove, None)
        notes.pop(remove, None)
        save_data(codes, used, notes)
        push_to_github(codes, used, notes)
        msg = "Kod '" + remove + "' borttagen."
    elif release is not None:
        release = release.strip().lower()
        used.pop(release, None)
        save_data(codes, used, notes)
        push_to_github(codes, used, notes)
        msg = "Kod '" + release + "' frigjord - kan anvandas pa ny enhet."
    elif note_code is not None:
        note_code = note_code.strip().lower()
        if note_value:
            notes[note_code] = note_value
        else:
            notes.pop(note_code, None)
        save_data(codes, used, notes)
        pushed = push_to_github(codes, used, notes)
        msg = "Notis sparad for '" + note_code + "'." + (" (permanent)" if pushed else " (OBS: sparas tills nasta uppdatering)")

    pw = request.args.get("pw", "")
    rows = ""
    for c in codes:
        dev = used.get(c)
        note = notes.get(c, "")
        if dev:
            rows += ("<tr><td>" + c + "</td><td style='color:#888'>upptagen</td>"
                     + "<td>" + note + "</td>"
                     + "<td><a href='/admin?pw=" + pw + "&release=" + c + "'>slapp</a> "
                     + "<a href='/admin?pw=" + pw + "&remove=" + c + "'>ta bort</a></td></tr>")
        else:
            rows += ("<tr><td>" + c + "</td><td style='color:#6bff8b'>ledig</td>"
                     + "<td>" + note + "</td>"
                     + "<td><a href='/admin?pw=" + pw + "&remove=" + c + "'>ta bort</a></td></tr>")
    options = "".join("<option value='" + c + "'>" + c + "</option>" for c in codes)
    html = """<!doctype html><html><head><meta charset="utf-8"><title>Marioflix koder</title>
<style>body{font-family:Roboto,Arial,sans-serif;background:#121218;color:#fff;padding:30px;max-width:500px;margin:auto}
h1{color:#e52020}table{border-collapse:collapse;width:100%}td{padding:8px;border-bottom:1px solid #333}
a{color:#ff6b6b}input{background:#1e1e28;border:1px solid #333;color:#fff;padding:10px;border-radius:8px}
button{background:#e52020;color:#fff;border:0;padding:10px 20px;border-radius:999px;cursor:pointer}
.msg{color:#6bff8b;margin:10px 0}</style></head><body>
<h1>Marioflix koder</h1>
<div class="msg">__MSG__</div>
<table>__ROWS__</table>
<h3>Lagg till kod (med notis)</h3>
<form><input type="hidden" name="pw" value="__PW__"><input name="add" placeholder="Ny kod">
<input name="note" placeholder="Vem? (t.ex. Mario)">
<button type="submit">Lagg till</button></form>
<h3>Notis till kod (vem ar vem?)</h3>
<form><input type="hidden" name="pw" value="__PW__">
<select name="note_code" style="background:#1e1e28;border:1px solid #333;color:#fff;padding:10px;border-radius:8px">__OPTIONS__</select>
<input name="note_value" placeholder="t.ex. Mario">
<button type="submit">Spara notis</button></form>
</body></html>"""
    return html.replace("__MSG__", msg).replace("__ROWS__", rows).replace("__PW__", request.args.get("pw", "")).replace("__OPTIONS__", options)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
