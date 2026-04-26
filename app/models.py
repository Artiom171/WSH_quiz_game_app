from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from sqlalchemy import Boolean


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Integer, default=0)
    name = Column(String, index=True)

    answers = relationship("Answer", back_populates="user")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("users.id"))
    round = Column(Integer)
    question_number = Column(Integer)
    answer_text = Column(String)
    is_correct = Column(Boolean, nullable=True)

    user = relationship("User", back_populates="answers")