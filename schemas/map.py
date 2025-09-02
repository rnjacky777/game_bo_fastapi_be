from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


# ---------- Map 相關 ----------


class MapData(BaseModel):
    map_id: int = Field(..., description="Map 的唯一識別 ID")
    name: str = Field(..., max_length=100, description="地圖名稱")
    description: Optional[str] = Field(None, description="地圖敘述描述")

    model_config = {"from_attributes": True}


class ListMapsResponse(BaseModel):
    next_cursor: Optional[int] = Field(
        None, description="下一頁的 cursor ID。若為 null 表示沒有下一頁。"
    )
    prev_cursor: Optional[int] = Field(
        None, description="上一頁的 cursor ID。若為 null 表示沒有上一頁。"
    )
    map_list: List[MapData] = Field(..., description="地圖資料列表")


class CreateMapData(BaseModel):
    name: str = Field(..., max_length=100, description="要建立的地圖名稱")
    description: Optional[str] = Field(None, description="地圖敘述")
    image_url: Optional[str] = Field(None, description="地圖圖片 URL")


class CreateMapRequest(BaseModel):
    map_datas: List[CreateMapData] = Field(..., description="批量新增的地圖資料列表")


class CreatedMapInfo(BaseModel):
    id: int
    name: str


class CreateMapResponse(BaseModel):
    message: str
    created_maps: List[CreatedMapInfo]


class MapConnectionUpsert(BaseModel):
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
    name: Optional[str] = Field(None, max_length=100, description="地圖名稱（可選）")
    description: Optional[str] = Field(None, description="地圖敘述（可選）")
    image_url: Optional[str] = Field(None, description="地圖圖片 URL（可選）")


class MapNeighborOut(BaseModel):
    id: int = Field(..., description="鄰居地圖 ID")
    name: str = Field(..., description="鄰居地圖名稱")
    is_locked: bool = Field(..., description="這條連線是否被鎖住")
    required_item: Optional[str] = Field(None, description="解鎖需要的道具")
    required_level: int = Field(..., description="解鎖需要的等級")

    model_config = {"from_attributes": True}


class MapOut(BaseModel):
    id: int = Field(..., description="地圖 ID")
    name: str = Field(..., description="地圖名稱")
    description: Optional[str] = Field(None, description="地圖敘述")
    image_url: Optional[str] = Field(None, description="地圖圖片 URL")
    neighbors: List[MapNeighborOut] = Field(..., description="所有鄰居地圖與連線條件")
    events: List["EventAssociationOut"] = Field(
        ..., description="地圖上可能發生的事件與機率"
    )
    map_areas: List["MapAreaData"] = Field(..., description="地圖中的所有地區")

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
                "map_areas": [
                    {
                        "id": 1,
                        "name": "入口",
                    }
                ],
            }
        },
    }


# ---------- Event Association 相關 ----------


class EventAssociationUpsert(BaseModel):
    event_id: int = Field(..., description="要關聯的 event ID")
    probability: float = Field(
        ..., ge=0.0, le=1.0, description="此 event 出現的機率（0~1 之間）"
    )


class EventAssociationsUpdate(BaseModel):
    upsert: Optional[List[EventAssociationUpsert]] = Field(
        default=None, description="要新增或更新的 event association"
    )
    remove: Optional[List[int]] = Field(
        default=None, description="要移除的 event ID 清單"
    )
    normalize: bool = Field(
        default=False, description="若為 true，會正規化剩餘事件機率總和為 1"
    )

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def check_upsert_and_remove(self) -> "EventAssociationsUpdate":
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
                    f"Event IDs {conflict} cannot be in both upsert and remove lists"
                )
        return self


class EventAssociationOut(BaseModel):
    event_id: int
    event_name: str
    probability: float

    model_config = {"from_attributes": True}


class MapAreaData(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
