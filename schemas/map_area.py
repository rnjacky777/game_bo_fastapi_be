from typing import List, Optional
from pydantic import BaseModel, Field


class MapAreaCreate(BaseModel):
    name: str = Field(..., max_length=100, description="地區名稱")
    description: Optional[str] = Field(None, description="地區描述")
    image_url: Optional[str] = Field(None, description="地區圖片 URL")


class MapAreaUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="地區名稱")
    description: Optional[str] = Field(None, description="地區描述")
    image_url: Optional[str] = Field(None, description="地區圖片 URL")


class NPCInfo(BaseModel):
    npc_id: int = Field(..., description="NPC ID")
    npc_name: str = Field(..., description="NPC 名稱")
    npc_role: str = Field(..., description="NPC 角色或身份")


class EventAssociationOut(BaseModel):
    event_id: int = Field(..., description="事件 ID")
    event_name: str = Field(..., description="事件名稱")
    probability: float = Field(..., ge=0.0, le=1.0, description="事件出現機率")


class MapAreaOut(BaseModel):
    id: int = Field(..., description="地區 ID")
    map_id: int = Field(..., description="所屬地圖 ID")
    name: str = Field(..., description="地區名稱")
    description: Optional[str] = Field(None, description="地區描述")
    image_url: Optional[str] = Field(None, description="地區圖片 URL")
    init_npc: Optional[List[NPCInfo]] = Field(None, description="初始 NPC 清單")
    event_associations: List[EventAssociationOut] = Field(..., description="事件關聯列表")

    model_config = {
        "from_attributes": True,
    }
