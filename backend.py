"""
TR YouTube 24H Live Studio — Backend
Python 3 + Flask + FFmpeg

Run:
  pip install -r requirements.txt
  cp .env.example .env   # set TR_LIVE_ADMIN_TOKEN + secrets
  python backend.py

Then open http://SERVER_IP:5000  (frontend is served from ./frontend/)
Or point the Blogger page at http://SERVER_IP:5000

SECURITY:
- Stream key is stored ONLY on this server in data/settings.json (chmod 600).
  It is NEVER returned in full via any API and NEVER written to logs.
- All /api/* endpoints (except /api/health) require header:
    X-Admin-Token: <TR_LIVE_ADMIN_TOKEN>
- Use HTTPS (reverse proxy / Cloudflare Tunnel / Nginx) in production.
- Only your own videos, or videos you have permission to broadcast.
"""
import os, json, time, secrets, subprocess, threading, re, shutil
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import psutil
except Exception:
    psutil = None

BASE = Path(__file__).resolve().parent
UPLOAD_DIR = BASE / "uploads"
DATA_DIR = BASE / "data"
LOG_FILE = DATA_DIR / "app.log"
SETTINGS_FILE = DATA_DIR / "settings.json"
FRONTEND_DIR = BASE / "frontend"

UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
FRONTEND_DIR.mkdir(exist_ok=True)

ADMIN_TOKEN = os.environ.get("TR_LIVE_ADMIN_TOKEN", "").strip()
if not ADMIN_TOKEN:
    ADMIN_TOKEN = secrets.token_urlsafe(32)
    print(f"[TR LIVE] No TR_LIVE_ADMIN_TOKEN set — generated one-time token: {ADMIN_TOKEN}")
    print("[TR LIVE] Set TR_LIVE_ADMIN_TOKEN in .env and restart. This token will change on restart.")

ALLOWED_EXT = {".mp4", ".mkv", ".mov"}
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "4096"))
PORT = int(os.environ.get("PORT", "5000"))
HOST = os.environ.get("HOST", "0.0.0.0")

RESOLUTIONS = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
}
DEFAULT_SETTINGS = {
    "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
    "stream_key": "",
    "title": "TR Live 24/7",
    "description": "",
    "category": "Entertainment",
    "privacy": "public",
    "resolution": "720p",
    "fps": 30,
    "video_bitrate_kbps": 2500,
    "audio_bitrate_kbps": 128,
    "duration_hours": 24,
}

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# ---------- logs (key-safe) ----------
LOGS = deque(maxlen=500)
_log_lock = threading.Lock()

def _redact(text: str) -> str:
    try:
        key = load_settings().get("stream_key", "")
        if key and len(key) >= 4 and key in str(text):
            return str(text).replace(key, "****")
    except Exception:
        pass
    return str(text)

def add_log(level: str, msg: str):
    msg = _redact(msg)
    entry = {"time": datetime.now(timezone.utc).isoformat(), "level": level, "message": msg}
    with _log_lock:
        LOGS.append(entry)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{entry['time']} [{level}] {msg}\n")
    except Exception:
        pass

# ---------- settings ----------
def load_settings():
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**DEFAULT_SETTINGS, **data}
            return merged
        except Exception as e:
            add_log("ERROR", f"Failed to read settings: {e}")
    return dict(DEFAULT_SETTINGS)

def save_settings(data: dict):
    # Only allow known keys
    clean = {k: data.get(k, DEFAULT_SETTINGS[k]) for k in DEFAULT_SETTINGS}
    clean["fps"] = int(clean["fps"])
    clean["video_bitrate_kbps"] = int(clean["video_bitrate_kbps"])
    clean["audio_bitrate_kbps"] = int(clean["audio_bitrate_kbps"])
    clean["duration_hours"] = float(clean["duration_hours"])
    if clean["resolution"] not in RESOLUTIONS:
        clean["resolution"] = "720p"
    SETTINGS_FILE.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(SETTINGS_FILE, 0o600)
    except Exception:
        pass
    return clean

def masked_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]

def public_settings():
    s = load_settings()
    out = dict(s)
    out["stream_key"] = masked_key(s.get("stream_key", ""))
    out["has_stream_key"] = bool(s.get("stream_key"))
    return out

# ---------- state ----------
state = {
    "video_path": None,          # str path
    "video_name": None,
    "video_size": 0,
    "video_duration": 0.0,
    "video_width": 0,
    "video_height": 0,
    "live": False,
    "started_at": None,          # epoch
    "ends_at": None,
    "ffmpeg_pid": None,
    "last_error": "",
    "last_bitrate": "",
    "restart_count": 0,
    "ffmpeg_cmd_preview": "",
}
_state_lock = threading.Lock()
ffmpeg_proc = None
_stop_requested = threading.Event()
_monitor_thread = None

def ffprobe_info(path: Path):
    """Return duration, width, height via ffprobe, or zeros if unavailable."""
    info = {"duration": 0.0, "width": 0, "height": 0}
    if shutil.which("ffprobe") is None:
        return info
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout or "{}")
        for s in d.get("streams", []):
            if s.get("codec_type") == "video":
                info["width"] = int(s.get("width", 0))
                info["height"] = int(s.get("height", 0))
        fmt = d.get("format", {})
        if fmt.get("duration"):
            info["duration"] = float(fmt["duration"])
    except Exception as e:
        add_log("ERROR", f"ffprobe failed: {e}")
    return info

def build_ffmpeg_cmd(video: Path, settings: dict):
    w, h = RESOLUTIONS[settings["resolution"]]
    fps = int(settings["fps"])
    vbr = int(settings["video_bitrate_kbps"])
    abr = int(settings["audio_bitrate_kbps"])
    rtmp = settings["rtmp_url"].rstrip("/")
    dest = f"{rtmp}/{settings['stream_key']}"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "info",
        "-stream_loop", "-1", "-re", "-i", str(video),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "veryfast",
        "-b:v", f"{vbr}k", "-maxrate", f"{vbr}k", "-bufsize", f"{vbr*2}k",
        "-g", str(fps * 2), "-keyint_min", str(fps),
        "-c:a", "aac", "-b:a", f"{abr}k", "-ar", "44100", "-ac", "2",
        "-f", "flv", dest,
    ]
    return cmd, dest

def _ffmpeg_reader(proc):
    """Read ffmpeg stderr, keep last bitrate line, log errors (redacted)."""
    try:
        for line in iter(proc.stderr.readline, ""):
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            m = re.search(r"bitrate=\s*([0-9.]+kbits/s)", line)
            if m:
                with _state_lock:
                    state["last_bitrate"] = m.group(1)
            if "error" in line.lower() or "failed" in line.lower() or "Connection refused" in line or "Invalid" in line:
                add_log("ERROR", f"FFmpeg: {line[:500]}")
                with _state_lock:
                    state["last_error"] = line[:500]
    except Exception:
        pass

def _monitor_loop():
    """Restart FFmpeg if it exits unexpectedly while live and within duration."""
    global ffmpeg_proc
    while True:
        time.sleep(2)
        with _state_lock:
            live = state["live"]
            ends_at = state["ends_at"]
        if not live:
            return
        if ends_at and time.time() >= ends_at:
            add_log("INFO", "Configured duration reached — stopping stream.")
            stop_stream_internal(reason="duration reached")
            return
        proc = ffmpeg_proc
        if proc is not None and proc.poll() is not None:
            # exited
            if _stop_requested.is_set():
                return
            rc = proc.returncode
            add_log("WARN", f"FFmpeg exited (code {rc}) — reconnecting in 5s…")
            with _state_lock:
                state["restart_count"] += 1
                state["last_error"] = f"FFmpeg exited code {rc}, reconnecting…"
            time.sleep(5)
            with _state_lock:
                if not state["live"] or _stop_requested.is_set():
                    return
            ok, msg = _start_ffmpeg_process()
            if not ok:
                add_log("ERROR", f"Reconnect failed: {msg}")
                time.sleep(10)

def _start_ffmpeg_process():
    global ffmpeg_proc
    settings = load_settings()
    video = state.get("video_path")
    if not video or not Path(video).exists():
        return False, "No video selected. Upload a video first."
    if not settings.get("stream_key"):
        return False, "Stream key is missing. Save it in Stream Settings first."
    if shutil.which("ffmpeg") is None:
        return False, "FFmpeg is not installed on this server."
    cmd, _dest = build_ffmpeg_cmd(Path(video), settings)
    # Preview without the key
    preview = " ".join(cmd[:-1] + ["<RTMP_URL>/****"])
    with _state_lock:
        state["ffmpeg_cmd_preview"] = preview
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, bufsize=1)
        ffmpeg_proc = proc
        threading.Thread(target=_ffmpeg_reader, args=(proc,), daemon=True).start()
        with _state_lock:
            state["ffmpeg_pid"] = proc.pid
        # Give it 3s to fail fast (bad RTMP / bad key usually exits quickly)
        time.sleep(3)
        if proc.poll() is not None:
            return False, f"FFmpeg exited immediately (code {proc.returncode}). Check RTMP URL / stream key and see Logs."
        return True, "FFmpeg started"
    except Exception as e:
        return False, f"Failed to start FFmpeg: {e}"

def start_stream_internal():
    global _monitor_thread
    _stop_requested.clear()
    settings = load_settings()
    ok, msg = _start_ffmpeg_process()
    if not ok:
        return False, msg
    now = time.time()
    duration = float(settings.get("duration_hours", 24)) * 3600
    with _state_lock:
        state["live"] = True
        state["started_at"] = now
        state["ends_at"] = now + duration
        state["restart_count"] = 0
        state["last_error"] = ""
    add_log("INFO", f"Streaming started — {state['video_name']} | {settings['resolution']} {settings['fps']}fps | {settings['video_bitrate_kbps']} kbps | duration {settings['duration_hours']}h")
    add_log("INFO", "RTMP connection established (FFmpeg running). Watch YouTube Studio → Go Live to confirm.")
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    return True, "Live started"

def stop_stream_internal(reason="stopped by user"):
    global ffmpeg_proc
    _stop_requested.set()
    proc = ffmpeg_proc
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as e:
            add_log("ERROR", f"Error stopping FFmpeg: {e}")
    ffmpeg_proc = None
    with _state_lock:
        was_live = state["live"]
        state["live"] = False
        state["ffmpeg_pid"] = None
        state["started_at"] = None
        state["ends_at"] = None
    if was_live:
        add_log("INFO", f"Streaming stopped ({reason}). FFmpeg process terminated, resources released.")
    return True

# ---------- auth / CORS ----------
def require_auth():
    token = request.headers.get("X-Admin-Token", "")
    if not token or token != ADMIN_TOKEN:
        return False
    return True

@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Token"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

@app.before_request
def _auth_guard():
    if request.method == "OPTIONS":
        return ("", 204)
    if request.path.startswith("/api/") and request.path != "/api/health":
        if not require_auth():
            return jsonify({"ok": False, "error": "Unauthorized — missing or wrong X-Admin-Token"}), 401

# ---------- routes: pages ----------
@app.route("/")
def index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")

@app.route("/<path:path>")
def _static(path):
    p = FRONTEND_DIR / path
    if p.is_file():
        return send_from_directory(str(FRONTEND_DIR), path)
    return send_from_directory(str(FRONTEND_DIR), "index.html")

# ---------- API ----------
@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "TR YouTube 24H Live Studio",
                    "ffmpeg": shutil.which("ffmpeg") is not None,
                    "ffprobe": shutil.which("ffprobe") is not None})

@app.route("/api/login", methods=["POST"])
def login():
    return jsonify({"ok": True, "message": "Token valid"})

@app.route("/api/upload", methods=["POST"])
def upload():
    if "video" not in request.files:
        return jsonify({"ok": False, "error": "No video file in request (field name must be 'video')"}), 400
    f = request.files["video"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Empty filename"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"ok": False, "error": f"Unsupported format {ext}. Use MP4, MKV or MOV."}), 400
    if state.get("live"):
        return jsonify({"ok": False, "error": "Stop the live stream before replacing the video."}), 400
    safe = secure_filename(f.filename) or "video.mp4"
    dest = UPLOAD_DIR / f"{int(time.time())}_{safe}"
    f.save(str(dest))
    info = ffprobe_info(dest)
    with _state_lock:
        state["video_path"] = str(dest)
        state["video_name"] = safe
        state["video_size"] = dest.stat().st_size
        state["video_duration"] = info["duration"]
        state["video_width"] = info["width"]
        state["video_height"] = info["height"]
    add_log("INFO", f"Video uploaded: {safe} ({dest.stat().st_size/1024/1024:.1f} MB, {info['duration']:.1f}s, {info['width']}x{info['height']})")
    return jsonify({"ok": True, "video": {
        "name": safe, "size": state["video_size"],
        "duration": info["duration"], "width": info["width"], "height": info["height"],
        "path": dest.name}})

@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify({"ok": True, "settings": public_settings()})

@app.route("/api/settings", methods=["POST"])
def post_settings():
    data = request.get_json(force=True, silent=True) or {}
    current = load_settings()
    # If frontend sends masked key (****xxxx), keep the real one
    incoming_key = (data.get("stream_key") or "").strip()
    if not incoming_key or incoming_key.startswith("****"):
        data["stream_key"] = current.get("stream_key", "")
    merged = {**current, **data}
    # Validate RTMP
    if merged.get("rtmp_url") and not str(merged["rtmp_url"]).startswith("rtmp://"):
        return jsonify({"ok": False, "error": "RTMP URL must start with rtmp://"}), 400
    saved = save_settings(merged)
    add_log("INFO", "Stream settings saved (stream key stored server-side only, never logged).")
    return jsonify({"ok": True, "settings": public_settings()})

@app.route("/api/start", methods=["POST"])
def start():
    with _state_lock:
        if state["live"]:
            return jsonify({"ok": False, "error": "Already live. Stop first, or use Restart."}), 400
    ok, msg = start_stream_internal()
    if not ok:
        add_log("ERROR", f"Start failed: {msg}")
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "message": msg, "status": status_payload()})

@app.route("/api/stop", methods=["POST"])
def stop():
    stop_stream_internal(reason="stopped by user")
    return jsonify({"ok": True, "message": "Live stopped", "status": status_payload()})

@app.route("/api/restart", methods=["POST"])
def restart():
    stop_stream_internal(reason="restart requested")
    time.sleep(1)
    ok, msg = start_stream_internal()
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "message": "Live restarted", "status": status_payload()})

def status_payload():
    now = time.time()
    with _state_lock:
        s = dict(state)
    elapsed = (now - s["started_at"]) if s["live"] and s["started_at"] else 0
    remaining = (s["ends_at"] - now) if s["live"] and s["ends_at"] else 0
    return {
        "live": s["live"],
        "elapsed_seconds": max(0, int(elapsed)),
        "remaining_seconds": max(0, int(remaining)),
        "video_name": s["video_name"],
        "video_size": s["video_size"],
        "video_duration": s["video_duration"],
        "video_resolution": f"{s['video_width']}x{s['video_height']}" if s["video_width"] else "",
        "ffmpeg_pid": s["ffmpeg_pid"],
        "last_error": s["last_error"],
        "last_bitrate": s["last_bitrate"],
        "restart_count": s["restart_count"],
        "settings": public_settings(),
    }

@app.route("/api/status")
def status():
    return jsonify({"ok": True, "status": status_payload()})

@app.route("/api/logs")
def logs():
    with _log_lock:
        items = list(LOGS)
    return jsonify({"ok": True, "logs": items[-200:]})

@app.route("/api/server-stats")
def server_stats():
    cpu = None; mem = None; disk = None
    ffmpeg_cpu = None; ffmpeg_mem_mb = None
    if psutil:
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            m = psutil.virtual_memory()
            mem = {"percent": m.percent, "used_mb": round(m.used/1024/1024), "total_mb": round(m.total/1024/1024)}
            d = psutil.disk_usage(str(BASE))
            disk = {"percent": d.percent, "free_gb": round(d.free/1024/1024/1024, 1)}
            pid = state.get("ffmpeg_pid")
            if pid:
                p = psutil.Process(pid)
                ffmpeg_cpu = p.cpu_percent(interval=0.1)
                ffmpeg_mem_mb = round(p.memory_info().rss/1024/1024, 1)
        except Exception as e:
            add_log("ERROR", f"server-stats failed: {e}")
    return jsonify({"ok": True, "cpu_percent": cpu, "memory": mem, "disk": disk,
                    "ffmpeg_cpu_percent": ffmpeg_cpu, "ffmpeg_mem_mb": ffmpeg_mem_mb})

if __name__ == "__main__":
    add_log("INFO", f"TR Live backend starting on {HOST}:{PORT} — ffmpeg: {shutil.which('ffmpeg') is not None}")
    print(f"[TR LIVE] Dashboard: http://{HOST}:{PORT}  (use your VPS IP in the browser)")
    print("[TR LIVE] Blogger page: set Backend URL to http://YOUR_VPS_IP:5000 and X-Admin-Token to your TR_LIVE_ADMIN_TOKEN")
    app.run(host=HOST, port=PORT, threaded=True)
