# Deploying the BSA Member Chat kiosk

The app is split across two services:

| Service   | What it runs                                    | Hosts                               |
| --------- | ----------------------------------------------- | ----------------------------------- |
| Frontend  | Vite + React kiosk (Woodhurst UI)               | **Vercel** (`bsa-member-chat`)      |
| Backend   | FastAPI + SQLite + LanceDB + OpenAI             | **Railway** (or similar container host) |

## 1. Backend — Railway (one-time setup)

The repo ships a `Dockerfile` that bakes the SQLite and LanceDB assets into
the image, so the backend runs stateless on Railway — no attached volume
needed.

```bash
# Install the Railway CLI once
brew install railwayapp/railway/railway

# From the repo root:
railway login
railway init          # create a new project, call it `bsa-backend`
railway link          # if not prompted
railway up            # builds the Dockerfile and deploys

# Set env vars (one-time)
railway variables set OPENAI_API_KEY=sk-proj-...
railway variables set OPENAI_MODEL=gpt-4o-mini
# Optional — leave blank to skip the related source:
railway variables set REDDIT_CLIENT_ID=
railway variables set REDDIT_CLIENT_SECRET=
railway variables set SERPAPI_KEY=
```

After the first deploy, Railway prints a public URL like
`https://bsa-backend-production.up.railway.app`. Note it — the frontend needs
it.

## 2. Frontend — Vercel

Vercel is already linked to `frontend/` (see `.vercel/project.json`). The
only thing the frontend needs in production is the backend URL.

**One-time: set the env var on Vercel**

```bash
cd frontend
# Set for production + preview + dev (Vercel prompts for each)
vercel env add VITE_API_BASE
# When prompted, paste the Railway URL (no trailing slash):
# https://bsa-backend-production.up.railway.app
```

**Deploy**

```bash
cd frontend
npx vercel --prod
```

That's it. The frontend will call `${VITE_API_BASE}/chat/stream` etc. rather
than the local `/api/*` proxy.

## 3. Running locally (day-to-day)

```bash
# Terminal 1 — backend (reads OPENAI_API_KEY from .env)
python -m uvicorn src.api.main:app --reload

# Terminal 2 — frontend (leaves VITE_API_BASE unset → uses the Vite proxy)
cd frontend && npm run dev
```

Open <http://localhost:5173>. The screensaver should cycle through real
review quotes (fetched from `/api/reviews/featured`), and
society → persona → chat should stream real OpenAI responses in character.

## 4. Re-deploying later

Changes to the **frontend** → `cd frontend && npx vercel --prod`.
Changes to the **backend** → `railway up`.
Neither requires a git push.

If you do push to `main`, Vercel will auto-rebuild the frontend from the
current `main` branch (which now includes the kiosk code in git, so that
works too).
