from sqlalchemy import Column, Integer, String
from app.db.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String)