# Sohoj Upay — sob kichu Blogger-e rakha jabe ki?

## Short answer: Na, sob kichu Blogger-e rakha jabe na

Eta amar ichha na, eta Blogger-er limit:

- Blogger sudhu static website dekhay — HTML/CSS/JS. Ekhane **Python chole na, FFmpeg chole na**.
- 24 ghonta stream korar jonno ekta program-ke background-e saradin cholte hoy. Blogger-e background program cholena.
- Browser tab bondho korle, PC bondho korle, net gele — stream bondho hoye jabe.
- Browser JavaScript diye YouTube RTMP-e 24h loop stream kora jay na — eta server-er kaj.

Tai: **Blogger = Dashboard (button + status)**, ar **Server = asol streaming**. Dashboard-ta Blogger-e thakbe, streaming-ta server-e cholbe. Eta bodlano jabe na — je kono AI ei ek-i kotha bolbe, karon etai sotti.

Tobe server-ta chalano ekhon onek sohoj kore diyechi — terminal command na likheo hobe.

---

## 3 ta sohoj upay — konta apnar jonno valo?

| Upay | Taka | PC on rakhte hobe? | Terminal command? | 24h cholbe? |
|---|---|---|---|---|
| **1. Render 1-click** | Free-te test, 24h-er jonno ~$7/month | Na | Na — sudhu click | Paid plan-e haan |
| **2. OBS diye PC theke** | Free | Haan, PC on rakhte hobe | Na — sudhu software | PC on thakle haan |
| **3. Windows start.bat** | Free | Haan | Na — double-click | PC on thakle haan |

---

## Upay 1 — Sobcheye sohoj, kono command nai (Render)

Ei folder-e ekhon `Dockerfile` + `render.yaml` ache, tai Render nijei sob install kore dibe.

1. GitHub-e free account khulen, ei folder-ta upload koren (zip upload / drag-drop).
2. `render.com` e jan → **New + → Web Service** → GitHub repo-ta select koren.
3. Render `render.yaml` dekhe nijei build korbe. `TR_LIVE_ADMIN_TOKEN` se nijei baniye dibe.
4. Deploy sesh hole ekta URL paben, jemon: `https://tr-youtube-live-studio.onrender.com`
5. Blogger page-e **Backend URL** hisebe oi URL-ta bosan, **Admin Token** hisebe Render-er Environment-e je token-ta dekhabe seta bosan. Bas.

**Sotti kotha (age theke janiye dichhi):**
- Render Free plan 15 min kono kaj na thakle ghumiye jay (sleep). Tai 24h live-er jonno Free plan valo na.
- 24h thik moto cholte **Starter plan (~$7/month)** lagbe.
- Free/paid — restart hole `uploads/`-er video muche jay, tai restart-er por video abar upload korte hobe. Eta Render/Railway sobar-i niyom, karon tader disk temporary.

Railway-teo ek-i vabe hobe — `railway.json` + `Dockerfile` ache, Railway-te repo connect korlei deploy hobe.

---

## Upay 2 — Kono taka, kono code lagbe na (OBS, PC theke)

Jodi apnar PC saradin on rakhte paren, eta sobcheye sohoj:

1. `obsproject.com` theke OBS Studio install koren (free).
2. OBS-e **+ → Media Source** → apnar video select koren → **Loop** tick den.
3. **Settings → Stream** → Service: YouTube, Stream Key bosan (YouTube Studio → Go Live theke copy koren).
4. **Settings → Output** → Video Bitrate 2500, Audio 128.
5. **Start Streaming** chapun. Video sesh hole nijei loop hobe.

PC bondho / ghumale live bondho hobe. Kintu kono VPS, kono command, kono taka lagbe na.

---

## Upay 3 — Windows PC-ke server banan (start.bat)

1. Python + FFmpeg install koren (ekbar-i).
2. Ei folder-e `start.bat` double-click koren.
3. Browser-e `http://localhost:5000` khulen — dashboard cholbe.
4. Blogger page-er Backend URL-e apnar PC-er IP bosate hobe — kintu PC-er baire theke (onno net theke) eta khulbe na, jodi na port-forward / tunnel koren.

Tai PC diye test korar jonno eta valo, kintu 24/7-er jonno VPS / Render paid-i valo.

---

## Amar poramorsho

- **Test korte chan, taka khoroch korte chan na:** OBS diye PC theke (Upay 2).
- **PC bondho rakhte chan, Blogger theke control korte chan:** Render Starter (~$7/month) — kono command nai, sudhu click (Upay 1).
- **Sobcheye sosta 24/7:** choto VPS (~$4-5/month) — kintu okhane `start.sh` command-ta ekbar likhte hobe, README-te lekha ache.

Blogger-e sudhu dashboard thakbe — eta-i asol design. Server chara 24h live somvob na, eta keu baniye dite parbe na.
