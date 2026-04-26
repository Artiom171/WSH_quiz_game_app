from pydantic import BaseModel

class AnswerCreate(BaseModel):
    session_id: int
    question_id: int
    answer_text: str