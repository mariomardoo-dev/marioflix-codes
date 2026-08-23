# Synka live-koderna till repot - KOR INNAN VARJE DEPLOY!
# Annars raderas koder som lagts till via admin-sidan (deploy overtyder live-filen).
import json
import os
import subprocess
import urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))
RAW = "https://marioflix-codes.onrender.com/codes-raw?pw=marioflix2026"

with urllib.request.urlopen(RAW, timeout=60) as r:
    data = json.loads(r.read().decode())

with open(os.path.join(REPO, "codes.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

subprocess.run(["git", "add", "codes.json"], cwd=REPO, check=True)
subprocess.run(["git", "-c", "user.name=mariomardoo-dev",
                "-c", "user.email=mariomardoo-dev@users.noreply.github.com",
                "commit", "-m", "synk: live-koder till repot"], cwd=REPO, check=True)
subprocess.run(["git", "push"], cwd=REPO, check=True)
print("SYNKAT:", data["codes"])
print("BINDNINGAR:", data["used"])
