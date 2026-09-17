#!/usr/bin/env python3

"""
Tiny admin backend for prnti: download and upload newsletters.csv, and run get_all.

  GET  /                 minimal html page: download link, upload form, get_all button
  GET  /newsletters.csv  download the current file
  POST /newsletters.csv  upload a replacement (multipart field "file" or raw body); rejected with the
                         reasons listed if it is malformed
  POST /get_all          run get_all.py in the background (restarted on failure, resumed after reboot)
  GET  /get_all/status   json: running, done, total, restarts, error, csv_error

POSTs are protected by basic auth if PRNTI_ADMIN_PASS is set in .env.
"""

import csv
import io
import os
import re
import subprocess
import sys
import threading
import time
from html import escape

from dotenv import load_dotenv
from flask import Flask, Response, request, send_file

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "newsletters.csv")
NEWSLETTERS_DIR = os.path.join(HERE, "newsletters")
GET_ALL = os.path.join(HERE, "get_all.py")
MARKER = os.path.join(HERE, "get_all.requested")  # exists while a run is wanted; survives reboots
MAX_RESTARTS = 5
HEADER = ["id", "type", "nr", "date", "url"]
URL_PREFIX = "https://mailchi.mp/"
MAX_BYTES = 5 * 1024 * 1024
MAX_ERRORS = 10
ADMIN_PASS = os.getenv("PRNTI_ADMIN_PASS")  # optional: if set, POSTs need basic auth (any user)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES

PAGE = """<!doctype html><title>prnti admin</title>
<style>
body { background: #f9f9f9; color: #444; font-family: "JetBrains Mono", monospace; text-align: center; padding: 15px }
h1 { color: #8C1AC4; font-size: 3rem }
a { color: #8C1AC4 }
input, button { font: inherit; font-size: 1.2rem; padding: .5rem; margin: 5px; border-radius: 8px; border: 2px solid #8C1AC4; background: #fff; color: #444 }
button:disabled { opacity: .4 }
pre { font: inherit; display: inline-block; text-align: left }
</style>
<h1>prnti admin</h1>
<!--MESSAGE-->
<p><a href="/newsletters.csv" download>download newsletters.csv</a></p>
<form method="post" action="/newsletters.csv" enctype="multipart/form-data">
<input type="file" name="file" accept=".csv,text/csv" required>
<button type="submit">upload newsletters.csv</button>
</form>
<p><button id="get_all" disabled>get_all (fetch missing screenshots)</button> <span id="progress"></span></p>
<p id="csv_error" style="color:red"></p>
<script>
const btn = document.getElementById("get_all"), out = document.getElementById("progress"),
      err = document.getElementById("csv_error");
async function poll() {
  const s = await (await fetch("/get_all/status")).json();
  btn.disabled = s.running || !!s.csv_error;
  err.textContent = s.csv_error ? "newsletters.csv on disk is broken, upload a fixed one: " + s.csv_error : "";
  out.textContent = `${s.done} / ${s.total}` + (s.running ? " running" : "")
    + (s.restarts ? ` (${s.restarts} restarts)` : "") + (s.error ? ` - ${s.error}` : "");
}
btn.onclick = async () => {
  btn.disabled = true;
  const r = await fetch("/get_all", {method: "POST"});
  if (!r.ok) alert(await r.text());
  poll();
};
poll(); setInterval(poll, 2000);
</script>
"""

state = {"running": False, "restarts": 0, "error": ""}
lock = threading.Lock()


def page(message="", ok=True):
    color = "green" if ok else "red"
    html = f'<pre style="color:{color}">{escape(message)}</pre>' if message else ""
    return PAGE.replace("<!--MESSAGE-->", html)


def validate(data: bytes) -> list[str]:
    """Return the list of problems (empty if data is an acceptable newsletters.csv)."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        return [f"not utf-8 (byte {e.start})"]
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as e:
        return [f"unparseable csv: {e}"]
    if not rows or rows[0] != HEADER:
        return [f"first line must be {','.join(HEADER)}, got {','.join(rows[0]) if rows else 'nothing'}"]
    errors, seen = [], set()
    for i, row in enumerate(rows[1:], start=2):
        if not row:
            continue  # blank line
        if len(row) != len(HEADER):
            errors.append(f"line {i}: expected {len(HEADER)} columns, got {len(row)}")
            continue
        id_, type_, nr, date, url = row
        if not re.fullmatch(r"\d{3}", id_):
            errors.append(f"line {i}: id must be 3 digits, got {id_!r}")
        elif id_ in seen:
            errors.append(f"line {i}: duplicate id {id_}")
        seen.add(id_)
        if not type_:
            errors.append(f"line {i}: type is empty")
        if not nr.isdigit():
            errors.append(f"line {i}: nr must be a number, got {nr!r}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            errors.append(f"line {i}: date must be YYYY-MM-DD, got {date!r}")
        if url and not url.startswith(URL_PREFIX):
            errors.append(f"line {i}: url must start with {URL_PREFIX} (or be empty), got {url!r}")
        if len(errors) >= MAX_ERRORS:
            errors.append("... (more errors not shown)")
            break
    return errors


def csv_on_disk_error() -> str:
    """Why newsletters.csv on disk is unusable, or '' if it is fine."""
    try:
        with open(CSV_PATH, "rb") as f:
            errors = validate(f.read())
    except OSError as e:
        return str(e)
    return "; ".join(errors)


def progress():
    """(done, total): newsletters with a url vs. those that already have a screenshot."""
    with open(CSV_PATH, newline="") as f:
        ids = [row["id"] for row in csv.DictReader(f) if row.get("url")]
    done = sum(os.path.getsize(p) > 0 for p in (os.path.join(NEWSLETTERS_DIR, f"{i}.jpg") for i in ids) if os.path.isfile(p))
    return done, len(ids)


def run_get_all():
    """Run get_all.py to completion, restarting it if it fails (it only fetches what is missing)."""
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
    if os.path.exists(MARKER):
        os.remove(MARKER)
    with lock:
        state["running"] = False
        state["error"] = error


def start_get_all() -> str | None:
    """Start a run in the background. Returns an error message if it cannot start."""
    if error := csv_on_disk_error():
        return f"newsletters.csv is broken: {error}"
    with lock:
        if state["running"]:
            return "already running"
        state.update(running=True, restarts=0, error="")
    open(MARKER, "w").close()
    threading.Thread(target=run_get_all, daemon=True).start()
    return None


@app.get("/")
def index():
    return page()


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
    if error := start_get_all():
        return Response(error + "\n", status=409 if error == "already running" else 400)
    return Response("started\n", status=202)


@app.get("/get_all/status")
def get_all_status():
    csv_error = csv_on_disk_error()
    try:
        done, total = progress()
    except Exception as e:  # unreadable csv: still answer, so the page can show the problem
        done, total = 0, 0
        csv_error = csv_error or str(e)
    with lock:
        return {"done": done, "total": total, "csv_error": csv_error, **state}


@app.post("/newsletters.csv")
def upload():
    if denied := unauthorized():
        return denied
    upload = request.files.get("file") if request.mimetype == "multipart/form-data" else None
    data = upload.read() if upload else request.get_data()
    errors = ["empty upload"] if not data else validate(data)
    if errors:
        text = "newsletters.csv rejected, nothing changed:\n" + "\n".join(errors)
        if upload:
            return page(text, ok=False), 400
        return Response(text + "\n", status=400)
    tmp = CSV_PATH + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CSV_PATH)  # atomic: readers never see a half-written file
    if upload:
        return page("uploaded.")
    return Response("ok\n", status=200)


if __name__ == "__main__":
    from waitress import serve

    if os.path.exists(MARKER):  # a run was interrupted (power cut, restart): pick it up again
        print("resuming interrupted get_all run", flush=True)
        start_get_all()
    serve(app, host="0.0.0.0", port=8080)
