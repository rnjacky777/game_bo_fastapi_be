from typing import Optional

from pydantic import BaseModel, Field
from .reward import RewardPoolSchema


class MonsterSchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class AddDropItemSchema(BaseModel):
    monster_id: int
    item_id: int
    probability: float = Field(..., ge=0.0, le=1.0)


class RemoveDropItemSchema(BaseModel):
    drop_id: int


class MonsterSchema(BaseModel):
    monster_id: int
    name: str
    drop_pool_ids: Optional[int] = None

    class Config:
        from_attributes = True


class MonsterListSchema(BaseModel):
    last_id: Optional[int] = None
    monster_data: list[MonsterSchema] = []


class GetMonsterDetailResponse(BaseModel):
    monster_id: int = Field(alias="id")
    name: str
    drop_pool_id: Optional[int] = None

    # attribute
    hp: int
    mp: int
    atk: int
    spd: int
    def_: int

    class Config:
        from_attributes = True


class EditMonsterRequest(BaseModel):
    monster_id: int = Field(alias="id")
    name: str
    drop_pool_id: int

    # attribute
    hp: int
    mp: int
    atk: int
    spd: int
    def_: int

    class Config:
        from_attributes = True


class MonsterData(BaseModel):
    name: str
    drop_pool_id: Optional[int] = None

    # attribute
    hp: int = Field(default=1)
    mp: int = Field(default=1)
    atk: int = Field(default=1)
    spd: int = Field(default=1)
    def_: int = Field(default=1)

    class Config:
        from_attributes = True


class AddMonsterRequest(BaseModel):
    auto_add_reward_pool: bool
    monster_data: list[MonsterData]

    class Config:
        from_attributes = True
