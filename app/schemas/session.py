from pydantic import BaseModel

class SessionCreate(BaseModel):
    name: str