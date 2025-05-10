

from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from models import RewardPool


def add_reward_pool(db: Session,name:str):
    new_pool = RewardPool(name=name)
    db.add(new_pool)
    db.commit()
    db.refresh(new_pool)
    return new_pool.id

