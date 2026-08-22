# Marioflix-koder - liten server som haller koderna.
# Koderna ligger i codes.json (i repot) - admin-sidan andrar filen direkt.
# En-kod-en-enhet: forsta enheten som loggar in med en kod binds till den.
# /cinejoy = proxy som visar cinejoy rent (utan cinejoy-marken).
# OBS: vid deploy las koderna fran repots codes.json, sa hall filen synkad.
import json
import os
import re
import urllib.request

import requests
from flask import Flask, Response, jsonify, redirect, request, send_file

app = Flask(__name__)

ADMIN_PW_ENV = "ADMIN_PW"
CODES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codes.json")

# --- Proxy till cinejoy ---
PROXY_BASE = "/cinejoy"
CINEJOY = "https://cinejoy.to"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def load_data():
    try:
        with open(CODES_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d.get("codes", []), d.get("used", {})
    except Exception:
        return [], {}


def save_data(codes, used):
    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump({"codes": codes, "used": used}, f, indent=2)


def load_codes():
    return load_data()[0]


@app.route("/check")
def check():
    code = request.args.get("code", "").strip().lower()
    device = request.args.get("device", "").strip()
    codes, used = load_data()
    if code not in codes:
        return jsonify({"ok": False, "reason": "fel"})
    if not device:
        # ingen enhet skickad (gammal stil) - bara medlemskoll
        return jsonify({"ok": True})
    prev = used.get(code)
    if prev is None:
        # forsta gangen: binda koden till denna enhet
        used[code] = device
        save_data(codes, used)
        return jsonify({"ok": True, "first": True})
    if prev == device:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "reason": "upptagen"})


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
    if "html" in ctype:
        text = body.decode("utf-8", errors="replace")
        # absoluta cinejoy-lankar -> var rot (gor att allt haller sig pa var doman)
        text = text.replace("https://cinejoy.to", "")
        text = text.replace("http://cinejoy.to", "")
        # no-referrer (skadar inte; vissa CDN:er svarar battre utan Referer)
        text = text.replace("<head>", '<head><meta name="referrer" content="no-referrer">', 1)
        # injicera stadaren (gommer cinejoy-marken) + play-vidarelogiken
        scripts = ('<script src="/static/cleanup.js"></script>'
                   '<script src="/static/playforward.js"></script>')
        if "</head>" in text:
            text = text.replace("</head>", scripts + "</head>", 1)
        elif "</body>" in text:
            text = text.replace("</body>", scripts + "</body>", 1)
        body = text.encode("utf-8")

    r = Response(body, status=resp.status_code)
    r.headers["Content-Type"] = ctype
    return r


@app.route("/")
def index():
    """Roten = cinejoy (rent, genom proxyn)."""
    return proxy_fetch("")


@app.route("/<path:path>")
def catch_all(path):
    """Allt annat (api, _app, routes, manifest osv) skickas till cinejoy."""
    return proxy_fetch(path)


@app.route("/apk")
def apk():
    """Serverar Android-appen - ren nedladdningslank utan namn i adressen."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Marioflix.apk")
    if not os.path.exists(path):
        return "APK saknas", 404
    return send_file(path, as_attachment=True, download_name="Marioflix.apk")


@app.route("/admin")
def admin():
    if request.args.get("pw", "") != os.environ.get(ADMIN_PW_ENV, ""):
        return "Fel losenord.", 401

    msg = ""
    codes, used = load_data()
    add = request.args.get("add")
    remove = request.args.get("remove")
    release = request.args.get("release")
    if add is not None:
        add = add.strip().lower()
        if add and add not in codes:
            codes.append(add)
            save_data(codes, used)
            msg = "Kod '" + add + "' tillagd."
        else:
            msg = "Koden finns redan (eller tom)."
    elif remove is not None:
        remove = remove.strip().lower()
        codes = [c for c in codes if c != remove]
        used.pop(remove, None)
        save_data(codes, used)
        msg = "Kod '" + remove + "' borttagen."
    elif release is not None:
        release = release.strip().lower()
        used.pop(release, None)
        save_data(codes, used)
        msg = "Kod '" + release + "' frigjord - kan anvandas pa ny enhet."

    pw = request.args.get("pw", "")
    rows = ""
    for c in codes:
        dev = used.get(c)
        if dev:
            rows += ("<tr><td>" + c + "</td><td style='color:#888'>upptagen</td>"
                     + "<td><a href='/admin?pw=" + pw + "&release=" + c + "'>slapp</a> "
                     + "<a href='/admin?pw=" + pw + "&remove=" + c + "'>ta bort</a></td></tr>")
        else:
            rows += ("<tr><td>" + c + "</td><td style='color:#6bff8b'>ledig</td>"
                     + "<td><a href='/admin?pw=" + pw + "&remove=" + c + "'>ta bort</a></td></tr>")
    html = """<!doctype html><html><head><meta charset="utf-8"><title>Marioflix koder</title>
<style>body{font-family:Roboto,Arial,sans-serif;background:#121218;color:#fff;padding:30px;max-width:500px;margin:auto}
h1{color:#e52020}table{border-collapse:collapse;width:100%}td{padding:8px;border-bottom:1px solid #333}
a{color:#ff6b6b}input{background:#1e1e28;border:1px solid #333;color:#fff;padding:10px;border-radius:8px}
button{background:#e52020;color:#fff;border:0;padding:10px 20px;border-radius:999px;cursor:pointer}
.msg{color:#6bff8b;margin:10px 0}</style></head><body>
<h1>Marioflix koder</h1>
<div class="msg">__MSG__</div>
<table>__ROWS__</table>
<h3>Lagg till kod</h3>
<form><input type="hidden" name="pw" value="__PW__"><input name="add" placeholder="Ny kod">
<button type="submit">Lagg till</button></form>
</body></html>"""
    return html.replace("__MSG__", msg).replace("__ROWS__", rows).replace("__PW__", request.args.get("pw", ""))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
