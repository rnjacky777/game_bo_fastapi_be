from pydantic import BaseModel, ConfigDict
from typing import Optional


class CharTempBase(BaseModel):
    """基本角色模板，包含所有共享的欄位。"""
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


class CharTempCreate(CharTempBase):
    """用於建立新角色模板的 Schema。"""
    pass


class CharTempUpdate(BaseModel):
    """用於更新現有角色模板的 Schema，所有欄位皆為可選。"""
    name: Optional[str] = None
    rarity: Optional[int] = None
    description: Optional[str] = None
    image_sm_url: Optional[str] = None
    image_lg_url: Optional[str] = None
    base_hp: Optional[int] = None
    base_mp: Optional[int] = None
    base_atk: Optional[int] = None
    base_spd: Optional[int] = None
    base_def: Optional[int] = None


class CharTempResponse(CharTempBase):
    """
    主要的回應 Schema，包含所有基本欄位以及資料庫生成的 'id'。
    為了保持 API 的一致性，此模型用於單一查詢、列表、建立和更新的回應。
    """
    id: int

    model_config = ConfigDict(from_attributes=True)
