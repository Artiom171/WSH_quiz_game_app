from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    question_id = Column(Integer)
    answer_text = Column(String)