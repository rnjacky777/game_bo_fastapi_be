from pydantic import BaseModel, Field
from typing import List, Optional


class RewardPoolItemSchema(BaseModel):
    id: int
    item_id: int
    probability: float
    item_name: str  # 加上這個欄位

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_item(cls, obj):
        return cls(
            id=obj.id,
            item_id=obj.item_id,
            probability=obj.probability,
            item_name=obj.item.name if obj.item else ""
        )


class RewardPoolSchema(BaseModel):
    id: int
    name: str
    items: Optional[List[RewardPoolItemSchema]]

    class Config:
        from_attributes = True

class UpdateDropProbabilitySchema(BaseModel):
    monster_id: int
    item_id: int
    probability: float = Field(..., ge=0.0, le=1.0)