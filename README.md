# WSH Quiz Game App

A multiplayer quiz game web app built with FastAPI and plain HTML. The host configures and runs the game tour by tour; players register on their own devices, submit answers in real time, and a live leaderboard tracks scores.

## Features

- Host configures the game (number of tours, type, and question count per tour) via `config.html`
- Host activates tours one at a time; players' screens update automatically
- Players register with a name and wait in a lobby until the game starts
- Per-tour answer submission on players' devices via `questions.html`
- Host reviews submitted answers and marks them correct/incorrect via `answers.html`
- Live leaderboard auto-refreshes on `final_result.html`
- Player list visible on `users.html`
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
  index.html       — player lobby / registration
  questions.html   — player answer submission
  config.html      — host game configuration and tour control
  answers.html     — host answer review
  final_result.html — live leaderboard
  users.html       — registered player list
  error_page.html  — 404 error page
  server_error_page.html — 500 error page
logs/              — rotating request log files
database.db        — SQLite database
requirements.txt
```

## Requirements

- Python 3.10+

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the app

From the project root:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Host pages

| URL | Purpose |
|-----|---------|
| `http://<host>:8000/config.html` | Configure tours and start the game |
| `http://<host>:8000/answers.html` | Review answers and mark correct/incorrect |
| `http://<host>:8000/final_result.html` | Live leaderboard (auto-refreshes) |
| `http://<host>:8000/users.html` | View registered players |

## Player pages

| URL | Purpose |
|-----|---------|
| `http://<host>:8000/` | Register and wait for the game to start |
| `http://<host>:8000/questions.html` | Submit answers (redirected here automatically) |

## How to run a game

1. **Host** opens `config.html`, sets the number of tours, configures each tour (type and question count), and clicks **Start game**.
2. **Players** open `http://<host_ip>:8000/` on their devices, enter a name, and wait in the lobby.
3. **Host** activates Tour 1 from `config.html`. All player screens transition to the first question automatically.
4. Players submit answers; the host opens `answers.html` to review and mark them correct or incorrect.
5. Repeat step 3–4 for each subsequent tour.
6. Scores update live on `final_result.html`.

## Notes

- Browser `localStorage` stores the player's session. Sessions are tied to a `game_id` so a new game always forces re-registration, even on returning devices.
- The `Reset database` button on the leaderboard page clears all users, answers, and game state.
- All HTTP requests are logged to `logs/` with timestamps, User-Agent, and request bodies for debugging.
