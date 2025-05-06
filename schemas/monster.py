from typing import Optional

from pydantic import BaseModel,Field
from .reward import RewardPoolSchema

class MonsterSchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class AddDropItemSchema(BaseModel):
    item_id: int
    probability: float = Field(..., ge=0.0, le=1.0)
