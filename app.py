# Marioflix-koder - liten server som haller koderna.
# Koderna ligger i codes.json (i repot) - admin-sidan andrar filen direkt.
# OBS: vid deploy las koderna fran repots codes.json, sa hall filen synkad.
import json
import os
import urllib.request

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

ADMIN_PW_ENV = "ADMIN_PW"
CODES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codes.json")


def load_codes():
    try:
        with open(CODES_FILE, encoding="utf-8") as f:
            return [c.lower() for c in json.load(f).get("codes", [])]
    except Exception:
        # fallback: gamla env-variabeln om filen saknas
        return [c.strip().lower() for c in os.environ.get("CODES", "").split(",") if c.strip()]


def save_codes(codes):
    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump({"codes": codes}, f, indent=2)


@app.route("/check")
def check():
    code = request.args.get("code", "").strip().lower()
    return jsonify({"ok": code in load_codes()})


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
    codes = load_codes()
    add = request.args.get("add")
    remove = request.args.get("remove")
    if add is not None:
        add = add.strip().lower()
        if add and add not in codes:
            codes.append(add)
            save_codes(codes)
            msg = "Kod '" + add + "' tillagd."
        else:
            msg = "Koden finns redan (eller tom)."
    elif remove is not None:
        remove = remove.strip().lower()
        codes = [c for c in codes if c != remove]
        save_codes(codes)
        msg = "Kod '" + remove + "' borttagen."

    rows = "".join(
        "<tr><td>" + c + "</td><td><a href='/admin?pw=" + request.args.get("pw", "")
        + "&remove=" + c + "'>ta bort</a></td></tr>"
        for c in codes
    )
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
