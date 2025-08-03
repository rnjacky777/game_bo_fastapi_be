import logging
from sqlite3 import IntegrityError
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_system.models.association_tables import MapConnection, MapEventAssociation
from core_system.models.event import Event
from core_system.models.maps import Map
from dependencies.db import get_db
from schemas.map import (CreateMapRequest, CreateMapResponse, CreatedMapInfo,
                         EventAssociationOut, EventAssociationsUpdate,
                         ListMapsResponse, MapConnectionUpsert, MapData, MapNeighborOut, MapOut,
                         MapUpdate, MessageResponse)
from core_system.services.map_service import create_map_service, delete_map_service, fetch_maps, get_map_by_id

router = APIRouter(prefix="/maps", tags=["Maps"])

# -------------------------- Map CRUD APIs -------------------------- #


@router.get(
    "/",
    response_model=ListMapsResponse,
    summary="列出地圖 (分頁)",
    description="""
使用 cursor-based 分頁來獲取地圖列表。

- **next_id**: 提供上次請求回傳的 `last_id` 來獲取下一頁。
- **prev_id**: 提供列表第一項的 ID 來獲取上一頁 (如果有的話)。
- 同時提供 `prev_id` 和 `next_id` 是不合法的，會優先使用 `prev_id`。
""",
)
def get_map_list(
    prev_id: Optional[int] = Query(None),
    next_id: Optional[int] = Query(None, description="從此 ID 之後的項目"),
    limit: int = Query(20, ge=1, le=100, description="每頁項目數"),
    db: Session = Depends(get_db)
):
    direction = "prev" if prev_id else "next"
    started_id = prev_id if prev_id else next_id
    fetch_limit = limit + 1

    maps = fetch_maps(db, started_id, fetch_limit, direction)
    has_more = len(maps) == fetch_limit

    if has_more:
        maps.pop()

    last_id = maps[-1].id if maps else None

    return ListMapsResponse(
        last_id=last_id,
        map_list=[
            MapData(
                map_id=map_item.id,
                name=map_item.name,
                description=map_item.description
            ) for map_item in maps
        ]
    )


@router.post(
    "/",
    status_code=201,
    summary="建立新地圖",
    description="批量建立一或多個新地圖。",
    response_model=CreateMapResponse,
)
def create_map(data: CreateMapRequest, db: Session = Depends(get_db)):
    created_maps = []
    for map_data in data.map_datas:
        new_map = create_map_service(
            db=db,
            name=map_data.name,
            description=map_data.description,
            image_url=map_data.image_url
        )
        created_maps.append(CreatedMapInfo(id=new_map.id, name=new_map.name))
    db.commit()
    return CreateMapResponse(message="Maps created successfully", created_maps=created_maps)


@router.get(
    "/{map_id}",
    response_model=MapOut,
    summary="取得單一地圖詳細資訊",
    description="根據地圖 ID 獲取其詳細資料，包含相鄰的地圖及其連線狀態。",
    responses={404: {"description": "找不到指定 ID 的地圖"}},
)
def get_map_details(map_id: int, db: Session = Depends(get_db)):
    map_obj = get_map_by_id(db=db, map_id=map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")

    return build_map_out_response(map_obj)


# -------------------------- Map Feature APIs -------------------------- #


@router.patch(
    "/{map_id}/events",
    response_model=List[EventAssociationOut],
    summary="更新地圖的事件關聯",
    description="""
批量更新地圖與事件的關聯。

- **upsert**: 新增或更新事件關聯，包含其出現機率。
- **remove**: 根據 event ID 列表移除關聯。
- **normalize**: 如果設為 `true`，操作完成後會將所有剩餘事件的機率總和正規化為 1。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖"},
        400: {"description": "請求無效 (例如：事件 ID 不存在、upsert 和 remove 中有重複的 ID)"},
    },
)
def update_map_events(
    map_id: int,
    payload: EventAssociationsUpdate,
    session: Session = Depends(get_db),
):
    map_obj = session.get(Map, map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")

    # Upsert
    if payload.upsert:
        for ev in payload.upsert:
            # 驗證 event 存在
            event_obj = session.get(Event, ev.event_id)
            if not event_obj:
                raise HTTPException(
                    status_code=400, detail=f"Event id {ev.event_id} does not exist")
            existing = (
                session.query(MapEventAssociation)
                .filter_by(map_id=map_obj.id, event_id=ev.event_id)
                .one_or_none()
            )
            if existing:
                existing.probability = ev.probability
            else:
                new_assoc = MapEventAssociation(
                    map=map_obj,
                    event=event_obj,
                    probability=ev.probability,
                )
                session.add(new_assoc)

    # Remove
    if payload.remove:
        for eid in payload.remove:
            assoc = (
                session.query(MapEventAssociation)
                .filter_by(map_id=map_obj.id, event_id=eid)
                .one_or_none()
            )
            if assoc:
                session.delete(assoc)

    # Optional normalization: 將所有 probability 總和調整成 1（如果需要）
    if payload.normalize:
        assocs = (
            session.query(MapEventAssociation)
            .filter_by(map_id=map_obj.id)
            .all()
        )
        total = sum(a.probability for a in assocs)
        if total > 0:
            for a in assocs:
                a.probability = a.probability / total

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400, detail="Failed to update event associations")

    session.refresh(map_obj)

    # 回傳目前的 associations
    out = []
    for assoc in map_obj.event_associations:
        event_obj = assoc.event  # 假設 relationship
        out.append(
            EventAssociationOut(
                event_id=event_obj.id,
                event_name=event_obj.name,
                probability=assoc.probability,
            )
        )
    return out


@router.patch(
    "/{map_id}",
    response_model=MapOut,
    summary="更新地圖基本屬性",
    description="""
只更新地圖的基本屬性：名稱 / 敘述 / 圖片 URL，不處理鄰居連線。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖"},
        400: {"description": "更新失敗 (例如違反資料完整性)"},
    },
)
def patch_map_basic(
    map_id: int,
    payload: MapUpdate,  # 只會用到 name/description/image_url
    session: Session = Depends(get_db),
):
    map_obj = session.get(Map, map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")

    if payload.name is not None:
        map_obj.name = payload.name
    if payload.description is not None:
        map_obj.description = payload.description
    if payload.image_url is not None:
        map_obj.image_url = payload.image_url

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400, detail="Failed to update map basic attributes")

    session.refresh(map_obj)

    # 組 neighbors（維持原本輸出格式）
    neighbors_out = []
    for conn in map_obj.connections_a:
        neighbor_map = conn.map_b
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )
    for conn in map_obj.connections_b:
        neighbor_map = conn.map_a
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )

    return MapOut(
        id=map_obj.id,
        name=map_obj.name,
        description=map_obj.description,
        image_url=map_obj.image_url,
        neighbors=neighbors_out,
    )


class ConnectionsUpdate(BaseModel):
    connections: Optional[List[MapConnectionUpsert]] = Field(
        None, description="要新增或更新的鄰居連線"
    )
    remove_connections: Optional[List[int]] = Field(
        None, description="要移除的鄰居地圖 ID"
    )


@router.patch(
    "/{map_id}/connections",
    response_model=List[MapNeighborOut],
    summary="更新地圖鄰居連線（新增/修改/移除）",
    description="""
針對某張地圖的鄰居連線做 upsert 或移除。  
- **connections**: 新增或更新無方向連線（含條件）。  
- **remove_connections**: 移除指定 neighbor 的連線。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖"},
        400: {"description": "連線操作失敗（例如 neighbor 不存在）"},
    },
)
def patch_map_connections(
    map_id: int,
    payload: ConnectionsUpdate,
    session: Session = Depends(get_db),
):
    map_obj = session.get(Map, map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")

    # upsert
    if payload.connections:
        for conn_in in payload.connections:
            if conn_in.neighbor_id == map_obj.id:
                continue  # 跳過自己
            neighbor = session.get(Map, conn_in.neighbor_id)
            if not neighbor:
                raise HTTPException(
                    status_code=400,
                    detail=f"Neighbor map id {conn_in.neighbor_id} does not exist"
                )
            upsert_connection(
                session,
                map_obj,
                neighbor,
                is_locked=conn_in.is_locked,
                required_item=conn_in.required_item,
                required_level=conn_in.required_level,
            )

    # remove
    if payload.remove_connections:
        for nid in payload.remove_connections:
            if nid == map_obj.id:
                continue
            neighbor = session.get(Map, nid)
            if neighbor:
                remove_connection(session, map_obj, neighbor)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400, detail="Failed to update connections")

    session.refresh(map_obj)

    neighbors_out = []
    for conn in map_obj.connections_a:
        neighbor_map = conn.map_b
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )
    for conn in map_obj.connections_b:
        neighbor_map = conn.map_a
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )

    return neighbors_out


@router.delete(
    "/{map_id}",
    status_code=200,
    summary="刪除地圖",
    description="根據 ID 刪除一個地圖。此操作會一併刪除所有與此地圖相關的連線。",
    response_model=MessageResponse,
    responses={404: {"description": "找不到指定 ID 的地圖"}},
)
def remove_map(map_id: int, db: Session = Depends(get_db)):
    if not delete_map_service(db=db, map_id=map_id):
        raise HTTPException(status_code=404, detail="Map not found")
    return MessageResponse(message="Map removed successfully")

# ---------------------- Helper Functions ---------------------- #


def build_map_out_response(map_obj: Map) -> MapOut:
    """Helper to build the MapOut response model from a Map ORM object."""
    neighbors_out: List[MapNeighborOut] = []
    for conn in map_obj.connections_a:
        neighbor_map = conn.map_b
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )
    for conn in map_obj.connections_b:
        neighbor_map = conn.map_a
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )

    events_out: List[EventAssociationOut] = []
    for assoc in map_obj.event_associations:
        events_out.append(
            EventAssociationOut(
                event_id=assoc.event.id,
                event_name=assoc.event.name,
                probability=assoc.probability,
            )
        )

    return MapOut(
        id=map_obj.id,
        name=map_obj.name,
        description=map_obj.description,
        image_url=map_obj.image_url,
        neighbors=neighbors_out,
        events=events_out,
    )


def get_ordered_pair(id1: int, id2: int) -> tuple[int, int]:
    return (id1, id2) if id1 < id2 else (id2, id1)


def upsert_connection(session: Session, map_obj: Map, neighbor: Map, **kwargs) -> MapConnection:
    a, b = (map_obj, neighbor) if map_obj.id < neighbor.id else (
        neighbor, map_obj)
    conn = (
        session.query(MapConnection)
        .filter_by(map_a_id=a.id, map_b_id=b.id)
        .one_or_none()
    )
    if conn is None:
        conn = MapConnection(map_a=a, map_b=b, **kwargs)
        session.add(conn)
    else:
        for key, val in kwargs.items():
            setattr(conn, key, val)
    return conn


def remove_connection(session: Session, map_obj: Map, neighbor: Map):
    a_id, b_id = get_ordered_pair(map_obj.id, neighbor.id)
    conn = (
        session.query(MapConnection)
        .filter_by(map_a_id=a_id, map_b_id=b_id)
        .one_or_none()
    )
    if conn:
        session.delete(conn)
