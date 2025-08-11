from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


# ---------- Map 相關 ----------


class MapData(BaseModel):
    """用於地圖列表和基本地圖資訊的回應模型。"""
    map_id: int = Field(..., description="Map 的唯一識別 ID")
    name: str = Field(..., max_length=100, description="地圖名稱")
    description: Optional[str] = Field(None, description="地圖敘述描述")

    model_config = {"from_attributes": True}


class ListMapsResponse(BaseModel):
    """GET /list-map 的回應模型。"""
    next_cursor: Optional[int] = Field(None, description="下一頁的 cursor ID。若為 null 表示沒有下一頁。")
    prev_cursor: Optional[int] = Field(None, description="上一頁的 cursor ID。若為 null 表示沒有上一頁。")
    map_list: List[MapData] = Field(..., description="地圖資料列表")


class CreateMapData(BaseModel):
    """用於建立單一地圖的資料模型。"""
    name: str = Field(..., max_length=100, description="要建立的地圖名稱")
    description: Optional[str] = Field(None, description="地圖敘述")
    image_url: Optional[str] = Field(None, description="地圖圖片 URL")


class CreateMapRequest(BaseModel):
    """POST /create-map 的請求模型，支援批量建立。"""
    map_datas: List[CreateMapData] = Field(..., description="批量新增的地圖資料列表")


class CreatedMapInfo(BaseModel):
    """成功建立的地圖資訊"""

    id: int
    name: str


class CreateMapResponse(BaseModel):
    """POST /maps/ 的回應模型"""
    message: str
    created_maps: List[CreatedMapInfo]


class MapConnectionUpsert(BaseModel):
    """用於新增或更新地圖連線的資料模型。"""
    neighbor_id: int = Field(..., description="鄰居地圖的 ID")
    is_locked: bool = Field(False, description="連線是否被鎖住")
    required_item: Optional[str] = Field(None, description="解鎖需要的道具")
    required_level: int = Field(0, ge=0, description="解鎖需要的等級")


class ConnectionsUpdate(BaseModel):
    connections: Optional[List[MapConnectionUpsert]] = Field(
        None, description="要新增或更新的鄰居連線"
    )
    remove_connections: Optional[List[int]] = Field(
        None, description="要移除的鄰居地圖 ID"
    )


class MapUpdate(BaseModel):
    """用於更新地圖資訊（包含連線）的請求模型。"""
    name: Optional[str] = Field(None, max_length=100, description="地圖名稱（可選）")
    description: Optional[str] = Field(None, description="地圖敘述（可選）")
    image_url: Optional[str] = Field(None, description="地圖圖片 URL（可選）")


class MapNeighborOut(BaseModel):
    """用於表示鄰居地圖及其連線條件的回應模型。"""
    id: int = Field(..., description="鄰居地圖 ID")
    name: str = Field(..., description="鄰居地圖名稱")
    is_locked: bool = Field(..., description="這條連線是否被鎖住")
    required_item: Optional[str] = Field(None, description="解鎖需要的道具")
    required_level: int = Field(..., description="解鎖需要的等級")

    model_config = {"from_attributes": True}


class MapOut(BaseModel):
    """用於回應單一地圖詳細資訊（包含鄰居）的模型。"""
    id: int = Field(..., description="地圖 ID")
    name: str = Field(..., description="地圖名稱")
    description: Optional[str] = Field(None, description="地圖敘述")
    image_url: Optional[str] = Field(None, description="地圖圖片 URL")
    neighbors: List[MapNeighborOut] = Field(..., description="所有鄰居地圖與連線條件")
    events: List["EventAssociationOut"] = Field(
        ..., description="地圖上可能發生的事件與機率")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 5,
                "name": "遺忘之森",
                "description": "被迷霧遮蔽的古樹林",
                "image_url": None,
                "neighbors": [
                    {
                        "id": 7,
                        "name": "密林出口",
                        "is_locked": True,
                        "required_item": "靈魂之鑰",
                        "required_level": 3,
                    }
                ],
                "events": [
                    {
                        "event_id": 1,
                        "event_name": "遭遇史萊姆",
                        "probability": 0.8,
                    },
                    {
                        "event_id": 2,
                        "event_name": "撿到藥草",
                        "probability": 0.2,
                    },
                ],
            }
        },
    }

# ---------- Event Association 相關 ----------


class EventAssociationUpsert(BaseModel):
    """用於新增或更新地圖與事件關聯的資料模型。"""
    event_id: int = Field(..., description="要關聯的 event ID")
    probability: float = Field(..., ge=0.0, le=1.0,
                               description="此 event 出現的機率（0~1 之間）")


class EventAssociationsUpdate(BaseModel):
    """用於批量更新地圖事件關聯的資料模型。"""
    upsert: Optional[List[EventAssociationUpsert]] = Field(
        default=None, description="要新增或更新的 event association"
    )
    remove: Optional[List[int]] = Field(
        default=None, description="要移除的 event ID 清單"
    )
    normalize: bool = Field(
        default=False,
        description=(
            "如果為 true，會在所有 upsert/remove 後把剩下的 probability 總和正規化為 1（"
            "若都是 0 則不改）"
        ),
    )

    model_config = {"from_attributes": True}

    @model_validator(mode='after')
    def check_upsert_and_remove(self) -> 'EventAssociationsUpdate':
        """驗證 upsert 列表的唯一性，以及 upsert 和 remove 列表之間沒有衝突。"""
        if self.upsert:
            ids = [item.event_id for item in self.upsert]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate event_id in upsert list")

        if self.upsert and self.remove:
            upsert_ids = {u.event_id for u in self.upsert}
            remove_ids = set(self.remove)
            conflict = upsert_ids & remove_ids
            if conflict:
                raise ValueError(
                    f"Event IDs {conflict} cannot be in both upsert and remove lists")
        return self


class EventAssociationOut(BaseModel):
    """用於回應地圖與事件關聯資訊的模型。"""
    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(..., description="Event 名稱")
    probability: float = Field(..., ge=0.0, le=1.0, description="該 event 的機率")

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """通用的訊息回應模型"""
    message: str

class MapAreaCreate(BaseModel):
    map_id: int
    name: str
    description: str | None = None
    image_url: str | None = None

class MapAreaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    image_url: str | None = None

class NPCInfo(BaseModel):
    npc_id: int
    npc_name: str
    npc_role: str

class EventAssociationOut(BaseModel):
    event_id: int
    event_name: str
    probability: float

class MapAreaOut(BaseModel):
    id: int
    map_id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    init_npc: Optional[List[NPCInfo]]
    event_associations: List[EventAssociationOut]