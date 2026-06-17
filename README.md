# WSH Quiz Game App

A multiplayer quiz game web app built with FastAPI and plain HTML. The host configures and runs the game tour by tour; players register on their own devices, submit answers in real time, and a live leaderboard tracks scores.

## Features

- Host configures tours and questions (including media and timers) via `config.html`
- Questions support three media types: text only, uploaded video file, or YouTube URL
- Per-question optional timer (overrides silence — no tour-level timer)
- YouTube questions show a thumbnail placeholder; press **Space** or click to reveal and start playback
- YouTube audio can be muted per question (toggle in the editor)
- Uploaded video audio can be stripped server-side via FFmpeg
- Host screen (`host_screen.html`) displays the current question to the audience
- Players register on their own devices, wait in a lobby, and submit answers in real time
- Host reviews submitted answers and marks them correct/incorrect via `answers.html`
- Live leaderboard auto-refreshes on `final_result.html`
- Saved game configurations (save/load from `saved_configs.json`)
- Game state persists to `game_state.json` — server restarts no longer reset the game
- Sessions are isolated per game — stale sessions from a previous game are invalidated automatically
- Request logging to timestamped files in `logs/`, with automatic cleanup of files older than 6 hours
- Responsive layout for mobile devices

## Project structure

```
app/
  main.py          — FastAPI application, all API routes
  db/              — database connection and setup
  models/          — SQLAlchemy models (User, Answer)
frontend/
  index.html            — player lobby / registration
  questions.html        — player answer submission
  config.html           — host game configuration and tour control
  host_screen.html      — host/audience question display screen
  answers.html          — host answer review
  final_result.html     — live leaderboard
  demo_final_result.html — leaderboard demo/preview
  error_page.html       — 404 error page
  server_error_page.html — 500 error page
uploads/           — uploaded media files (ignored by git)
logs/              — rotating request log files (ignored by git)
game_state.json    — persisted game state (ignored by git)
saved_configs.json — saved game configurations
database.db        — SQLite database (ignored by git)
server_.bat        — Windows startup script
requirements.txt
```

## Requirements

- Python 3.10+
- FFmpeg on PATH — required only if you use the **Remove audio** button on uploaded video files

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Run the app

**Windows (recommended):** double-click `server_.bat`. It checks Python, installs/updates dependencies, detects your local IP, and starts the server. When the server stops, press **R** to restart or **Q** to quit.

**Manual:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Host pages

| URL | Purpose |
|-----|---------|
| `http://<host>:8000/config.html` | Configure tours and questions, start/advance the game |
| `http://<host>:8000/host_screen.html` | Display the current question to the audience |
| `http://<host>:8000/answers.html` | Review submitted answers and mark correct/incorrect |
| `http://<host>:8000/final_result.html` | Live leaderboard (auto-refreshes) |

## Player pages

| URL | Purpose |
|-----|---------|
| `http://<host>:8000/` | Register and wait for the game to start |
| `http://<host>:8000/questions.html` | Submit answers (redirected here automatically) |

## How to run a game

1. **Host** opens `config.html`, creates or loads a configuration: sets tours, adds questions (with optional media and per-question timers), and clicks **Start game**.
2. **Players** open `http://<host_ip>:8000/` on their devices, enter a name, and wait in the lobby.
3. **Host** opens `host_screen.html` on the projector/screen and activates Tour 1 from `config.html`. The host screen and all player screens update automatically.
4. Players submit answers; the host opens `answers.html` to review and mark them correct or incorrect.
5. Repeat steps 3–4 for each subsequent tour.
6. Scores update live on `final_result.html`.

## Question media types

| Type | How it works |
|------|-------------|
| **Text** | Question text only, no media |
| **Uploaded video** | Upload a file via the editor; optionally strip audio with the **Remove audio** button (requires FFmpeg) |
| **YouTube URL** | Paste a YouTube link; the question shows a thumbnail placeholder — press Space or click to start playback. Toggle **Remove audio** in the editor to mute playback for that question |

## Notes

- Browser `localStorage` stores the player's session. Sessions are tied to a `game_id` so a new game always forces re-registration, even on returning devices.
- The **Reset database** button on the leaderboard page clears all users, answers, and game state.
- All HTTP requests are logged to `logs/` with timestamps, User-Agent, and request bodies for debugging.
- `game_state.json` is written on every game state change; if the server restarts mid-game, the state is restored automatically.
