from pathlib import Path
from datetime import datetime, timedelta
import logging
import re
from typing_extensions import Literal

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db.database import SessionLocal, engine, Base
from app.models import User, Answer

# --------------------
# INIT DB
# --------------------

Base.metadata.create_all(bind=engine)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE answers ADD COLUMN game_id INTEGER DEFAULT 0"))
        conn.commit()
except Exception:
    pass

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN game_id INTEGER DEFAULT 0"))
        conn.commit()
except Exception:
    pass

# --------------------
# APP
# --------------------

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_old_logs(hours: int = 6):
    expire_time = datetime.now() - timedelta(hours=hours)
    for path in LOG_DIR.glob("*.txt"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime) < expire_time:
                path.unlink()
                logging.getLogger("quiz_app").info(f"Deleted old log file: {path.name}")
        except Exception:
            logging.getLogger("quiz_app").exception(f"Failed to delete log file: {path}")

cleanup_old_logs()
log_file = LOG_DIR / f"{datetime.now():%Y%m%d_%H%M%S}.txt"

logger = logging.getLogger("quiz_app")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(file_handler)

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    client = request.client.host if request.client else "unknown"
    query = f"?{request.url.query}" if request.url.query else ""
    url = f"{request.url.path}{query}"
    logger.info(f"Request start: {request.method} {url} from {client}")
    logger.info(f"User-Agent: {request.headers.get('user-agent', 'unknown')}")
    logger.info(f"Accept: {request.headers.get('accept', 'unknown')}")

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        body = await request.body()
        if body:
            try:
                text_body = body.decode("utf-8")
            except UnicodeDecodeError:
                text_body = str(body)
            logger.info(f"Request body: {text_body}")

    try:
        response = await call_next(request)
        logger.info(
            f"Request complete: {request.method} {url} from {client} -> {response.status_code} {response.media_type or 'unknown'}"
        )
        return response
    except Exception:
        logger.exception(f"Exception handling request: {request.method} {url} from {client}")
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# --------------------
# DB SESSION
# --------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------
# SCHEMAS
# --------------------

class UserCreate(BaseModel):
    name: str

class AnswerCreate(BaseModel):
    session_id: int
    round: int
    question_number: int
    answer_text: str

class AnswerUpdate(BaseModel):
    is_correct: bool

class TourConfig(BaseModel):
    type: Literal["ordinary", "themed"]
    questions: int

class GameStartConfig(BaseModel):
    tours: list[TourConfig]

class TourActivate(BaseModel):
    tour_number: int

_game_state: dict = {"started": False, "config": None, "current_tour": 0, "game_id": 0}

# --------------------
# SESSION (create user)
# --------------------

@app.post("/session")
def create_session(data: UserCreate, db: Session = Depends(get_db)):
    if not data.name.strip():
        logger.warning("Session creation failed: empty name")
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    elif len(data.name) > 40:
        logger.warning(f"Session creation failed: name too long ({len(data.name)} chars)")
        raise HTTPException(status_code=400, detail="Слишком длинное имя (макс 40 символов)")
    elif not re.fullmatch(r"[A-Za-z0-9Ѐ-ӿ]+", data.name):
        logger.warning(f"Session creation failed: invalid characters in name ('{data.name}')")
        raise HTTPException(status_code=400, detail="Имя может содержать только латинские/кириллические буквы и цифры")
    elif db.query(User).filter(func.lower(User.name) == data.name.lower()).first():
        logger.warning(f"Session creation failed: name already exists ('{data.name}')")
        raise HTTPException(status_code=400, detail="Игрок с таким именем уже существует")
    
    user = User(name=data.name, game_id=_game_state["game_id"])
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(
        f"Created session: name='{data.name}', session_id={user.id}, score={user.score}"
    )
    return {"session_id": user.id}

# --------------------
# USERS
# --------------------

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()

    logger.info(f"Retrieved {len(users)} users")
    return [
        {"id": u.id, "name": u.name, "score": u.score}
        for u in users
    ]

# --------------------
# CREATE ANSWER
# --------------------

@app.post("/answers")
def create_answer(data: AnswerCreate, db: Session = Depends(get_db)):
    if len(data.answer_text) > 500:
        raise HTTPException(status_code=400, detail="Ответ слишком длинный (макс 500 символов)")
    answer = Answer(
        session_id=data.session_id,
        round=data.round,
        question_number=data.question_number,
        answer_text=data.answer_text,
        game_id=_game_state["game_id"]
    )

    db.add(answer)
    db.commit()
    db.refresh(answer)

    logger.info(
        f"Created answer: answer_id={answer.id}, session_id={data.session_id}, round={data.round}, question_number={data.question_number}, answer_text='{data.answer_text}'"
    )
    return {"status": "ok", "answer_id": answer.id}

# --------------------
# UPDATE ANSWER (CHECK / NOT CHECK)
# --------------------

@app.patch("/answers/{answer_id}")
def update_answer(answer_id: int, data: AnswerUpdate, db: Session = Depends(get_db)):

    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        logger.warning(f"Update failed: answer id={answer_id} not found")
        raise HTTPException(status_code=404, detail="Answer not found")

    prev = answer.is_correct
    answer.is_correct = data.is_correct

    if prev != data.is_correct:
        if data.is_correct:
            db.query(User).filter(User.id == answer.session_id).update(
                {"score": User.score + 1}, synchronize_session=False
            )
        elif prev is True:
            # only decrement when answer was previously correct (true → false)
            # null → false means never counted, so no score change
            db.query(User).filter(
                User.id == answer.session_id, User.score > 0
            ).update({"score": User.score - 1}, synchronize_session=False)

    db.commit()
    logger.info(
        f"Updated answer id={answer_id}: from is_correct={prev} to is_correct={data.is_correct}, session_id={answer.session_id}, question_number={answer.question_number}"
    )

    return {"status": "ok"}


# --------------------
# Expecting 404 and 500
# --------------------

@app.exception_handler(404)
async def cause_404(request: Request, exc: StarletteHTTPException):
    return RedirectResponse(url="/error_page.html")

# Example route that triggers a 500
@app.exception_handler(500)
async def cause_500(request: Request, exc: StarletteHTTPException):
    return RedirectResponse(url="/server_error_page.html")

# --------------------
# RESULTS (leaderboard)
# --------------------

@app.get("/results")
def get_results(db: Session = Depends(get_db)):
    score_subq = (
        db.query(Answer.session_id, func.count(Answer.id).label("score"))
        .filter(Answer.is_correct == True)
        .group_by(Answer.session_id)
        .subquery()
    )
    rows = (
        db.query(User, func.coalesce(score_subq.c.score, 0).label("score"))
        .outerjoin(score_subq, User.id == score_subq.c.session_id)
        .order_by(func.coalesce(score_subq.c.score, 0).desc())
        .all()
    )

    logger.info(
        f"Retrieved leaderboard: {len(rows)} users, top={rows[0][0].name if rows else 'none'}"
    )
    return [
        {"id": u.id, "name": u.name, "score": score}
        for u, score in rows
    ]

# --------------------
# ANSWERS LIST
# --------------------

@app.get("/answers")
def get_answers(db: Session = Depends(get_db)):
    results = db.query(Answer, User).join(User, Answer.session_id == User.id).all()

    logger.info(f"Retrieved {len(results)} answers")
    return [
        {
            "answer_id": answer.id,
            "user_name": user.name,
            "round": answer.round,
            "question_number": answer.question_number,
            "answer_text": answer.answer_text,
            "is_correct": answer.is_correct
        }
        for answer, user in results
    ]


@app.get("/answers/by-session/{session_id}")
def get_answers_by_session(session_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == session_id).first()
    if not user or user.game_id != _game_state["game_id"]:
        logger.warning(f"get_answers_by_session: session_id={session_id} not found or wrong game")
        raise HTTPException(status_code=404, detail="Session not found")
    answers = db.query(Answer).filter(
        Answer.session_id == session_id,
        Answer.game_id == _game_state["game_id"]
    ).all()
    logger.info(f"Retrieved {len(answers)} answers for session_id={session_id}")
    return [
        {"round": a.round, "question_number": a.question_number}
        for a in answers
    ]


@app.post("/game/start")
def start_game(config: GameStartConfig):
    _game_state["started"] = True
    _game_state["config"] = config.model_dump()
    _game_state["game_id"] = int(datetime.now().timestamp() * 1000)
    logger.info(f"Game started: {len(config.tours)} tours, game_id={_game_state['game_id']}")
    return {"status": "ok"}

@app.post("/game/tour")
def set_active_tour(data: TourActivate):
    _game_state["current_tour"] = data.tour_number
    logger.info(f"Active tour set to: {data.tour_number}")
    return {"status": "ok"}

@app.get("/game/status")
def get_game_status():
    return {
        "started": _game_state["started"],
        "config": _game_state["config"],
        "current_tour": _game_state["current_tour"],
        "game_id": _game_state["game_id"]
    }

@app.delete("/reset")
def reset_database(db: Session = Depends(get_db)):
    db.query(Answer).delete()
    db.query(User).delete()
    db.commit()
    _game_state["started"] = False
    _game_state["config"] = None
    _game_state["current_tour"] = 0
    logger.info("Database reset: all users and answers deleted, game state reset")
    return {"status": "ok"}


@app.get("/", response_class=FileResponse)
async def serve_index():
    logger.info("Served index page: /")
    return FileResponse(
        FRONTEND_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache"
        },
    )

@app.get("/favicon.ico")
def favicon():
    logger.info("Favicon requested")
    return Response(status_code=204)

@app.get("/{full_path:path}", response_class=FileResponse)
async def serve_frontend(full_path: str):
    target_path = (FRONTEND_DIR / full_path).resolve()
    if not str(target_path).startswith(str(FRONTEND_DIR.resolve())) or not target_path.exists():
        logger.warning(f"Frontend file not found: {full_path}")
        raise HTTPException(status_code=404, detail="Not found")
    logger.info(f"Served frontend file: {full_path}")
    return FileResponse(
        target_path,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache"
        },
    )