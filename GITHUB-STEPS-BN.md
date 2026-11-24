# GitHub Step by Step — kono command likhte hobe na, sudhu click

Ei guide-ta sudhu website click kore korar jonno. Terminal / git command lagbe na.

## Age ja lagbe

- Ekta Gmail / email (GitHub account-er jonno)
- Nicher ZIP-ta download kore PC-te Extract kora — `tr-youtube-24h-live-studio.zip`
- YouTube Studio theke Stream Key (pore lagbe, ekhon na)

---

## PART A — GitHub account + Repo banan (5 min)

**Step 1.** `github.com` e jan → upore dan dike **Sign up** chapun.
- Email, password, username din. Username jekono — jemon `trtanudas`.
- Email-e asa code-ta diye verify koren.

**Step 2.** Login howar por upore dan dike **+** icon → **New repository** chapun.
- Repository name: `tr-youtube-live-studio`
- Description: `TR YouTube 24H Live Studio`
- **Public** select koren (Free Render-er jonno sohoj).
- **Add a README file** — tick diben NA. Khali repo rakhben.
- Niche **Create repository** chapun.

Bas, repo toiri. Ekhon khali repo dekhabe — `Quick setup` lekha thakbe.

---

## PART B — File upload koren (10 min)

**Step 3.** Repo page-e **Add file** button → **Upload files** chapun.

**Step 4.** PC-te ZIP Extract kore `tr-youtube-live-studio` folder-ta khulen.
Vitorta ei file-gulo thakbe — eiguloi upload korben:

```
backend.py
requirements.txt
Dockerfile
render.yaml
railway.json
Procfile
.gitignore
.env.example
start.sh
start.bat
README.md
EASY-DEPLOY-BN.md
GITHUB-STEPS-BN.md   (ei file-ta)
blogger-page.html
frontend/index.html
frontend/style.css
frontend/script.js
```

**Step 5.** Root file-gulo (frontend folder chara baki sob) select kore GitHub-er upload box-e drag-drop koren.
- Ekbare 25 tar beshi file dile hobe na — tai 2 bare koren.
- Tarpor niche sobuj **Commit changes** button chapun.

**Step 6.** `frontend` folder-ta alada upload koren:
- Repo-te **frontend** folder-e click koren → **Add file → Upload files**.
- `index.html`, `style.css`, `script.js` — 3 ta file drag-drop koren → **Commit changes**.

**Step 7.** Check koren repo-te ei file-gulo ache kina:
`backend.py`, `Dockerfile`, `render.yaml`, `frontend/index.html`
- Thakle Part B sesh.

**Upload korben NA:**
- Video file (MP4) — GitHub 100MB-er boro file ney na
- `.env` file — ekhane token/key thake, kokhono GitHub-e diben na
- Stream Key — kothao paste korben na, sudhu dashboard-er Settings-e

---

## PART C — Render-e Deploy koren (10 min, kono command na)

**Step 8.** `render.com` e jan → **Get Started** → **GitHub** diye Sign up / Login koren.
- GitHub authorize chaybe — **Authorize render** chapun.

**Step 9.** Render Dashboard-e **New +** → **Web Service** chapun.
- Repo list theke `tr-youtube-live-studio` select koren. Na dekhale **Configure account** → repo-ta tick din.

**Step 10.** Ei setting-gulo check koren (Render `render.yaml` dekhe nijei bosabe):
- Name: `tr-youtube-live-studio`
- Environment: **Docker**
- Plan: **Starter** select koren (24h live-er jonno — Free plan 15 min por ghumiye jay)
- Baki sob ja ache tai thakbe.

**Step 11.** **Deploy Web Service** chapun.
- Build cholbe 3-5 min. Log-e `Live` lekha ashle bujhben hoye geche.
- Upor-e ekta URL paben, jemon: `https://tr-youtube-live-studio.onrender.com`
- **Ei URL-ta kothao likhe rakhen — etai apnar Backend URL.**

**Step 12.** Token-ta ber koren:
- Render-e service-ta khule bam dike **Environment** e jan.
- `TR_LIVE_ADMIN_TOKEN` er pashe je token-ta ache, **eye icon** chaple dekhabe — copy koren.
- **Ei token-ta kothao share korben na.**

---

## PART D — Blogger-e Dashboard bosan (5 min)

**Step 13.** Blogger Dashboard → **Pages → New Page** → upore **HTML view** (pencil icon) chapun.

**Step 14.** PC-te `blogger-page.html` file-ta Notepad-e khulen, sob copy koren, Blogger-er HTML box-e paste koren → **Publish** chapun.

**Step 15.** Publish howa page-ta khulen:
- **Backend URL** box-e Step 11-er URL-ta bosan: `https://tr-youtube-live-studio.onrender.com`
- **Admin Token** box-e Step 12-er token-ta bosan.
- **Save & Connect** chapun.
- Upor-e **OFFLINE** theke **Connected** dekhale bujhben connect hoyeche.

---

## PART E — Prothom Live test (10 min)

**Step 16.** YouTube Studio khulen → **Go Live** → **Stream URL** ar **Stream Key** copy koren.
- Stream URL: `rtmp://a.rtmp.youtube.com/live2`

**Step 17.** Blogger dashboard-e:
- **Video Upload** → apnar MP4 video upload koren → 100% howa porjonto wait koren.
- **Stream Settings** → RTMP URL + Stream Key + Title bosan → 720p / 30fps / 2500 kbps / 24h rekhe **Save Settings** chapun.

**Step 18.** **START LIVE** chapun.
- Log-e `Streaming started` + `RTMP connection established` dekhabe.
- YouTube Studio → Go Live-e 30-60 sec-er moddhe preview ashle bujhben Live cholche.

**Step 19.** **STOP LIVE** chaple live bondho hobe.

---

## Na hole ki korben

| Somossa | Ki korben |
|---|---|
| GitHub-e file upload hochhe na | File 25 tar beshi ekbare diben na, 2 bare koren |
| Render-e `Build failed` | Repo-te `Dockerfile` ar `backend.py` ache kina check koren |
| Blogger-e `BACKEND OFFLINE` | URL-er seshe `/` diben na, token-ta abar copy kore bosan |
| `401 Unauthorized` | Token vul — Render Environment theke abar copy koren |
| `No video selected` | Age video upload koren, tarpor START LIVE chapun |
| Live-e preview asche na | Stream Key notun kore YouTube Studio theke copy koren, Settings-e save koren |

**Mone rakhben:** Code GitHub-e, video dashboard upload-e, Stream Key sudhu dashboard-er Settings-e. Ei 3 ta alada jayga — ekta arektar jayga ney na.
