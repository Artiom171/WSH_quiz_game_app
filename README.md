# WSH Quiz Game App

A small quiz game web app built with FastAPI and plain frontend HTML pages. Players can register with a name, submit answers, and a host can mark answers as correct or incorrect. Final results are shown in a leaderboard.

## Features

- Player registration via `index.html`
- Question submission via `questions.html`
- Host answer review via `answers.html`
- Final leaderboard via `final_result.html`
- Data reset button for development/testing
- Responsive layout for mobile devices

## Project structure

- `app/` — backend code
  - `main.py` — FastAPI application
  - `db/` — database connection and setup
  - `models/` — SQLAlchemy models
- `frontend/` — frontend HTML pages for players and host
- `database.db` — SQLite database file

## Requirements

- Python 3.10+
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic

You can install the required packages with:

```bash
pip install fastapi uvicorn sqlalchemy pydantic
```

## Run the app

From the project root, start the backend server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open in your browser:

- `http://localhost:8000/` — player login page
- `http://localhost:8000/questions.html` — quiz page (after login)
- `http://localhost:8000/answers.html` — host answer review page
- `http://localhost:8000/final_result.html` — leaderboard

## How to use

1. Player opens `index.html` and enters a name.
2. The app creates a session and redirects to `questions.html`.
3. The player submits answers for each question.
4. The host opens `answers.html`, reviews answers, and marks them correct or incorrect.
5. Correct answers increase the player's score.
6. The final leaderboard is available on `final_result.html`.

## Notes

- The app uses browser `localStorage` to keep the logged-in player session across refreshes.
- The frontend is served from the FastAPI app, so all pages are available from the same origin.
- The `final_result.html` page refreshes automatically to show new users and scores in real time.
- The `Reset database` button on the final results page clears all users and answers for easy testing.
