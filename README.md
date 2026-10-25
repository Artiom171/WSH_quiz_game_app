# WSH Quiz Game App

A multiplayer quiz game web app built with FastAPI and plain HTML. The host configures and runs the game tour by tour, players join from their phones by scanning a QR code and answer in real time, and a live leaderboard tracks the scores.

## Features

### Game editor (`config.html`)
- Two-step editor: **1. Tour structure** (game name, number of tours, tour type and question count, color theme) and **2. Questions**
- Step 1 has **Save** (stays on the page) and **Save and continue** (saves and opens the questions)
- Tour types: **ordinary** (one question at a time) and **themed** (players answer all questions of the tour at once)
- Question types: text, photo, uploaded video, uploaded audio, YouTube link
- Every media question can have its own **question text**, shown large under the media
- **Photo questions take several images**, each with an optional caption
- **Answers** have the answer text, an optional description, and several images with optional captions
- **Rebus** checkbox per question: question and answer images are shown as one seamless strip, with no gaps
- Per-question timer, background music (YouTube URL), playback speed and mute for video/audio
- Uploaded video audio can be stripped server-side via FFmpeg
- **Preview** of any question and its answer exactly as the host screen shows them
- **Rehearsal**: plays a whole tour on the host screen up to the chosen question, with unsaved edits included
- Saved configurations (`saved_configs.json`); "Save as new" makes a copy

### Color themes
- 10 ready-made themes: Лайм (default), Океан, Закат, Неон, Золото, Светлая, Киберпанк, Голодные игры, Матрица, Half-Life
- Live mini preview of the question and answer screens
- Any of the 6 base colors (background, accent, answer, text, glow 1, glow 2) can be replaced with your own: click a color card to select it, then pick a color or type a hex code (`#e5c07b`, `e5c07b`, `#fc0`). Unselected cards keep the theme's color
- Readability warnings when text, accent or answer color blend into the background, with a one-click fix for the text
- The theme applies to the host screen, the editor preview and rehearsal, and **the players' phones**

### Host screen (`host_screen.html`)
- Waiting screen with a **QR code** players scan to join
- Images are laid out automatically: the layout picks the split into rows that makes them as large as possible on the current screen, keeping their order and the question text right under them
- Large tour/question number and timer, readable from the back of a hall
- YouTube questions show a cover; press **Space** or click to reveal and start playback
- Keyboard: **Space** starts the timer, **→** advances the game (begin tour → show answer → next question)
- Fullscreen button, end-game button

### Players and results
- Players register on their own devices, wait in a lobby, and submit answers in real time; answers lock automatically when the timer runs out
- Sessions are tied to a game: a new game always forces re-registration
- Host reviews answers and marks them correct/incorrect in `answers.html`
- Live leaderboard on `final_result.html`

### Other
- Host pages require login (see [Host login](#host-login))
- Request logging to timestamped files in `logs/`, with automatic cleanup of files older than 6 hours
- Responsive layout for phones

## Project structure

```
app/
  main.py               — FastAPI application, all API routes
  db/                   — database connection and setup
  models/               — SQLAlchemy models (User, Answer)
frontend/
  index.html            — player lobby / registration
  questions.html        — player answer submission
  config_login.html     — host login
  config.html           — game editor, preview, rehearsal and tour control
  host_screen.html      — audience screen (question, answer, timer)
  answers.html          — host answer review
  final_result.html     — live leaderboard
  demo_final_result.html — leaderboard demo/preview
  image_grid.js         — image layout for question/answer screens (rows, rebus strip)
  theme.js              — color themes: presets and applying them as CSS variables
  quit_btn.js           — end-game button for host pages
  error_page.html       — 404 error page
  server_error_page.html — 500 error page
uploads/                — uploaded media files (ignored by git)
logs/                   — rotating request log files (ignored by git)
saved_configs.json      — saved game configurations (ignored by git)
game_state.json         — current game state (ignored by git)
auth_config.json        — host password (ignored by git)
smtp_config.json        — mail settings (ignored by git)
database.db             — SQLite database (ignored by git)
server_.bat             — Windows startup script
requirements.txt
```

## Requirements

- Python 3.10+
- FFmpeg on PATH — required only for the **Remove audio** button on uploaded videos

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

While developing, add `--reload` so changes to `app/main.py` are picked up without a manual restart. Without it, the server must be restarted after changing the data models, or new fields (for example images or theme settings) are silently dropped when a configuration is saved.

> **Every server start resets the game:** all players, answers and the game state are cleared. Saved configurations and uploaded files are kept.

## Host login

`config.html`, `host_screen.html`, `answers.html` and `final_result.html` open only after logging in on `config_login.html`. The password is stored in `auth_config.json`, which is not tracked by git.

## Host pages

| URL | Purpose |
|-----|---------|
| `http://<host>:8000/config.html` | Edit games, preview/rehearse, start and control the game |
| `http://<host>:8000/host_screen.html` | Audience screen for the projector/TV |
| `http://<host>:8000/answers.html` | Review submitted answers and mark correct/incorrect |
| `http://<host>:8000/final_result.html` | Live leaderboard |

## Player pages

| URL | Purpose |
|-----|---------|
| `http://<host>:8000/` | Register and wait for the game to start (the QR code on the host screen leads here) |
| `http://<host>:8000/questions.html` | Submit answers (players are redirected here automatically) |

## How to run a game

1. **Host** logs in, opens `config.html`, and creates or opens a game: on step 1 sets the name, tours and color theme; on step 2 fills in the questions. Use **Preview** and **Rehearsal** to check how they look.
2. **Host** clicks **Start game** and opens `host_screen.html` on the projector.
3. **Players** scan the QR code on the host screen (or open `http://<host_ip>:8000/`), enter a name, and wait.
4. **Host** activates Tour 1. Press **→** to show questions and answers, **Space** to start the timer. Player phones follow automatically.
5. The host reviews answers in `answers.html`; scores update live on `final_result.html`.
6. Repeat for the remaining tours; the end-game button finishes the game.

## Question types

| Type | How it works |
|------|-------------|
| **Text** | Question text only |
| **Photo** | One or more images (upload several files at once or add by URL), each with an optional caption, plus optional question text. With **Rebus** on, the images are joined into one strip |
| **Video** | Uploaded file or URL; playback speed, mute, and **Remove audio** (requires FFmpeg). For big files, copy them to `uploads/` and enter `/uploads/<file>` as the URL |
| **Audio** | Uploaded file or URL; playback speed and mute |
| **YouTube** | YouTube link; the question shows a cover — press Space or click to start. Can be muted per question |

Any question can also have a timer and background music, and its answer can have a description and images with captions.

## Notes

- The player's session is stored in browser `localStorage` and tied to a `game_id`, so returning devices re-register for a new game. Phones also remember the game's color theme so pages open in it right away.
- The **Reset database** button on the leaderboard page clears all users, answers and the game state.
- All HTTP requests are logged to `logs/` with timestamps, User-Agent and request bodies for debugging.
- `game_state.json` is written on every game state change.
