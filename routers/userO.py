from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core_system.models.user import User
from dependencies.db import get_db
from schemas.user import UserOut  # 你可以建立一個 UserOut schema

router = APIRouter()


@router.get("/get_all_user", response_model=list[UserOut])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


# region need refactor
from pydantic import BaseModel
from typing import Optional

class CharTempCreate(BaseModel):
    name: str
    rarity: int
    description: Optional[str] = None
    image_sm_url: Optional[str] = None
    image_lg_url: Optional[str] = None
    base_hp: int
    base_mp: int
    base_atk: int
    base_spd: int
    base_def: int

from sqlalchemy.orm import Session
from core_system.models import CharTemp
from schemas.user import CharTempCreate

def create_char_temp(db: Session, char_data: CharTempCreate) -> CharTemp:
    char = CharTemp(**char_data.dict())
    db.add(char)
    db.commit()
    db.refresh(char)
    return char

@router.post("/create")
def create_char_template(char_data: CharTempCreate, db: Session = Depends(get_db)):
    return create_char_temp(db, char_data)

# endregion