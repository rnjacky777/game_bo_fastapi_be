from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core_system.models.user import User
from dependencies.db import get_db
from schemas.user import UserOut  # 你可以建立一個 UserOut schema

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/", response_model=list[UserOut])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
