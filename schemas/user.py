from pydantic import BaseModel
from datetime import datetime


class UserOut(BaseModel):
    id: int
    username: str
    current_map_id:int
    money: int
    last_login: datetime | None = None

    class Config:
        from_attributes = True
