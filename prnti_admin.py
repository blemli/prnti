#!/usr/bin/env python3

"""
Tiny admin backend for prnti: download and upload newsletters.csv, nothing else.

  GET  /                 minimal html page with download link and upload form
  GET  /newsletters.csv  download the current file
  POST /newsletters.csv  upload a replacement (multipart field "file" or raw body)
  POST /get_all          run get_all.py in the background (restarted on crash)
  GET  /get_all/status   json: running, done, total, restarts, error

POSTs are protected by basic auth if PRNTI_ADMIN_PASS is set in .env.
"""

import csv
import io
import os
import subprocess
import sys
import threading
import time

from dotenv import load_dotenv
from flask import Flask, Response, request, send_file

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "newsletters.csv")
NEWSLETTERS_DIR = os.path.join(HERE, "newsletters")
GET_ALL = os.path.join(HERE, "get_all.py")
MAX_RESTARTS = 5
HEADER = ["id", "type", "nr", "date", "url"]
MAX_BYTES = 5 * 1024 * 1024
ADMIN_PASS = os.getenv("PRNTI_ADMIN_PASS")  # optional: if set, uploads need basic auth (any user)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES

PAGE = """<!doctype html><title>prnti admin</title>
<h1>prnti admin</h1>
<p><a href="/newsletters.csv" download>download newsletters.csv</a></p>
<form method="post" action="/newsletters.csv" enctype="multipart/form-data">
<input type="file" name="file" accept=".csv,text/csv" required>
<button type="submit">upload newsletters.csv</button>
</form>
<p><button id="get_all" disabled>get_all (fetch missing screenshots)</button> <span id="progress"></span></p>
<script>
const btn = document.getElementById("get_all"), out = document.getElementById("progress");
async function poll() {
  const s = await (await fetch("/get_all/status")).json();
  btn.disabled = s.running;
  out.textContent = `${s.done} / ${s.total}` + (s.running ? " running" : "")
    + (s.restarts ? ` (${s.restarts} restarts)` : "") + (s.error ? ` - ${s.error}` : "");
}
btn.onclick = async () => { btn.disabled = true; await fetch("/get_all", {method: "POST"}); poll(); };
poll(); setInterval(poll, 2000);
</script>
"""

state = {"running": False, "restarts": 0, "error": ""}
lock = threading.Lock()


def progress():
    """(done, total): newsletters with a url vs. those that already have a screenshot."""
    with open(CSV_PATH, newline="") as f:
        ids = [row["id"] for row in csv.DictReader(f) if row["url"]]
    done = sum(os.path.isfile(os.path.join(NEWSLETTERS_DIR, f"{i}.jpg")) for i in ids)
    return done, len(ids)


def run_get_all():
    """Run get_all.py to completion, restarting it if it crashes (it skips already fetched files)."""
    for attempt in range(MAX_RESTARTS + 1):
        proc = subprocess.run([sys.executable, "-u", GET_ALL], cwd=HERE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0:
            error = ""
            break
        lines = [l for l in proc.stderr.splitlines() if l.strip()]
        error = lines[-1] if lines else f"exit code {proc.returncode}"
        print(f"get_all attempt {attempt + 1} failed: {error}", flush=True)
        if attempt == MAX_RESTARTS:
            break
        with lock:
            state["restarts"] = attempt + 1
            state["error"] = error
        time.sleep(5)
    with lock:
        state["running"] = False
        state["error"] = error


def validate(data: bytes) -> str | None:
    """Return an error message, or None if data is an acceptable newsletters.csv."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "not utf-8"
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0] != HEADER:
        return f"first line must be {','.join(HEADER)}"
    for i, row in enumerate(rows[1:], start=2):
        if row and len(row) != len(HEADER):
            return f"line {i}: expected {len(HEADER)} columns, got {len(row)}"
    return None


@app.get("/")
def index():
    return PAGE


@app.get("/newsletters.csv")
def download():
    return send_file(CSV_PATH, mimetype="text/csv", as_attachment=True, download_name="newsletters.csv")


def unauthorized():
    if ADMIN_PASS and (request.authorization is None or request.authorization.password != ADMIN_PASS):
        return Response("password required\n", status=401, headers={"WWW-Authenticate": 'Basic realm="prnti admin"'})


@app.post("/get_all")
def get_all():
    if denied := unauthorized():
        return denied
    with lock:
        if state["running"]:
            return Response("already running\n", status=409)
        state.update(running=True, restarts=0, error="")
    threading.Thread(target=run_get_all, daemon=True).start()
    return Response("started\n", status=202)


@app.get("/get_all/status")
def get_all_status():
    done, total = progress()
    with lock:
        return {"done": done, "total": total, **state}


@app.post("/newsletters.csv")
def upload():
    if denied := unauthorized():
        return denied
    upload = request.files.get("file") if request.mimetype == "multipart/form-data" else None
    data = upload.read() if upload else request.get_data()
    if not data:
        return Response("empty upload\n", status=400)
    if error := validate(data):
        return Response(error + "\n", status=400)
    tmp = CSV_PATH + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CSV_PATH)  # atomic: readers never see a half-written file
    if upload:
        return PAGE.replace("<h1>prnti admin</h1>", "<h1>prnti admin</h1><p><b>uploaded.</b></p>")
    return Response("ok\n", status=200)


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=8080)
