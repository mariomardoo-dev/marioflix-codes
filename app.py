# Marioflix-koder - liten server som haller koderna.
# Koderna ligger i Render-miljovariabeln CODES (t.ex. "m,1") - andras i Render
# dashboard eller via admin-sidan. Inga koder finns i koden eller i repot.
import base64
import json
import os
import urllib.request

from flask import Flask, jsonify, request

app = Flask(__name__)

CODES_ENV = "CODES"  # komma-separerade koder, t.ex. "m,1"
ADMIN_PW_ENV = "ADMIN_PW"
RENDER_KEY_ENV = "RENDER_API_KEY"
SERVICE_NAME = "marioflix-codes"


def current_codes():
    raw = os.environ.get(CODES_ENV, "").strip()
    return [c.strip().lower() for c in raw.split(",") if c.strip()]


def set_codes_env(codes):
    """Uppdatera CODES-miljovariabeln pa Render-tjansten via Render API."""
    key = os.environ.get(RENDER_KEY_ENV, "")
    if not key:
        return False
    try:
        # hitta service-id genom att lista tjansterna
        req = urllib.request.Request(
            "https://api.render.com/v1/services?name=" + SERVICE_NAME,
            headers={"Authorization": "Bearer " + key},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            services = json.loads(r.read().decode())
        if not services:
            return False
        sid = services[0]["service"]["id"]

        # las nuvarande envVars (Render doljer varden, sa bygg listan fran appens egna)
        env_vars = [
            {"key": k, "value": os.environ.get(k, "")}
            for k in (CODES_ENV, ADMIN_PW_ENV, RENDER_KEY_ENV)
            if os.environ.get(k)
        ]
        for ev in env_vars:
            if ev["key"] == CODES_ENV:
                ev["value"] = ",".join(codes)
                break
        else:
            env_vars.append({"key": CODES_ENV, "value": ",".join(codes)})

        data = json.dumps({"envVars": env_vars}).encode()
        req = urllib.request.Request(
            "https://api.render.com/v1/services/" + sid,
            data=data,
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status in (200, 201)
    except Exception:
        return False


@app.route("/check")
def check():
    code = request.args.get("code", "").strip().lower()
    return jsonify({"ok": code in current_codes()})


@app.route("/admin")
def admin():
    if request.args.get("pw", "") != os.environ.get(ADMIN_PW_ENV, ""):
        return "Fel losenord.", 401

    msg = ""
    codes = current_codes()
    add = request.args.get("add")
    remove = request.args.get("remove")
    if add is not None:
        add = add.strip().lower()
        if add and add not in codes:
            codes.append(add)
            os.environ[CODES_ENV] = ",".join(codes)  # galler direkt
            pushed = set_codes_env(codes)
            msg = "Kod '" + add + "' tillagd." + ("" if pushed else " (OBS: kunde inte spara pa Render - anvand dashboard for permanenta andringar)")
        else:
            msg = "Koden finns redan (eller tom)."
    elif remove is not None:
        remove = remove.strip().lower()
        codes = [c for c in codes if c != remove]
        os.environ[CODES_ENV] = ",".join(codes)
        set_codes_env(codes)
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
