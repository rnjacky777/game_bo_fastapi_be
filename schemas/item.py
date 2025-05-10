from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
from .reward import RewardPoolSchema


class ItemType(Enum):
    equipment = 'equipment'
    consumable = 'consumable'
    MATERIAL = 'material'
    quest = 'quest'


class ItemSchema(BaseModel):
    item_id: int
    name: str
    item_type: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ItemListSchema(BaseModel):
    last_id: Optional[int] = None
    item_data: list[ItemSchema] = []


class GetItemDetailRequest(BaseModel):
    item_id: int


class GetItemDetailResponse(BaseModel):
    item_id: int = Field(alias="id")
    name: str
    description: str
    item_type: str  # 'equipment', 'consumable', 'quest',"material"

    # Common
    price: int
    rarity: int

    # 裝備專屬欄位（選填）
    # 'weapon', 'armor', etc.
    slot: Optional[str]
    atk_bonus: Optional[int]
    def_bonus: Optional[int]

    # 消耗品專屬欄位（選填）
    hp_restore: Optional[int]
    mp_restore: Optional[int]

    class Config:
        from_attributes = True
        populate_by_name = True 


class AddItemRequest(BaseModel):
    name: str
    description: str
    item_type: str  # 'weapon', 'armor', etc.

    # Common
    price: int
    rarity: int

    # 裝備專屬欄位（選填）
    # 'weapon', 'armor', etc.
    # 裝備專屬欄位（選填）
    slot: Optional[str] = None
    atk_bonus: Optional[int] = None
    def_bonus: Optional[int] = None

    # 消耗品專屬欄位（選填）
    hp_restore: Optional[int] = None
    mp_restore: Optional[int] = None

    class Config:
        from_attributes = True

class EditItemRequest(BaseModel):
    name: str
    description: str
    item_type: str
    price: int
    rarity: int
    slot: Optional[str] = None
    atk_bonus: Optional[int] = None
    def_bonus: Optional[int] = None
    hp_restore: Optional[int] = None
    mp_restore: Optional[int] = None