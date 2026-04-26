from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    user = User(name=data.name)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"session_id": user.id}

# --------------------
# USERS
# --------------------

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()

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

    return {"status": "ok", "answer_id": answer.id}

# --------------------
# UPDATE ANSWER (CHECK / NOT CHECK)
# --------------------

@app.patch("/answers/{answer_id}")
def update_answer(answer_id: int, data: AnswerUpdate, db: Session = Depends(get_db)):

    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    prev = answer.is_correct
    answer.is_correct = data.is_correct

    # начисляем балл только если стало TRUE впервые
    if data.is_correct and not prev:
        user = db.query(User).filter(User.id == answer.session_id).first()
        if user:
            user.score += 1

    db.commit()

    return {"status": "ok"}

# --------------------
# RESULTS (leaderboard)
# --------------------

@app.get("/results")
def get_results(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.score.desc()).all()

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