from pathlib import Path
from datetime import datetime, timedelta
import logging
import json
import re
import shutil
import asyncio
import os
import tempfile
import secrets
import hashlib
from typing_extensions import Literal
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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
GAME_STATE_FILE = Path(__file__).resolve().parents[1] / "game_state.json"
SAVED_CONFIGS_FILE = Path(__file__).resolve().parents[1] / "saved_configs.json"
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# --------------------
# CONFIG AUTH
# --------------------

_ADMIN_USERNAME = "ArtiomHost"
_ADMIN_PW_HASH = "9152d9e8590f9e4d71ab0eb2c086d42c25a9564d3114084abf553871c08f1441"  # SHA-256
_config_sessions: set = set()

# --------------------
# GAME STATE
# --------------------

_GAME_STATE_DEFAULTS = {
    "started": False,
    "config": None,
    "current_tour": 0,
    "current_question": 0,
    "question_started_at": None,
    "host_state": "waiting",
    "game_id": 0,
}

def _load_game_state() -> dict:
    try:
        if GAME_STATE_FILE.exists():
            loaded = json.loads(GAME_STATE_FILE.read_text(encoding="utf-8"))
            return {**_GAME_STATE_DEFAULTS, **loaded}
    except Exception:
        pass
    return dict(_GAME_STATE_DEFAULTS)

def _save_game_state() -> None:
    try:
        GAME_STATE_FILE.write_text(json.dumps(_game_state), encoding="utf-8")
    except Exception:
        pass

# --------------------
# SAVED CONFIGS
# --------------------

def _load_saved_configs() -> list:
    try:
        if SAVED_CONFIGS_FILE.exists():
            return json.loads(SAVED_CONFIGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def _save_saved_configs(configs: list) -> None:
    try:
        SAVED_CONFIGS_FILE.write_text(
            json.dumps(configs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass

# --------------------
# LOGGING
# --------------------

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
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

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

class ConfigLoginRequest(BaseModel):
    username: str
    password: str

class QuestionData(BaseModel):
    type: Literal["text", "youtube", "image", "video", "audio"] = "text"
    text: str = ""
    media_url: str = ""
    answer: str = ""
    answer_description: str = ""
    answer_image_url: str = ""
    bg_music_url: str = ""
    playback_rate: float = 1.0
    muted: bool = False
    timer_seconds: Optional[int] = None

class TourConfigFull(BaseModel):
    type: Literal["ordinary", "themed"]
    name: str = ""
    timer_seconds: Optional[int] = None
    questions_data: list[QuestionData]

class ConfigSave(BaseModel):
    name: str
    tours: list[TourConfigFull]

class GameStartWithConfig(BaseModel):
    config_id: str

class TourActivate(BaseModel):
    tour_number: int

class QuestionActivate(BaseModel):
    question_number: int

class HostStateUpdate(BaseModel):
    state: Literal["waiting", "timer_running", "show_answer", "finish_answers"]

_game_state: dict = _load_game_state()

# --------------------
# STARTUP RESET
# --------------------

def _startup_reset():
    db = SessionLocal()
    try:
        db.query(Answer).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()
    _game_state.update(dict(_GAME_STATE_DEFAULTS))
    _save_game_state()
    logger.info("Startup reset: database cleared, game state reset")

_startup_reset()

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

    logger.info(f"Created session: name='{data.name}', session_id={user.id}, score={user.score}")
    return {"session_id": user.id}

# --------------------
# USERS
# --------------------

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    logger.info(f"Retrieved {len(users)} users")
    return [{"id": u.id, "name": u.name, "score": u.score} for u in users]

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
        f"Created answer: answer_id={answer.id}, session_id={data.session_id}, round={data.round}, "
        f"question_number={data.question_number}, answer_text='{data.answer_text}'"
    )
    return {"status": "ok", "answer_id": answer.id}

# --------------------
# UPDATE ANSWER
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
            db.query(User).filter(
                User.id == answer.session_id, User.score > 0
            ).update({"score": User.score - 1}, synchronize_session=False)

    db.commit()
    logger.info(
        f"Updated answer id={answer_id}: from is_correct={prev} to is_correct={data.is_correct}, "
        f"session_id={answer.session_id}, question_number={answer.question_number}"
    )
    return {"status": "ok"}

# --------------------
# ERROR PAGES
# --------------------

@app.exception_handler(404)
async def cause_404(request: Request, exc: StarletteHTTPException):
    return RedirectResponse(url="/error_page.html")

@app.exception_handler(500)
async def cause_500(request: Request, exc: Exception):
    if request.url.path.startswith("/api/"):
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(status_code=500, content={"detail": detail})
    return RedirectResponse(url="/server_error_page.html", status_code=303)

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
    logger.info(f"Retrieved leaderboard: {len(rows)} users, top={rows[0][0].name if rows else 'none'}")
    return [{"id": u.id, "name": u.name, "score": score} for u, score in rows]

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
    return [{"round": a.round, "question_number": a.question_number} for a in answers]

# --------------------
# SAVED CONFIGS CRUD
# --------------------

@app.get("/configs")
def list_configs():
    configs = _load_saved_configs()
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "created_at": c.get("created_at", ""),
            "tour_count": len(c["tours"]),
        }
        for c in configs
    ]

@app.post("/configs")
def create_config(data: ConfigSave):
    configs = _load_saved_configs()
    config_id = str(int(datetime.now().timestamp() * 1000))
    tours = []
    for t in data.tours:
        td = t.model_dump()
        td["questions"] = len(t.questions_data)
        tours.append(td)
    configs.append({
        "id": config_id,
        "name": data.name,
        "created_at": datetime.now().isoformat(),
        "tours": tours,
    })
    _save_saved_configs(configs)
    logger.info(f"Config created: id={config_id}, name='{data.name}'")
    return {"status": "ok", "id": config_id}

@app.get("/configs/{config_id}")
def get_config(config_id: str):
    configs = _load_saved_configs()
    config = next((c for c in configs if c["id"] == config_id), None)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@app.put("/configs/{config_id}")
def update_config(config_id: str, data: ConfigSave):
    configs = _load_saved_configs()
    idx = next((i for i, c in enumerate(configs) if c["id"] == config_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Config not found")
    tours = []
    for t in data.tours:
        td = t.model_dump()
        td["questions"] = len(t.questions_data)
        tours.append(td)
    configs[idx].update({
        "name": data.name,
        "tours": tours,
        "updated_at": datetime.now().isoformat(),
    })
    _save_saved_configs(configs)
    logger.info(f"Config updated: id={config_id}, name='{data.name}'")
    return {"status": "ok"}

@app.delete("/configs/{config_id}")
def delete_config(config_id: str):
    configs = _load_saved_configs()
    configs = [c for c in configs if c["id"] != config_id]
    _save_saved_configs(configs)
    logger.info(f"Config deleted: id={config_id}")
    return {"status": "ok"}

# --------------------
# GAME CONTROL
# --------------------

@app.post("/game/start")
def start_game(data: GameStartWithConfig):
    configs = _load_saved_configs()
    config = next((c for c in configs if c["id"] == data.config_id), None)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    _game_state["started"] = True
    _game_state["config"] = {"tours": config["tours"]}
    _game_state["game_id"] = int(datetime.now().timestamp() * 1000)
    _game_state["current_tour"] = 0
    _game_state["current_question"] = 0
    _game_state["question_started_at"] = None
    _game_state["host_state"] = "waiting"
    _save_game_state()
    logger.info(f"Game started: config='{config['name']}', game_id={_game_state['game_id']}")
    return {"status": "ok"}

@app.post("/game/tour")
def set_active_tour(data: TourActivate):
    _game_state["current_tour"] = data.tour_number
    _game_state["current_question"] = 0
    _game_state["question_started_at"] = None
    _game_state["host_state"] = "waiting"
    _save_game_state()
    logger.info(f"Active tour set to: {data.tour_number}")
    return {"status": "ok"}

@app.post("/game/question")
def set_active_question(data: QuestionActivate):
    _game_state["current_question"] = data.question_number
    _game_state["question_started_at"] = None
    _game_state["host_state"] = "waiting"
    _save_game_state()
    logger.info(f"Active question set to: {data.question_number}")
    return {"status": "ok"}

@app.post("/game/host-state")
def set_host_state(data: HostStateUpdate):
    _game_state["host_state"] = data.state
    if data.state == "timer_running":
        _game_state["question_started_at"] = int(datetime.now().timestamp() * 1000)
    _save_game_state()
    logger.info(f"Host state set to: {data.state}")
    return {"status": "ok"}

@app.get("/game/status")
def get_game_status():
    return {
        "started": _game_state["started"],
        "config": _game_state["config"],
        "current_tour": _game_state["current_tour"],
        "current_question": _game_state.get("current_question", 0),
        "question_started_at": _game_state.get("question_started_at"),
        "host_state": _game_state.get("host_state", "waiting"),
        "game_id": _game_state["game_id"],
    }

@app.delete("/reset")
def reset_database(db: Session = Depends(get_db)):
    db.query(Answer).delete()
    db.query(User).delete()
    db.commit()
    _game_state.update(dict(_GAME_STATE_DEFAULTS))
    _save_game_state()
    logger.info("Database reset: all users and answers deleted, game state reset")
    return {"status": "ok"}

# --------------------
# FILE UPLOAD
# --------------------

_ALLOWED_UPLOAD_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/webm", "video/ogg", "video/quicktime",
    "audio/mpeg", "audio/ogg", "audio/wav", "audio/webm", "audio/mp4", "audio/aac", "audio/flac",
}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail="Only image, video, or audio files are allowed")
    ext = Path(file.filename).suffix.lower() or ".bin"
    unique_name = f"{int(datetime.now().timestamp() * 1000)}{ext}"
    dest = UPLOADS_DIR / unique_name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    logger.info(f"File uploaded: {unique_name}")
    return {"url": f"/uploads/{unique_name}"}


class StripAudioRequest(BaseModel):
    url: str

@app.post("/api/strip-audio")
async def strip_audio(req: StripAudioRequest):
    out_name = f"{int(datetime.now().timestamp() * 1000)}_noaudio.mp4"
    output_path = UPLOADS_DIR / out_name

    if req.url.startswith("/uploads/"):
        input_path = UPLOADS_DIR / Path(req.url).name
        if not input_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(input_path), "-an", "-c:v", "copy", str(output_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"ffmpeg strip-audio failed: {stderr.decode(errors='replace')}")
            raise HTTPException(status_code=500, detail="FFmpeg failed to strip audio")
    else:
        tmp_dir = tempfile.mkdtemp()
        tmp_input = os.path.join(tmp_dir, "input.mp4")
        try:
            dl = await asyncio.create_subprocess_exec(
                "yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
                "--merge-output-format", "mp4", "-o", tmp_input, req.url,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, dl_err = await dl.communicate()
            if dl.returncode != 0:
                logger.error(f"yt-dlp failed: {dl_err.decode(errors='replace')}")
                raise HTTPException(status_code=500, detail="Failed to download video")
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", tmp_input, "-an", "-c:v", "copy", str(output_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(f"ffmpeg strip-audio failed: {stderr.decode(errors='replace')}")
                raise HTTPException(status_code=500, detail="FFmpeg failed to strip audio")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info(f"Audio stripped: {out_name}")
    return {"url": f"/uploads/{out_name}"}

# --------------------
# STATIC FILES
# --------------------

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

_NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"}

@app.post("/api/config-login")
async def config_login(data: ConfigLoginRequest, response: Response):
    pw_hash = hashlib.sha256(data.password.encode()).hexdigest()
    if data.username != _ADMIN_USERNAME or pw_hash != _ADMIN_PW_HASH:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_hex(32)
    _config_sessions.add(token)
    response.set_cookie("config_session", token, httponly=True, samesite="strict", max_age=86400 * 7)
    return {"ok": True}

@app.post("/api/config-logout")
async def config_logout(request: Request, response: Response):
    token = request.cookies.get("config_session")
    if token:
        _config_sessions.discard(token)
    response.delete_cookie("config_session")
    return {"ok": True}

@app.get("/config.html")
async def serve_config(request: Request):
    token = request.cookies.get("config_session")
    if not token or token not in _config_sessions:
        return RedirectResponse("/config_login.html", status_code=302)
    return FileResponse(FRONTEND_DIR / "config.html", headers=_NO_CACHE)

@app.get("/{full_path:path}", response_class=FileResponse)
async def serve_frontend(full_path: str):
    target_path = (FRONTEND_DIR / full_path).resolve()
    if not str(target_path).startswith(str(FRONTEND_DIR.resolve())) or not target_path.exists():
        logger.warning(f"Frontend file not found: {full_path}")
        raise HTTPException(status_code=404, detail="Not found")
    logger.info(f"Served frontend file: {full_path}")
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }
    return FileResponse(target_path, headers=headers)
