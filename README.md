---
title: Social Media Manager
emoji: 📱
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Social Media Manager

Open-source, zero-budget tool to manage **your own personal account** across
YouTube, Instagram, Facebook, TikTok, and Twitter/X: it detects what's
trending per platform, generates a content idea that ties the trend to your
own niche, produces the text/voiceover/image/video for it using free tools,
and publishes it on schedule. It is a **content manager**, not a
full "set and forget" automation bot — you review ideas before they go out.

## Pipeline

```
Trend detection  ->  Idea generation  ->  Content generation  ->  Scheduling queue  ->  Publishing layer  ->  Platforms
```

Every stage is its own Python module, so you can run and test them one at a
time (e.g. just trend detection + idea generation, reading the output as
plain text, before touching audio/image/video at all).

## Stack (all free)

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| Scheduler | APScheduler (in-process, no Redis needed) |
| Database | SQLite |
| Trend detection | pytrends (Google Trends) + YouTube Data API `mostPopular` |
| Idea generation | Gemini free tier, or a fully local model via Ollama |
| Text-to-speech | edge-tts (free, strong Arabic support) |
| Image generation | Pollinations.ai (swap for local Stable Diffusion later) |
| Video assembly | FFmpeg / moviepy |
| Publishing | YouTube Data API, Meta Graph API, TikTok Content Posting API, Twitter/X API |

## Project layout

```
app/
  config.py          settings loaded from .env
  database.py         SQLAlchemy engine/session
  models.py            Niche, PlatformAccount, TrendSignal, ContentIdea, ContentPiece, ScheduledPost, PostResult
  schemas.py            Pydantic request/response models
  scheduler.py           background job dispatching due posts every minute
  trends/                 pluggable trend sources + aggregator
  ideation/                LLM client + idea generator
  content/                  TTS, image, video pipeline
  publishing/                 one class per platform behind a common interface
  api/                          FastAPI routers (niches, accounts, trends, content, schedule, stats)
  timeutil.py / media_utils.py   timezone conversion, media file -> URL mapping
  main.py                        FastAPI app entrypoint (also serves /media and /dashboard)
dashboard/             zero-build Arabic (RTL) web UI: plain HTML/CSS/JS, served at /dashboard
tests/                 pytest suite (DB models, idea parsing, publisher contracts, API, time/media helpers)
scripts/init_db.py    one-off table creation without starting the server
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in whichever keys you have — every integration is optional and the
# app boots fine with blanks; a given feature just stays unavailable until
# its keys are set.

PYTHONPATH=. python scripts/init_db.py   # creates ./data/app.db
uvicorn app.main:app --reload            # dashboard at http://localhost:8000, API docs at /docs
```

Open **http://localhost:8000** — the dashboard walks the whole flow:
setup (niche + accounts) → trends → idea (review/edit) → generate media → schedule → monitor/retry.

Run the tests any time with `pytest` from the project root.

## Getting each platform working for your own personal account

- **YouTube**: create a Google Cloud project, enable the YouTube Data API v3,
  create an OAuth client (Desktop app type), download the client secret JSON
  to `./secrets/youtube_client_secret.json`. First publish opens a browser
  for one-time consent; the token is cached afterwards. Free quota is
  10,000 units/day (~6 uploads).
- **Instagram/Facebook**: your IG account needs to be a Business/Creator
  account linked to a Facebook Page. Create a Meta app, add yourself as a
  tester — for a personal account this is enough, **no App Review needed**.
  Graph API needs a **public URL** for the video (it can't accept a raw file
  upload), so set `MEDIA_PUBLIC_BASE_URL` to wherever you serve `./media`
  (your own domain, or a tunnel like ngrok/Cloudflare Tunnel while developing).
- **TikTok**: register at developers.tiktok.com, create an app with Content
  Posting API scope. Until your app passes TikTok's audit, posts can only
  use `privacy_level="SELF_ONLY"` (private/draft) — this is TikTok's
  documented limitation, not a bug here.
- **Twitter/X**: create a developer app (Essential/free tier), generate API
  key/secret + access token/secret with read+write permission.

## Typical flow through the API

```bash
# 1. Describe your niche
curl -X POST localhost:8000/niches -H 'Content-Type: application/json' -d '{
  "name": "Home fitness", "description": "Quick home workouts, no equipment",
  "target_audience": "busy professionals", "tone_of_voice": "energetic, friendly",
  "language": "ar"
}'

# 2. Pull fresh trends
curl -X POST localhost:8000/trends/collect

# 3. Generate an idea tying a trend to your niche
curl -X POST localhost:8000/content/ideas -H 'Content-Type: application/json' -d '{"niche_id": 1}'

# 4. Generate the audio/image/video for that idea
curl -X POST localhost:8000/content/pieces -H 'Content-Type: application/json' -d '{"idea_id": 1}'

# 5. Connect a platform account, then schedule the piece
curl -X POST localhost:8000/accounts -H 'Content-Type: application/json' -d '{"platform": "youtube", "display_name": "My channel"}'
curl -X POST localhost:8000/schedule -H 'Content-Type: application/json' -d '{
  "content_piece_id": 1, "account_id": 1, "scheduled_for": "2026-11-26T18:00:00"
}'
```

The background scheduler checks every minute for due posts and publishes
them automatically, recording the outcome in `PostResult`
(`GET /schedule/{id}/result`).

**Times:** `scheduled_for` without a timezone is read as local time in
`TIMEZONE` (default `Africa/Cairo`); with an offset/`Z` it is converted exactly.
Everything is stored as UTC and returned with a `Z` suffix. Scheduling in the
past is rejected. Failed posts can be re-queued with `POST /schedule/{id}/retry`.
If the app is stopped mid-publish, that post is marked failed on next start
(not re-sent automatically, to avoid a duplicate post) — check the platform,
then retry from the dashboard if needed.

Other endpoints added for the dashboard: `PATCH/DELETE /content/ideas/{id}`
(review step), `GET /stats`, and `GET /schedule?status=queued`.

## Roadmap / known limitations

- **Gemini model names retire.** The default is `gemini-3.5-flash-lite`
  (recommended for new projects on Google's deprecations page); verify it and
  its free-tier quota in your account, or set `LLM_PROVIDER=ollama`. The
  `google-generativeai` SDK is also being superseded by `google-genai`.
- **Arabic video captions** need a font with Arabic glyphs (`CAPTION_FONT`),
  ImageMagick installed, and `arabic-reshaper` + `python-bidi` (in
  requirements) so letters join and read right-to-left.
- Google Trends via `pytrends` is unofficial and sometimes rate-limited or
  broken by Google changes; failures are logged and the other source still runs.
- The default trend for idea generation is the strongest one in the latest
  collection, ranked within each source (not just the most recent row).

- TikTok posts are private-only until your app is TikTok-audited.
- Instagram/Facebook publishing needs a public URL for media — not an issue
  once you deploy somewhere with a real domain, but requires a tunnel while
  developing locally.
- The dashboard is plain JS (no build step, nothing to install). Porting it
  to React is straightforward if you want components/state management; the API
  is unchanged either way.
- **Login:** set `APP_PASSWORD` (and a random `APP_SECRET_KEY`) in `.env` to
  require a password for the API and dashboard (7-day signed session cookie;
  changing the password logs everyone out). `/media` stays public on purpose —
  Instagram/Facebook must fetch videos from it — so keep generated filenames
  private. Serve over HTTPS if exposed. Left empty = no login (localhost only).
- Trend detection currently uses Google Trends + YouTube's official charts
  only, by design (no scraping of TikTok/Instagram directly, to avoid
  account-ban risk) — can be extended carefully later.
