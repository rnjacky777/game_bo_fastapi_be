from typing import List, Optional
from pydantic import BaseModel, Field, confloat


class MapData(BaseModel):
    map_id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ListMapsResponse(BaseModel):
    last_id: Optional[int]
    map_list: List[MapData]


class CreateMapData(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class CreateMapRequest(BaseModel):
    map_datas: List[CreateMapData]

class MapConnectionUpsert(BaseModel):
    neighbor_id: int
    is_locked: Optional[bool] = False
    required_item: Optional[str] = None
    required_level: Optional[int] = 0

class MapUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    connections: Optional[List[MapConnectionUpsert]]
    remove_connections: Optional[List[int]]

class MapNeighborOut(BaseModel):
    id: int
    name: str
    is_locked: bool
    required_item: Optional[str]
    required_level: int

class MapOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    neighbors: List[MapNeighborOut]


class EventAssociationUpsert(BaseModel):
    event_id: int
    probability: confloat(ge=0.0, le=1.0) = Field(..., description="0~1 之間的機率")

class EventAssociationsUpdate(BaseModel):
    upsert: Optional[List[EventAssociationUpsert]] = None
    remove: Optional[List[int]] = None
    normalize: Optional[bool] = False  # 如果要正規化機率總和

class EventAssociationOut(BaseModel):
    event_id: int
    event_name: str
    probability: float