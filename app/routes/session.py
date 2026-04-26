from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from app.db.database import SessionLocal
from app.models.session import Session
from app.schemas.session import SessionCreate

router = APIRouter(prefix="/session", tags=["session"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_session(session: SessionCreate, db: DBSession = Depends(get_db)):
    new_session = Session(player_name=session.name)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {"session_id": new_session.id}