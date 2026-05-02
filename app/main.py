from pathlib import Path
from datetime import datetime, timedelta
import logging

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import SessionLocal, engine, Base
from app.models import User, Answer

# --------------------
# INIT DB
# --------------------

Base.metadata.create_all(bind=engine)

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
    elif db.query(User).filter(func.lower(User.name) == data.name.lower()).first():
        logger.warning(f"Session creation failed: name already exists ('{data.name}')")
        raise HTTPException(status_code=400, detail="Игрок с таким именем уже существует")
    
    user = User(name=data.name)
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
    answer = Answer(
        session_id=data.session_id,
        round=data.round,
        question_number=data.question_number,
        answer_text=data.answer_text
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

    # начисляем балл только если стало TRUE впервые
    if data.is_correct and not prev:
        user = db.query(User).filter(User.id == answer.session_id).first()
        if user:
            user.score += 1

    db.commit()
    logger.info(
        f"Updated answer id={answer_id}: from is_correct={prev} to is_correct={data.is_correct}, session_id={answer.session_id}, question_number={answer.question_number}"
    )

    return {"status": "ok"}

# --------------------
# RESULTS (leaderboard)
# --------------------

@app.get("/results")
def get_results(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.score.desc()).all()

    logger.info(
        f"Retrieved leaderboard: {len(users)} users, top={users[0].name if users else 'none'}"
    )
    return [
        {"id": u.id, "name": u.name, "score": u.score}
        for u in users
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


@app.delete("/reset")
def reset_database(db: Session = Depends(get_db)):
    db.query(Answer).delete()
    db.query(User).delete()
    db.commit()
    logger.info("Database reset: all users and answers deleted")
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