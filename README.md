# TR YouTube 24H Live Studio

Blogger dashboard + Python + FFmpeg backend that loops **your** video to YouTube Live for 24 hours.

**Architecture — read this first:**
- **Blogger = Dashboard only.** Blogger cannot run FFmpeg or stream RTMP. The Blogger page (`blogger-page.html`) is only buttons + status. It talks to your backend over HTTP.
- **VPS / Windows PC = Streaming server.** `backend.py` runs FFmpeg with `-stream_loop -1`, auto-reconnects on drop, and auto-stops after the configured duration (default 24h).
- Your PC can be off — if the backend runs on a VPS, the live keeps going.

## Files

| File | What it is |
|---|---|
| `backend.py` | Flask backend — upload, settings, start/stop/restart, status, logs, server stats |
| `requirements.txt` | Flask, psutil, python-dotenv |
| `.env.example` | Copy to `.env` — set `TR_LIVE_ADMIN_TOKEN` |
| `frontend/index.html`, `style.css`, `script.js` | Full standalone dashboard (served by Flask at `http://IP:5000`) |
| `blogger-page.html` | Single-file Blogger page — paste whole file into a Blogger Page (HTML view) |
| `start.sh` / `start.bat` | One-command start for Linux/VPS and Windows |
| `uploads/` | Uploaded videos land here (server-side, not browser storage) |
| `data/settings.json` | Stream settings + stream key — created on first save, chmod 600 |

## 1. VPS deployment (recommended for 24/7)

```bash
# Ubuntu / Debian VPS
sudo apt update && sudo apt install -y python3 python3-venv ffmpeg
git clone <your-repo>  # or upload this folder with scp / FileZilla
cd tr-youtube-live-studio
chmod +x start.sh
./start.sh
# First run creates .env — edit it:
nano .env   # set TR_LIVE_ADMIN_TOKEN to a long random token
./start.sh
```

Open `http://YOUR-VPS-IP:5000` — that is the full dashboard.
For HTTPS (recommended), put Nginx / Caddy in front, or use a Cloudflare Tunnel — the backend itself is HTTP on port 5000.

Keep it alive after you close SSH:
```bash
# option A — systemd (create /etc/systemd/system/tr-live.service):
[Unit]
Description=TR YouTube 24H Live Studio
After=network.target
[Service]
WorkingDirectory=/root/tr-youtube-live-studio
ExecStart=/root/tr-youtube-live-studio/.venv/bin/python backend.py
Restart=always
User=root
[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload && sudo systemctl enable --now tr-live
sudo systemctl status tr-live

# option B — quick: nohup .venv/bin/python backend.py &
```

Open firewall: `sudo ufw allow 5000/tcp` (or only your IP if you use a reverse proxy).

## 2. Windows local server (testing / PC stays on)

1. Install Python 3.11+ from python.org (tick **Add to PATH**) and FFmpeg — `winget install Gyan.FFmpeg` — then restart the terminal.
2. Double-click `start.bat`. First run creates `.env` — edit `TR_LIVE_ADMIN_TOKEN`, run again.
3. Open `http://localhost:5000`.
4. Note: if this PC sleeps / shuts down, the live stops. For true 24/7, use the VPS.

## 3. Blogger setup

1. Blogger → Pages → New Page → switch to **HTML view** → paste the **whole** `blogger-page.html` → Publish.
   (Or Theme → Add a Gadget → HTML/JavaScript — same paste.)
2. On the published page, set **Backend URL** to `http://YOUR-VPS-IP:5000` (or your https domain) and **Admin Token** to the token in the server `.env`. Click **Save & Connect**.
3. The page polls the backend every 5s. If it says `BACKEND OFFLINE`, the URL/token/firewall is wrong — the page never fakes LIVE.

## 4. Go live — step by step

1. YouTube Studio → **Go Live** → copy **Stream URL** (`rtmp://a.rtmp.youtube.com/live2`) and **Stream Key**.
   > Never paste the stream key into Blogger comments, AI chats, or screenshots. Paste it only in the dashboard's Stream Settings form — it goes to YOUR backend only.
2. Dashboard → **Video Upload** → upload your MP4/MKV/MOV. Wait for the 100% + metadata (duration / resolution).
3. Dashboard → **Stream Settings** → RTMP URL + Stream Key + title + 720p / 30fps / 2500 kbps + 24h → **Save Settings**.
4. Dashboard → **START LIVE**. Watch the Logs: `Streaming started` → `RTMP connection established`.
5. Confirm in YouTube Studio → Go Live — the preview should appear within 30–60s. Set the title / thumbnail / privacy there if needed.
6. **STOP LIVE** ends FFmpeg cleanly. **RESTART LIVE** stops + starts it again. If the RTMP drops, the backend retries after 5s and logs `reconnecting`.

## 5. API documentation

Base: `http://YOUR-SERVER:5000` — all `/api/*` except `/api/health` need header `X-Admin-Token: <token>`.

| Method & path | Body / response |
|---|---|
| `GET /api/health` | No auth. `{ok, service, ffmpeg: true/false, ffprobe}` |
| `POST /api/login` | `{}` → `{ok:true}` if token is valid |
| `POST /api/upload` | `multipart/form-data`, field `video` (MP4/MKV/MOV). Returns `{ok, video:{name,size,duration,width,height}}`. Refuses while live. |
| `GET /api/settings` | Returns settings with `stream_key: "****abcd"` (masked) + `has_stream_key` |
| `POST /api/settings` | JSON: `rtmp_url, stream_key, title, description, category, privacy, resolution (480p/720p/1080p), fps (24/25/30/60), video_bitrate_kbps (1500/2500/4500/6000), audio_bitrate_kbps (128/160/192), duration_hours`. Sending a masked/blank key keeps the saved key. |
| `POST /api/start` | Validates video + key + FFmpeg, starts loop. `{ok, status}` |
| `POST /api/stop` | Terminates FFmpeg, releases resources. |
| `POST /api/restart` | Stop + start. |
| `GET /api/status` | `{live, elapsed_seconds, remaining_seconds, video_name, video_size, video_duration, video_resolution, ffmpeg_pid, last_error, last_bitrate, restart_count, settings(masked)}` |
| `GET /api/logs` | Last 200 log lines — stream key is redacted before logging. |
| `GET /api/server-stats` | `{cpu_percent, memory:{percent,used_mb,total_mb}, disk, ffmpeg_cpu_percent, ffmpeg_mem_mb}` |

FFmpeg command (built by the backend, key never logged):
```
ffmpeg -stream_loop -1 -re -i <video> -vf scale=1280:720:… -r 30 \
  -c:v libx264 -preset veryfast -b:v 2500k -maxrate 2500k -bufsize 5000k \
  -g 60 -c:a aac -b:a 128k -ar 44100 -f flv rtmp://a.rtmp.youtube.com/live2/****
```

## 6. Security

- Stream key: stored only in `data/settings.json` on the server (600), masked in every API response, redacted from logs, never in Blogger HTML.
- Admin token: required on every API call. Change it in `.env` and restart if it leaks.
- Uploads: extension allow-list (mp4/mkv/mov), secure filenames, size cap `MAX_UPLOAD_MB` (default 4096 MB). No shell is built from filenames — FFmpeg args are a list, not a shell string.
- Use HTTPS in production. Do not expose port 5000 to the whole internet without a token + HTTPS.
- Only broadcast videos you own or have permission to broadcast, and follow YouTube's Live Streaming policies. Looped / repetitive content can be limited by YouTube — check YouTube Studio for any warning on your stream.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `BACKEND OFFLINE` | Backend not running, wrong IP/port, firewall closed, or wrong token. `curl http://IP:5000/api/health` on the server. |
| `FFmpeg exited immediately` | Wrong RTMP URL / expired stream key (YouTube keys can change — copy a fresh one), or video file corrupt. Check Logs. |
| `No video selected` | Upload first — the backend streams the file on disk, not the browser preview. |
| `Not enough / 401 Unauthorized` | Token in the dashboard ≠ `TR_LIVE_ADMIN_TOKEN` in `.env`. They must match exactly. |
| Live shows in Studio but no picture | Wait 30–60s; check bitrate in Monitor (should be ~2500 kbps). If 0, FFmpeg is failing — see Logs. |
| VPS disk full | Uploads stay in `uploads/`. Delete old videos when you replace them. |

## Test (this VM)

```bash
python3 -m py_compile backend.py
pip install -r requirements.txt
TR_LIVE_ADMIN_TOKEN=test-token python3 backend.py
# in another terminal:
curl http://localhost:5000/api/health
curl -H "X-Admin-Token: test-token" http://localhost:5000/api/status
```
